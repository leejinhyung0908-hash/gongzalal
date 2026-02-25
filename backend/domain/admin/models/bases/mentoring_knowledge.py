from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

from sqlalchemy import DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.shared.bases import Base


class MentoringKnowledge(Base):
    """멘토링 지식 테이블 — 합격 수기 원문 저장소.

    merged_success_stories.jsonl 데이터를 1:1 매핑하여 저장하고,
    KURE-v1 임베딩(1024차원)으로 RAG 벡터 검색을 지원합니다.
    """

    __tablename__ = "mentoring_knowledge"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── 데이터 출처 ──────────────────────────────────────────────
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # gongdanki / megagong

    # ── 합격 수기 원문 필드 (JSONL 1:1 매핑) ─────────────────────
    exam_info: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    study_style: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    daily_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subject_methods: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    interview_prep: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulties: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── 검색 / 임베딩 ────────────────────────────────────────────
    search_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 임베딩 대상 결합 텍스트
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    if Vector is not None:
        knowledge_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1024), nullable=True
        )
    else:
        knowledge_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    def __repr__(self) -> str:
        info = self.exam_info or {}
        label = f"{info.get('exam_type', '')} {info.get('grade', '')}급 {info.get('job_series', '')}"
        return f"<MentoringKnowledge(id={self.id}, source='{self.source}', exam='{label.strip()}')>"
