"""UserSolvingLog 요청 처리 Orchestrator (LangGraph 기반).

새 테이블 구조:
- User_Solving_Logs: user_id FK, question_id FK, selected_answer, time_spent 등

LangGraph StateGraph로 구현:
- 풀이 로그 기록/조회/통계 워크플로우
- 오답 노트 관리
- SolvingLogService를 통한 데이터 처리
"""

import logging
from typing import Dict, Any, Optional, TypedDict, List

from langgraph.graph import StateGraph, END, START

from backend.domain.admin.spokes.services.solving_log_service import SolvingLogService
from backend.domain.admin.models.transfers.user_transfer import (
    UserSolvingLogCreateRequest,
)

logger = logging.getLogger(__name__)


# ============================================================================
# State 정의
# ============================================================================

class SolvingLogProcessingState(TypedDict, total=False):
    """SolvingLog 처리 상태."""
    request_text: str
    request_data: Dict[str, Any]
    action: str  # create, list, statistics, wrong_notes
    user_id: Optional[int]
    question_id: Optional[int]
    log_id: Optional[int]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]


# ============================================================================
# SolvingLogFlow
# ============================================================================

class SolvingLogFlow:
    """UserSolvingLog 요청 처리 Orchestrator (LangGraph 기반)."""

    def __init__(self):
        """초기화."""
        self._service = SolvingLogService()
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph 빌드."""
        graph = StateGraph(SolvingLogProcessingState)

        # 노드 추가
        graph.add_node("validate", self._validate_node)
        graph.add_node("determine_action", self._determine_action_node)
        graph.add_node("process_create", self._process_create_node)
        graph.add_node("process_list", self._process_list_node)
        graph.add_node("process_statistics", self._process_statistics_node)
        graph.add_node("process_wrong_notes", self._process_wrong_notes_node)
        graph.add_node("finalize", self._finalize_node)

        # 엣지 추가
        graph.add_edge(START, "validate")
        graph.add_edge("validate", "determine_action")
        graph.add_conditional_edges(
            "determine_action",
            self._route_action,
            {
                "create": "process_create",
                "list": "process_list",
                "statistics": "process_statistics",
                "wrong_notes": "process_wrong_notes",
            }
        )
        graph.add_edge("process_create", "finalize")
        graph.add_edge("process_list", "finalize")
        graph.add_edge("process_statistics", "finalize")
        graph.add_edge("process_wrong_notes", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    async def _validate_node(self, state: SolvingLogProcessingState) -> SolvingLogProcessingState:
        """데이터 검증 노드."""
        request_data = state.get("request_data", {})

        if not request_data:
            return {**state, "error": "요청 데이터가 비어있습니다."}

        return state

    async def _determine_action_node(self, state: SolvingLogProcessingState) -> SolvingLogProcessingState:
        """액션 판단 노드."""
        request_data = state.get("request_data", {})
        action = request_data.get("action", "list")

        logger.info(f"[SolvingLogFlow] 액션 판단: {action}")

        return {
            **state,
            "action": action,
            "user_id": request_data.get("user_id"),
            "question_id": request_data.get("question_id"),
            "log_id": request_data.get("log_id"),
        }

    def _route_action(self, state: SolvingLogProcessingState) -> str:
        """액션에 따른 라우팅."""
        action = state.get("action", "list")
        if action in ("create", "list", "statistics", "wrong_notes"):
            return action
        return "list"

    async def _process_create_node(self, state: SolvingLogProcessingState) -> SolvingLogProcessingState:
        """풀이 로그 생성 노드 (Service 사용)."""
        request_data = state.get("request_data", {})

        try:
            request = UserSolvingLogCreateRequest(
                user_id=request_data.get("user_id"),
                question_id=request_data.get("question_id"),
                selected_answer=request_data.get("selected_answer"),
                time_spent=request_data.get("time_spent"),
                special_event=request_data.get("special_event"),
                is_wrong_note=request_data.get("is_wrong_note", False),
            )
            result = self._service.create_log(request)
            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[SolvingLogFlow] 풀이 로그 생성 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _process_list_node(self, state: SolvingLogProcessingState) -> SolvingLogProcessingState:
        """풀이 로그 목록 조회 노드 (Service 사용)."""
        user_id = state.get("user_id")
        question_id = state.get("question_id")
        request_data = state.get("request_data", {})

        try:
            limit = request_data.get("limit", 50)
            offset = request_data.get("offset", 0)

            if question_id:
                result = self._service.get_question_logs(question_id, user_id)
            elif user_id:
                result = self._service.get_user_logs(user_id, limit, offset)
            else:
                result = {"success": False, "error": "user_id 또는 question_id가 필요합니다."}

            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[SolvingLogFlow] 풀이 로그 목록 조회 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _process_statistics_node(self, state: SolvingLogProcessingState) -> SolvingLogProcessingState:
        """사용자 통계 조회 노드 (Service 사용)."""
        user_id = state.get("user_id")

        try:
            if not user_id:
                return {**state, "result": {"success": False, "error": "user_id가 필요합니다."}}

            result = self._service.get_user_statistics(user_id)
            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[SolvingLogFlow] 통계 조회 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _process_wrong_notes_node(self, state: SolvingLogProcessingState) -> SolvingLogProcessingState:
        """오답 노트 조회 노드 (Service 사용)."""
        user_id = state.get("user_id")
        request_data = state.get("request_data", {})

        try:
            if not user_id:
                return {**state, "result": {"success": False, "error": "user_id가 필요합니다."}}

            limit = request_data.get("limit", 50)
            result = self._service.get_wrong_notes(user_id, limit)
            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[SolvingLogFlow] 오답 노트 조회 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _finalize_node(self, state: SolvingLogProcessingState) -> SolvingLogProcessingState:
        """최종 정리 노드."""
        return state

    async def process_solving_log_request(
        self, request_text: str, request_data: dict
    ) -> dict:
        """SolvingLog 요청 처리.

        Args:
            request_text: 요청 텍스트
            request_data: 요청 데이터 (action, user_id, question_id 등)

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[SolvingLogFlow] 요청 처리 시작")

        initial_state: SolvingLogProcessingState = {
            "request_text": request_text,
            "request_data": request_data,
            "action": None,
            "user_id": None,
            "question_id": None,
            "log_id": None,
            "result": None,
            "error": None,
            "metadata": None,
        }

        try:
            final_state = await self._graph.ainvoke(initial_state)
            result = final_state.get("result")
            return result if result else {"success": False, "error": "처리 결과가 없습니다."}
        except Exception as e:
            logger.error(f"[SolvingLogFlow] 처리 오류: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
