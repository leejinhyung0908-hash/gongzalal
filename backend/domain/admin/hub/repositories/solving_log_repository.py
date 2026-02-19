"""SolvingLog 데이터 저장소 (Repository 패턴).

테이블 구조:
- user_solving_logs: 사용자 풀이 이력
  - id, user_id, question_id
  - selected_answer, time_spent, special_event, is_wrong_note
  - created_at, updated_at
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

import psycopg

from backend.dependencies import get_db_connection

logger = logging.getLogger(__name__)


class SolvingLogRepository:
    """SolvingLog 데이터 저장소."""

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
        user_id: int,
        question_id: int,
        selected_answer: Optional[str] = None,
        time_spent: Optional[int] = None,
        special_event: Optional[str] = None,
        is_wrong_note: bool = False,
    ) -> Dict[str, Any]:
        """풀이 로그 생성.

        Args:
            user_id: 사용자 ID
            question_id: 문제 ID
            selected_answer: 선택한 답안
            time_spent: 소요 시간 (초)
            special_event: 특별 이벤트 (hint_used, skipped 등)
            is_wrong_note: 오답 노트 여부

        Returns:
            생성된 풀이 로그 데이터
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_solving_logs (
                    user_id, question_id, selected_answer,
                    time_spent, special_event, is_wrong_note
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, user_id, question_id, selected_answer,
                          time_spent, special_event, is_wrong_note,
                          created_at, updated_at
                """,
                (
                    user_id, question_id, selected_answer,
                    time_spent, special_event, is_wrong_note
                )
            )
            row = cur.fetchone()
            conn.commit()

        logger.info(f"[SolvingLogRepository] 풀이 로그 생성: id={row[0]}, user_id={user_id}")

        return self._row_to_dict(row)

    def get_by_id(self, log_id: int) -> Optional[Dict[str, Any]]:
        """ID로 풀이 로그 조회.

        Args:
            log_id: 풀이 로그 ID

        Returns:
            풀이 로그 데이터 또는 None
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, question_id, selected_answer,
                       time_spent, special_event, is_wrong_note,
                       created_at, updated_at
                FROM user_solving_logs
                WHERE id = %s
                """,
                (log_id,)
            )
            row = cur.fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    def get_by_user_id(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """사용자의 풀이 로그 목록 조회.

        Args:
            user_id: 사용자 ID
            limit: 조회 개수
            offset: 오프셋

        Returns:
            풀이 로그 리스트 (최신순)
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, question_id, selected_answer,
                       time_spent, special_event, is_wrong_note,
                       created_at, updated_at
                FROM user_solving_logs
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset)
            )
            rows = cur.fetchall()

        return [self._row_to_dict(r) for r in rows]

    def update_wrong_note(self, log_id: int, is_wrong_note: bool) -> bool:
        """오답 노트 상태 업데이트.

        Args:
            log_id: 풀이 로그 ID
            is_wrong_note: 오답 노트 여부

        Returns:
            업데이트 성공 여부
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_solving_logs
                SET is_wrong_note = %s, updated_at = now()
                WHERE id = %s
                RETURNING id
                """,
                (is_wrong_note, log_id)
            )
            result = cur.fetchone()
            conn.commit()

        return result is not None

    def delete(self, log_id: int) -> bool:
        """풀이 로그 삭제.

        Args:
            log_id: 풀이 로그 ID

        Returns:
            삭제 성공 여부
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_solving_logs WHERE id = %s RETURNING id",
                (log_id,)
            )
            result = cur.fetchone()
            conn.commit()

        return result is not None

    # ========================================================================
    # 오답 노트 메서드
    # ========================================================================

    def get_wrong_notes(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """사용자의 오답 노트 목록 조회.

        Args:
            user_id: 사용자 ID
            limit: 조회 개수
            offset: 오프셋

        Returns:
            오답 노트 리스트 (문제 정보 포함)
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT usl.id, usl.question_id, usl.selected_answer, usl.time_spent,
                       usl.created_at, q.answer_key, q.question_text,
                       e.year, e.exam_type, e.subject
                FROM user_solving_logs usl
                JOIN questions q ON usl.question_id = q.id
                JOIN exams e ON q.exam_id = e.id
                WHERE usl.user_id = %s AND usl.is_wrong_note = TRUE
                ORDER BY usl.created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset)
            )
            rows = cur.fetchall()

        return [
            {
                "log_id": r[0],
                "question_id": r[1],
                "selected_answer": r[2],
                "correct_answer": r[5],
                "time_spent": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "question_preview": r[6][:100] + "..." if len(r[6]) > 100 else r[6],
                "exam_year": r[7],
                "exam_type": r[8],
                "subject": r[9],
            }
            for r in rows
        ]

    # ========================================================================
    # 통계 메서드
    # ========================================================================

    def get_stats(self, user_id: int) -> Dict[str, Any]:
        """사용자 풀이 통계 조회.

        Args:
            user_id: 사용자 ID

        Returns:
            통계 데이터
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            # 전체 풀이 수
            cur.execute(
                "SELECT COUNT(*) FROM user_solving_logs WHERE user_id = %s",
                (user_id,)
            )
            total_count = cur.fetchone()[0]

            # 정답 수
            cur.execute(
                """
                SELECT COUNT(*)
                FROM user_solving_logs usl
                JOIN questions q ON usl.question_id = q.id
                WHERE usl.user_id = %s AND usl.selected_answer = q.answer_key
                """,
                (user_id,)
            )
            correct_count = cur.fetchone()[0]

            # 오답 노트 수
            cur.execute(
                "SELECT COUNT(*) FROM user_solving_logs WHERE user_id = %s AND is_wrong_note = TRUE",
                (user_id,)
            )
            wrong_note_count = cur.fetchone()[0]

            # 평균 소요 시간
            cur.execute(
                "SELECT AVG(time_spent) FROM user_solving_logs WHERE user_id = %s AND time_spent IS NOT NULL",
                (user_id,)
            )
            avg_time = cur.fetchone()[0]

        accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

        return {
            "total_solved": total_count,
            "correct_count": correct_count,
            "wrong_count": total_count - correct_count,
            "wrong_note_count": wrong_note_count,
            "accuracy": round(accuracy, 2),
            "avg_time_seconds": round(avg_time, 2) if avg_time else None,
        }

    def get_subject_stats(self, user_id: int) -> List[Dict[str, Any]]:
        """과목별 풀이 통계 조회.

        Args:
            user_id: 사용자 ID

        Returns:
            과목별 통계 리스트
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT e.subject,
                       COUNT(*) as total,
                       SUM(CASE WHEN usl.selected_answer = q.answer_key THEN 1 ELSE 0 END) as correct
                FROM user_solving_logs usl
                JOIN questions q ON usl.question_id = q.id
                JOIN exams e ON q.exam_id = e.id
                WHERE usl.user_id = %s
                GROUP BY e.subject
                ORDER BY total DESC
                """,
                (user_id,)
            )
            rows = cur.fetchall()

        return [
            {
                "subject": r[0],
                "total": r[1],
                "correct": r[2],
                "accuracy": round(r[2] / r[1] * 100, 2) if r[1] > 0 else 0,
            }
            for r in rows
        ]

    def check_answer(self, question_id: int, selected_answer: str) -> Tuple[bool, str]:
        """정답 확인.

        Args:
            question_id: 문제 ID
            selected_answer: 선택한 답안

        Returns:
            (정답 여부, 정답 키)
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                "SELECT answer_key FROM questions WHERE id = %s",
                (question_id,)
            )
            row = cur.fetchone()

        if not row:
            return False, ""

        answer_key = row[0]
        return selected_answer == answer_key, answer_key

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """DB row를 딕셔너리로 변환."""
        return {
            "id": row[0],
            "user_id": row[1],
            "question_id": row[2],
            "selected_answer": row[3],
            "time_spent": row[4],
            "special_event": row[5],
            "is_wrong_note": row[6],
            "created_at": row[7].isoformat() if row[7] else None,
            "updated_at": row[8].isoformat() if row[8] else None,
        }

