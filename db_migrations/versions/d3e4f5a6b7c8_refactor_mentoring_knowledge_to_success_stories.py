"""refactor_mentoring_knowledge_to_success_stories

mentoring_knowledge 테이블의 컬럼을 합격 수기 원문 구조로 전환합니다.
- 기존 Q&A 컬럼 (instruction, question, intent, context, thought_process, response) 삭제
- 합격 수기 원문 컬럼 (source, exam_info, study_style, daily_plan, subject_methods,
  interview_prep, difficulties, key_points, search_text, source_url, crawled_at) 추가
- knowledge_vector (vector(1024)) 유지
- 기존 데이터는 모두 삭제됨 (TRUNCATE)

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-02-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 기존 데이터 전부 삭제 (컬럼 구조가 완전히 바뀌므로)
    op.execute("TRUNCATE TABLE mentoring_knowledge RESTART IDENTITY")

    # 2) 기존 Q&A 컬럼 삭제
    op.drop_column('mentoring_knowledge', 'instruction')
    op.drop_column('mentoring_knowledge', 'question')
    op.drop_column('mentoring_knowledge', 'intent')
    op.drop_column('mentoring_knowledge', 'context')
    op.drop_column('mentoring_knowledge', 'thought_process')
    op.drop_column('mentoring_knowledge', 'response')

    # 3) 합격 수기 원문 구조 컬럼 추가
    op.add_column('mentoring_knowledge', sa.Column('source', sa.String(length=50), nullable=False, server_default='unknown'))
    op.add_column('mentoring_knowledge', sa.Column('exam_info', sa.JSON(), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('study_style', sa.JSON(), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('daily_plan', sa.Text(), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('subject_methods', sa.JSON(), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('interview_prep', sa.Text(), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('difficulties', sa.Text(), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('key_points', sa.Text(), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('search_text', sa.Text(), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('source_url', sa.Text(), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('crawled_at', sa.DateTime(), nullable=True))

    # 4) 인덱스: source 컬럼
    op.create_index('ix_mentoring_knowledge_source', 'mentoring_knowledge', ['source'])

    # server_default 제거 (초기 마이그레이션 이후에는 불필요)
    op.alter_column('mentoring_knowledge', 'source', server_default=None)


def downgrade() -> None:
    # 인덱스 삭제
    op.drop_index('ix_mentoring_knowledge_source', table_name='mentoring_knowledge')

    # 합격 수기 컬럼 삭제
    op.drop_column('mentoring_knowledge', 'crawled_at')
    op.drop_column('mentoring_knowledge', 'source_url')
    op.drop_column('mentoring_knowledge', 'search_text')
    op.drop_column('mentoring_knowledge', 'key_points')
    op.drop_column('mentoring_knowledge', 'difficulties')
    op.drop_column('mentoring_knowledge', 'interview_prep')
    op.drop_column('mentoring_knowledge', 'subject_methods')
    op.drop_column('mentoring_knowledge', 'daily_plan')
    op.drop_column('mentoring_knowledge', 'study_style')
    op.drop_column('mentoring_knowledge', 'exam_info')
    op.drop_column('mentoring_knowledge', 'source')

    # 기존 데이터 비우기
    op.execute("TRUNCATE TABLE mentoring_knowledge RESTART IDENTITY")

    # 기존 Q&A 컬럼 복원
    op.add_column('mentoring_knowledge', sa.Column('instruction', sa.Text(), nullable=False, server_default=''))
    op.add_column('mentoring_knowledge', sa.Column('question', sa.Text(), nullable=False, server_default=''))
    op.add_column('mentoring_knowledge', sa.Column('intent', sa.String(length=50), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('context', sa.Text(), nullable=False, server_default=''))
    op.add_column('mentoring_knowledge', sa.Column('thought_process', sa.Text(), nullable=True))
    op.add_column('mentoring_knowledge', sa.Column('response', sa.Text(), nullable=False, server_default=''))

    # server_default 제거
    op.alter_column('mentoring_knowledge', 'instruction', server_default=None)
    op.alter_column('mentoring_knowledge', 'question', server_default=None)
    op.alter_column('mentoring_knowledge', 'context', server_default=None)
    op.alter_column('mentoring_knowledge', 'response', server_default=None)

