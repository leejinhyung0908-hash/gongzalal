"""
데이터베이스 모듈
루즈한 결합도로 설계된 공통 Base와 믹스인 제공
"""
from backend.core.database.base import Base
from backend.core.database.mixin import (
    TimestampMixin,
    SoftDeleteMixin,
    StatusMixin,
)
from backend.core.database.session import (
    engine,
    AsyncSessionLocal,
    get_db,
    init_database,
    check_migration_status,
    close_database,
    create_database_engine,
)

__all__ = [
    # Base
    "Base",
    # Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    "StatusMixin",
    # Session
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_database",
    "check_migration_status",
    "close_database",
    "create_database_engine",
]
