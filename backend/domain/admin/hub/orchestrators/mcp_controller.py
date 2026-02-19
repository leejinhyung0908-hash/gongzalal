"""MCP Controller - KoELECTRA 게이트웨이 및 세션 관리."""

import asyncio
from datetime import datetime
from typing import Dict, Optional
import uuid

from backend.domain.admin.hub.mcp import get_central_mcp_server
from backend.domain.admin.models.transfers.base_model import GatewayRequest, GatewayResponse
from backend.domain.admin.models.transfers.state_model import SessionStateState, RequestHistoryState


class McpController:
    """MCP Controller (게이트/에스컬레이션 판정)."""

    # KoELECTRA 임계치 설정
    SPAM_PROB_LOW = 0.3   # 이 미만이면 즉시 ALLOW
    SPAM_PROB_HIGH = 0.8  # 이 초과면 즉시 DENY

    def __init__(self):
        """초기화."""
        # 중앙 MCP 서버 연결
        self.central_mcp = get_central_mcp_server()

        self._sessions: Dict[str, SessionStateState] = {}

    async def process_gateway_request(self, request: GatewayRequest) -> GatewayResponse:
        """게이트웨이 요청 처리.

        Args:
            request: 게이트웨이 요청

        Returns:
            게이트웨이 응답
        """
        # 세션 ID 생성 또는 사용
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:12]}"
        request_id = request.request_id or f"req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 세션 상태 가져오기 또는 생성
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionStateState(
                session_id=session_id,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                request_count=0,
                history=[],
            )

        session = self._sessions[session_id]

        # 1단계: KoELECTRA 게이트 판정 (중앙 MCP 서버 사용)
        if self.central_mcp:
            koelectra_result = await self.central_mcp.call_tool("filter_spam", text=request.text)
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

        # 임계치 구간 판단
        if spam_prob < self.SPAM_PROB_LOW:
            threshold_zone = "low"
        elif spam_prob > self.SPAM_PROB_HIGH:
            threshold_zone = "high"
        else:
            threshold_zone = "ambiguous"

        # 2단계: Short-circuit 판단
        if spam_prob < self.SPAM_PROB_LOW:
            # 즉시 ALLOW (EXAONE 호출 안 함)
            gateway_action = "deliver"
            requires_exaone = False
            gateway_message = "KoELECTRA 판정: 정상 메일로 판단되어 즉시 전달"
        elif spam_prob > self.SPAM_PROB_HIGH:
            # 즉시 DENY
            gateway_action = "block"
            requires_exaone = False
            gateway_message = "KoELECTRA 판정: 스팸으로 판단되어 차단"
        else:
            # 애매한 구간: EXAONE 필요
            gateway_action = "analyze"
            requires_exaone = True
            gateway_message = "KoELECTRA 판정: 애매한 구간으로 EXAONE 분석 필요"

        # 요청 히스토리 추가
        history_item = RequestHistoryState(
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            text=request.text[:200],  # 최대 200자
            spam_prob=spam_prob,
            label=label,
            gateway_action=gateway_action,
            requires_exaone=requires_exaone,
        )
        session.add_request(history_item)

        # 응답 생성
        response = GatewayResponse(
            request_id=request_id,
            session_id=session_id,
            spam_prob=spam_prob,
            label=label,
            confidence=confidence,
            threshold_zone=threshold_zone,
            method="koelectra",
            requires_exaone=requires_exaone,
            gateway_action=gateway_action,
            gateway_message=gateway_message,
            exaone_used=False,  # 현재는 EXAONE 호출하지 않음
            exaone_result=None,
            session_request_count=session.request_count,
            timestamp=datetime.now().isoformat(),
        )

        return response

    def get_session_history(self, session_id: str) -> SessionStateState:
        """세션별 요청 히스토리 조회.

        Args:
            session_id: 세션 ID

        Returns:
            세션 상태

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        if session_id not in self._sessions:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")

        return self._sessions[session_id]

    def clear_session(self, session_id: str) -> Dict[str, str]:
        """세션 히스토리 삭제.

        Args:
            session_id: 세션 ID

        Returns:
            삭제 결과

        Raises:
            ValueError: 세션이 존재하지 않는 경우
        """
        if session_id not in self._sessions:
            raise ValueError(f"세션을 찾을 수 없습니다: {session_id}")

        del self._sessions[session_id]
        return {"message": f"세션 {session_id}가 삭제되었습니다.", "session_id": session_id}

    def get_health_status(self) -> Dict[str, any]:
        """MCP Gateway 상태 확인.

        Returns:
            상태 정보
        """
        return {
            "status": "healthy",
            "active_sessions": len(self._sessions),
            "total_requests": sum(s.request_count for s in self._sessions.values()),
            "timestamp": datetime.now().isoformat(),
        }

