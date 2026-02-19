"""
Alembic 환경 설정
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine import Connection

from alembic import context

# 이 설정 객체는 alembic.ini의 [alembic] 섹션을 사용합니다
config = context.config

# 로깅 설정 (alembic.ini의 [loggers] 섹션 사용)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 메타데이터 객체 - 모든 모델을 import하여 Base.metadata에 등록
from backend.domain.shared.bases import Base

# SQLAlchemy 모델들을 import하여 Base.metadata에 등록
# (경로: backend/domain/admin/models/bases/*.py)
from backend.domain.admin.models.bases.user import User
from backend.domain.admin.models.bases.exam import Exam
from backend.domain.admin.models.bases.question import Question
from backend.domain.admin.models.bases.question_image import QuestionImage
from backend.domain.admin.models.bases.commentary import Commentary
from backend.domain.admin.models.bases.audio_note import AudioNote
from backend.domain.admin.models.bases.user_solving_log import UserSolvingLog
from backend.domain.admin.models.bases.study_plan import StudyPlan
from backend.domain.admin.models.bases.mentoring_knowledge import MentoringKnowledge

# Embedding 테이블 (ExaOne으로 생성 예정이므로, 파일이 있을 때만 import)
# 생성 후 여기에 추가:
# from backend.domain.admin.models.bases.exam_embedding import ExamEmbedding
# from backend.domain.admin.models.bases.question_embedding import QuestionEmbedding
# from backend.domain.admin.models.bases.commentary_embedding import CommentaryEmbedding

# target_metadata는 모든 모델의 메타데이터를 포함
target_metadata = Base.metadata


def get_url():
    """데이터베이스 URL 가져오기"""
    from backend.config import settings

    # PostgreSQL URL을 sync 형식으로 변환 (Alembic은 sync 사용)
    database_url = settings.DATABASE_URL

    # postgresql+psycopg:// -> postgresql:// 변환
    if database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    elif database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    return database_url


def run_migrations_offline() -> None:
    """'offline' 모드로 마이그레이션 실행.

    이렇게 하면 SQL 스크립트가 생성됩니다.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """'online' 모드로 마이그레이션 실행.

    이 경우 Engine을 생성하고 연결을 통해 마이그레이션을 실행합니다.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
