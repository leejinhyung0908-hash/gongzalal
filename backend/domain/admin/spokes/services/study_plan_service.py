"""StudyPlan 서비스.

사용자 맞춤 학습 계획을 관리합니다.
AI(EXAONE)가 생성한 스케줄을 저장하고 조회합니다.
"""

import logging
from typing import Dict, Any, List, Optional

from backend.dependencies import get_db_connection
from backend.domain.admin.models.transfers.user_transfer import (
    StudyPlanTransfer,
    StudyPlanCreateRequest,
    StudyPlanUpdateRequest,
)

logger = logging.getLogger(__name__)


class StudyPlanService:
    """StudyPlan 서비스."""

    def __init__(self):
        """초기화."""
        pass

    def create_plan(self, request: StudyPlanCreateRequest) -> Dict[str, Any]:
        """학습 계획 생성.

        Args:
            request: 학습 계획 생성 요청

        Returns:
            생성 결과
        """
        conn = get_db_connection()
        from psycopg.types.json import Json

        try:
            with conn.cursor() as cur:
                # 기존 버전 확인
                cur.execute(
                    "SELECT MAX(version) FROM study_plans WHERE user_id = %s",
                    (request.user_id,)
                )
                row = cur.fetchone()
                new_version = (row[0] or 0) + 1 if row else 1

                # 새 계획 생성
                cur.execute(
                    """
                    INSERT INTO study_plans (user_id, plan_json, version)
                    VALUES (%s, %s::jsonb, %s)
                    RETURNING id, user_id, plan_json, version, created_at, updated_at
                    """,
                    (request.user_id, Json(request.plan_json), new_version)
                )
                row = cur.fetchone()
                conn.commit()

                return {
                    "success": True,
                    "plan": StudyPlanTransfer(
                        id=row[0],
                        user_id=row[1],
                        plan_json=row[2],
                        version=row[3],
                        created_at=row[4],
                        updated_at=row[5],
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[StudyPlanService] 생성 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_plan(self, plan_id: int) -> Dict[str, Any]:
        """학습 계획 조회.

        Args:
            plan_id: 계획 ID

        Returns:
            조회 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, plan_json, version, created_at, updated_at
                    FROM study_plans WHERE id = %s
                    """,
                    (plan_id,)
                )
                row = cur.fetchone()

                if not row:
                    return {"success": False, "error": "계획을 찾을 수 없습니다."}

                return {
                    "success": True,
                    "plan": StudyPlanTransfer(
                        id=row[0],
                        user_id=row[1],
                        plan_json=row[2],
                        version=row[3],
                        created_at=row[4],
                        updated_at=row[5],
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[StudyPlanService] 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_user_plans(self, user_id: int, limit: int = 10) -> Dict[str, Any]:
        """사용자의 학습 계획 목록 조회.

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
                    SELECT id, user_id, plan_json, version, created_at, updated_at
                    FROM study_plans
                    WHERE user_id = %s
                    ORDER BY version DESC
                    LIMIT %s
                    """,
                    (user_id, limit)
                )
                rows = cur.fetchall()

                plans = [
                    StudyPlanTransfer(
                        id=row[0],
                        user_id=row[1],
                        plan_json=row[2],
                        version=row[3],
                        created_at=row[4],
                        updated_at=row[5],
                    ).model_dump()
                    for row in rows
                ]

                return {"success": True, "plans": plans, "count": len(plans)}
        except Exception as e:
            logger.error(f"[StudyPlanService] 목록 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_latest_plan(self, user_id: int) -> Dict[str, Any]:
        """사용자의 최신 학습 계획 조회.

        Args:
            user_id: 사용자 ID

        Returns:
            조회 결과
        """
        conn = get_db_connection()

        try:
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
                    return {"success": False, "error": "학습 계획이 없습니다."}

                return {
                    "success": True,
                    "plan": StudyPlanTransfer(
                        id=row[0],
                        user_id=row[1],
                        plan_json=row[2],
                        version=row[3],
                        created_at=row[4],
                        updated_at=row[5],
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[StudyPlanService] 최신 계획 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def update_plan(self, plan_id: int, request: StudyPlanUpdateRequest) -> Dict[str, Any]:
        """학습 계획 수정.

        Args:
            plan_id: 계획 ID
            request: 수정 요청

        Returns:
            수정 결과
        """
        conn = get_db_connection()
        from psycopg.types.json import Json

        try:
            with conn.cursor() as cur:
                if request.plan_json is not None:
                    cur.execute(
                        """
                        UPDATE study_plans
                        SET plan_json = %s::jsonb, updated_at = now()
                        WHERE id = %s
                        RETURNING id, user_id, plan_json, version, created_at, updated_at
                        """,
                        (Json(request.plan_json), plan_id)
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, user_id, plan_json, version, created_at, updated_at
                        FROM study_plans WHERE id = %s
                        """,
                        (plan_id,)
                    )

                row = cur.fetchone()
                if not row:
                    return {"success": False, "error": "계획을 찾을 수 없습니다."}

                conn.commit()

                return {
                    "success": True,
                    "plan": StudyPlanTransfer(
                        id=row[0],
                        user_id=row[1],
                        plan_json=row[2],
                        version=row[3],
                        created_at=row[4],
                        updated_at=row[5],
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[StudyPlanService] 수정 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def delete_plan(self, plan_id: int) -> Dict[str, Any]:
        """학습 계획 삭제.

        Args:
            plan_id: 계획 ID

        Returns:
            삭제 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM study_plans WHERE id = %s RETURNING id",
                    (plan_id,)
                )
                row = cur.fetchone()
                conn.commit()

                if not row:
                    return {"success": False, "error": "계획을 찾을 수 없습니다."}

                return {"success": True, "deleted_id": row[0]}
        except Exception as e:
            logger.error(f"[StudyPlanService] 삭제 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def delete_user_plans(self, user_id: int) -> Dict[str, Any]:
        """사용자의 학습 계획 전체 삭제.

        AI 플랜 재생성 시 기존 계획을 모두 지우고 새로 시작하기 위해 사용.

        Args:
            user_id: 사용자 ID

        Returns:
            삭제 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM study_plans WHERE user_id = %s",
                    (user_id,)
                )
                deleted_count = cur.rowcount
                conn.commit()

                logger.info(
                    f"[StudyPlanService] user_id={user_id} 기존 학습 계획 "
                    f"{deleted_count}건 삭제 완료"
                )
                return {"success": True, "deleted_count": deleted_count}
        except Exception as e:
            logger.error(f"[StudyPlanService] 전체 삭제 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

