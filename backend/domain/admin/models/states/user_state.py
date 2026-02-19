#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User 상태 정의 (State Machine용)

새 테이블 구조:
- Users: 사용자 프로필 정보
- Study_Plans: 학습 계획
- User_Solving_Logs: 풀이 로그
"""

from enum import Enum
from typing import TypedDict, Optional, Dict, Any, List

from backend.domain.shared.models.states.base_state import BaseProcessingState


class UserState(str, Enum):
    """사용자 상태."""

    # 계정 생명주기
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"

    # 서비스 관점 상태(옵션)
    ONBOARDING = "onboarding"


class EmploymentStatusState(str, Enum):
    """직장 상태 (DB ENUM과 동기화)."""

    EMPLOYED = "재직"
    UNEMPLOYED = "무직"
    STUDENT = "학생"
    SELF_EMPLOYED = "자영업"
    OTHER = "기타"


class UserProcessingState(BaseProcessingState):
    """User 처리 상태 (LangGraph용)."""

    # KoELECTRA 분석 결과
    spam_prob: Optional[float]
    label: Optional[str]
    confidence: Optional[str]

    # 전략 판단 결과
    strategy: Optional[str]  # "rule_based", "policy_based"


class UserDataState(TypedDict):
    """User 테이블 데이터 상태.

    `backend/domain/admin/models/bases/user.py`의
    User SQLAlchemy 모델을 참조하여 작성한 TypedDict입니다.
    """

    # 기본 식별자
    id: int

    # 사용자 정보
    display_name: str
    age: Optional[int]
    employment_status: Optional[str]
    base_score: Optional[int]
    daily_study_time: Optional[int]
    target_date: Optional[str]  # ISO 형식 날짜

    # 타임스탬프 (ISO 형식 문자열)
    registration_date: str
    last_login: Optional[str]


class StudyPlanState(TypedDict):
    """StudyPlan 테이블 데이터 상태.

    `backend/domain/admin/models/bases/study_plan.py`의
    StudyPlan SQLAlchemy 모델을 참조하여 작성한 TypedDict입니다.
    """

    # 기본 식별자
    id: int
    user_id: int

    # 계획 데이터
    plan_json: Optional[Dict[str, Any]]
    version: int

    # 타임스탬프
    created_at: Optional[str]
    updated_at: Optional[str]


class UserSolvingLogState(TypedDict):
    """UserSolvingLog 테이블 데이터 상태.

    `backend/domain/admin/models/bases/user_solving_log.py`의
    UserSolvingLog SQLAlchemy 모델을 참조하여 작성한 TypedDict입니다.
    """

    # 기본 식별자
    id: int
    user_id: int
    question_id: int

    # 풀이 데이터
    selected_answer: Optional[str]
    time_spent: Optional[int]
    special_event: Optional[str]
    is_wrong_note: bool

    # 타임스탬프
    created_at: Optional[str]
