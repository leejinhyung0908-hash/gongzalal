"""StudyPlan 데이터 저장소 (Repository 패턴).

테이블 구조:
- study_plans: 사용자 맞춤 학습 계획
  - id, user_id, plan_json, version
  - created_at, updated_at
"""

import logging
from typing import List, Dict, Any, Optional

import psycopg
from psycopg.types.json import Json

from backend.dependencies import get_db_connection

logger = logging.getLogger(__name__)


class StudyPlanRepository:
    """StudyPlan 데이터 저장소."""

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
        plan_json: Dict[str, Any],
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """학습 계획 생성.

        Args:
            user_id: 사용자 ID
            plan_json: 학습 계획 JSON 데이터
            version: 버전 (None이면 자동 증가)

        Returns:
            생성된 학습 계획 데이터
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            # 버전이 없으면 기존 최대 버전 + 1
            if version is None:
                cur.execute(
                    "SELECT COALESCE(MAX(version), 0) FROM study_plans WHERE user_id = %s",
                    (user_id,)
                )
                version = cur.fetchone()[0] + 1

            cur.execute(
                """
                INSERT INTO study_plans (user_id, plan_json, version)
                VALUES (%s, %s::jsonb, %s)
                RETURNING id, user_id, plan_json, version, created_at, updated_at
                """,
                (user_id, Json(plan_json), version)
            )
            row = cur.fetchone()
            conn.commit()

        logger.info(f"[StudyPlanRepository] 학습 계획 생성: id={row[0]}, user_id={user_id}, version={version}")

        return self._row_to_dict(row)

    def get_by_id(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """ID로 학습 계획 조회.

        Args:
            plan_id: 학습 계획 ID

        Returns:
            학습 계획 데이터 또는 None
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, plan_json, version, created_at, updated_at
                FROM study_plans
                WHERE id = %s
                """,
                (plan_id,)
            )
            row = cur.fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    def get_latest_by_user_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """사용자의 최신 학습 계획 조회.

        Args:
            user_id: 사용자 ID

        Returns:
            최신 학습 계획 데이터 또는 None
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, plan_json, version, created_at, updated_at
                FROM study_plans
                WHERE user_id = %s
                ORDER BY version DESC
                LIMIT 1
                """,
                (user_id,)
            )
            row = cur.fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    def get_all_by_user_id(
        self, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """사용자의 모든 학습 계획 조회 (버전 이력).

        Args:
            user_id: 사용자 ID
            limit: 조회 개수

        Returns:
            학습 계획 리스트 (최신순)
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, plan_json, version, created_at, updated_at
                FROM study_plans
                WHERE user_id = %s
                ORDER BY version DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
            rows = cur.fetchall()

        return [self._row_to_dict(r) for r in rows]

    def update(
        self,
        plan_id: int,
        plan_json: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """학습 계획 수정.

        Args:
            plan_id: 학습 계획 ID
            plan_json: 수정할 계획 JSON 데이터

        Returns:
            수정된 학습 계획 데이터 또는 None
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE study_plans
                SET plan_json = %s::jsonb, updated_at = now()
                WHERE id = %s
                RETURNING id, user_id, plan_json, version, created_at, updated_at
                """,
                (Json(plan_json), plan_id)
            )
            row = cur.fetchone()
            conn.commit()

        if not row:
            return None

        return self._row_to_dict(row)

    def delete(self, plan_id: int) -> bool:
        """학습 계획 삭제.

        Args:
            plan_id: 학습 계획 ID

        Returns:
            삭제 성공 여부
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM study_plans WHERE id = %s RETURNING id",
                (plan_id,)
            )
            result = cur.fetchone()
            conn.commit()

        return result is not None

    def delete_old_versions(self, user_id: int, keep_versions: int = 5) -> int:
        """오래된 버전 삭제.

        Args:
            user_id: 사용자 ID
            keep_versions: 유지할 버전 수

        Returns:
            삭제된 개수
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM study_plans
                WHERE user_id = %s
                AND id NOT IN (
                    SELECT id FROM study_plans
                    WHERE user_id = %s
                    ORDER BY version DESC
                    LIMIT %s
                )
                """,
                (user_id, user_id, keep_versions)
            )
            deleted = cur.rowcount
            conn.commit()

        logger.info(f"[StudyPlanRepository] 오래된 버전 삭제: user_id={user_id}, deleted={deleted}")
        return deleted

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """DB row를 딕셔너리로 변환."""
        return {
            "id": row[0],
            "user_id": row[1],
            "plan_json": row[2] or {},
            "version": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None,
        }

