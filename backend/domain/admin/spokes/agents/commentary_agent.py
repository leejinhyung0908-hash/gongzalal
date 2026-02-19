"""Commentary 정책 기반 에이전트.

새 테이블 구조:
- Commentaries: question_id FK, body, type, success_period, target_exam, final_score, approved

애매한 경우(정책 기반)에 사용되는 에이전트.
LLM을 사용하여 더 정교한 판단을 수행할 수 있음.
"""

import json
from typing import Dict

from backend.dependencies import get_db_connection, get_llm
from backend.domain.admin.models.transfers.commentary_transfer import (
    CommentaryCreateRequest,
    CommentaryResponse,
)


class CommentaryAgent:
    """Commentary 정책 기반 에이전트."""

    async def handle_request(
        self, request_text: str, request_data: dict, koelectra_result: dict
    ) -> dict:
        """정책 기반 요청 처리.

        Args:
            request_text: 요청 텍스트 (LLM 분석용)
            request_data: 요청 데이터 (user_id, question_id, body 등)
            koelectra_result: KoELECTRA 분석 결과

        Returns:
            처리 결과
        """
        # CommentaryCreateRequest로 변환
        req = CommentaryCreateRequest(**request_data)

        # LLM으로 추가 분석 (필요시)
        spam_prob = koelectra_result.get("spam_prob", 0.5)

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM commentaries
                    WHERE user_id = %s AND question_id = %s
                    """,
                    (req.user_id, req.question_id),
                )
                row = cur.fetchone()

                if row:
                    # 기존 해설 업데이트
                    cur.execute(
                        """
                        UPDATE commentaries
                        SET body = %s,
                            type = %s,
                            success_period = %s,
                            target_exam = %s,
                            final_score = %s,
                            updated_at = now()
                        WHERE id = %s
                        RETURNING id, user_id, question_id, body, type,
                                  success_period, target_exam, final_score, approved,
                                  created_at, updated_at
                        """,
                        (
                            req.body,
                            req.type,
                            req.success_period,
                            req.target_exam,
                            req.final_score,
                            row[0],
                        ),
                    )
                    row = cur.fetchone()
                    conn.commit()

                    return {
                        "success": True,
                        "method": "policy_based",
                        "koelectra_result": koelectra_result,
                        "commentary": CommentaryResponse(
                            id=int(row[0]),
                            user_id=int(row[1]) if row[1] else None,
                            question_id=int(row[2]) if row[2] else None,
                            body=str(row[3]),
                            type=str(row[4]) if row[4] else None,
                            success_period=str(row[5]) if row[5] else None,
                            target_exam=str(row[6]) if row[6] else None,
                            final_score=int(row[7]) if row[7] else None,
                            approved=bool(row[8]),
                            created_at=row[9].isoformat() if row[9] else None,
                            updated_at=row[10].isoformat() if row[10] else None,
                        ).model_dump(),
                    }
                else:
                    # 새 해설 생성
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
                            req.user_id,
                            req.question_id,
                            req.body,
                            req.type,
                            req.success_period,
                            req.target_exam,
                            req.final_score,
                        ),
                    )
                    row = cur.fetchone()
                    conn.commit()

                    return {
                        "success": True,
                        "method": "policy_based",
                        "koelectra_result": koelectra_result,
                        "commentary": CommentaryResponse(
                            id=int(row[0]),
                            user_id=int(row[1]) if row[1] else None,
                            question_id=int(row[2]) if row[2] else None,
                            body=str(row[3]),
                            type=str(row[4]) if row[4] else None,
                            success_period=str(row[5]) if row[5] else None,
                            target_exam=str(row[6]) if row[6] else None,
                            final_score=int(row[7]) if row[7] else None,
                            approved=bool(row[8]),
                            created_at=row[9].isoformat() if row[9] else None,
                            updated_at=row[10].isoformat() if row[10] else None,
                        ).model_dump(),
                    }
        except Exception as exc:
            conn.rollback()
            return {
                "success": False,
                "method": "policy_based",
                "error": str(exc),
            }
