"""Exam 데이터 저장소 (Repository 패턴).

새 테이블 구조:
- exams: 시험 메타데이터
- questions: 개별 문제 정보

이전 exam_questions 테이블과의 호환성을 유지하면서 새 구조를 지원합니다.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

import psycopg

from backend.dependencies import get_db_connection

logger = logging.getLogger(__name__)


class ExamRepository:
    """Exam 데이터 저장소."""

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
    # 새 테이블 구조 메서드 (exams + questions)
    # ========================================================================

    def get_or_create_exam(
        self,
        year: int,
        exam_type: str,
        subject: str,
        series: Optional[str] = None,
        grade: Optional[str] = None
    ) -> int:
        """시험 조회 또는 생성하고 ID 반환.

        Args:
            year: 시험 연도
            exam_type: 시험 유형
            subject: 과목
            series: 시험 시리즈 (optional)
            grade: 등급 (optional)

        Returns:
            exam_id
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            # 동적 WHERE절 (psycopg3에서 None 파라미터 타입 추론 문제 방지)
            conditions = ["year = %s", "exam_type = %s", "subject = %s"]
            params: list = [year, exam_type, subject]

            if series is None:
                conditions.append("series IS NULL")
            else:
                conditions.append("series = %s")
                params.append(series)

            if grade is None:
                conditions.append("grade IS NULL")
            else:
                conditions.append("grade = %s")
                params.append(grade)

            where_clause = " AND ".join(conditions)
            cur.execute(
                f"SELECT id FROM exams WHERE {where_clause} LIMIT 1",
                tuple(params)
            )
            row = cur.fetchone()
            if row:
                return row[0]

            # 새 시험 생성 (명시적 타입 캐스팅으로 NULL 처리)
            cur.execute(
                """
                INSERT INTO exams (year, exam_type, subject, series, grade)
                VALUES (%s, %s, %s, %s::text, %s::text)
                RETURNING id
                """,
                (year, exam_type, subject, series, grade)
            )
            exam_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"[ExamRepository] 새 시험 생성: id={exam_id}, {year}년 {exam_type} {subject}")
            return exam_id

    def insert_question(
        self,
        exam_id: int,
        question_no: int,
        question_text: str,
        answer_key: str,
        sub_category: Optional[str] = None,
        ind: Optional[bool] = None,
        source_pdf: Optional[str] = None,
        extra_json: Optional[Dict[str, Any]] = None
    ) -> int:
        """문제 삽입.

        Args:
            exam_id: 시험 ID
            question_no: 문제 번호
            question_text: 문제 텍스트
            answer_key: 정답
            sub_category: 하위 카테고리
            ind: 독립 소스 여부
            source_pdf: 원본 PDF 경로
            extra_json: 추가 데이터

        Returns:
            question_id
        """
        conn = self._get_connection()
        from psycopg.types.json import Json

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO questions (
                    exam_id, question_no, question_text, answer_key,
                    sub_category, ind, source_pdf, extra_json
                ) VALUES (%s, %s, %s, %s, %s::text, %s::bool, %s::text, %s::jsonb)
                RETURNING id
                """,
                (
                    exam_id, question_no, question_text, answer_key,
                    sub_category, ind, source_pdf,
                    Json(extra_json or {})
                )
            )
            question_id = cur.fetchone()[0]
            conn.commit()
            return question_id

    def find_question(
        self,
        year: int,
        subject: str,
        question_no: int,
        exam_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """문제 검색 (exams + questions 조인).

        Args:
            year: 시험 연도
            subject: 과목
            question_no: 문제 번호
            exam_type: 시험 유형 (optional)

        Returns:
            문제 데이터 딕셔너리 또는 None
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            if exam_type:
                cur.execute(
                    """
                    SELECT
                        e.year, e.exam_type, e.series, e.grade, e.subject,
                        q.question_no, q.answer_key, q.question_text, q.extra_json
                    FROM questions q
                    JOIN exams e ON q.exam_id = e.id
                    WHERE e.year = %s AND e.subject = %s AND q.question_no = %s
                      AND e.exam_type = %s
                    LIMIT 1
                    """,
                    (year, subject, question_no, exam_type)
                )
            else:
                cur.execute(
                    """
                    SELECT
                        e.year, e.exam_type, e.series, e.grade, e.subject,
                        q.question_no, q.answer_key, q.question_text, q.extra_json
                    FROM questions q
                    JOIN exams e ON q.exam_id = e.id
                    WHERE e.year = %s AND e.subject = %s AND q.question_no = %s
                    LIMIT 1
                    """,
                    (year, subject, question_no)
                )

            row = cur.fetchone()
            if not row:
                return None

            return {
                "year": row[0],
                "exam_type": row[1],
                "series": row[2],
                "grade": row[3],
                "subject": row[4],
                "question_no": row[5],
                "answer_key": row[6],
                "question_text": row[7],
                "extra_json": row[8],
            }

    def get_subjects(self) -> List[str]:
        """DB에 있는 모든 과목 목록 조회.

        Returns:
            과목명 리스트
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            try:
                cur.execute("SELECT DISTINCT subject FROM exams ORDER BY subject")
                subjects = [str(r[0]) for r in cur.fetchall() if r and r[0]]
                return subjects
            except psycopg.errors.UndefinedTable:
                logger.warning("[ExamRepository] exams 테이블이 존재하지 않습니다.")
                return []

    # ========================================================================
    # 레거시 호환 메서드 (exam_questions 테이블)
    # ========================================================================

    def insert_exam_questions(
        self, exam_questions: List[Dict[str, Any]], skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """exam_questions 테이블에 데이터 삽입 (레거시 호환).

        새 테이블 구조(exams + questions)가 있으면 그쪽에 삽입하고,
        없으면 기존 exam_questions 테이블에 삽입합니다.

        Args:
            exam_questions: 삽입할 시험 문항 데이터 리스트
            skip_duplicates: 중복 시 건너뛰기 (True) 또는 에러 발생 (False)

        Returns:
            삽입 결과 (inserted_count, skipped_count, errors)
        """
        conn = self._get_connection()
        inserted_count = 0
        skipped_count = 0
        errors: List[Dict[str, Any]] = []

        # 새 테이블 존재 여부 확인
        use_new_tables = self._check_new_tables_exist(conn)

        if use_new_tables:
            return self._insert_to_new_tables(exam_questions, skip_duplicates)
        else:
            return self._insert_to_legacy_table(exam_questions, skip_duplicates)

    def _check_new_tables_exist(self, conn: psycopg.Connection) -> bool:
        """새 테이블(exams, questions)이 존재하는지 확인."""
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'exams'
                    ) AND EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'questions'
                    )
                    """
                )
                return cur.fetchone()[0]
        except Exception:
            return False

    def _insert_to_new_tables(
        self, exam_questions: List[Dict[str, Any]], skip_duplicates: bool
    ) -> Dict[str, Any]:
        """새 테이블 구조에 데이터 삽입."""
        inserted_count = 0
        skipped_count = 0
        errors: List[Dict[str, Any]] = []

        for idx, item in enumerate(exam_questions, start=1):
            try:
                year = int(item["year"])
                exam_type = str(item.get("exam_type", "지방직"))
                subject = str(item["subject"])
                series = item.get("job_series") or item.get("series")
                grade = item.get("grade")
                question_no = int(item["question_no"])
                question_text = str(item["question_text"])
                answer_key = str(item["answer_key"])
                source_pdf = item.get("source_pdf")
                extra_json = item.get("extra_json", {})

                # 시험 조회 또는 생성
                exam_id = self.get_or_create_exam(
                    year=year,
                    exam_type=exam_type,
                    subject=subject,
                    series=series,
                    grade=grade
                )

                # 중복 확인
                if skip_duplicates:
                    conn = self._get_connection()
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT id FROM questions
                            WHERE exam_id = %s AND question_no = %s
                            """,
                            (exam_id, question_no)
                        )
                        if cur.fetchone():
                            skipped_count += 1
                            continue

                # 문제 삽입
                self.insert_question(
                    exam_id=exam_id,
                    question_no=question_no,
                    question_text=question_text,
                    answer_key=answer_key,
                    source_pdf=source_pdf,
                    extra_json=extra_json
                )
                inserted_count += 1

            except Exception as e:
                errors.append({
                    "index": idx,
                    "error": str(e),
                    "data": item
                })
                logger.error(f"[ExamRepository] 삽입 오류 (index={idx}): {e}")

        logger.info(
            f"[ExamRepository] 새 테이블 삽입 완료: inserted={inserted_count}, "
            f"skipped={skipped_count}, errors={len(errors)}"
        )

        return {
            "inserted_count": inserted_count,
            "skipped_count": skipped_count,
            "errors": errors,
            "total": len(exam_questions)
        }

    def _insert_to_legacy_table(
        self, exam_questions: List[Dict[str, Any]], skip_duplicates: bool
    ) -> Dict[str, Any]:
        """레거시 exam_questions 테이블에 데이터 삽입."""
        conn = self._get_connection()
        inserted_count = 0
        skipped_count = 0
        errors: List[Dict[str, Any]] = []

        required_fields = ["year", "exam_type", "job_series", "subject", "question_no", "answer_key", "question_text"]

        with conn.cursor() as cur:
            for idx, item in enumerate(exam_questions, start=1):
                try:
                    missing_fields = [f for f in required_fields if f not in item or item[f] is None]
                    if missing_fields:
                        errors.append({
                            "index": idx,
                            "error": f"필수 필드 누락: {', '.join(missing_fields)}",
                            "data": item
                        })
                        continue

                    year = int(item["year"])
                    exam_type = str(item["exam_type"])
                    job_series = str(item["job_series"])
                    grade = str(item.get("grade", "9급"))
                    exam_name = str(item.get("exam_name", "지방공무원 공개경쟁임용"))
                    subject = str(item["subject"])
                    question_no = int(item["question_no"])
                    question_text = str(item["question_text"])
                    answer_key = str(item["answer_key"])
                    source_md = item.get("source_md")
                    source_pdf = item.get("source_pdf")

                    from psycopg.types.json import Json
                    extra_json = Json(item.get("extra_json", {}))

                    if skip_duplicates:
                        cur.execute(
                            """
                            SELECT id FROM exam_questions
                            WHERE year=%s AND exam_type=%s AND job_series=%s
                              AND grade=%s AND subject=%s AND question_no=%s
                            """,
                            (year, exam_type, job_series, grade, subject, question_no)
                        )
                        if cur.fetchone():
                            skipped_count += 1
                            continue

                    cur.execute(
                        """
                        INSERT INTO exam_questions (
                            year, exam_type, job_series, grade, exam_name,
                            subject, question_no, question_text, answer_key,
                            source_md, source_pdf, extra_json
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        RETURNING id
                        """,
                        (
                            year, exam_type, job_series, grade, exam_name,
                            subject, question_no, question_text, answer_key,
                            source_md, source_pdf, extra_json
                        )
                    )
                    inserted_count += 1

                except psycopg.IntegrityError:
                    if skip_duplicates:
                        skipped_count += 1
                    else:
                        errors.append({"index": idx, "error": "무결성 제약 위반", "data": item})
                except Exception as e:
                    errors.append({"index": idx, "error": str(e), "data": item})

            try:
                conn.commit()
            except Exception as e:
                logger.error(f"[ExamRepository] 커밋 실패: {e}")

        return {
            "inserted_count": inserted_count,
            "skipped_count": skipped_count,
            "errors": errors,
            "total": len(exam_questions)
        }

    def find_question_legacy(
        self,
        year: int,
        subject: str,
        question_no: int,
        exam_type: Optional[str] = None,
        job_series: Optional[str] = None,
        grade: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """레거시 exam_questions 테이블에서 문제 검색.

        Args:
            year: 시험 연도
            subject: 과목
            question_no: 문제 번호
            exam_type: 시험 유형 (optional)
            job_series: 직렬 (optional)
            grade: 등급 (optional)

        Returns:
            문제 데이터 딕셔너리 또는 None
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            sql = """
                SELECT year, exam_type, job_series, grade, subject, question_no, answer_key
                FROM exam_questions
                WHERE year = %s AND subject = %s AND question_no = %s
            """
            params = [year, subject, question_no]

            if exam_type:
                sql += " AND exam_type = %s"
                params.append(exam_type)
            if job_series:
                sql += " AND job_series = %s"
                params.append(job_series)
            if grade:
                sql += " AND grade = %s"
                params.append(grade)

            sql += " LIMIT 1"

            cur.execute(sql, params)
            row = cur.fetchone()

            if not row:
                return None

            return {
                "year": row[0],
                "exam_type": row[1],
                "job_series": row[2],
                "grade": row[3],
                "subject": row[4],
                "question_no": row[5],
                "answer_key": row[6],
            }
