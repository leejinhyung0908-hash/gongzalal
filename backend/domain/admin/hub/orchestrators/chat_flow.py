"""Chat 요청 처리 Orchestrator (LangGraph 기반).

종합 라우터 역할:
- KoELECTRA 1차 분류 (BLOCK/POLICY_BASED/RULE_BASED) → 키워드 2차 세분화
- 각 도메인 Flow로 라우팅
- 일반 채팅은 RAG/EXAONE 처리

멀티턴 대화 지원:
- Upstash Redis에서 대화 이력 로드/저장
- Query Rewriter로 맥락 반영된 검색 쿼리 재구성
- context_summary 자동 갱신

LangGraph StateGraph:
- START → validate → load_history → rewrite_query
        → koelectra_classify → classify_detail → route_xxx
        → save_history → finalize → END
"""

import logging
from typing import Dict, Any, Optional, List, Tuple

from langgraph.graph import StateGraph, END, START

from backend.domain.admin.models.states.chat_state import ChatProcessingState
from backend.domain.admin.hub.orchestrators.exam_flow import ExamFlow
from backend.domain.admin.hub.orchestrators.question_flow import QuestionFlow
from backend.domain.admin.hub.orchestrators.study_plan_flow import StudyPlanFlow
from backend.domain.admin.hub.orchestrators.solving_log_flow import SolvingLogFlow
from backend.domain.admin.hub.orchestrators.audio_note_flow import AudioNoteFlow
from backend.domain.admin.spokes.agents.retrieval.mentoring_rag import (
    process_mentoring_rag,
)
from backend.domain.admin.spokes.agents.retrieval.query_rewriter import (
    rewrite_query,
    generate_context_summary,
)
from backend.api.v1.shared.redis import (
    is_redis_available,
    get_chat_history,
    store_chat_message,
    update_context_summary as redis_update_context_summary,
)

logger = logging.getLogger(__name__)

# ============================================================================
# KoELECTRA 신뢰도 임계값
# ============================================================================
KOELECTRA_CONFIDENCE_THRESHOLD = 0.7  # 이 이상이면 KoELECTRA 결과 신뢰

# 운동·건강 등 라이프스타일 질문은 "일정/계획" 키워드보다 우선하여 멘토링 RAG로 보냄
_LIFESTYLE_MENTORING_KEYWORDS = [
    "운동", "헬스", "건강", "스트레칭", "수면", "루틴", "다이어트", "체력",
    "헬스장", "근력", "유산소", "근육",
]


def _mentions_lifestyle_mentoring(text_lower: str) -> bool:
    return any(kw in text_lower for kw in _LIFESTYLE_MENTORING_KEYWORDS)


# ============================================================================
# KoELECTRA 게이트웨이 분류 함수
# ============================================================================

def _call_koelectra_gateway(text: str) -> Dict[str, Any]:
    """KoELECTRA 게이트웨이 분류기를 호출합니다.

    MCP 서버의 classify_gateway 툴을 사용하여
    BLOCK(0) / POLICY_BASED(1) / RULE_BASED(2)로 분류합니다.

    Returns:
        {
            "gateway": "BLOCK" | "POLICY_BASED" | "RULE_BASED",
            "confidence": float,
            "method": "koelectra_gateway" | "unavailable" | "error",
        }
    """
    try:
        from backend.domain.admin.hub.mcp import call_koelectra_gateway_classifier
        result = call_koelectra_gateway_classifier(text)
        return result
    except Exception as e:
        logger.warning(f"[KoELECTRA] 게이트웨이 분류 호출 실패: {e}")
        return {
            "gateway": "POLICY_BASED",
            "confidence": 0.0,
            "method": "error",
        }


# ============================================================================
# 2차 키워드 세분화 함수 (RULE_BASED / POLICY_BASED 내 세부 라우팅)
# ============================================================================

def _classify_rule_based_detail(text: str) -> str:
    """RULE_BASED (DB 직접 조회) 내에서 세부 라우팅.

    KoELECTRA가 RULE_BASED로 판단한 질문을 키워드로 세분화합니다.

    Returns:
        "exam" | "question" | "solving_log"
    """
    text_lower = text.lower()

    # 풀이 기록/오답 노트 키워드
    solving_log_keywords = ["오답", "틀린 문제", "풀이 기록", "정답률", "내 성적", "학습 통계"]
    if any(kw in text_lower for kw in solving_log_keywords):
        return "solving_log"

    # 기본적으로 RULE_BASED = DB 조회 = exam
    return "exam"


def _classify_policy_based_detail(text: str) -> str:
    """POLICY_BASED (LLM 추론 필요) 내에서 세부 라우팅.

    KoELECTRA가 POLICY_BASED로 판단한 질문을 키워드로 세분화합니다.

    Returns:
        "study_plan" | "mentoring" | "audio_note" | "chat"
    """
    text_lower = text.lower()

    # 오디오 관련 키워드
    audio_keywords = ["음성", "오디오", "듣기", "tts", "읽어"]
    if any(kw in text_lower for kw in audio_keywords):
        return "audio_note"

    if _mentions_lifestyle_mentoring(text_lower):
        return "mentoring"

    # 학습 계획 조회/생성 관련 키워드 (단독 "일정"/"스케줄"은 운동 일정 등과 혼동되므로 제외)
    study_plan_keywords = [
        "학습 계획", "공부 계획", "계획 세워",
        "계획 짜", "플랜", "플랜 세워", "플랜 짜",
        "학습 일정", "공부 일정", "시험 일정", "학습 스케줄", "공부 스케줄",
        "약점 분석", "취약 분석", "성적 분석", "학습 분석",
        # 학습계획 조회 관련 (띄어쓰기 없는 형태 포함)
        "학습계획", "내 계획", "내 학습", "학습플랜",
        "계획 조회", "계획 보여", "계획 확인", "계획 알려",
        "ai 플랜", "ai플랜", "ai 계획",
    ]
    if any(kw in text_lower for kw in study_plan_keywords):
        return "study_plan"

    # 기본적으로 POLICY_BASED = 멘토링 RAG (합격 수기 기반 답변)
    return "mentoring"


