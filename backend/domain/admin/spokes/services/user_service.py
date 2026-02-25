"""User 규칙 기반 서비스.

새 테이블 구조:
- Users: display_name, age, employment_status, base_score, daily_study_time, study_duration
"""

from typing import Optional

from backend.dependencies import get_db_connection
from backend.domain.admin.models.transfers.user_transfer import (
    UserCreateRequest,
    UserUpdateRequest,
    UserResponse,
)


class UserService:
    """User 규칙 기반 서비스."""

    async def handle_request(self, request_data: dict, koelectra_result: dict) -> dict:
        """규칙 기반 요청 처리.

        Args:
            request_data: 요청 데이터 (display_name, age 등)
            koelectra_result: KoELECTRA 분석 결과 (참고용)

        Returns:
            처리 결과
        """
        # UserCreateRequest로 변환
        req = UserCreateRequest(**request_data)

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # display_name으로 기존 사용자 조회
                cur.execute(
                    """
                    SELECT id, display_name, age, employment_status, base_score,
                           daily_study_time, study_duration, registration_date, last_login
                    FROM users WHERE display_name = %s
                    """,
                    (req.display_name,),
                )
                row = cur.fetchone()

                if row:
                    # 기존 사용자 업데이트
                    cur.execute(
                        """
                        UPDATE users SET
                            age = COALESCE(%s, age),
                            employment_status = COALESCE(%s, employment_status),
                            base_score = COALESCE(%s, base_score),
                            daily_study_time = COALESCE(%s, daily_study_time),
                            study_duration = COALESCE(%s, study_duration),
                            last_login = now()
                        WHERE id = %s
                        RETURNING id, display_name, age, employment_status, base_score,
                                  daily_study_time, study_duration, registration_date, last_login
                        """,
                        (
                            req.age,
                            req.employment_status,
                            req.base_score,
                            req.daily_study_time,
                            req.study_duration,
                            row[0],
                        ),
                    )
                    row = cur.fetchone()
                    conn.commit()

                    return {
                        "success": True,
                        "method": "rule_based",
                        "user": UserResponse(
                            id=int(row[0]),
                            display_name=str(row[1]),
                            age=int(row[2]) if row[2] else None,
                            employment_status=str(row[3]) if row[3] else None,
                            base_score=int(row[4]) if row[4] else None,
                            daily_study_time=int(row[5]) if row[5] else None,
                            study_duration=str(row[6]) if row[6] else None,
                            registration_date=row[7].isoformat() if row[7] else None,
                            last_login=row[8].isoformat() if row[8] else None,
                        ).model_dump(),
                    }
                else:
                    # 새 사용자 생성
                    cur.execute(
                        """
                        INSERT INTO users (display_name, age, employment_status, base_score,
                                         daily_study_time, study_duration)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, display_name, age, employment_status, base_score,
                                  daily_study_time, study_duration, registration_date, last_login
                        """,
                        (
                            req.display_name,
                            req.age,
                            req.employment_status,
                            req.base_score,
                            req.daily_study_time,
                            req.study_duration,
                        ),
                    )
                    row = cur.fetchone()
                    conn.commit()

                    return {
                        "success": True,
                        "method": "rule_based",
                        "user": UserResponse(
                            id=int(row[0]),
                            display_name=str(row[1]),
                            age=int(row[2]) if row[2] else None,
                            employment_status=str(row[3]) if row[3] else None,
                            base_score=int(row[4]) if row[4] else None,
                            daily_study_time=int(row[5]) if row[5] else None,
                            study_duration=str(row[6]) if row[6] else None,
                            registration_date=row[7].isoformat() if row[7] else None,
                            last_login=row[8].isoformat() if row[8] else None,
                        ).model_dump(),
                    }
        except Exception as exc:
            conn.rollback()
            return {
                "success": False,
                "method": "rule_based",
                "error": str(exc),
            }

    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """사용자 ID로 조회.

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 정보 또는 None
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, display_name, age, employment_status, base_score,
                           daily_study_time, study_duration, registration_date, last_login,
                           is_first_timer, target_position, weak_subjects, strong_subjects,
                           provider
                    FROM users WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()

                if row:
                    return UserResponse(
                        id=int(row[0]),
                        display_name=str(row[1]),
                        age=int(row[2]) if row[2] else None,
                        employment_status=str(row[3]) if row[3] else None,
                        base_score=int(row[4]) if row[4] else None,
                        daily_study_time=int(row[5]) if row[5] else None,
                        study_duration=str(row[6]) if row[6] else None,
                        registration_date=row[7].isoformat() if row[7] else None,
                        last_login=row[8].isoformat() if row[8] else None,
                        is_first_timer=bool(row[9]) if row[9] is not None else None,
                        target_position=str(row[10]) if row[10] else None,
                        weak_subjects=str(row[11]) if row[11] else None,
                        strong_subjects=str(row[12]) if row[12] else None,
                        provider=str(row[13]) if row[13] else None,
                    ).model_dump()
                return None
        except Exception:
            return None

    async def update_user_profile(self, user_id: int, req: UserUpdateRequest) -> Optional[dict]:
        """사용자 프로필 업데이트.

        Args:
            user_id: 사용자 ID
            req: 업데이트 요청 데이터

        Returns:
            업데이트된 사용자 정보 또는 None
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # 동적 SET 절 생성: 요청에 포함된 필드만 업데이트
                # Pydantic model_fields_set 을 통해 명시적으로 전달된 필드 판별
                fields_to_update = req.model_fields_set  # 실제 전송된 필드 집합
                set_clauses = []
                params: list = []

                field_column_map = {
                    "display_name": "display_name",
                    "age": "age",
                    "employment_status": "employment_status",
                    "base_score": "base_score",
                    "daily_study_time": "daily_study_time",
                    "study_duration": "study_duration",
                    "is_first_timer": "is_first_timer",
                    "target_position": "target_position",
                    "weak_subjects": "weak_subjects",
                    "strong_subjects": "strong_subjects",
                }

                for field_name, col_name in field_column_map.items():
                    if field_name in fields_to_update:
                        set_clauses.append(f"{col_name} = %s")
                        params.append(getattr(req, field_name))

                if not set_clauses:
                    # 업데이트할 필드가 없으면 현재 값 그대로 반환
                    return await self.get_user_by_id(user_id)

                params.append(user_id)

                sql = f"""
                    UPDATE users SET
                        {', '.join(set_clauses)}
                    WHERE id = %s
                    RETURNING id, display_name, age, employment_status, base_score,
                              daily_study_time, study_duration, registration_date, last_login,
                              is_first_timer, target_position, weak_subjects, strong_subjects,
                              provider
                """
                cur.execute(sql, tuple(params))
                row = cur.fetchone()
                conn.commit()

                if row:
                    return UserResponse(
                        id=int(row[0]),
                        display_name=str(row[1]),
                        age=int(row[2]) if row[2] else None,
                        employment_status=str(row[3]) if row[3] else None,
                        base_score=int(row[4]) if row[4] else None,
                        daily_study_time=int(row[5]) if row[5] else None,
                        study_duration=str(row[6]) if row[6] else None,
                        registration_date=row[7].isoformat() if row[7] else None,
                        last_login=row[8].isoformat() if row[8] else None,
                        is_first_timer=bool(row[9]) if row[9] is not None else None,
                        target_position=str(row[10]) if row[10] else None,
                        weak_subjects=str(row[11]) if row[11] else None,
                        strong_subjects=str(row[12]) if row[12] else None,
                        provider=str(row[13]) if row[13] else None,
                    ).model_dump()
                return None
        except Exception as exc:
            conn.rollback()
            raise exc
