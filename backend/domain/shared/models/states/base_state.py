#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
공통 상태 베이스 클래스 (LangGraph용)

모든 Orchestrator의 상태 스키마가 상속할 베이스 클래스입니다.
"""

from typing import TypedDict, Optional, Dict, Any, List


class BaseProcessingState(TypedDict):
    """공통 처리 상태 베이스 클래스.

    모든 Orchestrator의 상태가 공통으로 가지는 필드들을 정의합니다.
    """

    # 요청 데이터
    request_text: str
    request_data: Dict[str, Any]

    # KoELECTRA 분석 결과
    koelectra_result: Optional[Dict[str, Any]]

    # 처리 결과
    result: Optional[Dict[str, Any]]

    # 에러 정보
    error: Optional[str]

    # 메타데이터
    metadata: Optional[Dict[str, Any]]

