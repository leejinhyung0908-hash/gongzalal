from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

from backend.domain.shared.bases import Base

if TYPE_CHECKING:
    from backend.domain.admin.models.bases.commentary import Commentary

class AudioNote(Base):
    """오디오 노트 테이블."""

    __tablename__ = "audio_notes"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 외래 키 - 해설
    commentary_id: Mapped[int] = mapped_column(
        ForeignKey("commentaries.id", ondelete="CASCADE"),
        nullable=False
    )

    # 오디오 파일 경로 (예: '/audio/c1.mp3')
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)

    # 음성 유형 (예:'male', 'female')
    voice_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # 오디오 지속 시간 (초 단위)
    duration: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # 해설 본문 텍스트 (TTS 변환 원본)
    commentary_text: Mapped[Optional[str]] = mapped_column(
        "commentary", Text, nullable=True
    )

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    # Vector 임베딩
    # ─────────────────────────────────────────────────────────────
    # 벡터 컬럼 정의
    if Vector is not None:
        audio_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1024), nullable=True
        )
    else:
        audio_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    # ─────────────────────────────────────────────────────────────
    # 관계 (Relationships)
    # ─────────────────────────────────────────────────────────────

    # 해설 (N:1)
    commentary: Mapped["Commentary"] = relationship(back_populates="audio_notes")

    def __repr__(self) -> str:
        return f"<AudioNote(id={self.id}, commentary_id={self.commentary_id}, file_path='{self.file_path}')>"
