"""User 데이터 저장소 (Repository 패턴).

테이블 구조:
- users: 사용자 프로필 정보
  - id, display_name, age, employment_status
  - base_score, daily_study_time, target_date
  - registration_date, last_login
"""

import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional

import psycopg

from backend.dependencies import get_db_connection

logger = logging.getLogger(__name__)


class UserRepository:
    """User 데이터 저장소."""

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
        display_name: str,
        age: Optional[int] = None,
        employment_status: Optional[str] = None,
        base_score: Optional[int] = None,
        daily_study_time: Optional[int] = None,
        target_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """사용자 생성.

        Args:
            display_name: 표시 이름
            age: 나이
            employment_status: 직장 상태 ('재직', '무직', '학생')
            base_score: 베이스 점수
            daily_study_time: 일일 학습 시간 (분)
            target_date: 목표 시험 날짜

        Returns:
            생성된 사용자 데이터
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (
                    display_name, age, employment_status,
                    base_score, daily_study_time, target_date
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, display_name, age, employment_status,
                          base_score, daily_study_time, target_date,
                          registration_date, last_login
                """,
                (
                    display_name, age, employment_status,
                    base_score, daily_study_time, target_date
                )
            )
            row = cur.fetchone()
            conn.commit()

        logger.info(f"[UserRepository] 사용자 생성: id={row[0]}, display_name={row[1]}")

        return self._row_to_dict(row)

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """ID로 사용자 조회.

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 데이터 또는 None
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, display_name, age, employment_status,
                       base_score, daily_study_time, target_date,
                       registration_date, last_login
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )
            row = cur.fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    def get_by_display_name(self, display_name: str) -> Optional[Dict[str, Any]]:
        """표시 이름으로 사용자 조회.

        Args:
            display_name: 표시 이름

        Returns:
            사용자 데이터 또는 None
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, display_name, age, employment_status,
                       base_score, daily_study_time, target_date,
                       registration_date, last_login
                FROM users
                WHERE display_name = %s
                """,
                (display_name,)
            )
            row = cur.fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    def update(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        age: Optional[int] = None,
        employment_status: Optional[str] = None,
        base_score: Optional[int] = None,
        daily_study_time: Optional[int] = None,
        target_date: Optional[date] = None,
    ) -> Optional[Dict[str, Any]]:
        """사용자 정보 수정.

        Args:
            user_id: 사용자 ID
            display_name: 표시 이름
            age: 나이
            employment_status: 직장 상태
            base_score: 베이스 점수
            daily_study_time: 일일 학습 시간
            target_date: 목표 날짜

        Returns:
            수정된 사용자 데이터 또는 None
        """
        conn = self._get_connection()

        # 동적으로 업데이트할 필드 구성
        updates = []
        params = []

        if display_name is not None:
            updates.append("display_name = %s")
            params.append(display_name)
        if age is not None:
            updates.append("age = %s")
            params.append(age)
        if employment_status is not None:
            updates.append("employment_status = %s")
            params.append(employment_status)
        if base_score is not None:
            updates.append("base_score = %s")
            params.append(base_score)
        if daily_study_time is not None:
            updates.append("daily_study_time = %s")
            params.append(daily_study_time)
        if target_date is not None:
            updates.append("target_date = %s")
            params.append(target_date)

        if not updates:
            return self.get_by_id(user_id)

        updates.append("last_login = now()")
        params.append(user_id)

        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE users
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, display_name, age, employment_status,
                          base_score, daily_study_time, target_date,
                          registration_date, last_login
                """,
                params
            )
            row = cur.fetchone()
            conn.commit()

        if not row:
            return None

        return self._row_to_dict(row)

    def update_last_login(self, user_id: int) -> bool:
        """마지막 로그인 시간 갱신.

        Args:
            user_id: 사용자 ID

        Returns:
            성공 여부
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users SET last_login = now()
                WHERE id = %s RETURNING id
                """,
                (user_id,)
            )
            result = cur.fetchone()
            conn.commit()

        return result is not None

    def delete(self, user_id: int) -> bool:
        """사용자 삭제.

        Args:
            user_id: 사용자 ID

        Returns:
            삭제 성공 여부
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM users WHERE id = %s RETURNING id",
                (user_id,)
            )
            result = cur.fetchone()
            conn.commit()

        return result is not None

    def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "registration_date",
        order_desc: bool = True,
    ) -> List[Dict[str, Any]]:
        """전체 사용자 목록 조회.

        Args:
            limit: 조회 개수
            offset: 오프셋
            order_by: 정렬 기준 컬럼
            order_desc: 내림차순 여부

        Returns:
            사용자 리스트
        """
        conn = self._get_connection()

        # 허용된 정렬 컬럼만 사용
        allowed_columns = ["id", "display_name", "registration_date", "last_login"]
        if order_by not in allowed_columns:
            order_by = "registration_date"

        order = "DESC" if order_desc else "ASC"

        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, display_name, age, employment_status,
                       base_score, daily_study_time, target_date,
                       registration_date, last_login
                FROM users
                ORDER BY {order_by} {order}
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            rows = cur.fetchall()

        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """DB row를 딕셔너리로 변환."""
        return {
            "id": row[0],
            "display_name": row[1],
            "age": row[2],
            "employment_status": row[3],
            "base_score": row[4],
            "daily_study_time": row[5],
            "target_date": row[6].isoformat() if row[6] else None,
            "registration_date": row[7].isoformat() if row[7] else None,
            "last_login": row[8].isoformat() if row[8] else None,
        }

