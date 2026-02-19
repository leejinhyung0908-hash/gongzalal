"""Commentaries 테이블 (SQLAlchemy 모델).

문제 해설을 저장합니다. 본문 텍스트, 유형(ENUM: 수기/해설/멘토링), 벡터 임베딩을
관리하여 상세 설명과 멘토링을 제공합니다.

합격 수기(Success Story) 기능:
- type='수기'로 합격 수기 저장 가능
- success_period, target_exam, final_score 등 수기 전용 필드 지원
- approved 필드로 관리자 승인 여부 관리

관계:
- Users: N:1 (user_id FK로 참조, 생성자, optional)
- Questions: N:1 (question_id FK로 참조, 문제에 속함) - 수기는 NULL 가능
- Audio_Notes: 1:N (commentary_id FK로 연결, 해설별 오디오)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.shared.bases import Base
from backend.domain.admin.models.enums import CommentaryType

# pgvector 지원
try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

if TYPE_CHECKING:
    from backend.domain.admin.models.bases.user import User
    from backend.domain.admin.models.bases.question import Question
    from backend.domain.admin.models.bases.audio_note import AudioNote


class Commentary(Base):
    """해설 테이블."""

    __tablename__ = "commentaries"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 외래 키 - 사용자 (생성자, optional)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # 외래 키 - 문제 (합격 수기는 NULL 허용)
    question_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=True  # 일반 합격 수기는 특정 문제와 연결되지 않을 수 있음
    )

    # 해설 본문 텍스트
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # 해설 유형 (ENUM: 수기, 해설, 멘토링)
    type: Mapped[Optional[CommentaryType]] = mapped_column(
        Enum(CommentaryType, name="commentary_type_enum", create_type=True),
        nullable=True
    )

    # ─────────────────────────────────────────────────────────────
    # 합격 수기 전용 필드 (type='수기' 일 때 사용)
    # ─────────────────────────────────────────────────────────────

    # 수험 기간 (예: '1년~1년 6개월')
    success_period: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 목표 시험 (예: '국가직 9급', '보호직')
    target_exam: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 최종 합격 점수
    final_score: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # 관리자 승인 여부 (UGC 부적절 콘텐츠 필터링용)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    # 벡터 임베딩
    if Vector is not None:
        commentary_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1024), nullable=True
        )
    else:
        commentary_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    # ─────────────────────────────────────────────────────────────
    # 관계 (Relationships)
    # ─────────────────────────────────────────────────────────────

    # 사용자 (N:1, optional)
    user: Mapped[Optional["User"]] = relationship(back_populates="commentaries")

    # 문제 (N:1, 합격 수기는 NULL 가능)
    question: Mapped[Optional["Question"]] = relationship(back_populates="commentaries")

    # 오디오 노트 (1:N)
    audio_notes: Mapped[List["AudioNote"]] = relationship(
        back_populates="commentary",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Commentary(id={self.id}, question_id={self.question_id}, type={self.type})>"
