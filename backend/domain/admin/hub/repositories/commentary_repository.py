"""Commentary 데이터 저장소 (Repository 패턴).

테이블 구조:
- commentaries: 해설/합격수기/멘토링 정보
  - id, user_id, question_id, body, type
  - success_period, target_exam, final_score, approved (합격수기용)
  - commentary_vector (1024차원 임베딩, KURE-v1)
"""

import logging
from typing import List, Dict, Any, Optional

import psycopg
from psycopg.types.json import Json

from backend.dependencies import get_db_connection

logger = logging.getLogger(__name__)


class CommentaryRepository:
    """Commentary 데이터 저장소."""

    def __init__(self, conn: Optional[psycopg.Connection] = None):
        """초기화.

        Args:
            conn: DB 연결 (None이면 get_db_connection() 사용)
        """
        self._conn = conn

    def _get_connection(self) -> psycopg.Connection:
        """DB 연결 가져오기."""
        if self._conn is not None:
            return self._conn
        return get_db_connection()

    # ========================================================================
    # CRUD 메서드
    # ========================================================================

    def create(
        self,
        body: str,
        user_id: Optional[int] = None,
        question_id: Optional[int] = None,
        commentary_type: Optional[str] = None,
        success_period: Optional[str] = None,
        target_exam: Optional[str] = None,
        final_score: Optional[int] = None,
    ) -> Dict[str, Any]:
        """해설 생성.

        Args:
            body: 해설 본문
            user_id: 작성자 ID (optional)
            question_id: 문제 ID (optional, 합격수기는 NULL 가능)
            commentary_type: 유형 ('수기', '해설', '멘토링', '합격수기')
            success_period: 수험 기간 (합격수기용)
            target_exam: 목표 시험 (합격수기용)
            final_score: 최종 점수 (합격수기용)

        Returns:
            생성된 해설 데이터
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO commentaries (
                    user_id, question_id, body, type,
                    success_period, target_exam, final_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, question_id, body, type,
                          success_period, target_exam, final_score, approved,
                          created_at, updated_at
                """,
                (
                    user_id, question_id, body, commentary_type,
                    success_period, target_exam, final_score
                )
            )
            row = cur.fetchone()
            conn.commit()

        logger.info(f"[CommentaryRepository] 해설 생성: id={row[0]}")

        return {
            "id": row[0],
            "user_id": row[1],
            "question_id": row[2],
            "body": row[3],
            "type": row[4],
            "success_period": row[5],
            "target_exam": row[6],
            "final_score": row[7],
            "approved": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None,
        }

    def get_by_id(self, commentary_id: int) -> Optional[Dict[str, Any]]:
        """ID로 해설 조회.

        Args:
            commentary_id: 해설 ID

        Returns:
            해설 데이터 또는 None
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, question_id, body, type,
                       success_period, target_exam, final_score, approved,
                       created_at, updated_at
                FROM commentaries
                WHERE id = %s
                """,
                (commentary_id,)
            )
            row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "user_id": row[1],
            "question_id": row[2],
            "body": row[3],
            "type": row[4],
            "success_period": row[5],
            "target_exam": row[6],
            "final_score": row[7],
            "approved": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None,
        }

    def get_by_question_id(self, question_id: int) -> List[Dict[str, Any]]:
        """문제 ID로 해설 목록 조회.

        Args:
            question_id: 문제 ID

        Returns:
            해설 데이터 리스트
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, question_id, body, type,
                       success_period, target_exam, final_score, approved,
                       created_at
                FROM commentaries
                WHERE question_id = %s
                ORDER BY created_at DESC
                """,
                (question_id,)
            )
            rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "user_id": r[1],
                "question_id": r[2],
                "body": r[3],
                "type": r[4],
                "success_period": r[5],
                "target_exam": r[6],
                "final_score": r[7],
                "approved": r[8],
                "created_at": r[9].isoformat() if r[9] else None,
            }
            for r in rows
        ]

    def update(
        self,
        commentary_id: int,
        body: Optional[str] = None,
        commentary_type: Optional[str] = None,
        success_period: Optional[str] = None,
        target_exam: Optional[str] = None,
        final_score: Optional[int] = None,
        approved: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """해설 수정.

        Args:
            commentary_id: 해설 ID
            body: 해설 본문
            commentary_type: 유형
            success_period: 수험 기간
            target_exam: 목표 시험
            final_score: 최종 점수
            approved: 승인 여부

        Returns:
            수정된 해설 데이터 또는 None
        """
        conn = self._get_connection()

        # 동적으로 업데이트할 필드 구성
        updates = []
        params = []

        if body is not None:
            updates.append("body = %s")
            params.append(body)
        if commentary_type is not None:
            updates.append("type = %s")
            params.append(commentary_type)
        if success_period is not None:
            updates.append("success_period = %s")
            params.append(success_period)
        if target_exam is not None:
            updates.append("target_exam = %s")
            params.append(target_exam)
        if final_score is not None:
            updates.append("final_score = %s")
            params.append(final_score)
        if approved is not None:
            updates.append("approved = %s")
            params.append(approved)

        if not updates:
            return self.get_by_id(commentary_id)

        updates.append("updated_at = now()")
        params.append(commentary_id)

        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE commentaries
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, user_id, question_id, body, type,
                          success_period, target_exam, final_score, approved,
                          created_at, updated_at
                """,
                params
            )
            row = cur.fetchone()
            conn.commit()

        if not row:
            return None

        return {
            "id": row[0],
            "user_id": row[1],
            "question_id": row[2],
            "body": row[3],
            "type": row[4],
            "success_period": row[5],
            "target_exam": row[6],
            "final_score": row[7],
            "approved": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None,
        }

    def delete(self, commentary_id: int) -> bool:
        """해설 삭제.

        Args:
            commentary_id: 해설 ID

        Returns:
            삭제 성공 여부
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM commentaries WHERE id = %s RETURNING id",
                (commentary_id,)
            )
            result = cur.fetchone()
            conn.commit()

        return result is not None

    # ========================================================================
    # 합격수기 전용 메서드
    # ========================================================================

    def get_success_stories(
        self,
        approved_only: bool = True,
        limit: int = 50,
        offset: int = 0,
        target_exam: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """합격수기 목록 조회.

        Args:
            approved_only: 승인된 것만 조회
            limit: 조회 개수
            offset: 오프셋
            target_exam: 목표 시험 필터

        Returns:
            합격수기 리스트
        """
        conn = self._get_connection()

        conditions = ["type = '합격수기'"]
        params = []

        if approved_only:
            conditions.append("approved = TRUE")
        if target_exam:
            conditions.append("target_exam = %s")
            params.append(target_exam)

        params.extend([limit, offset])

        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, user_id, body, success_period, target_exam,
                       final_score, approved, created_at
                FROM commentaries
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params
            )
            rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "user_id": r[1],
                "body": r[2],
                "success_period": r[3],
                "target_exam": r[4],
                "final_score": r[5],
                "approved": r[6],
                "created_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ]

    def search_similar(
        self,
        query_vector: List[float],
        limit: int = 5,
        commentary_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """벡터 유사도 검색 (RAG용).

        Args:
            query_vector: 쿼리 벡터 (1024차원)
            limit: 조회 개수
            commentary_type: 유형 필터

        Returns:
            유사한 해설 리스트 (유사도 포함)
        """
        conn = self._get_connection()

        type_filter = ""
        params = [str(query_vector), limit]

        if commentary_type:
            type_filter = "AND type = %s"
            params.insert(1, commentary_type)

        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, body, type,
                       1 - (commentary_vector <=> %s::vector) AS similarity
                FROM commentaries
                WHERE commentary_vector IS NOT NULL {type_filter}
                ORDER BY commentary_vector <=> %s::vector
                LIMIT %s
                """,
                [str(query_vector)] + params[1:-1] + [str(query_vector), limit]
            )
            rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "body": r[1],
                "type": r[2],
                "similarity": float(r[3]) if r[3] else 0.0,
            }
            for r in rows
        ]

    def update_embedding(
        self, commentary_id: int, embedding: List[float]
    ) -> bool:
        """해설 임베딩 업데이트.

        Args:
            commentary_id: 해설 ID
            embedding: 임베딩 벡터 (1024차원)

        Returns:
            업데이트 성공 여부
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE commentaries
                SET commentary_vector = %s::vector, updated_at = now()
                WHERE id = %s
                RETURNING id
                """,
                (str(embedding), commentary_id)
            )
            result = cur.fetchone()
            conn.commit()

        return result is not None

    def get_without_embeddings(self, limit: int = 100) -> List[Dict[str, Any]]:
        """임베딩이 없는 해설 목록 조회.

        Args:
            limit: 조회 개수

        Returns:
            임베딩이 없는 해설 리스트
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, body, type
                FROM commentaries
                WHERE commentary_vector IS NULL
                ORDER BY id
                LIMIT %s
                """,
                (limit,)
            )
            rows = cur.fetchall()

        return [{"id": r[0], "body": r[1], "type": r[2]} for r in rows]

