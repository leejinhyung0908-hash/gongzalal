"""Exam 관련 Pydantic(transfer) 모델.

새 테이블 구조:
- Exams: 시험 메타데이터 (연도, 유형, 시리즈, 등급, 과목)
- Questions: 개별 문제 정보 (exam_id FK로 연결)
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime

from pydantic import BaseModel, Field


class ExamTransfer(BaseModel):
    """Exam SQLAlchemy 모델을 기반으로 한 Pydantic transfer 모델."""

    id: Optional[int] = Field(default=None, description="exams.id")

    # 시험 메타
    year: int = Field(..., description="시험 연도 (예: 2025)")
    exam_type: str = Field(..., description="시험 유형 (예: '공무원', '경찰직')")
    series: Optional[str] = Field(default=None, description="시험 시리즈 (예: '국가직', '지방직')")
    grade: Optional[str] = Field(default=None, description="시험 등급 (예: '9급', '7급')")
    subject: str = Field(..., description="과목 이름 (예: '한국사', '행정법')")

    # 벡터 임베딩 (선택)
    exam_vector: Optional[List[float]] = Field(
        default=None, description="시험 벡터 임베딩 (1024차원, KURE-v1)"
    )

    # 타임스탬프
    created_at: Optional[datetime] = Field(default=None, description="생성 시각")
    updated_at: Optional[datetime] = Field(default=None, description="갱신 시각")

    class Config:
        """Pydantic 설정."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }


class ExamCreateRequest(BaseModel):
    """Exam 생성 요청."""

    year: int = Field(..., ge=2000, le=2100, description="시험 연도")
    exam_type: str = Field(..., min_length=1, max_length=50, description="시험 유형")
    series: Optional[str] = Field(default=None, max_length=50, description="시험 시리즈")
    grade: Optional[str] = Field(default=None, max_length=20, description="시험 등급")
    subject: str = Field(..., min_length=1, max_length=50, description="과목 이름")


class ExamUpdateRequest(BaseModel):
    """Exam 수정 요청."""

    year: Optional[int] = Field(default=None, ge=2000, le=2100, description="시험 연도")
    exam_type: Optional[str] = Field(default=None, min_length=1, max_length=50, description="시험 유형")
    series: Optional[str] = Field(default=None, max_length=50, description="시험 시리즈")
    grade: Optional[str] = Field(default=None, max_length=20, description="시험 등급")
    subject: Optional[str] = Field(default=None, min_length=1, max_length=50, description="과목 이름")


class ExamSearchRequest(BaseModel):
    """Exam 검색 요청."""

    year: Optional[int] = Field(default=None, description="시험 연도")
    exam_type: Optional[str] = Field(default=None, description="시험 유형")
    series: Optional[str] = Field(default=None, description="시험 시리즈")
    grade: Optional[str] = Field(default=None, description="시험 등급")
    subject: Optional[str] = Field(default=None, description="과목 이름")
    limit: int = Field(default=20, ge=1, le=100, description="최대 결과 수")
    offset: int = Field(default=0, ge=0, description="시작 위치")

