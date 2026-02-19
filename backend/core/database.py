"""
데이터베이스 연결 및 세션 관리 (호환성 레이어)
backend.core.database를 사용하도록 리다이렉트
기존 코드와의 호환성을 위해 유지
"""
# 새로운 구조로 리다이렉트 (루즈한 결합도 유지)
from backend.core.database import (
    Base,
    TimestampMixin,
    SoftDeleteMixin,
    StatusMixin,
    engine,
    AsyncSessionLocal,
    get_db,
    init_database,
    check_migration_status,
    close_database,
    create_database_engine,
)

__all__ = [
"Base",
"TimestampMixin",
"SoftDeleteMixin",
"StatusMixin",
"engine",
"AsyncSessionLocal",
"get_db",
"init_database",
"check_migration_status",
"close_database",
"create_database_engine",
]
