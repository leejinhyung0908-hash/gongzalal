"""Users 테이블 (SQLAlchemy 모델).

사용자 프로필 정보를 저장합니다. 사용자의 기본 정보(이름, 나이, 직장 상태,
베이스 점수, 일일 학습 시간, 목표 날짜, 등록/마지막 로그인 시간)를 관리하여
개인화된 학습 경험을 제공합니다.

관계:
- Study_Plans: 1:N (user_id FK로 연결, 사용자별 여러 학습 계획)
- User_Solving_Logs: 1:N (user_id FK로 연결, 사용자별 풀이 로그)
- Commentaries: 1:N (user_id FK로 연결, 사용자 생성 해설, optional)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

try:
    from pgvector.sqlalchemy import Vector  # type: ignore
except ImportError:
    Vector = None  # type: ignore

from sqlalchemy import Date, DateTime, Enum, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.shared.bases import Base
from backend.domain.admin.models.enums import EmploymentStatus

if TYPE_CHECKING:
    from backend.domain.admin.models.bases.study_plan import StudyPlan
    from backend.domain.admin.models.bases.user_solving_log import UserSolvingLog
    from backend.domain.admin.models.bases.commentary import Commentary


class User(Base):
    """사용자 테이블."""

    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # 사용자 표시 이름 (닉네임 또는 실명)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 사용자 나이 (선택적)
    age: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # 직장 상태 (ENUM)
    employment_status: Mapped[Optional[EmploymentStatus]] = mapped_column(
        Enum(EmploymentStatus, name="employment_status_enum", create_type=True),
        nullable=True
    )

    # 초기 베이스 점수 (모의고사 점수 등)
    base_score: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # 일일 학습 시간 (분 단위)
    daily_study_time: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # 목표 시험 날짜
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # 등록 날짜 (자동 설정)
    registration_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # 마지막 로그인
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # 소셜 로그인 연동
    social_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ─────────────────────────────────────────────────────────────
    # 벡터 임베딩 컬럼 추가
    # ─────────────────────────────────────────────────────────────
    if Vector is not None:
        user_vector: Mapped[Optional[List[float]]] = mapped_column(
            Vector(1024), nullable=True
        )
    else:
        user_vector: Mapped[Optional[List[float]]] = mapped_column(nullable=True)  # type: ignore[assignment]

    # ─────────────────────────────────────────────────────────────
    # 관계 (Relationships)
    # ─────────────────────────────────────────────────────────────

    # 학습 계획 (1:N)
    study_plans: Mapped[List["StudyPlan"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # 풀이 로그 (1:N)
    solving_logs: Mapped[List["UserSolvingLog"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # 해설 (1:N, 사용자가 생성한 해설)
    commentaries: Mapped[List["Commentary"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, display_name='{self.display_name}')>"