# ============================================================================
# 멀티턴 대화: 후속 질문 판별 (참조어 기반)
# ============================================================================

# 이전 대화를 참조하는 표현 패턴
_FOLLOW_UP_PATTERNS = [
    # 대명사 / 지시어
    "다른", "그거", "그것", "이거", "이것", "저거", "저것",
    "그건", "이건", "저건", "그게", "이게", "저게",
    "거기", "여기", "저기",
    # 후속 요청 표현
    "더", "또", "그 외", "그외", "말고", "대신",
    "추가로", "그리고", "그러면", "그럼",
    # 비교 / 대안 요청
    "비교", "차이", "어떤 게", "뭐가",
    # 이전 답변 참조
    "아까", "방금", "위에", "앞에서",
    "말한", "말했던", "알려준", "추천한", "추천해준",
    # 축약형 후속 질문 (주어 생략)
    "없어?", "있어?", "없나?", "있나?",
    "알려줘", "해줘", "해봐",
]


def _is_follow_up_question(text: str) -> bool:
    """질문이 이전 대화를 참조하는 후속 질문인지 판별합니다.

    대명사, 지시어, 후속 표현 등이 포함되어 있으면 True를 반환합니다.
    "다른 교재는?" → True
    "맛집 추천해줘" → False
    """
    text_lower = text.strip()
    for pattern in _FOLLOW_UP_PATTERNS:
        if pattern in text_lower:
            return True
    return False


# ============================================================================
# 순수 키워드 기반 분류 (KoELECTRA 폴백용)
# ============================================================================

def _classify_request_keyword_only(text: str) -> str:
    """순수 키워드 기반 요청 분류 (KoELECTRA 미사용 시 폴백).

    Returns:
        "exam" | "question" | "study_plan" | "solving_log" |
        "mentoring" | "audio_note" | "chat"
    """
    text_lower = text.lower()

    # 풀이 기록/오답 노트 관련 키워드
    solving_log_keywords = ["오답", "틀린 문제", "풀이 기록", "정답률", "내 성적", "학습 통계"]
    if any(kw in text_lower for kw in solving_log_keywords):
        return "solving_log"

    # 오디오 관련 키워드
    audio_keywords = ["음성", "오디오", "듣기", "tts", "읽어"]
    if any(kw in text_lower for kw in audio_keywords):
        return "audio_note"

    # 시험/문제 관련 키워드 (정답 조회, 기출 검색 등)
    exam_keywords = [
        "정답", "작년", "재작년", "번 정답", "번 답",
        "국가직", "지방직", "문항", "25년", "24년",
        "23년", "22년", "21년", "20년", "기출", "몇 번"
    ]
    if any(kw in text_lower for kw in exam_keywords):
        return "exam"

    if _mentions_lifestyle_mentoring(text_lower):
        return "mentoring"

    # 학습 계획 조회/생성 관련 키워드 (단독 "일정"/"전략" 등은 오분류 방지를 위해 구체 구문만)
    study_plan_keywords = [
        "학습 계획", "공부 계획", "계획 세워",
        "계획 짜", "플랜", "플랜 세워", "플랜 짜",
        "학습 일정", "공부 일정", "시험 일정", "학습 스케줄", "공부 스케줄",
        "약점 분석", "취약 분석", "성적 분석", "학습 분석",
        "어떻게 공부", "어떻게 준비", "공부법",
        "과목별", "약점", "취약", "보완",
        "학습 전략", "공부 전략", "시험 전략",
        # 학습계획 조회 관련 (띄어쓰기 없는 형태 포함)
        "학습계획", "내 계획", "내 학습", "학습플랜",
        "계획 조회", "계획 보여", "계획 확인", "계획 알려",
        "ai 플랜", "ai플랜", "ai 계획",
    ]
    if any(kw in text_lower for kw in study_plan_keywords):
        return "study_plan"

    # 멘토링/합격수기/학습방법 관련 키워드 (RAG)
    # 주의: "추천", "팁" 등 너무 넓은 키워드는 도메인 외 질문과 혼동될 수 있으므로
    #       "교재 추천", "인강 추천" 등 도메인 맥락이 포함된 형태로만 사용
    mentoring_keywords = [
        "합격 수기", "합격수기", "멘토링", "합격 후기", "공부 방법",
        "학습 방법", "노베이스", "커리큘럼", "교재 추천", "인강 추천",
        "합격 비결", "합격 전략", "수험 생활", "수험생활",
        "단기 합격", "1년 합격", "독학", "학원", "인강",
        "행정직", "일행직", "일반행정", "교육행정", "세무직",
        "준비 기간", "조언", "교재", "과목 추천", "공부 팁",
        "시험 준비", "수험", "공부", "공무원 준비",
        "동기부여", "슬럼프", "멘탈", "의지",
    ]
    if any(kw in text_lower for kw in mentoring_keywords):
        return "mentoring"

    return "chat"


def _is_exam_related(text: str) -> bool:
    """시험 관련 질문인지 판단 (하위 호환성)."""
    return _classify_request_keyword_only(text) == "exam"


