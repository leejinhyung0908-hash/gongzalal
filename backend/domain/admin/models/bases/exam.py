"""Exams 테이블 (SQLAlchemy 모델).

시험 메타데이터를 저장합니다. 시험의 연도, 유형, 시리즈, 등급, 과목, 벡터 임베딩을
관리하여 기출 시험을 분류하고 AI 기반 검색/추천을 지원합니다.

관계:
- Questions: 1:N (exam_id FK로 연결, 시험별 여러 문제)
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

from sqlalchemy import DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.shared.bases import Base

if TYPE_CHECKING:
    from backend.domain.admin.models.bases.question import Question


class Exam(Base):
    """시험 메타데이터 테이블."""

    __tablename__ = "exams"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 시험 연도 (예: 2023)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # 시험 유형 (예: '공무원', '경찰직')
    exam_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # 시험 시리즈 (예: '국가직', '지방직')
    series: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 시험 등급 (예: '9급', '7급')
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # 과목 이름 (예: '한국사', '행정법')
    subject: Mapped[str] = mapped_column(String(50), nullable=False)

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
    # ─────────────────────────────────────────────────────────────
    # Vector 컬럼 추가:
    # 컬럼명: exam_vector
    # 타입: Vector(1024), nullable=True (KURE-v1)
    # 설명: 시험 콘텐츠 임베딩 벡터
    # ─────────────────────────────────────────────────────────────
    if Vector is not None:
        exam_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1024), nullable=True
        )
    else:
        exam_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    # ─────────────────────────────────────────────────────────────
    # 관계 (Relationships)
    # ─────────────────────────────────────────────────────────────

    # 문제 (1:N)
    questions: Mapped[List["Question"]] = relationship(
        back_populates="exam",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Exam(id={self.id}, year={self.year}, subject='{self.subject}')>"
