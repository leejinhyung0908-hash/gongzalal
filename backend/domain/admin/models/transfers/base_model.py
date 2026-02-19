#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기본 요청/응답 모델

게이트웨이 API의 요청 및 응답을 위한 Pydantic 모델
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class GatewayRequest(BaseModel):
    """KoELECTRA 게이트웨이 요청 모델"""
    text: str = Field(..., description="분석할 텍스트 (이메일 제목/내용)")
    session_id: Optional[str] = Field(None, description="세션 ID (상태 관리용, 기본값: 자동 생성)")
    request_id: Optional[str] = Field(None, description="요청 ID (기본값: 자동 생성)")


class GatewayResponse(BaseModel):
    """KoELECTRA 게이트웨이 응답 모델"""
    request_id: str = Field(..., description="요청 ID")
    session_id: str = Field(..., description="세션 ID")

    # KoELECTRA 결과
    spam_prob: float = Field(..., description="스팸 확률 (0.0 ~ 1.0)")
    label: str = Field(..., description="라벨 (ham/spam/uncertain)")
    confidence: str = Field(..., description="신뢰도 (low/medium/high)")
    threshold_zone: str = Field(..., description="임계치 구간 (low/ambiguous/high)")
    method: str = Field(..., description="사용된 방법 (koelectra/keyword)")

    # 게이트웨이 결정
    requires_exaone: bool = Field(..., description="EXAONE 판별기 필요 여부")
    gateway_action: str = Field(..., description="게이트웨이 액션 (deliver/quarantine/block/analyze)")
    gateway_message: str = Field(..., description="게이트웨이 메시지")

    # EXAONE 결과 (애매한 구간에서 호출된 경우)
    exaone_used: bool = Field(default=False, description="EXAONE 판별기 사용 여부")
    exaone_result: Optional[Dict[str, Any]] = Field(default=None, description="EXAONE 분석 결과")

    # 상태 정보
    session_request_count: int = Field(..., description="세션별 요청 수")
    timestamp: str = Field(..., description="요청 시간")

