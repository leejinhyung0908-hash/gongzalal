"""
데이터베이스 세션 관리
FastAPI 의존성 주입을 위한 세션 팩토리 및 get_db 함수
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config import settings

def create_database_engine():
    """데이터베이스 엔진 생성"""
    database_url = settings.DATABASE_URL

    # PostgreSQL URL을 asyncpg로 변환
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # 엔진 설정
    engine_kwargs = {
        "echo": settings.DEBUG,
        "future": True,
        "pool_pre_ping": True,
    }

    # SQLite의 경우 특별 설정 (테스트 환경)
    if "sqlite" in database_url:
        engine_kwargs.update({
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,
            },
        })

    return create_async_engine(database_url, **engine_kwargs)

# 전역 엔진 인스턴스
engine = create_database_engine()

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    데이터베이스 세션 의존성
    FastAPI Depends와 함께 사용

    사용 예:

@router
.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_database():
    """
    데이터베이스 연결 확인 및 마이그레이션 상태 체크
    ❌ DDL 자동 생성 금지 - Alembic 우선 전략
    ✅ 연결 테스트 및 마이그레이션 상태만 확인
    """
    from sqlalchemy import text

    try:
        async with engine.begin() as conn:
            # 데이터베이스 연결 테스트
            await conn.execute(text("SELECT 1"))

            # alembic_version 테이블 존재 확인 (마이그레이션 적용 여부)
            result = await conn.execute(
                text("SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version'")
            )
            alembic_exists = result.fetchone() is not None

            if not alembic_exists:
                # 마이그레이션 미적용 경고 (앱 종료하지 않고 경고만)
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("⚠️ alembic_version 테이블이 없습니다. 마이그레이션을 적용하세요: alembic upgrade head")

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise

async def check_migration_status() -> bool:
    """
    마이그레이션 적용 여부 확인 (fail-fast)
    앱 시작 시 가볍게 체크하여 마이그레이션 미적용 시 명확한 에러
    """
    from sqlalchemy import text
    # MigrationNotAppliedError는 없으므로 일반 Exception 사용
    import logging

    logger = logging.getLogger(__name__)

    try:
        async with AsyncSessionLocal() as session:
            # alembic_version 테이블 존재 여부 확인
            result = await session.execute(
                text("SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version'")
            )
            exists = result.fetchone() is not None

            if not exists:
                logger.warning("alembic_version 테이블이 존재하지 않습니다. 'alembic upgrade head'를 실행하세요.")
                return False

            logger.info("데이터베이스 마이그레이션 상태 확인 완료")
            return True
    except Exception as e:
        logger.warning(f"마이그레이션 상태 확인 실패 (무시하고 진행): {e}")
        return False

async def close_database():
    """
    데이터베이스 연결 종료
    애플리케이션 종료 시 호출
    """
    await engine.dispose()
