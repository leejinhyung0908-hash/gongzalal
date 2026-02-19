from __future__ import annotations
from datetime import datetime
from typing import List, Optional

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.shared.bases import Base

class MentoringKnowledge(Base):
    """멘토링 지식 테이블 — 합격 수기 기반 Q&A 지식 저장소."""

    __tablename__ = "mentoring_knowledge"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    thought_process: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    if Vector is not None:
        knowledge_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1024), nullable=True
        )
    else:
        knowledge_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    def __repr__(self) -> str:
        return f"<MentoringKnowledge(id={self.id}, instruction='{self.instruction[:30]}...')>"
