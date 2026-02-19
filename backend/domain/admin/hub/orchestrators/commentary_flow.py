"""Commentary 요청 처리 Orchestrator (LangGraph 기반).

KoELECTRA 모델을 사용하여 규칙 기반/정책 기반 분기:
- 규칙 기반: 명확한 경우 → commentary_service.py
- 정책 기반: 애매한 경우 → commentary_agent.py

LangGraph StateGraph로 구현:
- 노드 기반 워크플로우로 전환
"""

import asyncio
from typing import Dict, List, Any

from langgraph.graph import StateGraph, END, START

from backend.domain.admin.models.states.commentary_state import CommentaryProcessingState
from backend.domain.admin.hub.mcp import get_central_mcp_server
from backend.domain.admin.spokes.services.commentary_service import CommentaryService
from backend.domain.admin.spokes.agents.commentary_agent import CommentaryAgent


class CommentaryFlow:
    """Commentary 요청 처리 Orchestrator (LangGraph 기반)."""

    # KoELECTRA 임계치 설정
    RULE_BASED_THRESHOLD_LOW = 0.3  # 이하: 규칙 기반 (commentary_service)
    RULE_BASED_THRESHOLD_HIGH = 0.8  # 이상: 규칙 기반 (commentary_service)
    POLICY_BASED_THRESHOLD = (RULE_BASED_THRESHOLD_LOW, RULE_BASED_THRESHOLD_HIGH)  # 애매한 구간: 정책 기반 (commentary_agent)

    def __init__(self):
        """초기화."""
        # 중앙 MCP 서버 연결
        self.central_mcp = get_central_mcp_server()

        self._commentary_service = CommentaryService()
        self._commentary_agent = CommentaryAgent()

        # LangGraph 그래프 빌드
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph 빌드."""
        graph = StateGraph(CommentaryProcessingState)

        # 노드 추가
        graph.add_node("validate", self._validate_node)
        graph.add_node("koelectra_analyze", self._koelectra_analyze_node)
        graph.add_node("determine_strategy", self._determine_strategy_node)
        graph.add_node("rule_process", self._rule_process_node)
        graph.add_node("policy_process", self._policy_process_node)
        graph.add_node("finalize", self._finalize_node)

        # 엣지 추가
        graph.add_edge(START, "validate")
        graph.add_edge("validate", "koelectra_analyze")
        graph.add_edge("koelectra_analyze", "determine_strategy")
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

    async def _validate_node(self, state: CommentaryProcessingState) -> CommentaryProcessingState:
        """데이터 검증 노드."""
        return state

    async def _koelectra_analyze_node(self, state: CommentaryProcessingState) -> CommentaryProcessingState:
        """KoELECTRA 분석 노드."""
        request_text = state.get("request_text", "")

        # 중앙 MCP 서버의 filter_spam 툴 호출
        if self.central_mcp:
            koelectra_result = await self.central_mcp.call_tool("filter_spam", text=request_text)
        else:
            # 폴백: 기본값 반환
            koelectra_result = {
                "spam_prob": 0.5,
                "label": "uncertain",
                "confidence": "low",
                "method": "unavailable",
                "threshold_zone": "ambiguous",
            }

        spam_prob = koelectra_result.get("spam_prob", 0.5)
        label = koelectra_result.get("label", "uncertain")
        confidence = koelectra_result.get("confidence", "low")

        print(
            f"[CommentaryFlow] KoELECTRA 결과: spam_prob={spam_prob:.2f}, "
            f"label={label}, confidence={confidence}",
            flush=True,
        )

        return {
            **state,
            "spam_prob": spam_prob,
            "label": label,
            "confidence": confidence,
            "koelectra_result": koelectra_result,
        }

    async def _determine_strategy_node(self, state: CommentaryProcessingState) -> CommentaryProcessingState:
        """전략 판단 노드."""
        spam_prob = state.get("spam_prob", 0.5)

        # 규칙/정책 분기 판단
        if spam_prob < self.RULE_BASED_THRESHOLD_LOW or spam_prob > self.RULE_BASED_THRESHOLD_HIGH:
            strategy = "rule_based"
            print("[CommentaryFlow] 규칙 기반 처리로 판단", flush=True)
        else:
            strategy = "policy_based"
            print("[CommentaryFlow] 정책 기반 처리로 판단", flush=True)

        return {
            **state,
            "strategy": strategy,
        }

    def _route_strategy(self, state: CommentaryProcessingState) -> str:
        """전략에 따른 라우팅."""
        strategy = state.get("strategy", "policy_based")
        return strategy

    async def _rule_process_node(self, state: CommentaryProcessingState) -> CommentaryProcessingState:
        """규칙 기반 처리 노드 (commentary_service)."""
        request_data = state.get("request_data", {})
        koelectra_result = state.get("koelectra_result", {})

        print("[CommentaryFlow] 규칙 기반 처리로 라우팅 → commentary_service", flush=True)

        try:
            result = await self._commentary_service.handle_request(request_data, koelectra_result)
            return {
                **state,
                "result": result,
            }
        except Exception as e:
            print(f"[CommentaryFlow] 규칙 기반 처리 오류: {e}", flush=True)
            return {
                **state,
                "result": {
                    "success": False,
                    "error": str(e),
                },
                "error": str(e),
            }

    async def _policy_process_node(self, state: CommentaryProcessingState) -> CommentaryProcessingState:
        """정책 기반 처리 노드 (commentary_agent)."""
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})
        koelectra_result = state.get("koelectra_result", {})

        print("[CommentaryFlow] 정책 기반 처리로 라우팅 → commentary_agent", flush=True)

        try:
            result = await self._commentary_agent.handle_request(request_text, request_data, koelectra_result)
            return {
                **state,
                "result": result,
            }
        except Exception as e:
            print(f"[CommentaryFlow] 정책 기반 처리 오류: {e}", flush=True)
            return {
                **state,
                "result": {
                    "success": False,
                    "error": str(e),
                },
                "error": str(e),
            }

    async def _finalize_node(self, state: CommentaryProcessingState) -> CommentaryProcessingState:
        """최종 정리 노드."""
        return state

    async def process_commentary_request(
        self, request_text: str, request_data: dict
    ) -> dict:
        """Commentary 요청을 처리한다.

        Args:
            request_text: 사용자 요청 텍스트 (KoELECTRA 분석용)
            request_data: 요청 데이터 (user_id, exam_question_id, body 등)

        Returns:
            처리 결과 딕셔너리
        """
        # 초기 상태 설정
        initial_state: CommentaryProcessingState = {
            "request_text": request_text,
            "request_data": request_data,
            "koelectra_result": None,
            "result": None,
            "error": None,
            "metadata": None,
            "spam_prob": None,
            "label": None,
            "confidence": None,
            "strategy": None,
        }

        # LangGraph 실행
        print("[CommentaryFlow] LangGraph 실행 시작", flush=True)
        try:
            final_state = await self._graph.ainvoke(initial_state)
            print("[CommentaryFlow] LangGraph 실행 완료", flush=True)

            result = final_state.get("result")
            if result is None:
                return {
                    "success": False,
                    "error": "처리 결과가 없습니다.",
                }
            return result
        except Exception as e:
            print(f"[CommentaryFlow] LangGraph 실행 오류: {e}", flush=True)
            import traceback
            traceback.print_exc()
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
            category: 파일 카테고리 (commentary)
            filename: 파일명

        Returns:
            처리 결과
        """
        import json
        import logging

        logger = logging.getLogger(__name__)

        logger.info("=" * 80)
        logger.info(f"[CommentaryFlow] JSONL 데이터 수신: filename={filename}, category={category}")
        logger.info(f"[CommentaryFlow] 총 데이터 개수: {len(jsonl_data)}")

        # 상위 5개 데이터 출력
        top_5 = jsonl_data[:5]
        logger.info("[CommentaryFlow] 상위 5개 데이터 내용:")
        for idx, item in enumerate(top_5, start=1):
            try:
                item_str = json.dumps(item, ensure_ascii=False, indent=2)
                logger.info(f"  [{idx}] {item_str}")
            except Exception as e:
                logger.warning(f"  [{idx}] 데이터 직렬화 실패: {e}, 원본: {item}")

        logger.info("=" * 80)

        # category가 "commentary"인 경우 commentaries 테이블에 추가
        if category == "commentary":
            logger.info("[CommentaryFlow] commentary 카테고리 감지 → CommentaryService로 데이터 추가 요청")
            try:
                insert_result = await self._commentary_service.process_jsonl_to_commentaries(
                    jsonl_data=jsonl_data,
                    user_id=1,  # 시스템 사용자
                    series=None,  # series는 NULL 허용으로 조회
                )
                logger.info(
                    f"[CommentaryFlow] DB 삽입 결과: success={insert_result.get('success', False)}, "
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
                    "insertion_errors": insert_result.get("insertion_errors", []),
                }
            except Exception as e:
                logger.error(f"[CommentaryFlow] DB 삽입 중 오류 발생: {e}", exc_info=True)
                return {
                    "success": False,
                    "message": f"DB 삽입 중 오류: {str(e)}",
                    "category": category,
                    "filename": filename,
                    "total_items": len(jsonl_data),
                    "top_5_items": top_5,
                }
        else:
            logger.info(f"[CommentaryFlow] category '{category}'는 commentaries 테이블에 추가하지 않습니다.")

        return {
            "success": True,
            "message": f"JSONL 데이터 {len(jsonl_data)}개 수신 완료 (상위 5개 출력)",
            "category": category,
            "filename": filename,
            "total_items": len(jsonl_data),
            "top_5_items": top_5,
        }
