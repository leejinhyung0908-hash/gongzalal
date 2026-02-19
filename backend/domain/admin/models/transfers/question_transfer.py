"""Question 관련 Pydantic(transfer) 모델.

새 테이블 구조:
- Questions: 개별 문제 정보 (exam_id FK로 Exams 참조)
- Question_Images: 문제 관련 이미지
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime

from pydantic import BaseModel, Field


class QuestionTransfer(BaseModel):
    """Question SQLAlchemy 모델을 기반으로 한 Pydantic transfer 모델."""

    id: Optional[int] = Field(default=None, description="questions.id")

    # 외래키
    exam_id: int = Field(..., description="시험 ID (exams.id FK)")

    # 문제 메타
    question_no: int = Field(..., ge=1, le=200, description="문제 번호 (1~200)")
    question_text: str = Field(..., description="문제 지문 텍스트")
    sub_category: Optional[str] = Field(default=None, description="하위 카테고리")
    answer_key: str = Field(..., description="정답 키 (예: '1', 'A')")
    ind: Optional[bool] = Field(default=None, description="독립 소스 여부")
    source_pdf: Optional[str] = Field(default=None, description="원본 PDF 파일 경로")
    extra_json: Optional[Dict[str, Any]] = Field(
        default=None, description="추가 데이터 (JSON)"
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


class QuestionWithExamTransfer(BaseModel):
    """Question + Exam 정보 통합 Pydantic transfer 모델.

    기존 exam_questions 테이블과의 호환성을 위한 통합 모델.
    """

    id: Optional[int] = Field(default=None, description="questions.id")

    # Exam 정보 (조인 결과)
    year: int = Field(..., description="시험 연도")
    exam_type: str = Field(..., description="시험 유형")
    series: Optional[str] = Field(default=None, description="시험 시리즈")
    grade: Optional[str] = Field(default=None, description="시험 등급")
    subject: str = Field(..., description="과목 이름")

    # Question 정보
    question_no: int = Field(..., ge=1, le=200, description="문제 번호")
    question_text: str = Field(..., description="문제 지문 텍스트")
    sub_category: Optional[str] = Field(default=None, description="하위 카테고리")
    answer_key: str = Field(..., description="정답 키")
    ind: Optional[bool] = Field(default=None, description="독립 소스 여부")
    source_pdf: Optional[str] = Field(default=None, description="원본 PDF 파일 경로")
    extra_json: Optional[Dict[str, Any]] = Field(default=None, description="추가 데이터")

    # 타임스탬프
    created_at: Optional[datetime] = Field(default=None, description="생성 시각")
    updated_at: Optional[datetime] = Field(default=None, description="갱신 시각")

    class Config:
        """Pydantic 설정."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }


class QuestionCreateRequest(BaseModel):
    """Question 생성 요청."""

    exam_id: int = Field(..., description="시험 ID")
    question_no: int = Field(..., ge=1, le=200, description="문제 번호")
    question_text: str = Field(..., min_length=1, description="문제 지문")
    answer_key: str = Field(..., min_length=1, max_length=10, description="정답 키")
    sub_category: Optional[str] = Field(default=None, max_length=50, description="하위 카테고리")
    ind: Optional[bool] = Field(default=None, description="독립 소스 여부")
    source_pdf: Optional[str] = Field(default=None, max_length=255, description="원본 PDF 경로")
    extra_json: Optional[Dict[str, Any]] = Field(default=None, description="추가 데이터")


class QuestionUpdateRequest(BaseModel):
    """Question 수정 요청."""

    question_no: Optional[int] = Field(default=None, ge=1, le=200, description="문제 번호")
    question_text: Optional[str] = Field(default=None, min_length=1, description="문제 지문")
    answer_key: Optional[str] = Field(default=None, min_length=1, max_length=10, description="정답 키")
    sub_category: Optional[str] = Field(default=None, max_length=50, description="하위 카테고리")
    ind: Optional[bool] = Field(default=None, description="독립 소스 여부")
    source_pdf: Optional[str] = Field(default=None, max_length=255, description="원본 PDF 경로")
    extra_json: Optional[Dict[str, Any]] = Field(default=None, description="추가 데이터")


class QuestionSearchRequest(BaseModel):
    """Question 검색 요청."""

    exam_id: Optional[int] = Field(default=None, description="시험 ID")
    year: Optional[int] = Field(default=None, description="시험 연도")
    exam_type: Optional[str] = Field(default=None, description="시험 유형")
    subject: Optional[str] = Field(default=None, description="과목 이름")
    question_no: Optional[int] = Field(default=None, description="문제 번호")
    sub_category: Optional[str] = Field(default=None, description="하위 카테고리")
    limit: int = Field(default=20, ge=1, le=100, description="최대 결과 수")
    offset: int = Field(default=0, ge=0, description="시작 위치")


class QuestionImageTransfer(BaseModel):
    """QuestionImage SQLAlchemy 모델을 기반으로 한 Pydantic transfer 모델."""

    id: Optional[int] = Field(default=None, description="question_images.id")
    question_id: int = Field(..., description="문제 ID (questions.id FK)")
    file_path: str = Field(..., description="이미지 파일 경로")
    coordinates_json: Optional[Dict[str, Any]] = Field(
        default=None, description="YOLO cropping 좌표"
    )
    image_type: Optional[str] = Field(default=None, description="이미지 유형")
    created_at: Optional[datetime] = Field(default=None, description="생성 시각")

    class Config:
        """Pydantic 설정."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }


class QuestionAnswerResponse(BaseModel):
    """문제 정답 조회 응답 (기존 ExamAnswerResponse 대체)."""

    year: int
    exam_type: str
    series: Optional[str] = None
    grade: Optional[str] = None
    subject: str
    question_no: int
    answer_key: str

