#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KoELECTRA 게이트웨이 라우터

KoELECTRA를 1차 필터(게이트웨이)로 사용하여 빠르게 spam_prob를 산출합니다.
상태관리 기능을 포함하여 세션별로 요청을 추적합니다.

EXAONE 판별기는 별도 에이전트(verdict_agent)로 분리되었습니다.
"""

from fastapi import APIRouter, HTTPException

# 모델 import
from backend.domain.admin.models.transfers.base_model import GatewayRequest, GatewayResponse
from backend.domain.admin.models.transfers.state_model import SessionStateState

# 컨트롤러 import (ochestrator로 통합됨)
from backend.domain.admin.hub.orchestrators.mcp_controller import McpController

router = APIRouter(prefix="/api/mcp", tags=["mcp-gateway"])

# 컨트롤러 인스턴스 (싱글톤 패턴)
_controller = McpController()


@router.post("/gateway", response_model=GatewayResponse)
async def gateway_endpoint(request: GatewayRequest) -> GatewayResponse:
    """
    KoELECTRA 게이트웨이 엔드포인트

    KoELECTRA를 1차 필터로 사용하여 빠르게 spam_prob를 산출하고,
    임계치에 따라 게이트웨이 결정을 내립니다.

    Args:
        request: 게이트웨이 요청 (text, session_id, request_id)

    Returns:
        게이트웨이 응답 (spam_prob, requires_exaone, gateway_action 등)
    """
    try:
        return await _controller.process_gateway_request(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        print(f"[GATEWAY] 오류 발생: {exc}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(exc)}")


@router.get("/gateway/session/{session_id}", response_model=SessionStateState)
async def get_session_history(session_id: str) -> SessionStateState:
    """세션별 요청 히스토리 조회"""
    try:
        return _controller.get_session_history(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/gateway/session/{session_id}")
async def clear_session(session_id: str):
    """세션 히스토리 삭제"""
    try:
        return _controller.clear_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/health")
async def mcp_health_check():
    """MCP Gateway 상태 확인"""
    return _controller.get_health_status()

