"""Commentary 관련 Pydantic(transfer) 모델.

새 테이블 구조:
- Commentaries: 문제 해설 + 합격 수기
- Audio_Notes: TTS 오디오 파일
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from datetime import datetime

from pydantic import BaseModel, Field


# ============================================================================
# Commentary Transfer 모델
# ============================================================================

class CommentaryTransfer(BaseModel):
    """Commentary SQLAlchemy 모델을 기반으로 한 Pydantic transfer 모델."""

    id: Optional[int] = Field(default=None, description="commentaries.id")

    # 외래키
    user_id: Optional[int] = Field(default=None, description="사용자 ID (users.id FK, optional)")
    question_id: Optional[int] = Field(default=None, description="문제 ID (questions.id FK, optional)")

    # 해설 데이터
    body: str = Field(..., min_length=1, description="해설 본문 텍스트")
    type: Optional[str] = Field(default=None, description="해설 유형 (수기/합격수기/해설/멘토링)")

    # 합격 수기 전용 필드
    success_period: Optional[str] = Field(default=None, description="수험 기간 (예: '1년~1년 6개월')")
    target_exam: Optional[str] = Field(default=None, description="목표 시험 (예: '국가직 9급')")
    final_score: Optional[int] = Field(default=None, description="최종 합격 점수")
    approved: bool = Field(default=False, description="관리자 승인 여부")

    # 벡터 임베딩 (선택)
    commentary_vector: Optional[List[float]] = Field(
        default=None, description="해설 벡터 임베딩 (1024차원, KURE-v1)"
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


class CommentaryCreateRequest(BaseModel):
    """Commentary 생성 요청."""

    user_id: Optional[int] = Field(default=None, ge=1, description="사용자 ID (optional)")
    question_id: Optional[int] = Field(default=None, ge=1, description="문제 ID (optional)")
    body: str = Field(..., min_length=1, description="해설 본문")
    type: Optional[str] = Field(default=None, description="해설 유형")

    # 합격 수기 전용 필드
    success_period: Optional[str] = Field(default=None, max_length=100, description="수험 기간")
    target_exam: Optional[str] = Field(default=None, max_length=100, description="목표 시험")
    final_score: Optional[int] = Field(default=None, ge=0, le=100, description="최종 점수")


class CommentaryUpdateRequest(BaseModel):
    """Commentary 수정 요청."""

    body: Optional[str] = Field(default=None, min_length=1, description="해설 본문")
    type: Optional[str] = Field(default=None, description="해설 유형")
    success_period: Optional[str] = Field(default=None, max_length=100, description="수험 기간")
    target_exam: Optional[str] = Field(default=None, max_length=100, description="목표 시험")
    final_score: Optional[int] = Field(default=None, ge=0, le=100, description="최종 점수")
    approved: Optional[bool] = Field(default=None, description="관리자 승인 여부")


class CommentaryResponse(BaseModel):
    """Commentary 응답."""

    id: int = Field(..., description="해설 ID")
    user_id: Optional[int] = Field(default=None, description="사용자 ID")
    question_id: Optional[int] = Field(default=None, description="문제 ID")
    body: str = Field(..., description="해설 본문")
    type: Optional[str] = Field(default=None, description="해설 유형")
    success_period: Optional[str] = Field(default=None, description="수험 기간")
    target_exam: Optional[str] = Field(default=None, description="목표 시험")
    final_score: Optional[int] = Field(default=None, description="최종 점수")
    approved: bool = Field(default=False, description="승인 여부")
    created_at: Optional[str] = Field(default=None, description="생성 시각 (ISO)")
    updated_at: Optional[str] = Field(default=None, description="갱신 시각 (ISO)")


class SuccessStoryCreateRequest(BaseModel):
    """합격 수기 생성 요청 (Commentary의 특화 버전)."""

    user_id: Optional[int] = Field(default=None, ge=1, description="작성자 ID")
    body: str = Field(..., min_length=10, description="합격 수기 본문")
    success_period: str = Field(..., max_length=100, description="수험 기간")
    target_exam: str = Field(..., max_length=100, description="목표 시험")
    final_score: Optional[int] = Field(default=None, ge=0, le=100, description="최종 점수")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "body": "1년~1년 6개월 수험기간, 국가직 합격을 목표로 했을 때...",
                "success_period": "1년~1년 6개월",
                "target_exam": "국가직 9급",
                "final_score": 85
            }
        }


class SuccessStorySearchRequest(BaseModel):
    """합격 수기 검색 요청."""

    query: str = Field(..., min_length=1, description="검색 쿼리")
    target_exam: Optional[str] = Field(default=None, description="목표 시험 필터")
    min_score: Optional[int] = Field(default=None, ge=0, le=100, description="최소 점수 필터")
    approved_only: bool = Field(default=True, description="승인된 수기만 검색")
    top_k: int = Field(default=3, ge=1, le=20, description="반환할 결과 수")


# ============================================================================
# AudioNote Transfer 모델
# ============================================================================

class AudioNoteTransfer(BaseModel):
    """AudioNote SQLAlchemy 모델을 기반으로 한 Pydantic transfer 모델."""

    id: Optional[int] = Field(default=None, description="audio_notes.id")
    commentary_id: int = Field(..., description="해설 ID (commentaries.id FK)")
    file_path: str = Field(..., description="오디오 파일 경로")
    voice_type: Optional[str] = Field(default=None, description="음성 유형")
    duration: Optional[int] = Field(default=None, description="지속 시간 (초)")
    created_at: Optional[datetime] = Field(default=None, description="생성 시각")

    class Config:
        """Pydantic 설정."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }


class AudioNoteCreateRequest(BaseModel):
    """AudioNote 생성 요청."""

    commentary_id: int = Field(..., ge=1, description="해설 ID")
    file_path: str = Field(..., max_length=255, description="오디오 파일 경로")
    voice_type: Optional[str] = Field(default=None, max_length=20, description="음성 유형")
    duration: Optional[int] = Field(default=None, ge=0, description="지속 시간 (초)")


class AudioNoteResponse(BaseModel):
    """AudioNote 응답."""

    id: int = Field(..., description="오디오 노트 ID")
    commentary_id: int = Field(..., description="해설 ID")
    file_path: str = Field(..., description="파일 경로")
    voice_type: Optional[str] = Field(default=None, description="음성 유형")
    duration: Optional[int] = Field(default=None, description="지속 시간 (초)")
    created_at: Optional[str] = Field(default=None, description="생성 시각 (ISO)")
