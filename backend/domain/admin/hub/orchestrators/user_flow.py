"""User 요청 처리 Orchestrator (LangGraph 기반).

KoELECTRA 모델을 사용하여 규칙 기반/정책 기반 분기:
- 규칙 기반: 명확한 경우 → user_service.py
- 정책 기반: 애매한 경우 → user_agent.py

LangGraph StateGraph로 구현:
- 노드 기반 워크플로우로 전환
"""

import asyncio
from typing import Literal, Optional

from langgraph.graph import StateGraph, END, START

from backend.domain.admin.models.states.user_state import UserProcessingState
from backend.domain.admin.hub.mcp import get_central_mcp_server
from backend.domain.admin.spokes.services.user_service import UserService
from backend.domain.admin.spokes.agents.user_agent import UserAgent


class UserFlow:
    """User 요청 처리 Orchestrator (LangGraph 기반)."""

    # KoELECTRA 임계치 설정
    RULE_BASED_THRESHOLD_LOW = 0.3  # 이하: 규칙 기반 (user_service)
    RULE_BASED_THRESHOLD_HIGH = 0.8  # 이상: 규칙 기반 (user_service)
    POLICY_BASED_THRESHOLD = (RULE_BASED_THRESHOLD_LOW, RULE_BASED_THRESHOLD_HIGH)  # 애매한 구간: 정책 기반 (user_agent)

    def __init__(self):
        """초기화."""
        # 중앙 MCP 서버 연결
        self.central_mcp = get_central_mcp_server()

        self._user_service = UserService()
        self._user_agent = UserAgent()

        # LangGraph 그래프 빌드
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph 빌드."""
        graph = StateGraph(UserProcessingState)

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

    async def _validate_node(self, state: UserProcessingState) -> UserProcessingState:
        """데이터 검증 노드."""
        return state

    async def _koelectra_analyze_node(self, state: UserProcessingState) -> UserProcessingState:
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
            f"[UserFlow] KoELECTRA 결과: spam_prob={spam_prob:.2f}, "
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

    async def _determine_strategy_node(self, state: UserProcessingState) -> UserProcessingState:
        """전략 판단 노드."""
        spam_prob = state.get("spam_prob", 0.5)

        # 규칙/정책 분기 판단
        if spam_prob < self.RULE_BASED_THRESHOLD_LOW or spam_prob > self.RULE_BASED_THRESHOLD_HIGH:
            strategy = "rule_based"
            print("[UserFlow] 규칙 기반 처리로 판단", flush=True)
        else:
            strategy = "policy_based"
            print("[UserFlow] 정책 기반 처리로 판단", flush=True)

        return {
            **state,
            "strategy": strategy,
        }

    def _route_strategy(self, state: UserProcessingState) -> str:
        """전략에 따른 라우팅."""
        strategy = state.get("strategy", "policy_based")
        return strategy

    async def _rule_process_node(self, state: UserProcessingState) -> UserProcessingState:
        """규칙 기반 처리 노드 (user_service)."""
        request_data = state.get("request_data", {})
        koelectra_result = state.get("koelectra_result", {})

        print("[UserFlow] 규칙 기반 처리로 라우팅 → user_service", flush=True)

        try:
            result = await self._user_service.handle_request(request_data, koelectra_result)
            return {
                **state,
                "result": result,
            }
        except Exception as e:
            print(f"[UserFlow] 규칙 기반 처리 오류: {e}", flush=True)
            return {
                **state,
                "result": {
                    "success": False,
                    "error": str(e),
                },
                "error": str(e),
            }

    async def _policy_process_node(self, state: UserProcessingState) -> UserProcessingState:
        """정책 기반 처리 노드 (user_agent)."""
        request_text = state.get("request_text", "")
        request_data = state.get("request_data", {})
        koelectra_result = state.get("koelectra_result", {})

        print("[UserFlow] 정책 기반 처리로 라우팅 → user_agent", flush=True)

        try:
            result = await self._user_agent.handle_request(request_text, request_data, koelectra_result)
            return {
                **state,
                "result": result,
            }
        except Exception as e:
            print(f"[UserFlow] 정책 기반 처리 오류: {e}", flush=True)
            return {
                **state,
                "result": {
                    "success": False,
                    "error": str(e),
                },
                "error": str(e),
            }

    async def _finalize_node(self, state: UserProcessingState) -> UserProcessingState:
        """최종 정리 노드."""
        return state

    async def process_user_request(
        self, request_text: str, request_data: dict
    ) -> dict:
        """User 요청을 처리한다.

        Args:
            request_text: 사용자 요청 텍스트 (KoELECTRA 분석용)
            request_data: 요청 데이터 (external_id, nickname 등)

        Returns:
            처리 결과 딕셔너리
        """
        # 초기 상태 설정
        initial_state: UserProcessingState = {
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
        print("[UserFlow] LangGraph 실행 시작", flush=True)
        try:
            final_state = await self._graph.ainvoke(initial_state)
            print("[UserFlow] LangGraph 실행 완료", flush=True)

            result = final_state.get("result")
            if result is None:
                return {
                    "success": False,
                    "error": "처리 결과가 없습니다.",
                }
            return result
        except Exception as e:
            print(f"[UserFlow] LangGraph 실행 오류: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
            }
