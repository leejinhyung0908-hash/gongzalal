"""UserSolvingLog 서비스.

사용자 풀이 이력을 관리합니다.
학습 진행과 성과 분석을 지원합니다.
"""

import logging
from typing import Dict, Any, List, Optional

from backend.dependencies import get_db_connection
from backend.domain.admin.models.transfers.user_transfer import (
    UserSolvingLogTransfer,
    UserSolvingLogCreateRequest,
    UserSolvingLogResponse,
)

logger = logging.getLogger(__name__)


class SolvingLogService:
    """UserSolvingLog 서비스."""

    def __init__(self):
        """초기화."""
        pass

    def create_log(self, request: UserSolvingLogCreateRequest) -> Dict[str, Any]:
        """풀이 로그 생성.

        Args:
            request: 풀이 로그 생성 요청

        Returns:
            생성 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_solving_logs (
                        user_id, question_id, selected_answer,
                        time_spent, special_event, is_wrong_note
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, question_id, selected_answer,
                              time_spent, special_event, is_wrong_note, created_at
                    """,
                    (
                        request.user_id,
                        request.question_id,
                        request.selected_answer,
                        request.time_spent,
                        request.special_event,
                        request.is_wrong_note,
                    )
                )
                row = cur.fetchone()
                conn.commit()

                # 정답 확인 (questions 테이블에서)
                cur.execute(
                    "SELECT answer_key FROM questions WHERE id = %s",
                    (request.question_id,)
                )
                answer_row = cur.fetchone()
                is_correct = None
                if answer_row and request.selected_answer:
                    is_correct = str(answer_row[0]) == str(request.selected_answer)

                return {
                    "success": True,
                    "log": UserSolvingLogResponse(
                        id=row[0],
                        user_id=row[1],
                        question_id=row[2],
                        selected_answer=row[3],
                        time_spent=row[4],
                        special_event=row[5],
                        is_wrong_note=row[6],
                        is_correct=is_correct,
                        created_at=row[7].isoformat() if row[7] else None,
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[SolvingLogService] 생성 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_user_logs(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """사용자의 풀이 로그 목록 조회.

        Args:
            user_id: 사용자 ID
            limit: 최대 결과 수
            offset: 시작 위치

        Returns:
            조회 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        l.id, l.user_id, l.question_id, l.selected_answer,
                        l.time_spent, l.special_event, l.is_wrong_note, l.created_at,
                        q.answer_key
                    FROM user_solving_logs l
                    LEFT JOIN questions q ON l.question_id = q.id
                    WHERE l.user_id = %s
                    ORDER BY l.created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset)
                )
                rows = cur.fetchall()

                logs = []
                for row in rows:
                    is_correct = None
                    if row[8] and row[3]:  # answer_key and selected_answer
                        is_correct = str(row[8]) == str(row[3])

                    logs.append(UserSolvingLogResponse(
                        id=row[0],
                        user_id=row[1],
                        question_id=row[2],
                        selected_answer=row[3],
                        time_spent=row[4],
                        special_event=row[5],
                        is_wrong_note=row[6],
                        is_correct=is_correct,
                        created_at=row[7].isoformat() if row[7] else None,
                    ).model_dump())

                return {"success": True, "logs": logs, "count": len(logs)}
        except Exception as e:
            logger.error(f"[SolvingLogService] 목록 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_question_logs(
        self,
        question_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """문제별 풀이 로그 조회.

        Args:
            question_id: 문제 ID
            user_id: 사용자 ID (optional, 특정 사용자 필터)

        Returns:
            조회 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        """
                        SELECT
                            l.id, l.user_id, l.question_id, l.selected_answer,
                            l.time_spent, l.special_event, l.is_wrong_note, l.created_at,
                            q.answer_key
                        FROM user_solving_logs l
                        LEFT JOIN questions q ON l.question_id = q.id
                        WHERE l.question_id = %s AND l.user_id = %s
                        ORDER BY l.created_at DESC
                        """,
                        (question_id, user_id)
                    )
                else:
                    cur.execute(
                        """
                        SELECT
                            l.id, l.user_id, l.question_id, l.selected_answer,
                            l.time_spent, l.special_event, l.is_wrong_note, l.created_at,
                            q.answer_key
                        FROM user_solving_logs l
                        LEFT JOIN questions q ON l.question_id = q.id
                        WHERE l.question_id = %s
                        ORDER BY l.created_at DESC
                        """,
                        (question_id,)
                    )

                rows = cur.fetchall()

                logs = []
                for row in rows:
                    is_correct = None
                    if row[8] and row[3]:
                        is_correct = str(row[8]) == str(row[3])

                    logs.append(UserSolvingLogResponse(
                        id=row[0],
                        user_id=row[1],
                        question_id=row[2],
                        selected_answer=row[3],
                        time_spent=row[4],
                        special_event=row[5],
                        is_wrong_note=row[6],
                        is_correct=is_correct,
                        created_at=row[7].isoformat() if row[7] else None,
                    ).model_dump())

                return {"success": True, "logs": logs, "count": len(logs)}
        except Exception as e:
            logger.error(f"[SolvingLogService] 문제별 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_wrong_notes(self, user_id: int, limit: int = 50) -> Dict[str, Any]:
        """사용자의 오답 노트 목록 조회.

        Args:
            user_id: 사용자 ID
            limit: 최대 결과 수

        Returns:
            조회 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        l.id, l.user_id, l.question_id, l.selected_answer,
                        l.time_spent, l.special_event, l.is_wrong_note, l.created_at,
                        q.answer_key
                    FROM user_solving_logs l
                    LEFT JOIN questions q ON l.question_id = q.id
                    WHERE l.user_id = %s AND l.is_wrong_note = TRUE
                    ORDER BY l.created_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit)
                )
                rows = cur.fetchall()

                logs = []
                for row in rows:
                    is_correct = None
                    if row[8] and row[3]:
                        is_correct = str(row[8]) == str(row[3])

                    logs.append(UserSolvingLogResponse(
                        id=row[0],
                        user_id=row[1],
                        question_id=row[2],
                        selected_answer=row[3],
                        time_spent=row[4],
                        special_event=row[5],
                        is_wrong_note=row[6],
                        is_correct=is_correct,
                        created_at=row[7].isoformat() if row[7] else None,
                    ).model_dump())

                return {"success": True, "wrong_notes": logs, "count": len(logs)}
        except Exception as e:
            logger.error(f"[SolvingLogService] 오답 노트 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """사용자 풀이 통계 조회.

        Args:
            user_id: 사용자 ID

        Returns:
            통계 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                # 총 풀이 수
                cur.execute(
                    "SELECT COUNT(*) FROM user_solving_logs WHERE user_id = %s",
                    (user_id,)
                )
                total_count = cur.fetchone()[0]

                # 정답 수 계산
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM user_solving_logs l
                    JOIN questions q ON l.question_id = q.id
                    WHERE l.user_id = %s AND l.selected_answer = q.answer_key
                    """,
                    (user_id,)
                )
                correct_count = cur.fetchone()[0]

                # 평균 풀이 시간
                cur.execute(
                    """
                    SELECT AVG(time_spent)
                    FROM user_solving_logs
                    WHERE user_id = %s AND time_spent IS NOT NULL
                    """,
                    (user_id,)
                )
                avg_time = cur.fetchone()[0]

                # 오답 노트 수
                cur.execute(
                    "SELECT COUNT(*) FROM user_solving_logs WHERE user_id = %s AND is_wrong_note = TRUE",
                    (user_id,)
                )
                wrong_note_count = cur.fetchone()[0]

                accuracy = (correct_count / total_count * 100) if total_count > 0 else 0

                return {
                    "success": True,
                    "statistics": {
                        "total_solved": total_count,
                        "correct_count": correct_count,
                        "wrong_count": total_count - correct_count,
                        "accuracy_percent": round(accuracy, 2),
                        "average_time_seconds": round(avg_time, 2) if avg_time else None,
                        "wrong_note_count": wrong_note_count,
                    }
                }
        except Exception as e:
            logger.error(f"[SolvingLogService] 통계 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def toggle_wrong_note(self, log_id: int) -> Dict[str, Any]:
        """오답 노트 토글.

        Args:
            log_id: 풀이 로그 ID

        Returns:
            토글 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE user_solving_logs
                    SET is_wrong_note = NOT is_wrong_note
                    WHERE id = %s
                    RETURNING id, is_wrong_note
                    """,
                    (log_id,)
                )
                row = cur.fetchone()
                conn.commit()

                if not row:
                    return {"success": False, "error": "로그를 찾을 수 없습니다."}

                return {
                    "success": True,
                    "log_id": row[0],
                    "is_wrong_note": row[1]
                }
        except Exception as e:
            logger.error(f"[SolvingLogService] 오답 노트 토글 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

