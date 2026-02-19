"""User 관련 Pydantic(transfer) 모델.

새 테이블 구조:
- Users: 사용자 프로필 정보
- Study_Plans: 학습 계획
- User_Solving_Logs: 풀이 로그
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime, date

from pydantic import BaseModel, Field


# ============================================================================
# User Transfer 모델
# ============================================================================

class UserTransfer(BaseModel):
    """User SQLAlchemy 모델을 기반으로 한 Pydantic transfer 모델."""

    id: Optional[int] = Field(default=None, description="users.id")

    # 사용자 정보
    display_name: str = Field(..., description="표시 이름 (닉네임 또는 실명)")
    age: Optional[int] = Field(default=None, description="나이")
    employment_status: Optional[str] = Field(default=None, description="직장 상태")
    base_score: Optional[int] = Field(default=None, description="초기 베이스 점수")
    daily_study_time: Optional[int] = Field(default=None, description="일일 학습 시간 (분)")
    target_date: Optional[date] = Field(default=None, description="목표 시험 날짜")

    # 타임스탬프
    registration_date: Optional[datetime] = Field(default=None, description="등록 시각")
    last_login: Optional[datetime] = Field(default=None, description="마지막 로그인")

    class Config:
        """Pydantic 설정."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
        }


class UserCreateRequest(BaseModel):
    """User 생성 요청."""

    display_name: str = Field(..., min_length=1, max_length=100, description="표시 이름")
    age: Optional[int] = Field(default=None, ge=0, le=150, description="나이")
    employment_status: Optional[str] = Field(default=None, description="직장 상태")
    base_score: Optional[int] = Field(default=None, ge=0, le=100, description="초기 점수")
    daily_study_time: Optional[int] = Field(default=None, ge=0, description="일일 학습 시간 (분)")
    target_date: Optional[date] = Field(default=None, description="목표 시험 날짜")

    class Config:
        json_schema_extra = {
            "example": {
                "display_name": "홍길동",
                "age": 25,
                "employment_status": "학생",
                "base_score": 70,
                "daily_study_time": 180,
                "target_date": "2026-06-01"
            }
        }


class UserUpdateRequest(BaseModel):
    """User 수정 요청."""

    display_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    age: Optional[int] = Field(default=None, ge=0, le=150)
    employment_status: Optional[str] = Field(default=None)
    base_score: Optional[int] = Field(default=None, ge=0, le=100)
    daily_study_time: Optional[int] = Field(default=None, ge=0)
    target_date: Optional[date] = Field(default=None)


class UserResponse(BaseModel):
    """User 응답 (조회/생성 결과)."""

    id: int = Field(..., description="DB 사용자 ID")
    display_name: str = Field(..., description="표시 이름")
    age: Optional[int] = Field(default=None, description="나이")
    employment_status: Optional[str] = Field(default=None, description="직장 상태")
    base_score: Optional[int] = Field(default=None, description="초기 점수")
    daily_study_time: Optional[int] = Field(default=None, description="일일 학습 시간 (분)")
    target_date: Optional[str] = Field(default=None, description="목표 시험 날짜 (ISO)")
    registration_date: Optional[str] = Field(default=None, description="등록 시각 (ISO)")
    last_login: Optional[str] = Field(default=None, description="마지막 로그인 (ISO)")


# ============================================================================
# StudyPlan Transfer 모델
# ============================================================================

class StudyPlanTransfer(BaseModel):
    """StudyPlan SQLAlchemy 모델을 기반으로 한 Pydantic transfer 모델."""

    id: Optional[int] = Field(default=None, description="study_plans.id")
    user_id: int = Field(..., description="사용자 ID (users.id FK)")
    plan_json: Optional[Dict[str, Any]] = Field(default=None, description="학습 계획 데이터")
    version: int = Field(default=1, description="계획 버전")
    created_at: Optional[datetime] = Field(default=None, description="생성 시각")
    updated_at: Optional[datetime] = Field(default=None, description="갱신 시각")

    class Config:
        """Pydantic 설정."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }


class StudyPlanCreateRequest(BaseModel):
    """StudyPlan 생성 요청."""

    user_id: int = Field(..., ge=1, description="사용자 ID")
    plan_json: Dict[str, Any] = Field(..., description="학습 계획 데이터")


class StudyPlanUpdateRequest(BaseModel):
    """StudyPlan 수정 요청."""

    plan_json: Optional[Dict[str, Any]] = Field(default=None, description="학습 계획 데이터")


# ============================================================================
# UserSolvingLog Transfer 모델
# ============================================================================

class UserSolvingLogTransfer(BaseModel):
    """UserSolvingLog SQLAlchemy 모델을 기반으로 한 Pydantic transfer 모델."""

    id: Optional[int] = Field(default=None, description="user_solving_logs.id")
    user_id: int = Field(..., description="사용자 ID (users.id FK)")
    question_id: int = Field(..., description="문제 ID (questions.id FK)")
    selected_answer: Optional[str] = Field(default=None, description="선택한 답안")
    time_spent: Optional[int] = Field(default=None, description="풀이 소요 시간 (초)")
    special_event: Optional[str] = Field(default=None, description="특별 이벤트")
    is_wrong_note: bool = Field(default=False, description="오답 노트 여부")
    created_at: Optional[datetime] = Field(default=None, description="풀이 시간")

    class Config:
        """Pydantic 설정."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }


class UserSolvingLogCreateRequest(BaseModel):
    """UserSolvingLog 생성 요청."""

    user_id: int = Field(..., ge=1, description="사용자 ID")
    question_id: int = Field(..., ge=1, description="문제 ID")
    selected_answer: Optional[str] = Field(default=None, max_length=10, description="선택 답안")
    time_spent: Optional[int] = Field(default=None, ge=0, description="풀이 소요 시간 (초)")
    special_event: Optional[str] = Field(default=None, max_length=50, description="특별 이벤트")
    is_wrong_note: bool = Field(default=False, description="오답 노트 여부")


class UserSolvingLogResponse(BaseModel):
    """UserSolvingLog 응답."""

    id: int = Field(..., description="풀이 로그 ID")
    user_id: int = Field(..., description="사용자 ID")
    question_id: int = Field(..., description="문제 ID")
    selected_answer: Optional[str] = Field(default=None, description="선택 답안")
    time_spent: Optional[int] = Field(default=None, description="풀이 소요 시간 (초)")
    special_event: Optional[str] = Field(default=None, description="특별 이벤트")
    is_wrong_note: bool = Field(default=False, description="오답 노트 여부")
    is_correct: Optional[bool] = Field(default=None, description="정답 여부 (계산됨)")
    created_at: Optional[str] = Field(default=None, description="풀이 시간 (ISO)")

