"""vector_1536_to_1024_kure_v1

모든 벡터 컬럼을 Vector(1536)에서 Vector(1024)로 변경합니다.
임베딩 모델을 simple_embed(해시 데모) → KURE-v1(한국어 SentenceTransformer)로 교체.
기존 해시 기반 임베딩은 무의미하므로 NULL 처리 후 차원을 변경합니다.

Revision ID: b1c2d3e4f5a6
Revises: a99936f01ab2
Create Date: 2026-02-11 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy.vector


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a99936f01ab2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 변경할 테이블 및 벡터 컬럼 매핑
VECTOR_COLUMNS = [
    ("exams", "exam_vector"),
    ("questions", "question_vector"),
    ("question_images", "image_vector"),
    ("commentaries", "commentary_vector"),
    ("audio_notes", "audio_vector"),
    ("users", "user_vector"),
    ("user_solving_logs", "solving_vector"),
    ("study_plans", "plan_vector"),
    ("mentoring_knowledge", "knowledge_vector"),
]


def upgrade() -> None:
    # 1) 기존 해시 기반 임베딩을 모두 NULL 처리 (무의미한 데이터 제거)
    for table, column in VECTOR_COLUMNS:
        op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IS NOT NULL")

    # 2) 벡터 컬럼 차원을 1536 → 1024로 변경 (KURE-v1 호환)
    for table, column in VECTOR_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} TYPE vector(1024) "
            f"USING {column}::vector(1024)"
        )


def downgrade() -> None:
    # 롤백: 1024 → 1536
    for table, column in VECTOR_COLUMNS:
        op.execute(f"UPDATE {table} SET {column} = NULL WHERE {column} IS NOT NULL")

    for table, column in VECTOR_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN {column} TYPE vector(1536) "
            f"USING {column}::vector(1536)"
        )

