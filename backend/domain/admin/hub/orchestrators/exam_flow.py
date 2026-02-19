"""Exam 요청 처리 Orchestrator (LangGraph 기반).

1단계: KoELECTRA(koelectra-small-v3-discriminator) 게이트웨이 분류기로 빠른 분기
- RULE_BASED: 규칙 기반 → `ExamService` (DB 조회)
- POLICY_BASED: 정책 기반 → 의도 분류 후 `ExamAgent` (LLM)
- BLOCK: 도메인 외 → 거절 메시지

2단계: POLICY_BASED인 경우 의도 분류
- DB_QUERY: 명확한 데이터 조회 → 규칙 기반 전략 (ExamService)
- EXPLAIN: 해설 요청 → 정책 기반 전략 (ExamAgent + LLM)
- ADVICE: 학습 상담 → 정책 기반 전략 (RAG + EXAONE)

LangGraph StateGraph로 구현:
- Strategy Pattern 제거
- 노드 기반 워크플로우로 전환
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal, TypedDict

from langgraph.graph import StateGraph, END, START

try:
    from fastmcp import FastMCP
    _FASTMCP_AVAILABLE = True
except ImportError:
    _FASTMCP_AVAILABLE = False
    FastMCP = None

from backend.config import settings
from backend.dependencies import get_db_connection
from backend.domain.admin.models.states.exam_state import ExamProcessingState
from backend.domain.admin.spokes.agents.analysis.entity_extractor import (
    extract_all_entities,
    ExamEntities,
)
from backend.domain.admin.spokes.services.exam_service import ExamService
# ExamAgent 직접 연결 제거 (중앙 MCP 서버를 통한 연결로 전환 예정)
# from backend.domain.admin.spokes.agents.exam_agent import ExamAgent

logger = logging.getLogger(__name__)

# ============================================================================
# FastMCP 서버 초기화 제거: 중앙 MCP 서버 사용
# ============================================================================

# get_koelectra_mcp_server() 함수 제거: 중앙 MCP 서버를 사용하도록 변경됨
# 중앙 MCP 서버는 backend.domain.admin.hub.mcp.get_central_mcp_server()를 통해 접근

# ============================================================================
# KoELECTRA / Intent utilities (통합됨: 기존 spam_detector.py + intent_classifier.py)
# ============================================================================

# transformers/peft/torch는 환경에 따라 없을 수 있어 try-import
try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from peft import PeftModel
    import torch

    _KOELECTRA_AVAILABLE = True
except ImportError:
    _KOELECTRA_AVAILABLE = False


# KoELECTRA spam_prob 기반 임계치 (UserFlow/CommentaryFlow에서 사용)
SPAM_PROB_LOW = 0.35
SPAM_PROB_HIGH = 0.75
SPAM_PROB_AMBIGUOUS = (SPAM_PROB_LOW, SPAM_PROB_HIGH)


# 게이트웨이 레이블 매핑 (학습 데이터셋 기준)
# 0: BLOCK, 1: POLICY_BASED, 2: RULE_BASED
GATEWAY_LABELS = {
    "BLOCK": 0,
    "POLICY_BASED": 1,
    "RULE_BASED": 2,
}
LABEL_TO_GATEWAY = {v: k for k, v in GATEWAY_LABELS.items()}


# 의도 레이블 매핑
INTENT_LABELS = {
    "DB_QUERY": 0,
    "EXPLAIN": 1,
    "ADVICE": 2,
    "OUT_OF_DOMAIN": 3,
}
LABEL_TO_INTENT = {v: k for k, v in INTENT_LABELS.items()}


# 레거시 @tool 함수들 제거됨: 이제 중앙 MCP 서버를 사용합니다.
# 필요한 경우 backend.domain.admin.hub.mcp.get_central_mcp_server()를 통해 접근하세요.


class ExamIntent(TypedDict):
    intent: Literal["DB_QUERY", "EXPLAIN", "ADVICE", "OUT_OF_DOMAIN"]
    confidence: float
    is_complex: bool
    entities_found: List[str]
    missing_entities: List[str]


def generate_clarification_message(missing: List[str]) -> str:
    messages = {
        "year": "연도를 알려주세요. (예: 2024년, 작년)",
        "subject": "과목명을 알려주세요. (예: 회계학, 행정법총론)",
        "question_no": "문항 번호를 알려주세요. (예: 3번)",
        "exam_type": "시험 구분을 알려주세요. (예: 국가직, 지방직)",
        "job_series": "직렬을 알려주세요. (예: 교육행정직, 일반행정직)",
        "grade": "급수를 알려주세요. (예: 9급, 7급)",
    }

    if not missing:
        return ""

    msg_list = [f"• {messages.get(k, k)}" for k in missing if k in messages]
    return "다음 정보를 추가로 알려주세요:\n" + "\n".join(msg_list)


def _get_found_entities(entities: ExamEntities) -> List[str]:
    # entity_extractor의 헬퍼를 그대로 쓰되, import 사이클 회피를 위해 런타임 import
    from backend.domain.admin.spokes.agents.analysis.entity_extractor import get_found_entities
    return get_found_entities(entities)


def _get_missing_entities(entities: ExamEntities) -> List[str]:
    from backend.domain.admin.spokes.agents.analysis.entity_extractor import get_missing_entities
    return get_missing_entities(entities)


def classify_intent_rule_based(text: str, entities: ExamEntities) -> ExamIntent:
    text_lower = text.lower()
    entities_found = _get_found_entities(entities)
    missing_entities = _get_missing_entities(entities)

    out_of_domain_keywords = [
        "날씨", "음식", "배고파", "놀고싶어", "영화", "드라마",
        "게임", "쇼핑", "여행", "운동", "취미",
    ]
    if any(kw in text for kw in out_of_domain_keywords):
        return {
            "intent": "OUT_OF_DOMAIN",
            "confidence": 0.9,
            "is_complex": False,
            "entities_found": entities_found,
            "missing_entities": missing_entities,
        }

    if entities.get("has_all_required", False):
        explain_keywords = ["왜", "이유", "설명", "해설", "원리", "근거", "판례", "적용"]
        advice_keywords = ["어떻게", "방법", "공부", "학습", "합격", "가능", "추천", "계획"]
        has_explain = any(kw in text for kw in explain_keywords)
        has_advice = any(kw in text for kw in advice_keywords)
        if not has_explain and not has_advice:
            return {
                "intent": "DB_QUERY",
                "confidence": 0.9,
                "is_complex": False,
                "entities_found": entities_found,
                "missing_entities": [],
            }

    explain_keywords = [
        "왜", "이유", "설명", "해설", "원리", "근거", "판례", "적용",
        "의미", "개념", "차이", "비교", "관계", "효과",
    ]
    if any(kw in text for kw in explain_keywords):
        return {
            "intent": "EXPLAIN",
            "confidence": 0.8 if entities.get("has_all_required") else 0.6,
            "is_complex": True,
            "entities_found": entities_found,
            "missing_entities": missing_entities,
        }

    advice_keywords = [
        "어떻게", "방법", "공부", "학습", "합격", "가능", "추천", "계획",
        "전략", "팁", "조언", "도움", "준비", "시작",
    ]
    if any(kw in text for kw in advice_keywords):
        return {
            "intent": "ADVICE",
            "confidence": 0.8,
            "is_complex": True,
            "entities_found": entities_found,
            "missing_entities": missing_entities,
        }

    if any([entities.get("year"), entities.get("subject"), entities.get("question_no")]):
        return {
            "intent": "DB_QUERY",
            "confidence": 0.6 if entities.get("has_all_required") else 0.4,
            "is_complex": False,
            "entities_found": entities_found,
            "missing_entities": missing_entities,
        }

    return {
        "intent": "DB_QUERY",
        "confidence": 0.3,
        "is_complex": True,
        "entities_found": entities_found,
        "missing_entities": missing_entities,
    }


async def classify_intent_model_based(text: str, entities: ExamEntities, central_mcp: Any = None) -> ExamIntent:
    """모델 기반 의도 분류 (중앙 MCP 서버 사용)."""
    if central_mcp is None:
        from backend.domain.admin.hub.mcp import get_central_mcp_server
        central_mcp = get_central_mcp_server()

    if central_mcp is None:
        # 폴백: 규칙 기반 분류
        return classify_intent_rule_based(text, entities)

    # 중앙 MCP 서버의 classify_intent 툴 호출
    result = central_mcp._tools["classify_intent"](text)
    intent_id = result.get("predicted_label", 0)
    confidence = result.get("confidence", 0.5)

    intent_map = {0: "DB_QUERY", 1: "EXPLAIN", 2: "ADVICE", 3: "OUT_OF_DOMAIN"}
    intent = intent_map.get(intent_id, "DB_QUERY")

    entities_found = _get_found_entities(entities)
    missing_entities = _get_missing_entities(entities)

    return {
        "intent": intent,  # type: ignore[return-value]
        "confidence": confidence,
        "is_complex": intent_id in [1, 2],
        "entities_found": entities_found,
        "missing_entities": missing_entities,
    }


def _safe_text(text, limit: int = 50) -> str:
    """안전한 텍스트 슬라이싱 헬퍼 함수.

    Args:
        text: 텍스트 (str, dict, 또는 기타 타입)
        limit: 최대 길이

    Returns:
        슬라이싱된 문자열
    """
    if text is None:
        return "N/A"
    if isinstance(text, str):
        return text[:limit] if len(text) > limit else text
    # dict나 다른 타입인 경우 문자열로 변환 후 슬라이싱
    text_str = str(text)
    return text_str[:limit] if len(text_str) > limit else text_str


class ExamFlow:
    """Exam 요청 처리 Orchestrator (LangGraph 기반)."""

    def __init__(self):
        """초기화."""
        # 중앙 MCP 서버 연결
        from backend.domain.admin.hub.mcp import get_central_mcp_server
        self.central_mcp = get_central_mcp_server()
        if self.central_mcp:
            self.mcp = self.central_mcp.get_mcp_server()
        else:
            self.mcp = None

        self._exam_service = ExamService()
        # ExamAgent 직접 연결 제거 (중앙 MCP 서버를 통한 연결로 전환 예정)
        # self._exam_agent = ExamAgent()

        # LangGraph 그래프 빌드
        self._graph = self._build_graph()

        logger.info("[ExamFlow] ExamFlow 초기화 완료 (중앙 MCP 서버 사용)")

    async def _call_central_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """중앙 MCP 서버의 툴을 호출합니다."""
        if self.central_mcp is None:
            return {
                "success": False,
                "error": "중앙 MCP 서버가 초기화되지 않았습니다."
            }
        try:
            result = await self.central_mcp.call_tool(tool_name, **kwargs)
            return result
        except Exception as e:
            logger.error(f"[ExamFlow] 중앙 MCP 툴 호출 실패: {tool_name}, {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph 빌드."""
        graph = StateGraph(ExamProcessingState)

        # 노드 추가
        graph.add_node("validate", self._validate_node)
        graph.add_node("gateway_classify", self._gateway_classify_node)
        graph.add_node("determine_strategy", self._determine_strategy_node)
        graph.add_node("rule_process", self._rule_process_node)
        graph.add_node("policy_process", self._policy_process_node)
        graph.add_node("finalize", self._finalize_node)

        # 엣지 추가
        graph.add_edge(START, "validate")
        graph.add_edge("validate", "gateway_classify")
        graph.add_conditional_edges(
            "gateway_classify",
            self._route_gateway,
            {
                "rule_based": "rule_process",
                "block": "finalize",
                "policy_based": "determine_strategy",
            }
        )
        graph.add_conditional_edges(
            "determine_strategy",
            self._route_strategy,
            {
                "rule_based": "rule_process",
                "policy_based": "policy_process",
            }
        )
        graph.add_edge("rule_process", "finalize")
        graph.add_edge("policy_process", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    async def _validate_node(self, state: ExamProcessingState) -> ExamProcessingState:
        """데이터 검증 노드."""
        logger.info(f"[ExamFlow] 검증 노드 진입 - request_text type={type(state.get('request_text')).__name__}")

        request_text = state.get("request_text", "")

        # request_text를 반드시 문자열로 보장
        if not isinstance(request_text, str):
            logger.warning(f"[ExamFlow] request_text가 str이 아님: {type(request_text).__name__}, 변환 시도")
            if isinstance(request_text, dict):
                request_text = request_text.get("question", str(request_text))
            else:
                request_text = str(request_text)
            logger.info(f"[ExamFlow] request_text 변환 완료: {_safe_text(request_text, 100)}")

        return {
            **state,
            "request_text": request_text,
        }

    async def _gateway_classify_node(self, state: ExamProcessingState) -> ExamProcessingState:
        """게이트웨이 분류 노드."""
        request_text = state.get("request_text", "")

        # 게이트웨이 호출
        loop = asyncio.get_event_loop()
        try:
            if not isinstance(request_text, str):
                raise TypeError(f"게이트웨이 호출 전 request_text는 str이어야 합니다. 현재 타입: {type(request_text).__name__}")

            # 중앙 MCP 서버 사용
            gateway_result = await self._call_central_tool("classify_gateway", text=request_text)
            gateway = gateway_result.get("gateway", "POLICY_BASED")
            gateway_confidence = gateway_result.get("confidence", 0.5)

            logger.info(
                f"[ExamFlow] 게이트웨이 분류: {gateway}, "
                f"신뢰도: {gateway_confidence:.2f}"
            )
        except Exception as e:
            logger.warning(f"[ExamFlow] 게이트웨이 분류 오류, POLICY_BASED로 폴백: {e}")
            gateway = "POLICY_BASED"
            gateway_confidence = 0.5

        return {
            **state,
            "gateway": gateway,
            "gateway_confidence": gateway_confidence,
            "koelectra_result": {"gateway": gateway, "confidence": gateway_confidence},
        }

    def _route_gateway(self, state: ExamProcessingState) -> str:
        """게이트웨이 결과에 따른 라우팅."""
        gateway = state.get("gateway", "POLICY_BASED")

        if gateway == "RULE_BASED":
            logger.info("[ExamFlow] RULE_BASED → 규칙 기반 처리로 라우팅")
            return "rule_based"
        elif gateway == "BLOCK":
            logger.info("[ExamFlow] BLOCK → 차단 처리로 라우팅")
            return "block"
        else:  # POLICY_BASED
            logger.info("[ExamFlow] POLICY_BASED → 의도 분류로 라우팅")
            return "policy_based"

    async def _determine_strategy_node(self, state: ExamProcessingState) -> ExamProcessingState:
        """전략 판단 노드 (의도 분류 + 엔티티 추출)."""
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})

        # 엔티티 추출
        conn = get_db_connection()
        entities = extract_all_entities(request_text, conn)

        # 의도 분류
        if settings.KOELECTRA_INTENT_LORA_PATH and settings.USE_MODEL_BASED_INTENT:
            try:
                intent_result = await classify_intent_model_based(request_text, entities, self.central_mcp)
                logger.info("[ExamFlow] 모델 기반 의도 분류 사용")
            except Exception as e:
                logger.warning(f"[ExamFlow] 모델 기반 의도 분류 오류, 규칙 기반으로 폴백: {e}")
                intent_result = classify_intent_rule_based(request_text, entities)
        else:
            intent_result = classify_intent_rule_based(request_text, entities)
            logger.info("[ExamFlow] 규칙 기반 의도 분류 사용")

        logger.info(
            f"[ExamFlow] 의도: {intent_result['intent']}, "
            f"신뢰도: {intent_result['confidence']:.2f}, "
            f"복잡도: {intent_result['is_complex']}, "
            f"엔티티: {intent_result['entities_found']}"
        )

        # 전략 판단: DB_QUERY는 규칙 기반, EXPLAIN/ADVICE는 정책 기반
        if intent_result["intent"] == "DB_QUERY":
            strategy = "rule_based"
        else:
            strategy = "policy_based"

        # koelectra_result 업데이트
        koelectra_result = state.get("koelectra_result", {})
        koelectra_result.update({
            "intent": intent_result,
            "entities": entities,
        })

        return {
            **state,
            "intent_result": intent_result,
            "entities": entities,
            "strategy": strategy,
            "koelectra_result": koelectra_result,
        }

    def _route_strategy(self, state: ExamProcessingState) -> str:
        """전략에 따른 라우팅."""
        strategy = state.get("strategy", "policy_based")
        return strategy

    async def _rule_process_node(self, state: ExamProcessingState) -> ExamProcessingState:
        """규칙 기반 처리 노드 (ExamService)."""
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})
        koelectra_result = state.get("koelectra_result", {})

        # 엔티티가 아직 추출되지 않은 경우 추출
        if "entities" not in koelectra_result or not koelectra_result.get("entities"):
            conn = get_db_connection()
            entities = extract_all_entities(request_text, conn)
            koelectra_result["entities"] = entities
            logger.info("[ExamFlow] 규칙 기반 처리 노드에서 엔티티 추출 완료")

        logger.info("[ExamFlow] 규칙 기반 처리 노드 실행 → ExamService")

        try:
            result = await self._exam_service.handle_request(request_data, koelectra_result)
            return {
                **state,
                "result": result,
                "koelectra_result": koelectra_result,
            }
        except Exception as e:
            logger.error(f"[ExamFlow] 규칙 기반 처리 오류: {e}", exc_info=True)
            return {
                **state,
                "result": {
                    "success": False,
                    "error": str(e),
                },
                "error": str(e),
            }

    async def _policy_process_node(self, state: ExamProcessingState) -> ExamProcessingState:
        """정책 기반 처리 노드 (ExamAgent 직접 연결 제거됨)."""
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})
        koelectra_result = state.get("koelectra_result", {})

        logger.warning("[ExamFlow] 정책 기반 처리 노드: ExamAgent 직접 연결이 제거되었습니다. 중앙 MCP 서버를 통한 연결이 필요합니다.")

        # ExamAgent 직접 연결 제거됨 (중앙 MCP 서버를 통한 연결로 전환 예정)
        result = {
            "success": False,
            "method": "policy_based",
            "error": "정책 기반 처리가 아직 구현되지 않았습니다. 중앙 MCP 서버를 통한 ExamAgent 연결이 필요합니다.",
            "request_text": request_text,
            "request_data": request_data,
            "koelectra_result": koelectra_result,
        }

        return {
            **state,
            "result": result,
        }

    async def _finalize_node(self, state: ExamProcessingState) -> ExamProcessingState:
        """최종 정리 노드."""
        gateway = state.get("gateway", "")

        # BLOCK인 경우 특별 처리
        if gateway == "BLOCK":
            request_text = state.get("request_text", "")
            request_text_safe = _safe_text(request_text, limit=50)
            logger.info(f"[ExamFlow] BLOCK 요청: {request_text_safe}...")

            result = {
                "success": False,
                "method": "gateway_block",
                "gateway": "BLOCK",
                "error": "공무원 시험 및 학습 관련 질문에만 답변을 드릴 수 있습니다.",
                "user_message": (
                    "공무원 시험 관련 질문을 해주시면 도와드리겠습니다.\n"
                    "예시:\n"
                    "• '2025년 국가직 행정법총론 3번 알려줘'\n"
                    "• '신뢰보호의 원칙이 이 판례에서 왜 적용 안 돼?'\n"
                    "• '직장인인데 하루 4시간 공부로 합격 가능할까?'"
                )
            }
            return {
                **state,
                "result": result,
            }

        # 의도 분류 결과에 따른 처리 (POLICY_BASED 경로에서만 존재)
        intent_result = state.get("intent_result")
        if intent_result:
            intent = intent_result.get("intent", "")

            # OUT_OF_DOMAIN 처리
            if intent == "OUT_OF_DOMAIN":
                request_text = state.get("request_text", "")
                request_text_safe = _safe_text(request_text, limit=50)
                logger.info(f"[ExamFlow] OUT_OF_DOMAIN 요청: {request_text_safe}...")

                result = {
                    "success": False,
                    "method": "out_of_domain",
                    "intent": "OUT_OF_DOMAIN",
                    "error": "공무원 시험 및 학습 관련 질문에만 답변을 드릴 수 있습니다.",
                    "user_message": (
                        "공무원 시험 관련 질문을 해주시면 도와드리겠습니다.\n"
                        "예시:\n"
                        "• '작년 회계학 3번 정답 뭐야?'\n"
                        "• '신뢰보호의 원칙이 이 판례에서 왜 적용 안 돼?'\n"
                        "• '직장인인데 하루 4시간 공부로 합격 가능할까?'"
                    )
                }
                return {
                    **state,
                    "result": result,
                }

            # DB_QUERY에서 필수 엔티티 누락 처리
            if intent == "DB_QUERY":
                entities = state.get("entities", {})
                if not entities.get("has_all_required", False):
                    missing = intent_result.get("missing_entities", [])
                    suggestion = generate_clarification_message(missing)

                    logger.warning(
                        f"[ExamFlow] DB_QUERY 실패: 필수 엔티티 누락 - {missing}"
                    )

                    result = {
                        "success": False,
                        "method": "rule_based",
                        "intent": "DB_QUERY",
                        "error": f"필수 정보가 누락되었습니다: {', '.join(missing)}",
                        "missing_entities": missing,
                        "suggestion": suggestion,
                        "entities_found": intent_result.get("entities_found", [])
                    }
                    return {
                        **state,
                        "result": result,
                    }

        # 정상 처리 완료
        return state

    async def process_exam_request(
        self, request_text: str, request_data: dict
    ) -> dict:
        """게이트웨이 + 의도 기반 요청 처리.

        Args:
            request_text: 사용자 요청 텍스트
            request_data: 요청 데이터 (question 등)

        Returns:
            처리 결과 딕셔너리
        """
        # 요청이 exam_router.py를 통해 여기까지 전달되었는지 빠르게 확인하기 위한 출력
        # (Windows/서버 로그에서 쉽게 보이도록 print 사용)
        try:
            print(f"[ExamFlow] 수신 질문: {request_text}", flush=True)
        except Exception:
            pass

        # 초기 상태 설정
        initial_state: ExamProcessingState = {
            "request_text": request_text,
            "request_data": request_data,
            "koelectra_result": None,
            "result": None,
            "error": None,
            "metadata": None,
            "gateway": None,
            "gateway_confidence": None,
            "intent_result": None,
            "entities": None,
            "strategy": None,
        }

        # LangGraph 실행
        logger.info("[ExamFlow] LangGraph 실행 시작")
        try:
            final_state = await self._graph.ainvoke(initial_state)
            logger.info("[ExamFlow] LangGraph 실행 완료")

            result = final_state.get("result")
            if result is None:
                return {
                    "success": False,
                    "error": "처리 결과가 없습니다.",
                }
            return result
        except Exception as e:
            logger.error(f"[ExamFlow] LangGraph 실행 오류: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    async def process_jsonl_data(
        self, jsonl_data: List[Dict[str, Any]], category: str, filename: str
    ) -> dict:
        """JSONL 데이터 처리 (라우터에서 전달받은 데이터).

        Args:
            jsonl_data: 파싱된 JSONL 데이터 리스트
            category: 파일 카테고리 (exam, commentary, user)
            filename: 파일명

        Returns:
            처리 결과
        """
        import json

        logger.info("=" * 80)
        logger.info(f"[ExamFlow] JSONL 데이터 수신: filename={filename}, category={category}")
        logger.info(f"[ExamFlow] 총 데이터 개수: {len(jsonl_data)}")

        # 상위 5개 데이터 출력
        top_5 = jsonl_data[:5]
        logger.info("[ExamFlow] 상위 5개 데이터 내용:")
        for idx, item in enumerate(top_5, start=1):
            # JSON 형식으로 예쁘게 출력
            try:
                item_str = json.dumps(item, ensure_ascii=False, indent=2)
                logger.info(f"  [{idx}] {item_str}")
            except Exception as e:
                logger.warning(f"  [{idx}] 데이터 직렬화 실패: {e}, 원본: {item}")

        logger.info("=" * 80)

        # category가 "commentary"인 경우 별도 라우터로 리다이렉트
        if category == "commentary":
            logger.warning(
                "[ExamFlow] category='commentary'는 CommentaryRouter를 사용하세요."
            )
            return {
                "success": False,
                "message": "commentary 카테고리는 /api/v1/admin/commentaries/upload-jsonl 엔드포인트를 사용하세요.",
                "category": category,
                "filename": filename,
                "total_items": len(jsonl_data),
            }

        # category가 "exam"인 경우 exam_questions 테이블에 추가
        if category == "exam":
            logger.info("[ExamFlow] exam 카테고리 감지 → ExamService로 데이터 추가 요청")
            try:
                insert_result = self._exam_service.process_jsonl_to_exam_questions(
                    jsonl_data=jsonl_data,
                    category=category
                )
                logger.info(
                    f"[ExamFlow] DB 삽입 결과: success={insert_result.get('success', False)}, "
                    f"inserted={insert_result.get('inserted_count', 0)}, "
                    f"skipped={insert_result.get('skipped_count', 0)}"
                )
                return {
                    "success": insert_result.get("success", False),
                    "message": insert_result.get("message", "처리 완료"),
                    "category": category,
                    "filename": filename,
                    "total_items": len(jsonl_data),
                    "top_5_items": top_5,
                    "inserted_count": insert_result.get("inserted_count", 0),
                    "skipped_count": insert_result.get("skipped_count", 0),
                    "conversion_errors": insert_result.get("conversion_errors", []),
                    "insertion_errors": insert_result.get("insertion_errors", [])
                }
            except Exception as e:
                logger.error(f"[ExamFlow] DB 삽입 중 오류 발생: {e}", exc_info=True)
                return {
                    "success": False,
                    "message": f"DB 삽입 중 오류: {str(e)}",
                    "category": category,
                    "filename": filename,
                    "total_items": len(jsonl_data),
                    "top_5_items": top_5
                }
        else:
            logger.info(f"[ExamFlow] category '{category}'는 처리하지 않습니다.")

        return {
            "success": True,
            "message": f"JSONL 데이터 {len(jsonl_data)}개 수신 완료 (상위 5개 출력)",
            "category": category,
            "filename": filename,
            "total_items": len(jsonl_data),
            "top_5_items": top_5
        }
