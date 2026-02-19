#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chat 처리 상태 정의 (LangGraph용)

종합 라우터 역할을 하는 ChatFlow의 상태 스키마입니다.
KoELECTRA 1차 분류 → 키워드 2차 세분화 → 라우팅 흐름을 지원합니다.
"""

from typing import TypedDict, Optional, Dict, Any, List, Literal

from backend.domain.shared.models.states.base_state import BaseProcessingState


class ChatProcessingState(BaseProcessingState):
    """Chat 처리 상태 (LangGraph용).

    KoELECTRA 게이트웨이 분류 + 키워드 세분화로 적절한 Flow에 라우팅합니다.
    멀티턴 대화 이력 및 질문 재구성 결과도 포함합니다.
    """

    # ── KoELECTRA 1차 분류 결과 ──
    koelectra_gateway: Optional[str]       # "BLOCK" / "POLICY_BASED" / "RULE_BASED"
    koelectra_confidence: Optional[float]  # 분류 신뢰도 (0.0 ~ 1.0)
    koelectra_intent: Optional[str]        # "DB_QUERY" / "EXPLAIN" / "ADVICE" / "OUT_OF_DOMAIN"
    koelectra_method: Optional[str]        # "koelectra_gateway" / "keyword_fallback"

    # 요청 분류 결과 (2차 세분화 후 최종)
    request_type: Optional[Literal[
        "exam", "question", "study_plan", "solving_log",
        "mentoring", "audio_note", "chat", "block",
    ]]

    # 라우팅 대상 Flow
    target_flow: Optional[str]

    # 라우팅 결과 (하위 Flow에서 처리된 결과)
    routed_result: Optional[Dict[str, Any]]

    # ── 멀티턴 대화 관련 필드 ──
    # Redis에서 불러온 이전 대화 이력
    chat_history: Optional[List[Dict[str, Any]]]

    # Query Rewriter가 재구성한 검색 쿼리
    rewritten_query: Optional[str]

    # 대화 맥락 요약 (키워드 또는 한 줄 요약)
    context_summary: Optional[str]

    # 대화 세션 ID (thread_id)
    thread_id: Optional[str]

