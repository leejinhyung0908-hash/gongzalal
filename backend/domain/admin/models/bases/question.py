from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.shared.bases import Base

if TYPE_CHECKING:
    from backend.domain.admin.models.bases.exam import Exam
    from backend.domain.admin.models.bases.question_image import QuestionImage
    from backend.domain.admin.models.bases.commentary import Commentary
    from backend.domain.admin.models.bases.user_solving_log import UserSolvingLog

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

class Question(Base):
    """문제 테이블."""

    __tablename__ = "questions"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 외래 키 - 시험
    exam_id: Mapped[int] = mapped_column(
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False
    )

    # 문제 번호 (시험 내 순서)
    question_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # 문제 지문 텍스트
    question_text: Mapped[str] = mapped_column(Text, nullable=False)

    # 하위 카테고리 (예: '기본', '심화')
    sub_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 정답 키 (예: '1', 'A')
    answer_key: Mapped[str] = mapped_column(String(10), nullable=False)

    # 독립 소스 여부 (source independent indicator)
    ind: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # 원본 PDF 파일 경로
    source_pdf: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 추가 데이터 (JSON 형식 - 보기 옵션, 난이도 등)
    extra_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    # ─────────────────────────────────────────────────────────────
    # 벡터 임베딩 컬럼 추가
    # ─────────────────────────────────────────────────────────────
    if Vector is not None:
        question_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1024), nullable=True
        )
    else:
        question_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    # ─────────────────────────────────────────────────────────────
    # 관계 (Relationships)
    # ─────────────────────────────────────────────────────────────

    # 시험 (N:1)
    exam: Mapped["Exam"] = relationship(back_populates="questions")

    # 문제 이미지 (1:N)
    images: Mapped[List["QuestionImage"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan"
    )

    # 해설 (1:N)
    commentaries: Mapped[List["Commentary"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan"
    )

    # 풀이 로그 (1:N)
    solving_logs: Mapped[List["UserSolvingLog"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, exam_id={self.exam_id}, question_no={self.question_no})>"
