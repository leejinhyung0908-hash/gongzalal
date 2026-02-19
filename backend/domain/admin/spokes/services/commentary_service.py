"""Commentary 규칙 기반 서비스.

새 테이블 구조:
- Commentaries: question_id FK, body, type, success_period, target_exam, final_score, approved
- Audio_Notes: commentary_id FK, file_path, voice_type, duration
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional

from backend.dependencies import get_db_connection
from backend.domain.admin.models.transfers.commentary_transfer import (
    CommentaryCreateRequest,
    CommentaryResponse,
)

logger = logging.getLogger(__name__)


class CommentaryService:
    """Commentary 규칙 기반 서비스."""

    async def handle_request(self, request_data: dict, koelectra_result: dict) -> dict:
        """규칙 기반 요청 처리.

        Args:
            request_data: 요청 데이터 (user_id, question_id, body 등)
            koelectra_result: KoELECTRA 분석 결과 (참고용)

        Returns:
            처리 결과
        """
        # CommentaryCreateRequest로 변환
        req = CommentaryCreateRequest(**request_data)

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # 기존 해설 조회 (user_id + question_id)
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
                        "method": "rule_based",
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
                        "method": "rule_based",
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
                "method": "rule_based",
                "error": str(exc),
            }

    def _parse_source_md(self, source_md: str) -> Dict[str, Any]:
        """source_md 파일명에서 메타데이터 추출.

        예: "250621 지방직 9급 한국사 해설 한pro.md"
        → {"year": 2025, "exam_type": "지방직", "grade": "9급"}

        Args:
            source_md: source_md 파일명

        Returns:
            파싱된 메타데이터 딕셔너리
        """
        if not source_md:
            return {}

        result = {}

        # 날짜 추출 (앞 6자리: YYMMDD)
        date_match = re.match(r"(\d{2})\d{4}", source_md)
        if date_match:
            try:
                year_2digit = int(date_match.group(1))
                if year_2digit < 50:
                    result["year"] = 2000 + year_2digit
                else:
                    result["year"] = 1900 + year_2digit
            except (ValueError, IndexError):
                pass

        # exam_type 추출
        if "지방" in source_md or "지방직" in source_md:
            result["exam_type"] = "지방직"
        elif "국가" in source_md or "국가직" in source_md:
            result["exam_type"] = "국가직"

        # grade 추출
        grade_match = re.search(r"(\d+)\s*급", source_md)
        if grade_match:
            result["grade"] = f"{grade_match.group(1)}급"

        return result

    def _find_question_id(
        self,
        conn,
        year: int,
        exam_type: str,
        subject: str,
        question_no: int,
        grade: Optional[str] = None,
        series: Optional[str] = None,
    ) -> Optional[int]:
        """questions 테이블에서 question_id 찾기 (새 스키마).

        Args:
            conn: DB 연결
            year: 연도
            exam_type: 시험 유형
            subject: 과목명
            question_no: 문항 번호
            grade: 급수 (선택)
            series: 시리즈 (선택)

        Returns:
            question_id 또는 None
        """
        try:
            with conn.cursor() as cur:
                # exams와 questions를 JOIN하여 조회
                cur.execute(
                    """
                    SELECT q.id FROM questions q
                    JOIN exams e ON q.exam_id = e.id
                    WHERE e.year = %s AND e.exam_type = %s AND e.subject = %s
                      AND q.question_no = %s
                    LIMIT 1
                    """,
                    (year, exam_type, subject, question_no),
                )
                row = cur.fetchone()
                if row:
                    question_id = int(row[0])
                    logger.debug(f"[CommentaryService] question_id 찾음: {question_id}")
                    return question_id
                else:
                    logger.warning(
                        f"[CommentaryService] question_id를 찾을 수 없음: "
                        f"year={year}, exam_type={exam_type}, subject={subject}, question_no={question_no}"
                    )
                return None
        except Exception as e:
            logger.error(f"[CommentaryService] question_id 조회 실패: {e}", exc_info=True)
            return None

    async def process_jsonl_to_commentaries(
        self,
        jsonl_data: List[Dict[str, Any]],
        user_id: int = 1,
        series: Optional[str] = None,
    ) -> Dict[str, Any]:
        """JSONL 데이터를 commentaries 테이블 형식으로 변환 및 삽입.

        all_commentary.jsonl 형식 지원:
        - id: 전역 순번 (과목별 question_no가 아님 → 과목별로 자동 재계산)
        - question: 해설 본문 (body)
        - answer: 정답 번호 (참고용)
        - subject: 과목명
        - source_md: 원본 마크다운 파일명 (연도/시험유형/급수 파싱)
        - source_pdf: 원본 PDF 파일명

        Args:
            jsonl_data: 파싱된 JSONL 데이터 리스트
            user_id: 해설을 작성한 사용자 ID (기본값: 1, 시스템 사용자)
            series: 시리즈 (선택)

        Returns:
            처리 결과
        """
        conn = get_db_connection()
        conversion_errors: List[Dict[str, Any]] = []
        insertion_errors: List[Dict[str, Any]] = []
        inserted_count = 0
        skipped_count = 0

        # 시스템 사용자 확인 및 생성
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                existing_user = cur.fetchone()

                if not existing_user:
                    logger.info(f"[CommentaryService] 시스템 사용자(user_id={user_id})가 없어 생성합니다.")
                    cur.execute(
                        """
                        INSERT INTO users (display_name)
                        VALUES (%s)
                        RETURNING id
                        """,
                        (f"시스템 사용자 {user_id}",),
                    )
                    new_user = cur.fetchone()
                    if new_user:
                        user_id = int(new_user[0])
                        conn.commit()
                        logger.info(f"[CommentaryService] 새 시스템 사용자 생성 완료: user_id={user_id}")
                    else:
                        raise Exception("시스템 사용자 생성 실패")
        except Exception as e:
            conn.rollback()
            logger.error(f"[CommentaryService] 시스템 사용자 확인/생성 실패: {e}", exc_info=True)
            print(f"[CommentaryService] ⚠️ 시스템 사용자 확인/생성 실패: {e}", flush=True)

        logger.info(
            f"[CommentaryService] JSONL → commentaries 변환 시작: {len(jsonl_data)}개 항목"
        )
        print(
            f"[CommentaryService] JSONL → commentaries 변환 시작: {len(jsonl_data)}개 항목",
            flush=True,
        )

        # ── 과목별 question_no 카운터 ──
        # all_commentary.jsonl의 id는 전역 순번이므로 과목별로 1부터 다시 세야 함
        subject_counter: Dict[str, int] = {}

        for idx, item in enumerate(jsonl_data, start=1):
            try:
                # ── 필드 추출 ──
                body = str(item.get("question", "")).replace("\x00", "").strip()
                if not body:
                    conversion_errors.append({
                        "index": idx,
                        "error": "question 필드가 없거나 비어있습니다.",
                        "data": item,
                    })
                    continue

                subject = str(item.get("subject", "")).strip()
                if not subject:
                    conversion_errors.append({
                        "index": idx,
                        "error": "subject 필드가 없습니다.",
                        "data": item,
                    })
                    continue

                source_md = item.get("source_md")

                # ── 과목별 question_no 계산 ──
                # 같은 subject가 처음 나오면 1, 이후 +1
                if subject not in subject_counter:
                    subject_counter[subject] = 0
                subject_counter[subject] += 1
                question_no = subject_counter[subject]

                # source_md에서 메타데이터 추출
                parsed = self._parse_source_md(source_md or "")
                year = parsed.get("year") or 2025
                exam_type = parsed.get("exam_type") or "지방직"
                grade = parsed.get("grade") or "9급"

                if idx <= 3:
                    print(
                        f"[CommentaryService] [{idx}] subject={subject}, "
                        f"question_no={question_no}, year={year}, exam_type={exam_type}, "
                        f"body_len={len(body)}, source_md={source_md}",
                        flush=True,
                    )

                # question_id 찾기
                question_id = self._find_question_id(
                    conn=conn,
                    year=year,
                    exam_type=exam_type,
                    subject=subject,
                    question_no=question_no,
                    grade=grade,
                    series=series,
                )

                if idx <= 3:
                    print(
                        f"[CommentaryService] [{idx}] _find_question_id → {question_id}",
                        flush=True,
                    )

                # 연도 불일치 시 2024로도 시도
                if not question_id and year == 2025:
                    question_id = self._find_question_id(
                        conn=conn,
                        year=2024,
                        exam_type=exam_type,
                        subject=subject,
                        question_no=question_no,
                        grade=grade,
                        series=series,
                    )
                    if question_id:
                        year = 2024

                if not question_id:
                    error_msg = (
                        f"question_id를 찾을 수 없습니다. "
                        f"(year={year}, exam_type={exam_type}, subject={subject}, "
                        f"question_no={question_no})"
                    )
                    print(f"[CommentaryService] ⚠️ [{idx}] {error_msg}", flush=True)
                    conversion_errors.append({
                        "index": idx,
                        "error": error_msg,
                        "data": {
                            "id": item.get("id"),
                            "subject": subject,
                            "question_no": question_no,
                        },
                    })
                    continue

                # ── commentaries 삽입/업데이트 ──
                try:
                    with conn.cursor() as cur:
                        # 기존 해설 확인 (question_id 기준)
                        # DB enum은 name (EXPLANATION) 을 사용
                        cur.execute(
                            """
                            SELECT id FROM commentaries
                            WHERE question_id = %s AND type = 'EXPLANATION'
                            LIMIT 1
                            """,
                            (question_id,),
                        )
                        existing = cur.fetchone()

                        if existing:
                            cur.execute(
                                """
                                UPDATE commentaries
                                SET body = %s, user_id = %s, updated_at = now()
                                WHERE id = %s
                                """,
                                (body, user_id, existing[0]),
                            )
                            skipped_count += 1
                            if idx <= 3:
                                print(
                                    f"[CommentaryService] [{idx}] 해설 업데이트: commentary_id={existing[0]}",
                                    flush=True,
                                )
                        else:
                            cur.execute(
                                """
                                INSERT INTO commentaries (user_id, question_id, body, type, approved)
                                VALUES (%s, %s, %s, 'EXPLANATION'::commentary_type_enum, true)
                                RETURNING id
                                """,
                                (user_id, question_id, body),
                            )
                            new_id = cur.fetchone()
                            if new_id:
                                inserted_count += 1
                                if idx <= 3:
                                    print(
                                        f"[CommentaryService] [{idx}] 해설 생성: commentary_id={new_id[0]}",
                                        flush=True,
                                    )
                            else:
                                raise Exception("INSERT 후 RETURNING id가 None")

                    conn.commit()

                except Exception as e:
                    conn.rollback()
                    print(
                        f"[CommentaryService] ❌ [{idx}] DB 삽입 실패: {e}",
                        flush=True,
                    )
                    insertion_errors.append({
                        "index": idx,
                        "error": f"DB 삽입 실패: {str(e)}",
                        "data": {
                            "question_id": question_id,
                            "question_no": question_no,
                            "subject": subject,
                        },
                    })

            except Exception as e:
                print(f"[CommentaryService] ❌ [{idx}] 변환 오류: {e}", flush=True)
                conversion_errors.append({
                    "index": idx,
                    "error": f"변환 중 오류: {str(e)}",
                    "data": item,
                })

        summary = (
            f"commentaries: {inserted_count}개 삽입, {skipped_count}개 업데이트"
        )
        logger.info(
            f"[CommentaryService] 완료 — {summary}, "
            f"변환실패={len(conversion_errors)}, 삽입실패={len(insertion_errors)}"
        )
        print(f"[CommentaryService] ✅ {summary}", flush=True)

        return {
            "success": True,
            "message": summary,
            "inserted_count": inserted_count,
            "skipped_count": skipped_count,
            "conversion_errors": conversion_errors,
            "insertion_errors": insertion_errors,
        }

    async def get_commentary_by_id(self, commentary_id: int) -> Optional[dict]:
        """해설 ID로 조회.

        Args:
            commentary_id: 해설 ID

        Returns:
            해설 정보 또는 None
        """
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, user_id, question_id, body, type,
                           success_period, target_exam, final_score, approved,
                           created_at, updated_at
                    FROM commentaries WHERE id = %s
                    """,
                    (commentary_id,),
                )
                row = cur.fetchone()

                if row:
                    return CommentaryResponse(
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
                    ).model_dump()
                return None
        except Exception:
            return None
