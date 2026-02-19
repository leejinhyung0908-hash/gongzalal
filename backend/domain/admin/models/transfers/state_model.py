#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상태 관리 모델

세션별 요청 히스토리 및 상태 관리를 위한 Pydantic 모델
"""

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class RequestHistoryState(BaseModel):
    """개별 요청 히스토리 상태 모델"""
    request_id: str = Field(..., description="요청 ID")
    timestamp: str = Field(..., description="요청 시간 (ISO 형식)")
    text: str = Field(..., description="분석된 텍스트 (최대 200자)")
    spam_prob: float = Field(..., description="스팸 확률 (0.0 ~ 1.0)")
    label: str = Field(..., description="라벨 (ham/spam/uncertain)")
    gateway_action: str = Field(..., description="게이트웨이 액션 (deliver/quarantine/block/analyze)")
    requires_exaone: bool = Field(..., description="EXAONE 판별기 필요 여부")


class SessionStateState(BaseModel):
    """세션별 상태 관리 모델"""
    session_id: str = Field(..., description="세션 ID")
    created_at: str = Field(..., description="세션 생성 시간 (ISO 형식)")
    updated_at: str = Field(..., description="세션 마지막 업데이트 시간 (ISO 형식)")
    request_count: int = Field(default=0, description="요청 수")
    history: List[RequestHistoryState] = Field(default_factory=list, description="요청 히스토리 리스트")

    def add_request(self, request_history: RequestHistoryState) -> None:
        """요청 히스토리 추가"""
        self.history.append(request_history)
        self.request_count = len(self.history)
        self.updated_at = datetime.now().isoformat()

    def clear_history(self) -> None:
        """히스토리 초기화"""
        self.history.clear()
        self.request_count = 0
        self.updated_at = datetime.now().isoformat()

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "created_at": "2024-01-15T10:00:00",
                "updated_at": "2024-01-15T10:05:00",
                "request_count": 3,
                "history": [
                    {
                        "request_id": "req_20240115_100000",
                        "timestamp": "2024-01-15T10:00:00",
                        "text": "테스트 메일 내용...",
                        "spam_prob": 0.45,
                        "label": "uncertain",
                        "gateway_action": "analyze",
                        "requires_exaone": True
                    }
                ]
            }
        }

