from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, List

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.shared.bases import Base

if TYPE_CHECKING:
    from backend.domain.admin.models.bases.question import Question

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

class QuestionImage(Base):
    """문제 이미지 테이블."""

    __tablename__ = "question_images"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 외래 키 - 문제
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False
    )

    # 이미지 파일 경로 (예: '/images/q1.png')
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)

    # YOLO cropping 좌표 (JSON 형식)
    # 예: {"x": 100, "y": 150, "w": 300, "h": 200}
    coordinates_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # 이미지 유형 (예: 'png', 'jpg')
    image_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    # Vector 임베딩
    # ─────────────────────────────────────────────────────────────
    # # 벡터 임베딩
    # ─────────────────────────────────────────────────────────────
    if Vector is not None:
        image_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1024), nullable=True
        )
    else:
        image_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    # ─────────────────────────────────────────────────────────────
    # 관계 (Relationships)
    # ─────────────────────────────────────────────────────────────

    # 문제 (N:1)
    question: Mapped["Question"] = relationship(back_populates="images")

    def __repr__(self) -> str:
        return f"<QuestionImage(id={self.id}, question_id={self.question_id}, file_path='{self.file_path}')>"
