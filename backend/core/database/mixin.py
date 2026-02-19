"""
공통 믹스인 클래스
각 도메인 모델에서 선택적으로 사용 가능 (루즈한 결합도)
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

class TimestampMixin:
    """
    생성일시/수정일시 자동 관리 믹스인
    사용 예: class MyModel(Base, TimestampMixin):
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="생성일시"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="수정일시"
    )

class SoftDeleteMixin:
    """
    소프트 삭제 믹스인
    deleted_at이 None이 아니면 삭제된 것으로 간주
    """
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="삭제일시 (소프트 삭제)"
    )


    @property
    def is_deleted(self) -> bool:
        """삭제 여부 확인"""
        return self.deleted_at is not None

class StatusMixin:
    """
    상태 관리 믹스인
    기본 상태값과 상태 변경 메서드 제공
    """
    status: Mapped[str] = mapped_column(
        nullable=False,
        default="active",
        comment="상태"
    )

    def activate(self):
        """활성화"""
        self.status = "active"

    def deactivate(self):
        """비활성화"""
        self.status = "inactive"

    def suspend(self):
        """일시 중지"""
        self.status = "suspended"


    @property
    def is_active(self) -> bool:
        """활성 상태 확인"""
        return self.status == "active"
