from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.shared.bases import Base

if TYPE_CHECKING:
    from backend.domain.admin.models.bases.user import User
    from backend.domain.admin.models.bases.question import Question

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

class UserSolvingLog(Base):
    """사용자 풀이 로그 테이블."""

    __tablename__ = "user_solving_logs"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 외래 키 - 사용자
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # 외래 키 - 문제
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False
    )

    # 사용자가 선택한 답안 (예: '1', 'A')
    selected_answer: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # 타임스탬프 (풀이 시간)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Vector 임베딩
    # ─────────────────────────────────────────────────────────────
    # 벡터 컬럼 정의 (if Vector is not None 분기)
    if Vector is not None:
        solving_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1024), nullable=True
        )
    else:
        solving_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    # 풀이 소요 시간 (초 단위)
    time_spent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 특별 이벤트 (예: 'hint_used','skipped')
    special_event: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 오답 노트 작성 여부
    is_wrong_note: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ─────────────────────────────────────────────────────────────
    # 관계 (Relationships)
    # ─────────────────────────────────────────────────────────────

    # 사용자 (N:1)
    user: Mapped["User"] = relationship(back_populates="solving_logs")

    # 문제 (N:1)
    question: Mapped["Question"] = relationship(back_populates="solving_logs")

    def __repr__(self) -> str:
        return f"<UserSolvingLog(id={self.id}, user_id={self.user_id}, question_id={self.question_id})>"