class ChatFlow:
    """Chat 요청 처리 Orchestrator (LangGraph 기반)."""

    def __init__(self):
        """초기화."""
        # 도메인별 Flow 인스턴스
        self._exam_flow = ExamFlow()
        self._question_flow = QuestionFlow()
        self._study_plan_flow = StudyPlanFlow()
        self._solving_log_flow = SolvingLogFlow()
        self._audio_note_flow = AudioNoteFlow()
        # commentary_flow, user_flow는 기존 것 사용

        # LangGraph 그래프 빌드
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph 빌드.

        KoELECTRA 하이브리드 + 멀티턴 대화 흐름:
        START → validate → load_history → rewrite_query
              → koelectra_classify → classify_detail → route_xxx
              → save_history → finalize → END
        """
        graph = StateGraph(ChatProcessingState)

        # 노드 추가
        graph.add_node("validate", self._validate_node)
        graph.add_node("load_history", self._load_history_node)
        graph.add_node("rewrite_query", self._rewrite_query_node)
        graph.add_node("koelectra_classify", self._koelectra_classify_node)
        graph.add_node("classify_detail", self._classify_detail_node)
        graph.add_node("route_exam", self._route_exam_node)
        graph.add_node("route_question", self._route_question_node)
        graph.add_node("route_study_plan", self._route_study_plan_node)
        graph.add_node("route_solving_log", self._route_solving_log_node)
        graph.add_node("route_mentoring", self._route_mentoring_node)
        graph.add_node("route_audio_note", self._route_audio_note_node)
        graph.add_node("route_chat", self._route_chat_node)
        graph.add_node("save_history", self._save_history_node)
        graph.add_node("finalize", self._finalize_node)

        # 엣지 추가 (KoELECTRA 하이브리드 + 멀티턴 파이프라인)
        graph.add_edge(START, "validate")
        graph.add_edge("validate", "load_history")
        graph.add_edge("load_history", "rewrite_query")
        graph.add_edge("rewrite_query", "koelectra_classify")
        graph.add_edge("koelectra_classify", "classify_detail")
        graph.add_conditional_edges(
            "classify_detail",
            self._route_request_type,
            {
                "exam": "route_exam",
                "question": "route_question",
                "study_plan": "route_study_plan",
                "solving_log": "route_solving_log",
                "mentoring": "route_mentoring",
                "audio_note": "route_audio_note",
                "chat": "route_chat",
                "block": "save_history",
            }
        )
        graph.add_edge("route_exam", "save_history")
        graph.add_edge("route_question", "save_history")
        graph.add_edge("route_study_plan", "save_history")
        graph.add_edge("route_solving_log", "save_history")
        graph.add_edge("route_mentoring", "save_history")
        graph.add_edge("route_audio_note", "save_history")
        graph.add_edge("route_chat", "save_history")
        graph.add_edge("save_history", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    async def _validate_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """데이터 검증 노드."""
        request_text = state.get("request_text", "")

        # request_text를 반드시 문자열로 보장
        if not isinstance(request_text, str):
            logger.warning(f"[ChatFlow] request_text가 str이 아님: {type(request_text).__name__}, 변환 시도")
            if isinstance(request_text, dict):
                request_text = request_text.get("question", str(request_text))
            else:
                request_text = str(request_text)

        if not request_text or not request_text.strip():
            logger.warning("[ChatFlow] request_text가 비어있음")
            return {
                **state,
                "request_text": request_text or "",
                "error": "질문이 비어있습니다.",
            }

        return {
            **state,
            "request_text": request_text,
        }

    async def _load_history_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """대화 이력 로드 노드 — Redis에서 thread_id로 이전 대화 이력을 가져옵니다."""
        request_data = state.get("request_data", {})
        thread_id = request_data.get("thread_id")

        if not thread_id or not is_redis_available():
            logger.debug("[ChatFlow] thread_id 없음 또는 Redis 미사용 → 이력 로드 생략")
            return {
                **state,
                "thread_id": thread_id,
                "chat_history": [],
                "context_summary": "",
            }

        try:
            history_data = get_chat_history(thread_id)
            chat_history = history_data.get("messages", [])
            context_summary = history_data.get("context_summary", "")

            logger.info(
                f"[ChatFlow] 대화 이력 로드: session={thread_id}, "
                f"messages={len(chat_history)}건, summary='{context_summary[:50]}...'"
            )

            return {
                **state,
                "thread_id": thread_id,
                "chat_history": chat_history,
                "context_summary": context_summary,
            }
        except Exception as e:
            logger.warning(f"[ChatFlow] 대화 이력 로드 실패: {e}")
            return {
                **state,
                "thread_id": thread_id,
                "chat_history": [],
                "context_summary": "",
            }

    async def _rewrite_query_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """쿼리 재구성 노드 — 대화 이력을 반영하여 검색 쿼리를 재구성합니다."""
        request_text = state.get("request_text", "")
        chat_history = state.get("chat_history", [])
        context_summary = state.get("context_summary", "")

        if not chat_history:
            # 첫 질문이면 재구성 불필요
            return {**state, "rewritten_query": request_text}

        try:
            rewritten = rewrite_query(
                current_question=request_text,
                chat_history=chat_history,
                context_summary=context_summary,
                llm=state.get("request_data", {}).get("_llm"),
                use_llm=True,
            )

            logger.info(f"[ChatFlow] 쿼리 재구성: '{request_text[:40]}' → '{rewritten[:60]}'")
            return {**state, "rewritten_query": rewritten}
        except Exception as e:
            logger.warning(f"[ChatFlow] 쿼리 재구성 실패: {e}")
            return {**state, "rewritten_query": request_text}

    async def _koelectra_classify_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """KoELECTRA 1차 분류 노드.

        게이트웨이 분류: BLOCK / POLICY_BASED / RULE_BASED
        신뢰도가 임계값 미만이면 method='keyword_fallback'으로 표시합니다.

        멀티턴 대화 보호 (참조어 기반):
        - 원본 질문이 BLOCK이고 대화 이력이 있을 때,
          질문에 이전 대화를 참조하는 표현(대명사, 지시어, 후속 표현)이 있으면
          맥락상 후속 질문으로 판단하여 POLICY_BASED로 오버라이드합니다.
        - "다른 교재는?" → 참조어 "다른" 포함 → 오버라이드
        - "맛집 추천해줘" → 참조어 없음 → BLOCK 유지
        """
        request_text = state.get("request_text", "")
        chat_history = state.get("chat_history", [])
        has_history = bool(chat_history and len(chat_history) >= 1)

        # 원본 질문으로 KoELECTRA 게이트웨이 분류
        gw_result = _call_koelectra_gateway(request_text)

        gateway = gw_result.get("gateway", "POLICY_BASED")
        confidence = gw_result.get("confidence", 0.0)
        method = gw_result.get("method", "unknown")

        logger.info(
            f"[ChatFlow] KoELECTRA 1차 분류: gateway={gateway}, "
            f"confidence={confidence:.3f}, method={method} — '{request_text[:40]}...'"
        )

        # 멀티턴 대화에서 원본이 BLOCK인 경우 → 참조어 기반 후속 질문 판별
        if has_history and gateway == "BLOCK":
            if _is_follow_up_question(request_text):
                logger.info(
                    f"[ChatFlow] 참조어 감지 → 후속 질문으로 판단, BLOCK 오버라이드 "
                    f"(원본: '{request_text[:30]}', history={len(chat_history)}건)"
                )
                gateway = "POLICY_BASED"
                method = "multiturn_override"
            else:
                logger.info(
                    f"[ChatFlow] 참조어 없음 → 새 주제, BLOCK 유지 "
                    f"(원본: '{request_text[:30]}')"
                )

        # 신뢰도가 낮으면 폴백 표시 (2차 세분화에서 키워드 분류로 전환됨)
        if confidence < KOELECTRA_CONFIDENCE_THRESHOLD and method == "koelectra_gateway":
            logger.info(
                f"[ChatFlow] 신뢰도 {confidence:.3f} < {KOELECTRA_CONFIDENCE_THRESHOLD} → "
                f"키워드 폴백 모드로 전환"
            )
            method = "keyword_fallback"

        return {
            **state,
            "koelectra_gateway": gateway,
            "koelectra_confidence": confidence,
            "koelectra_method": method,
        }

    async def _classify_detail_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """2차 세분화 노드.

        KoELECTRA 1차 결과(gateway)를 기반으로 키워드 세분화:
        - BLOCK         → request_type = "block"
        - RULE_BASED    → exam / solving_log (DB 직접 조회)
        - POLICY_BASED  → study_plan / mentoring / audio_note / chat (LLM 추론)
        - 폴백          → 순수 키워드 분류

        멀티턴 대화에서는 rewritten_query를 키워드 분류에도 활용합니다.
        """
        request_text = state.get("request_text", "")
        gateway = state.get("koelectra_gateway", "POLICY_BASED")
        confidence = state.get("koelectra_confidence", 0.0)
        method = state.get("koelectra_method", "unknown")
        rewritten_query = state.get("rewritten_query")

        # 멀티턴 대화에서는 rewritten_query를 키워드 분류 대상으로 사용
        # (짧은 후속 질문 "다른 교재는?" → "행정법 교재 추천 다른 추천" 으로 키워드 매칭 향상)
        classify_text = request_text
        if rewritten_query and rewritten_query != request_text:
            classify_text = rewritten_query

        # ── 멀티턴 오버라이드: 대화 이어가는 중이면 멘토링으로 라우팅 ──
        if method == "multiturn_override":
            # rewritten_query로 세부 분류 시도, 그래도 'chat'이면 mentoring으로 보강
            request_type = _classify_policy_based_detail(classify_text)
            if request_type == "chat":
                request_type = "mentoring"
            logger.info(
                f"[ChatFlow] 멀티턴 오버라이드 세분화: {request_type.upper()} "
                f"(classify_text='{classify_text[:40]}')"
            )
            return {
                **state,
                "request_type": request_type,
                "target_flow": f"{request_type}_flow",
            }

        # ── BLOCK (고신뢰): 신뢰도가 충분해도 도메인 키워드 있으면 오분류 가능 ──
        if gateway == "BLOCK" and method not in ("keyword_fallback", "error", "unavailable"):
            # 원본 텍스트에 도메인 키워드가 있는지 확인 (오분류 방지)
            # 예: "독학 vs 학원 어떤게 나을까?" → "독학", "학원" 포함 → mentoring
            original_type = _classify_request_keyword_only(request_text)
            if original_type != "chat":
                # 도메인 키워드가 있음 → KoELECTRA BLOCK은 오분류
                logger.info(
                    f"[ChatFlow] KoELECTRA BLOCK이지만 도메인 키워드 매칭({original_type.upper()}) → "
                    f"BLOCK 무시 (confidence={confidence:.3f}, text='{request_text[:40]}')"
                )
                return {
                    **state,
                    "request_type": original_type,
                    "target_flow": f"{original_type}_flow",
                }

            logger.info(
                f"[ChatFlow] KoELECTRA → BLOCK (고신뢰 차단) "
                f"[confidence={confidence:.3f}, method={method}]"
            )
            return {
                **state,
                "request_type": "block",
                "target_flow": "block",
            }

        # ── 폴백 모드: KoELECTRA 불가 또는 신뢰도 낮음 ──
        # 신뢰도가 낮은 BLOCK은 오분류 가능성이 높으므로 키워드 분류로 넘김
        # (예: "행정법 교재 추천" → BLOCK(0.67) → keyword_fallback → mentoring)
        if method in ("keyword_fallback", "error", "unavailable"):
            # KoELECTRA가 BLOCK이라고 했는데 신뢰도가 낮은 경우:
            # → 원본 텍스트에 도메인 키워드가 있는지 확인
            #   (rewritten_query는 이전 대화 맥락이 섞여 있어 부정확)
            if gateway == "BLOCK":
                original_type = _classify_request_keyword_only(request_text)
                if original_type == "chat":
                    # 원본에 도메인 키워드 없음 → KoELECTRA BLOCK 존중
                    # (예: "맛집 추천해줘" → 키워드 없음 + BLOCK → 차단)
                    logger.info(
                        f"[ChatFlow] 원본 키워드 미매칭 + KoELECTRA BLOCK → 차단 "
                        f"(confidence={confidence:.3f}, original='{request_text[:30]}')"
                    )
                    return {
                        **state,
                        "request_type": "block",
                        "target_flow": "block",
                    }
                else:
                    # 원본에 도메인 키워드 있음 → KoELECTRA BLOCK은 오분류
                    # (예: "행정법 교재 추천" → "교재" 매칭 → mentoring)
                    logger.info(
                        f"[ChatFlow] 원본 키워드 매칭({original_type.upper()}) → "
                        f"KoELECTRA BLOCK 무시 (confidence={confidence:.3f})"
                    )
                    return {
                        **state,
                        "request_type": original_type,
                        "target_flow": f"{original_type}_flow",
                    }

            # BLOCK이 아닌 폴백: 게이트웨이 범주 내 세부 분류
            # KoELECTRA의 게이트웨이 범주(POLICY/RULE)는 저신뢰도에서도 비교적 정확하므로
            # 범주 내에서 세분화하여 오분류 방지
            # (예: POLICY_BASED "교재 추천" → 넓은 키워드("전략") 매칭 → study_plan 오분류 방지)
            if gateway == "RULE_BASED":
                request_type = _classify_rule_based_detail(classify_text)
            elif gateway == "POLICY_BASED":
                request_type = _classify_policy_based_detail(classify_text)
            else:
                request_type = _classify_request_keyword_only(classify_text)
            logger.info(
                f"[ChatFlow] 키워드 폴백 분류: {request_type.upper()} "
                f"(gateway={gateway}, confidence={confidence:.3f})"
            )
            return {
                **state,
                "request_type": request_type,
                "target_flow": f"{request_type}_flow",
            }

        # ── RULE_BASED: DB 직접 조회 ──
        if gateway == "RULE_BASED":
            request_type = _classify_rule_based_detail(classify_text)
            logger.info(f"[ChatFlow] KoELECTRA RULE_BASED → 세분화: {request_type.upper()}")
            return {
                **state,
                "request_type": request_type,
                "target_flow": f"{request_type}_flow",
            }

        # ── POLICY_BASED: LLM 추론 필요 ──
        request_type = _classify_policy_based_detail(classify_text)
        logger.info(f"[ChatFlow] KoELECTRA POLICY_BASED → 세분화: {request_type.upper()}")
        return {
            **state,
            "request_type": request_type,
            "target_flow": f"{request_type}_flow",
        }

    def _route_request_type(self, state: ChatProcessingState) -> str:
        """요청 타입에 따른 라우팅."""
        request_type = state.get("request_type", "chat")
        valid_types = [
            "exam", "question", "study_plan", "solving_log",
            "mentoring", "audio_note", "block", "chat",
        ]

        if request_type in valid_types:
            logger.info(f"[ChatFlow] {request_type.upper()}으로 라우팅")
            return request_type
        else:
            logger.info("[ChatFlow] CHAT으로 라우팅 (기본값)")
            return "chat"

    async def _route_exam_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """Exam Flow로 라우팅 노드."""
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})

        logger.info(f"[ChatFlow] ExamFlow로 요청 전달: {request_text[:50]}...")

        try:
            # ExamFlow로 요청 처리
            exam_result = await self._exam_flow.process_exam_request(
                request_text=request_text,
                request_data=request_data
            )

            logger.info(f"[ChatFlow] ExamFlow 처리 완료: success={exam_result.get('success', False)}")

            # ExamFlow 결과를 ChatFlow 형식으로 변환
            # ExamFlow의 result는 { success, answer, error, ... } 형식
            # answer는 문자열 또는 dict일 수 있음
            answer = exam_result.get("answer")
            if answer is None:
                # answer가 없으면 error 메시지 사용
                answer = exam_result.get("error", "응답을 생성하지 못했습니다.")
            elif isinstance(answer, dict):
                # answer가 dict인 경우 (정답 조회 결과)
                year = answer.get("year", "")
                exam_type = answer.get("exam_type", "")
                subject = answer.get("subject", "")
                question_no = answer.get("question_no", "")
                answer_key = answer.get("answer_key", "")
                if year and subject and question_no and answer_key:
                    answer = f"{year}년 {exam_type} {subject} {question_no}번 정답은 {answer_key}번입니다."
                else:
                    # ADVICE 의도인 경우 response 필드 사용
                    answer = answer.get("response", str(answer))
            elif not isinstance(answer, str):
                answer = str(answer)

            # ChatFlow 결과 형식으로 변환
            result = {
                "success": exam_result.get("success", False),
                "answer": answer,
                "mode": "exam",
                "intent": exam_result.get("intent"),
                "method": exam_result.get("method"),
            }

            return {
                **state,
                "routed_result": exam_result,  # 원본 ExamFlow 결과
                "result": result,  # ChatFlow 형식으로 변환된 결과
            }
        except Exception as e:
            logger.error(f"[ChatFlow] ExamFlow 처리 오류: {e}", exc_info=True)
            error_result = {
                "success": False,
                "error": str(e),
                "answer": f"처리 중 오류가 발생했습니다: {str(e)}",
                "mode": "exam",
            }
            return {
                **state,
                "routed_result": error_result,
                "result": error_result,
                "error": str(e),
            }

    async def _route_question_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """Question Flow로 라우팅 노드."""
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})

        logger.info(f"[ChatFlow] QuestionFlow로 요청 전달: {request_text[:50]}...")

        try:
            question_result = await self._question_flow.process_question_request(
                request_text=request_text,
                request_data={"action": "search", "keyword": request_text, **request_data}
            )

            answer = self._format_flow_answer(question_result, "question")
            result = {
                "success": question_result.get("success", False),
                "answer": answer,
                "mode": "question",
            }

            return {**state, "routed_result": question_result, "result": result}
        except Exception as e:
            logger.error(f"[ChatFlow] QuestionFlow 처리 오류: {e}", exc_info=True)
            return self._create_error_state(state, e, "question")

    async def _route_study_plan_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """StudyPlan Flow로 라우팅 노드 — 가상모의고사 기반 기존 학습계획 조회.

        채팅에서는 AI 학습계획을 새로 생성하지 않고,
        가상모의고사를 통해 이미 생성된 학습계획을 조회하여 보여줍니다.
        학습계획이 없으면 가상모의고사 안내 메시지를 반환합니다.
        """
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})
        conn = request_data.get("_conn")
        llm = request_data.get("_llm")

        try:
            user_id = request_data.get("user_id")

            if user_id is None:
                logger.warning("[ChatFlow] user_id가 None입니다. 로그인이 필요합니다.")
                result = {
                    "success": True,
                    "answer": (
                        "로그인이 필요해요!\n\n"
                        "학습 계획을 조회하려면 먼저 로그인해주세요.\n"
                        "상단의 로그인 버튼을 눌러 카카오/네이버/구글 계정으로 로그인할 수 있습니다."
                    ),
                    "mode": "study_plan",
                }
                return {**state, "result": result}

            logger.info(f"[ChatFlow] StudyPlanFlow로 요청 전달 (조회 모드, user_id={user_id}): {request_text[:50]}...")

            # 채팅에서는 항상 기존 학습계획 조회 (생성은 학습분석 페이지에서만)
            plan_request_data = {
                "action": "read",
                "user_id": user_id,
                "_conn": conn,
                "_llm": llm,
                **{k: v for k, v in request_data.items() if k not in ("_conn", "_llm")},
            }

            plan_result = await self._study_plan_flow.process_study_plan_request(
                request_text=request_text,
                request_data=plan_request_data,
            )

            answer = self._format_flow_answer(plan_result, "study_plan")
            result = {
                "success": True,
                "answer": answer,
                "mode": "study_plan",
            }

            return {**state, "routed_result": plan_result, "result": result}
        except Exception as e:
            logger.error(f"[ChatFlow] StudyPlanFlow 처리 오류: {e}", exc_info=True)
            return self._create_error_state(state, e, "study_plan")

    async def _route_solving_log_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """SolvingLog Flow로 라우팅 노드."""
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})

        logger.info(f"[ChatFlow] SolvingLogFlow로 요청 전달: {request_text[:50]}...")

        try:
            # 오답 노트 요청인지 판단
            if any(kw in request_text for kw in ["오답", "틀린"]):
                action = "wrong_notes"
            elif any(kw in request_text for kw in ["정답률", "통계"]):
                action = "analyze"
            else:
                action = "read"

            user_id = request_data.get("user_id")
            if user_id is None:
                result = {
                    "success": True,
                    "answer": "로그인이 필요해요!\n\n풀이 기록을 조회하려면 먼저 로그인해주세요.",
                    "mode": "solving_log",
                }
                return {**state, "result": result}

            log_result = await self._solving_log_flow.process_solving_log_request(
                request_text=request_text,
                request_data={"action": action, "user_id": user_id, **request_data}
            )

            answer = self._format_flow_answer(log_result, "solving_log")
            result = {
                "success": log_result.get("success", False),
                "answer": answer,
                "mode": "solving_log",
            }

            return {**state, "routed_result": log_result, "result": result}
        except Exception as e:
            logger.error(f"[ChatFlow] SolvingLogFlow 처리 오류: {e}", exc_info=True)
            return self._create_error_state(state, e, "solving_log")

    async def _route_mentoring_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """멘토링 RAG 노드 — KURE-v1 임베딩 + pgvector로 합격 수기 검색 후 EXAONE으로 답변 생성.

        멀티턴 대화 이력과 재구성된 쿼리를 활용하여 맥락 있는 답변을 생성합니다.
        """
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})
        conn = request_data.get("_conn")
        llm = request_data.get("_llm")

        # 멀티턴 데이터
        chat_history = state.get("chat_history", [])
        context_summary = state.get("context_summary", "")
        rewritten_query = state.get("rewritten_query")

        logger.info(f"[ChatFlow] 멘토링 RAG 요청: {request_text[:50]}...")

        if conn is None:
            logger.warning("[ChatFlow] DB 연결이 없어 멘토링 RAG를 수행할 수 없습니다.")
            result = {
                "success": False,
                "answer": "멘토링 검색을 수행할 수 없습니다. 서버 설정을 확인해주세요.",
                "mode": "mentoring",
            }
            return {**state, "routed_result": result, "result": result}

        try:
            top_k = request_data.get("top_k", 5)
            rag_result = await process_mentoring_rag(
                conn=conn,
                question=request_text,
                top_k=top_k,
                use_llm=True,
                llm=llm,
                chat_history=chat_history if chat_history else None,
                context_summary=context_summary,
                rewritten_query=rewritten_query,
            )

            result = {
                "success": rag_result.get("success", False),
                "answer": rag_result.get("answer", "답변을 생성하지 못했습니다."),
                "retrieved_docs": rag_result.get("retrieved_docs"),
                "mode": "mentoring",
                "metadata": rag_result.get("metadata"),
            }

            return {**state, "routed_result": rag_result, "result": result}
        except Exception as e:
            logger.error(f"[ChatFlow] 멘토링 RAG 오류: {e}", exc_info=True)
            return self._create_error_state(state, e, "mentoring")

    async def _route_audio_note_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """AudioNote Flow로 라우팅 노드."""
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})

        logger.info(f"[ChatFlow] AudioNoteFlow로 요청 전달: {request_text[:50]}...")

        try:
            audio_result = await self._audio_note_flow.process_audio_note_request(
                request_text=request_text,
                request_data={"action": "read", **request_data}
            )

            answer = self._format_flow_answer(audio_result, "audio_note")
            result = {
                "success": audio_result.get("success", False),
                "answer": answer,
                "mode": "audio_note",
            }

            return {**state, "routed_result": audio_result, "result": result}
        except Exception as e:
            logger.error(f"[ChatFlow] AudioNoteFlow 처리 오류: {e}", exc_info=True)
            return self._create_error_state(state, e, "audio_note")

    async def _route_chat_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """일반 Chat 처리 노드 — 멘토링 RAG 폴백 포함, EXAONE으로 응답 생성.

        멀티턴 대화 이력을 활용하여 맥락 있는 답변을 시도합니다.
        """
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})
        conn = request_data.get("_conn")
        llm = request_data.get("_llm")

        # 멀티턴 데이터
        chat_history = state.get("chat_history", [])
        context_summary = state.get("context_summary", "")
        rewritten_query = state.get("rewritten_query")

        logger.info(f"[ChatFlow] 일반 Chat 처리: {request_text[:50]}...")

        # DB 연결이 있으면 멘토링 RAG로 시도 (범용 질문도 수기 기반 답변 가능)
        if conn is not None:
            try:
                top_k = request_data.get("top_k", 3)
                rag_result = await process_mentoring_rag(
                    conn=conn,
                    question=request_text,
                    top_k=top_k,
                    use_llm=True,
                    llm=llm,
                    chat_history=chat_history if chat_history else None,
                    context_summary=context_summary,
                    rewritten_query=rewritten_query,
                )

                # 유사한 결과가 있으면 멘토링 RAG 답변 사용
                metadata = rag_result.get("metadata", {})
                if metadata.get("result_count", 0) > 0 and metadata.get("top_similarity", 0) > 0.4:
                    result = {
                        "success": True,
                        "answer": rag_result.get("answer", ""),
                        "retrieved_docs": rag_result.get("retrieved_docs"),
                        "mode": "mentoring",
                        "metadata": metadata,
                    }
                    return {**state, "routed_result": rag_result, "result": result}
            except Exception as e:
                logger.warning(f"[ChatFlow] 일반 Chat에서 멘토링 RAG 실패: {e}")

        # 멘토링 RAG에 적합한 결과가 없으면 EXAONE으로 직접 응답
        if llm is not None and llm.is_loaded():
            try:
                prompt = (
                    "당신은 공무원 시험 준비를 돕는 AI 멘토입니다. "
                    "사용자의 질문에 친절하고 도움이 되는 답변을 해주세요.\n\n"
                    f"질문: {request_text}\n\n"
                    "답변:"
                )
                generated = llm.generate(prompt=prompt, max_new_tokens=512, temperature=0.7)
                result = {
                    "success": True,
                    "answer": generated,
                    "mode": "chat",
                }
                return {**state, "routed_result": result, "result": result}
            except Exception as llm_err:
                logger.warning(f"[ChatFlow] EXAONE 직접 응답 실패: {llm_err}")

        # 최종 폴백: 안내 메시지 반환
        result = {
            "success": True,
            "answer": "죄송합니다, 해당 질문에 대한 정보를 찾지 못했습니다. "
                      "공무원 시험 준비에 관한 구체적인 질문을 해주시면 더 정확한 답변을 드릴 수 있습니다.",
            "mode": "chat",
        }

        return {
            **state,
            "routed_result": result,
            "result": result,
        }

    def _format_flow_answer(self, flow_result: dict, mode: str) -> str:
        """Flow 결과를 답변 문자열로 포맷팅."""

        # study_plan은 success=False일 때도 안내 메시지를 보여줘야 하므로 먼저 처리
        if mode == "study_plan":
            plan = flow_result.get("plan")

            # 학습계획이 없는 경우 (success=False 또는 plan이 None)
            if not flow_result.get("success", False) or not plan:
                return (
                    "아직 학습 계획이 생성되지 않았어요!\n\n"
                    "가상모의고사를 통해 본인의 강점과 취약점인 과목을 알아보세요~\n"
                    "공잘알이 정밀한 분석을 통해 세심한 학습계획을 짜드릴게요!\n\n"
                    "상단 메뉴의 [학습 분석 & AI 플랜] 페이지에서 "
                    "풀이 분석 -> AI 플랜 생성을 진행해주세요."
                )

            # 학습계획이 있는 경우 → plan_json 내용을 채팅에 보기 좋게 출력
            plan_json = plan.get("plan_json", {}) if isinstance(plan, dict) else {}
            version = plan.get("version", "?")

            if not plan_json or not isinstance(plan_json, dict):
                return f"학습 계획(v{version})이 있지만 상세 내용을 불러올 수 없습니다."

            parts = [f"📋 나의 학습 계획 (v{version})"]

            # 1) 분석 요약
            summary = plan_json.get("summary")
            if summary:
                parts.append(f"\n📊 분석 요약\n{summary}")

            # 2) 우선 보강 과목
            priority = plan_json.get("priority_subjects")
            if priority and isinstance(priority, list):
                subjects_str = ", ".join(
                    f"{i}. {s}" for i, s in enumerate(priority, 1)
                )
                parts.append(f"\n🎯 우선 보강 과목: {subjects_str}")

            # 3) 주간 학습 스케줄
            schedule = plan_json.get("weekly_schedule")
            if schedule and isinstance(schedule, list):
                parts.append("\n📅 주간 학습 스케줄")
                for entry in schedule:
                    if isinstance(entry, dict):
                        day = entry.get("day", "")
                        subjects = entry.get("subjects", [])
                        focus = entry.get("focus", "")
                        hours = entry.get("hours", "")
                        subj_str = " / ".join(subjects) if isinstance(subjects, list) else str(subjects)
                        line = f"  [{day}] {subj_str}"
                        if focus:
                            line += f" — {focus}"
                        if hours:
                            line += f" ({hours}시간)"
                        parts.append(line)

            # 4) 학습 조언
            advice = plan_json.get("specific_advice")
            if advice and isinstance(advice, list):
                parts.append("\n💡 학습 조언")
                for i, a in enumerate(advice[:6], 1):
                    parts.append(f"  {i}. {a}")

            # 5) 동기부여 메시지
            motivation = plan_json.get("motivation")
            if motivation:
                parts.append(f"\n🔥 {motivation}")

            # 6) 하단 안내
            parts.append(
                "\n\n📌 자세한 내용은 학습 분석 & AI 플랜의 학습계획 항목에서 확인하세요."
            )

            return "\n".join(parts)

        # study_plan 이외 모드: success=False이면 에러 메시지 반환
        if not flow_result.get("success", False):
            return flow_result.get("error", "처리 중 오류가 발생했습니다.")

        if mode == "question":
            questions = flow_result.get("questions", [])
            if questions:
                lines = [f"검색 결과 {len(questions)}개의 문제를 찾았습니다:"]
                for q in questions[:5]:
                    lines.append(f"- {q.get('exam_year')}년 {q.get('exam_type')} {q.get('subject')} {q.get('question_no')}번")
                return "\n".join(lines)
            return "검색 결과가 없습니다."

        elif mode == "solving_log":
            if "stats" in flow_result:
                stats = flow_result["stats"]
                return (
                    f"학습 통계:\n"
                    f"- 총 풀이 수: {stats.get('total_solved')}문제\n"
                    f"- 정답률: {stats.get('accuracy')}%\n"
                    f"- 오답 노트: {stats.get('wrong_note_count')}개"
                )
            elif "wrong_notes" in flow_result:
                notes = flow_result["wrong_notes"]
                return f"오답 노트 {len(notes)}개를 찾았습니다."
            return "풀이 기록을 조회했습니다."

        elif mode == "audio_note":
            audio = flow_result.get("audio_note") or flow_result.get("audio_notes", [])
            if audio:
                return "오디오 노트를 조회했습니다."
            return "오디오 노트가 없습니다."

        return str(flow_result)

    def _create_error_state(self, state: dict, error: Exception, mode: str) -> dict:
        """에러 상태 생성."""
        error_result = {
            "success": False,
            "error": str(error),
            "answer": f"처리 중 오류가 발생했습니다: {str(error)}",
            "mode": mode,
        }
        return {
            **state,
            "routed_result": error_result,
            "result": error_result,
            "error": str(error),
        }

    async def _save_history_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """대화 이력 저장 노드 — 현재 질문과 답변을 Redis에 저장하고 맥락 요약을 갱신합니다."""
        thread_id = state.get("thread_id")

        if not thread_id or not is_redis_available():
            return state

        request_text = state.get("request_text", "")
        result = state.get("result", {})
        answer = result.get("answer", "") if result else ""
        chat_history = state.get("chat_history", [])
        context_summary = state.get("context_summary", "")

        try:
            # 1) 사용자 메시지 저장
            store_chat_message(thread_id, "user", request_text)

            # 2) 봇 답변 저장 (answer가 있을 때만)
            if answer:
                # 저장 시 너무 긴 답변은 잘라서 저장 (Redis 용량 절약)
                save_answer = answer[:500] if len(answer) > 500 else answer
                store_chat_message(thread_id, "bot", save_answer)

            # 3) 맥락 요약 갱신
            new_summary = generate_context_summary(
                chat_history=chat_history + [
                    {"role": "user", "text": request_text},
                ],
                current_question=request_text,
                old_summary=context_summary,
            )
            if new_summary != context_summary:
                redis_update_context_summary(thread_id, new_summary)
                logger.debug(f"[ChatFlow] 맥락 요약 갱신: '{new_summary[:60]}'")

            logger.info(f"[ChatFlow] 대화 이력 저장 완료: session={thread_id}")
        except Exception as e:
            logger.warning(f"[ChatFlow] 대화 이력 저장 실패: {e}")

        return state

    async def _finalize_node(self, state: ChatProcessingState) -> ChatProcessingState:
        """최종 정리 노드."""
        request_type = state.get("request_type", "chat")

        # BLOCK인 경우 특별 처리
        if request_type == "block":
            result = {
                "success": True,
                "answer": "안녕하세요! 공잘알 AI 멘토입니다. 😊\n공무원 시험 준비에 관한 질문을 해주시면 맞춤 조언을 드리겠습니다.\n\n💡 예시 질문:\n• 노베이스 1년 일행직 어떻게 준비해?\n• 행정법 교재 추천해줘\n• 단기 합격 학습 계획 짜줘",
                "mode": "block",
            }
            return {
                **state,
                "result": result,
            }

        # 정상 처리 완료 (result는 이미 routed_result에서 설정됨)
        return state

    async def process_chat_request(
        self, request_text: str, request_data: dict, mode: str = "rag_openai",
        conn=None, llm=None,
    ) -> dict:
        """Chat 요청 처리.

        Args:
            request_text: 사용자 요청 텍스트
            request_data: 요청 데이터 (question, mode 등)
            mode: 처리 모드 (rag_openai, rag, openai 등)
            conn: PostgreSQL DB 연결 (멘토링 RAG 등에 사용)
            llm: EXAONE BaseLLM 인스턴스 (멘토링 RAG에서 사용)

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[ChatFlow] Chat 요청 수신: {request_text[:50]}...")

        # 초기 상태 설정 (conn, llm은 request_data에 전달)
        initial_state: ChatProcessingState = {
            "request_text": request_text,
            "request_data": {**request_data, "mode": mode, "_conn": conn, "_llm": llm},
            "result": None,
            "error": None,
            "metadata": None,
            # KoELECTRA 1차 분류 (koelectra_classify 노드에서 채워짐)
            "koelectra_gateway": None,
            "koelectra_confidence": None,
            "koelectra_intent": None,
            "koelectra_method": None,
            # 2차 세분화 결과
            "request_type": None,
            "target_flow": None,
            "routed_result": None,
            # 멀티턴 대화 관련 (load_history 노드에서 채워짐)
            "chat_history": None,
            "rewritten_query": None,
            "context_summary": None,
            "thread_id": request_data.get("thread_id"),
        }

        # LangGraph 실행
        logger.info("[ChatFlow] LangGraph 실행 시작")
        try:
            final_state = await self._graph.ainvoke(initial_state)
            logger.info("[ChatFlow] LangGraph 실행 완료")

            result = final_state.get("result")
            if result is None:
                return {
                    "success": False,
                    "error": "처리 결과가 없습니다.",
                }

            # KoELECTRA 메타데이터를 결과에 포함
            result["koelectra"] = {
                "gateway": final_state.get("koelectra_gateway"),
                "confidence": final_state.get("koelectra_confidence"),
                "method": final_state.get("koelectra_method"),
            }

            return result
        except Exception as e:
            logger.error(f"[ChatFlow] LangGraph 실행 오류: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

