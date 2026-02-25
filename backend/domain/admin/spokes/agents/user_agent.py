"""User 정책 기반 에이전트.

새 테이블 구조:
- Users: display_name, age, employment_status, base_score, daily_study_time, study_duration

애매한 경우(정책 기반)에 사용되는 에이전트.
LLM을 사용하여 더 정교한 판단을 수행할 수 있음.
"""

from typing import Optional

from backend.dependencies import get_db_connection, get_llm
from backend.domain.admin.models.transfers.user_transfer import (
    UserCreateRequest,
    UserResponse,
)


class UserAgent:
    """User 정책 기반 에이전트."""

    async def handle_request(
        self, request_text: str, request_data: dict, koelectra_result: dict
    ) -> dict:
        """정책 기반 요청 처리.

        Args:
            request_text: 요청 텍스트 (LLM 분석용)
            request_data: 요청 데이터 (display_name, age 등)
            koelectra_result: KoELECTRA 분석 결과

        Returns:
            처리 결과
        """
        # UserCreateRequest로 변환
        req = UserCreateRequest(**request_data)

        # LLM으로 추가 분석 (필요시)
        spam_prob = koelectra_result.get("spam_prob", 0.5)

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
                        "method": "policy_based",
                        "koelectra_result": koelectra_result,
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
                        "method": "policy_based",
                        "koelectra_result": koelectra_result,
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
                "method": "policy_based",
                "error": str(exc),
            }
