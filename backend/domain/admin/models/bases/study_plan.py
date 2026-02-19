from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, List

from sqlalchemy import DateTime, ForeignKey, SmallInteger, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.shared.bases import Base

if TYPE_CHECKING:
    from backend.domain.admin.models.bases.user import User

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

class StudyPlan(Base):
    """학습 계획 테이블."""

    __tablename__ = "study_plans"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 외래 키 - 사용자
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # 학습 계획 데이터 (JSON 형식)
    # 예: {"week1": [...], "week2": [...]}
    plan_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # 계획 버전 (업데이트 이력 관리)
    version: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)

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
    # Vector 컬럼 추가 (if Vector is available)
    if Vector is not None:
        plan_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1024), nullable=True
        )
    else:
        plan_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    # ─────────────────────────────────────────────────────────────
    # 관계 (Relationships)
    # ─────────────────────────────────────────────────────────────

    # 사용자 (N:1)
    user: Mapped["User"] = relationship(back_populates="study_plans")

    def __repr__(self) -> str:
        return f"<StudyPlan(id={self.id}, user_id={self.user_id}, version={self.version})>"
