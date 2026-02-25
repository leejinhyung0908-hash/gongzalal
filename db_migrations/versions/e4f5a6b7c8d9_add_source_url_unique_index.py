"""add_source_url_unique_index

mentoring_knowledge 테이블의 source_url 컬럼에 UNIQUE 인덱스를 추가하여
동일한 합격 수기가 중복 삽입되는 것을 방지합니다.

- NULL 값은 UNIQUE 제약에서 제외됩니다 (PostgreSQL 기본 동작)
- 업로드 시 ON CONFLICT (source_url) DO NOTHING 으로 중복 스킵

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-02-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 기존 중복 데이터 제거 (가장 낮은 id만 남기고 삭제)
    op.execute("""
        DELETE FROM mentoring_knowledge
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM mentoring_knowledge
            WHERE source_url IS NOT NULL
            GROUP BY source_url
        )
        AND source_url IS NOT NULL
    """)

    # 2) source_url에 UNIQUE 인덱스 추가 (중복 방지)
    # NULL은 PostgreSQL에서 unique 제약에 영향받지 않음
    op.create_index(
        'uq_mentoring_knowledge_source_url',
        'mentoring_knowledge',
        ['source_url'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_mentoring_knowledge_source_url', table_name='mentoring_knowledge')

