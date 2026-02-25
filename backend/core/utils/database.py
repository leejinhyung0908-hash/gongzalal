"""데이터베이스 서비스."""
import logging
from typing import Sequence, Tuple

import psycopg

from backend.core.utils.embedding import generate_embedding

logger = logging.getLogger(__name__)


def search_similar(
    conn: psycopg.Connection, query: str, *, top_k: int = 3
) -> Sequence[Tuple[str, float]]:
    """pgvector를 사용해 mentoring_knowledge 테이블에서 유사한 문서를 검색한다.

    KURE-v1 임베딩(1024차원)으로 코사인 거리 기반 유사도 검색을 수행합니다.
    """
    try:
        query_emb = generate_embedding(query)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(search_text, '') AS content,
                    knowledge_vector <=> %s::vector AS distance
                FROM mentoring_knowledge
                WHERE knowledge_vector IS NOT NULL
                ORDER BY knowledge_vector <=> %s::vector
                LIMIT %s
                """,
                (query_emb, query_emb, top_k),
            )
            rows = cur.fetchall()
        return [(row[0], float(row[1])) for row in rows]
    except Exception as e:
        logger.error(f"[DB] search_similar 오류: {e}")
        return []

