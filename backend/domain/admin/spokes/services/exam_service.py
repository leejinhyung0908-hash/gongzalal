"""Exam 규칙 기반 서비스.

명확한 경우(규칙 기반)에 사용되는 서비스.
"""

import re
from datetime import datetime
from typing import Optional, Dict, List, Any

import psycopg
from pydantic import BaseModel, Field

from backend.dependencies import get_db_connection
from backend.domain.admin.hub.repositories.exam_repository import ExamRepository


# 모델 정의 (순환 import 방지)
class ExamAnswerRequest(BaseModel):
    question: str = Field(..., description="사용자 질문(예: 작년 회계학 3번 문제 정답 뭐야?)")


class ExamAnswerResponse(BaseModel):
    year: int
    exam_type: str
    job_series: str
    grade: str
    subject: str
    question_no: int
    answer_key: str


# 파싱 함수들 (순환 import 방지)
def _resolve_relative_year(text: str, now_year: int) -> Optional[int]:
    """상대 연도 파싱."""
    m = re.search(r"(?:(20)?(\d{2}))\s*년", text)
    if m:
        y2 = int(m.group(2))
        return 2000 + y2
    if "올해" in text:
        return now_year
    if "작년" in text:
        return now_year - 1
    if "재작년" in text or "그저께" in text:
        return now_year - 2
    return None


def _parse_exam_type(text: str) -> Optional[str]:
    """시험 구분 파싱."""
    if "국가직" in text:
        return "국가직"
    if "지방직" in text or "지방" in text:
        return "지방직"
    return None


def _parse_grade(text: str) -> str:
    """급수 파싱."""
    m = re.search(r"(\d)\s*급", text)
    if m:
        return f"{m.group(1)}급"
    return "9급"


def _parse_question_no(text: str) -> Optional[int]:
    """문항 번호 파싱."""
    m = re.search(r"(\d{1,3})\s*번", text)
    if not m:
        return None
    return int(m.group(1))


def _parse_subject(text: str, conn: psycopg.Connection) -> Optional[str]:
    """과목명 파싱 (DB 기반)."""
    import logging
    import difflib
    logger = logging.getLogger(__name__)

    with conn.cursor() as cur:
        # 실제 DB 테이블명과 컬럼명 사용 (exams 테이블)
        cur.execute("SELECT DISTINCT subject FROM exams ORDER BY subject")
        raw_subjects = [str(r[0]) for r in cur.fetchall() if r and r[0]]

    # DB 값에 선행/후행 공백이 섞여있는 케이스가 있어 정규화
    subjects_stripped = [s.strip() for s in raw_subjects if s and s.strip()]
    # 중복 제거(순서 유지)
    seen = set()
    subjects: list[str] = []
    for s in subjects_stripped:
        if s not in seen:
            seen.add(s)
            subjects.append(s)

    if subjects:
        logger.info(f"[ExamService] DB에서 가져온 과목 목록: {list(subjects[:10])}... (총 {len(subjects)}개)")
    else:
        logger.warning("[ExamService] DB에서 과목 목록을 가져오지 못했습니다.")
    logger.info(f"[ExamService] 파싱할 텍스트: {text}")

    # 긴 과목명부터 매칭 (예: "행정법총론"이 "행정법"보다 우선)
    if not subjects:
        return None

    subjects_sorted = sorted(subjects, key=len, reverse=True)

    # 1) 원문 기반 매칭 (사용자 텍스트 안에 '전체 과목명'이 포함된 경우)
    for s in subjects_sorted:
        if s and s in text:
            logger.info(f"[ExamService] 과목명 매칭 성공(원문): '{s}'")
            return s

    # 2) 공백 제거 후 매칭 (예: '행정 법 총 론' 등)
    text_compact = text.replace(" ", "")
    compact_to_original: dict[str, str] = {}
    for s in subjects_sorted:
        key = s.replace(" ", "")
        if key and key not in compact_to_original:
            compact_to_original[key] = s
        if key and key in text_compact:
            matched = compact_to_original[key]
            logger.info(f"[ExamService] 과목명 매칭 성공(공백제거): '{matched}'")
            return matched

    # 3) 축약 과목명 매칭 (사용자 입력이 더 짧고, DB 과목명이 더 긴 경우)
    # 예: 사용자 '행정법' vs DB '행정법총론'
    #
    # 기존 토큰 추출은 '25년행정법3번...' 같은 문자열에서 '년행정법'처럼 불필요 접두가 섞일 수 있어
    # 먼저 숫자/년/번/고정문구를 제거한 hint를 만든 뒤, hint가 과목명에 포함되는지로 매칭한다.
    hint = text_compact
    hint = re.sub(r"(20\d{2}|\d{2})년", "", hint)
    hint = re.sub(r"\d+\s*급", "", hint)
    hint = re.sub(r"\d+\s*번", "", hint)
    hint = re.sub(r"\d+", "", hint)
    hint = re.sub(r"(정답|문제|시험|과목|문항|알려줘|알려|답|해설|설명)", "", hint)
    hint = hint.strip()

    if hint:
        candidates: list[str] = []
        for s in subjects_sorted:
            s_compact = s.replace(" ", "")
            if hint in s_compact:
                candidates.append(s)

        if candidates:
            # 여러 개면: 가장 짧은 과목명(가장 표준/핵심)에 우선
            candidates.sort(key=lambda x: len(x.replace(" ", "")))
            best = candidates[0]
            logger.info(f"[ExamService] 과목명 매칭 성공(축약-hint): '{best}' (hint='{hint}')")
            return best

    if subjects:
        # 유사 과목 후보 제안 (디버깅/UX 개선)
        candidates = difflib.get_close_matches(text_compact, list(compact_to_original.keys()), n=5, cutoff=0.6)
        suggestions = [compact_to_original[c] for c in candidates] if candidates else []
        logger.warning(
            f"[ExamService] 과목명 매칭 실패. 텍스트: {text}, "
            f"가능한 과목(예시): {list(subjects[:5])}, "
            f"유사 제안: {suggestions}"
        )
    else:
        logger.warning(f"[ExamService] 과목명 매칭 실패. 텍스트: {text}, 과목 목록 없음")
    return None


def _parse_job_series(text: str) -> Optional[str]:
    """직렬 파싱."""
    m = re.search(r"([가-힣]+행정직)", text)
    if m:
        return m.group(1)
    if "교육행정" in text:
        return "교육행정직"
    if "일반행정" in text:
        return "일반행정직"
    return None


class ExamService:
    """Exam 규칙 기반 서비스."""

    def __init__(self):
        """초기화."""
        self._repository = ExamRepository()

    async def handle_request(self, request_data: dict, koelectra_result: dict) -> dict:
        """규칙 기반 요청 처리.

        Args:
            request_data: 요청 데이터 (question 등)
            koelectra_result: KoELECTRA 분석 결과 (참고용)

        Returns:
            처리 결과
        """
        # ExamAnswerRequest로 변환
        req = ExamAnswerRequest(**request_data)

        # 기존 exam_router의 로직 재사용
        import logging
        logger = logging.getLogger(__name__)

        conn = get_db_connection()
        now_year = datetime.now().year
        year = _resolve_relative_year(req.question, now_year) or now_year

        # exam_type 파싱: DB에는 NULL일 수 있으므로 조건에서 제외하거나 IS NULL 처리
        parsed_exam_type = _parse_exam_type(req.question)
        exam_type = parsed_exam_type  # NULL일 수 있으므로 조건 완화

        grade = _parse_grade(req.question)
        subject = _parse_subject(req.question, conn)
        qno = _parse_question_no(req.question)
        job_series = _parse_job_series(req.question)

        logger.info(
            f"[ExamService] 파싱된 엔티티: year={year}, exam_type={exam_type}, "
            f"grade={grade}, subject={subject}, question_no={qno}, job_series={job_series}"
        )

        if subject is None:
            # 사용자 입력에서 과목 후보 텍스트를 뽑아 유사 과목을 제안
            import difflib
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT subject FROM exams ORDER BY subject")
                raw_subjects = [str(r[0]) for r in cur.fetchall() if r and r[0]]
            subjects = []
            seen = set()
            for s in raw_subjects:
                s2 = s.strip()
                if s2 and s2 not in seen:
                    seen.add(s2)
                    subjects.append(s2)

            # 질문에서 숫자/조사/고정 문구를 제거해 '과목 후보'만 남김
            q_clean = req.question
            q_clean = re.sub(r"\s+", "", q_clean)
            q_clean = re.sub(r"(20\d{2}|\d{2})년", "", q_clean)
            q_clean = re.sub(r"\d+\s*급", "", q_clean)
            q_clean = re.sub(r"\d+\s*번", "", q_clean)
            q_clean = re.sub(r"(정답|문제|시험|과목|문항|알려줘|알려|답|알려줄래)", "", q_clean)
            q_clean = q_clean.strip()

            # 유사도 기반 제안 (과목 후보 vs DB 과목)
            subj_compact = [s.replace(" ", "") for s in subjects]
            compact_to_original = {s.replace(" ", ""): s for s in subjects}
            candidates = difflib.get_close_matches(q_clean, subj_compact, n=5, cutoff=0.55)
            suggestions = [compact_to_original[c] for c in candidates] if candidates else []

            logger.warning(
                f"[ExamService] 과목 인식 실패: input_subject_hint='{q_clean}', suggestions={suggestions}"
            )
            return {
                "success": False,
                "method": "rule_based",
                "error": "과목명을 인식하지 못했습니다. (예: 회계학/행정학개론/헌법총론)",
                "available_subjects": subjects[:30],
                "suggested_subjects": suggestions,
            }
        if qno is None:
            return {
                "success": False,
                "method": "rule_based",
                "error": "문항 번호를 인식하지 못했습니다. (예: 3번)",
            }

        # DB 조회
        try:
            import logging
            logger = logging.getLogger(__name__)

            with conn.cursor() as cur:
                # 실제 DB 스키마: exams + questions 테이블 (조인)
                # exam_type, grade, series는 NULL일 수 있으므로 year, subject, question_no만 필수 조건으로 사용
                sql = """
                    SELECT e.year, e.exam_type, e.series, e.grade, e.subject, q.question_no, q.answer_key
                    FROM questions q
                    JOIN exams e ON q.exam_id = e.id
                    WHERE e.year=%s AND e.subject=%s AND q.question_no=%s
                    LIMIT 1
                """
                params = (year, subject, qno)
                logger.info(f"[ExamService] DB 조회: year={year}, subject={subject}, question_no={qno}")

                cur.execute(sql, params)
                row = cur.fetchone()

                if not row:
                    # 유사한 데이터가 있는지 확인 (디버깅용)
                    with conn.cursor() as debug_cur:
                        debug_cur.execute(
                            """
                            SELECT e.year, e.exam_type, e.series, e.grade, e.subject, q.question_no
                            FROM questions q
                            JOIN exams e ON q.exam_id = e.id
                            WHERE e.subject=%s AND q.question_no=%s
                            LIMIT 5
                            """,
                            (subject, qno),
                        )
                        similar_rows = debug_cur.fetchall()
                        if similar_rows:
                            logger.warning(
                                f"[ExamService] 유사한 문항 발견 (과목={subject}, 문항={qno}): "
                                f"{[dict(zip(['year', 'exam_type', 'series', 'grade', 'subject', 'question_no'], r)) for r in similar_rows]}"
                            )
                        else:
                            # 과목과 문항이 다른 경우도 확인
                            if subject and isinstance(subject, str) and len(subject) >= 2:
                                debug_cur.execute(
                                    """
                                    SELECT DISTINCT year, exam_type, subject
                                    FROM exams
                                    WHERE subject LIKE %s OR subject LIKE %s
                                    LIMIT 10
                                    """,
                                    (f"%{subject[:2]}%", f"%{subject[-2:]}%"),
                                )
                            else:
                                debug_cur.execute(
                                    """
                                    SELECT DISTINCT year, exam_type, subject
                                    FROM exams
                                    LIMIT 10
                                    """
                                )
                            similar_subjects = debug_cur.fetchall()
                            logger.warning(
                                f"[ExamService] 유사한 과목 발견: {similar_subjects}"
                            )

                    return {
                        "success": False,
                        "method": "rule_based",
                        "error": "해당 조건의 문항을 찾지 못했습니다. (연도, 시험구분, 직렬, 급수, 과목, 문항을 기입해서 알려주세요. 예: 25년 지방 일반행정 9급 한국사 17번)",
                    }

                answer = ExamAnswerResponse(
                    year=int(row[0]),
                    exam_type=str(row[1] or ""),
                    job_series=str(row[2] or ""),
                    grade=str(row[3] or ""),
                    subject=str(row[4]),
                    question_no=int(row[5]),
                    answer_key=str(row[6]),
                )

                return {
                    "success": True,
                    "method": "rule_based",
                    "answer": answer.model_dump(),
                }
        except Exception as exc:
            return {
                "success": False,
                "method": "rule_based",
                "error": str(exc),
            }

    def process_jsonl_to_exam_questions(
        self, jsonl_data: List[Dict[str, Any]], category: str
    ) -> Dict[str, Any]:
        """JSONL 데이터를 휴리스틱으로 처리하여 exam_questions 테이블에 추가.

        Args:
            jsonl_data: 파싱된 JSONL 데이터 리스트
            category: 파일 카테고리 (exam, commentary, user)

        Returns:
            처리 결과
        """
        import logging
        logger = logging.getLogger(__name__)

        if category != "exam":
            return {
                "success": False,
                "error": f"category '{category}'는 exam_questions 테이블에 적합하지 않습니다."
            }

        logger.info(f"[ExamService] JSONL 데이터를 exam_questions로 변환 시작: {len(jsonl_data)}개 항목")

        # 휴리스틱 변환: JSONL 데이터를 exam_questions 형식으로 변환
        exam_questions = []
        conversion_errors = []

        for idx, item in enumerate(jsonl_data, start=1):
            try:
                # 휴리스틱: 다양한 JSONL 형식에 대응
                exam_question = self._heuristic_convert_to_exam_question(item, idx)
                if exam_question:
                    exam_questions.append(exam_question)
                else:
                    conversion_errors.append({
                        "index": idx,
                        "error": "휴리스틱 변환 실패",
                        "data": item
                    })
            except Exception as e:
                conversion_errors.append({
                    "index": idx,
                    "error": f"변환 중 오류: {str(e)}",
                    "data": item
                })
                logger.warning(f"[ExamService] 변환 실패 (index={idx}): {e}")

        logger.info(
            f"[ExamService] 변환 완료: 성공={len(exam_questions)}, 실패={len(conversion_errors)}"
        )

        if not exam_questions:
            return {
                "success": False,
                "error": "변환된 exam_questions 데이터가 없습니다.",
                "conversion_errors": conversion_errors
            }

        # Repository를 통해 DB에 삽입
        try:
            result = self._repository.insert_exam_questions(
                exam_questions,
                skip_duplicates=True
            )

            return {
                "success": True,
                "message": f"exam_questions 테이블에 {result['inserted_count']}개 삽입 완료",
                "inserted_count": result["inserted_count"],
                "skipped_count": result["skipped_count"],
                "conversion_errors": conversion_errors,
                "insertion_errors": result["errors"]
            }
        except Exception as e:
            logger.error(f"[ExamService] DB 삽입 실패: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"DB 삽입 실패: {str(e)}",
                "conversion_errors": conversion_errors
            }

    def _heuristic_convert_to_exam_question(
        self, item: Dict[str, Any], index: int
    ) -> Optional[Dict[str, Any]]:
        """휴리스틱으로 JSONL 아이템을 exam_question 형식으로 변환.

        Args:
            item: JSONL 데이터 아이템
            index: 아이템 인덱스 (에러 메시지용)

        Returns:
            exam_question 딕셔너리 또는 None (변환 실패)
        """
        import logging
        import re

        logger = logging.getLogger(__name__)

        # 디버그용: 들어온 원본 아이템 구조 확인 (최대 1~2줄만 출력)
        try:
            logger.info(
                f"[ExamService] 원본 JSONL 아이템 (index={index}) keys={list(item.keys())}, "
                f"preview={str(item)[:200]}"
            )
        except Exception:
            logger.info(f"[ExamService] 원본 JSONL 아이템 (index={index}) 로깅 실패")

        # ----------------------------------------------------------------------------------
        # 1) gongmuwon 형식(all_subjects_from_md.jsonl 등)에 대한 전용 매핑
        #    - keys: id, question, answer, subject, source_md, source_pdf
        # ----------------------------------------------------------------------------------
        if {"id", "question", "answer", "subject"}.issubset(item.keys()):
            logger.info(f"[ExamService] gongmuwon 형식 감지 (index={index}) → 전용 매핑 사용")

            source_md = item.get("source_md") or item.get("sourceMd")
            raw_id = item.get("id")

            # 연도 추론 (예: '250621+지방+9급+교육학개론-B.md' → 2025년)
            year: Optional[int] = None
            if isinstance(source_md, str):
                m = re.match(r"(\d{2})\d{4}", source_md)
                if m:
                    try:
                        year = 2000 + int(m.group(1))
                    except Exception:
                        year = None

            if year is None:
                logger.warning(f"[ExamService] year 추론 실패 (index={index}, source_md={source_md})")
                return None

            # 시험 구분: 지방 / 국가
            if isinstance(source_md, str) and "국가" in source_md:
                exam_type = "국가직"
            else:
                exam_type = "지방직"

            subject = str(item.get("subject") or "")
            if not subject:
                logger.warning(f"[ExamService] subject 누락 (index={index})")
                return None

            # 직렬 매핑 (앞에서 정의한 규칙 재사용)
            subject_norm = subject.replace(" ", "")
            if "교육학" in subject_norm:
                job_series = "교육행정직"
            elif "행정법" in subject_norm or "행정학" in subject_norm:
                job_series = "일반행정직"
            elif "사회복지" in subject_norm:
                job_series = "사회복지직"
            elif "지방세" in subject_norm or "세법" in subject_norm:
                job_series = "지방세(세무)직"
            elif "사서" in subject_norm or "자료조직" in subject_norm or "정보봉사" in subject_norm:
                job_series = "사서직"
            elif "전산" in subject_norm or "컴퓨터" in subject_norm or "정보보호" in subject_norm:
                job_series = "전산직"
            elif "토목" in subject_norm or "측량" in subject_norm or "응용역학" in subject_norm:
                job_series = "일반토목직"
            elif "건축" in subject_norm and "계획" in subject_norm:
                job_series = "건축직"
            elif "전기" in subject_norm:
                job_series = "일반전기직"
            elif "기계" in subject_norm:
                job_series = "일반기계직"
            elif "보건" in subject_norm:
                job_series = "보건직"
            elif "환경" in subject_norm:
                job_series = "일반환경직"
            elif "농업" in subject_norm or "재배학" in subject_norm or "식용작물" in subject_norm:
                job_series = "일반농업직"
            else:
                job_series = "일반행정직"

            try:
                question_no = int(raw_id)
            except Exception:
                logger.warning(f"[ExamService] question_no(id) 변환 실패 (index={index}, id={raw_id})")
                return None

            answer_key = str(item.get("answer") or "").strip()
            question_text = str(item.get("question") or "").strip()

            if not answer_key or not question_text:
                logger.warning(
                    f"[ExamService] answer/question 누락 (index={index}, answer={answer_key}, question_len={len(question_text)})"
                )
                return None

            grade = "9급"
            exam_name = "지방공무원 공개경쟁임용"
            source_pdf = item.get("source_pdf")
            extra_json = {}

            return {
                "year": int(year),
                "exam_type": str(exam_type),
                "job_series": str(job_series),
                "grade": str(grade),
                "exam_name": str(exam_name),
                "subject": str(subject),
                "question_no": int(question_no),
                "question_text": str(question_text),
                "answer_key": str(answer_key),
                "source_md": source_md,
                "source_pdf": source_pdf,
                "extra_json": extra_json,
            }

        # ----------------------------------------------------------------------------------
        # 2) 일반적인 JSONL 형식에 대한 휴리스틱 처리 (기존 로직)
        # ----------------------------------------------------------------------------------

        # 필수 필드 추출 (다양한 키 이름에 대응)
        year = self._extract_field(item, ["year", "연도", "시험연도"], int)
        exam_type = self._extract_field(item, ["exam_type", "시험구분", "examType", "시험_구분"], str)
        job_series = self._extract_field(item, ["job_series", "직렬", "jobSeries", "직렬명"], str)
        subject = self._extract_field(item, ["subject", "과목", "과목명", "subject_name"], str)
        question_no = self._extract_field(item, ["question_no", "문항번호", "questionNo", "문항", "번호"], int)
        answer_key = self._extract_field(item, ["answer_key", "정답", "answerKey", "answer", "정답키"], str)
        question_text = self._extract_field(
            item,
            ["question_text", "문제", "questionText", "question", "문제내용", "문항내용"],
            str
        )

        # ---------- 추가 휴리스틱: gongmuwon JSONL(all_subjects_from_md 등) 대응 ----------
        source_md = item.get("source_md") or item.get("sourceMd")
        raw_id = item.get("id")

        # year: source_md에서 앞 두 자리 연도를 추론 (예: '250621+지방+9급+...' → 2025)
        if year is None and isinstance(source_md, str):
            m = re.match(r"(\d{2})\d{4}", source_md)
            if m:
                try:
                    year = 2000 + int(m.group(1))
                except Exception:
                    year = None

        # exam_type: source_md에 '지방', '국가' 포함 여부로 추론
        if exam_type is None:
            if isinstance(source_md, str):
                if "지방" in source_md:
                    exam_type = "지방직"
                elif "국가" in source_md:
                    exam_type = "국가직"
        # 여전히 없으면 기본값
        if exam_type is None:
            exam_type = "지방직"

        # job_series: 과목명을 기반으로 직렬 추론 (질문에서 정의한 직렬/과목 매핑 반영)
        if job_series is None and isinstance(subject, str):
            subject_norm = subject.replace(" ", "")

            # 행정직군
            if "교육학" in subject_norm:
                job_series = "교육행정직"
            elif "행정법" in subject_norm or "행정학" in subject_norm:
                job_series = "일반행정직"
            elif "사회복지" in subject_norm:
                job_series = "사회복지직"
            elif "지방세" in subject_norm or "세법" in subject_norm:
                job_series = "지방세(세무)직"
            elif "사서" in subject_norm or "자료조직" in subject_norm or "정보봉사" in subject_norm:
                job_series = "사서직"
            elif "전산" in subject_norm or "컴퓨터" in subject_norm or "정보보호" in subject_norm:
                job_series = "전산직"

            # 기술직군 (향후 확장 대비 기본 매핑)
            elif "토목" in subject_norm or "측량" in subject_norm or "응용역학" in subject_norm:
                job_series = "일반토목직"
            elif "건축" in subject_norm and "계획" in subject_norm:
                job_series = "건축직"
            elif "전기" in subject_norm:
                job_series = "일반전기직"
            elif "기계" in subject_norm:
                job_series = "일반기계직"
            elif "보건" in subject_norm:
                job_series = "보건직"
            elif "환경" in subject_norm:
                job_series = "일반환경직"
            elif "농업" in subject_norm or "재배학" in subject_norm or "식용작물" in subject_norm:
                job_series = "일반농업직"

        # 그래도 결정되지 않은 경우 안전한 기본값 사용
        if job_series is None:
            job_series = "일반행정직"

        # question_no: id 필드가 있을 경우 그대로 사용 (1,2,3,...)
        if question_no is None and raw_id is not None:
            try:
                question_no = int(raw_id)
            except Exception:
                question_no = None

        # 필수 필드 검증
        if None in [year, exam_type, job_series, subject, question_no, answer_key, question_text]:
            missing = []
            if year is None:
                missing.append("year")
            if exam_type is None:
                missing.append("exam_type")
            if job_series is None:
                missing.append("job_series")
            if subject is None:
                missing.append("subject")
            if question_no is None:
                missing.append("question_no")
            if answer_key is None:
                missing.append("answer_key")
            if question_text is None:
                missing.append("question_text")

            logger.warning(
                f"[ExamService] 필수 필드 누락 (index={index}): {', '.join(missing)}"
            )
            return None

        # 선택 필드 추출
        grade = self._extract_field(item, ["grade", "급수", "급"], str) or "9급"
        exam_name = self._extract_field(
            item,
            ["exam_name", "시험명", "examName", "시험_이름"],
            str
        ) or "지방공무원 공개경쟁임용"
        source_md = self._extract_field(item, ["source_md", "sourceMd", "md_path"], str)
        source_pdf = self._extract_field(item, ["source_pdf", "sourcePdf", "pdf_path"], str)
        extra_json = item.get("extra_json", item.get("extraJson", item.get("extra", {})))

        # exam_type 정규화
        if "국가" in exam_type or "national" in exam_type.lower():
            exam_type = "국가직"
        elif "지방" in exam_type or "local" in exam_type.lower():
            exam_type = "지방직"
        else:
            # 기본값
            exam_type = "지방직"

        # answer_key 정규화 (1, 2, 3, 4 또는 "1", "2", "3", "4")
        if isinstance(answer_key, int):
            answer_key = str(answer_key)
        elif isinstance(answer_key, str):
            answer_key = answer_key.strip()

        return {
            "year": int(year),
            "exam_type": str(exam_type),
            "job_series": str(job_series),
            "grade": str(grade),
            "exam_name": str(exam_name),
            "subject": str(subject),
            "question_no": int(question_no),
            "question_text": str(question_text),
            "answer_key": str(answer_key),
            "source_md": source_md,
            "source_pdf": source_pdf,
            "extra_json": extra_json if isinstance(extra_json, dict) else {}
        }

    def _extract_field(
        self, item: Dict[str, Any], possible_keys: List[str], field_type: type
    ) -> Any:
        """여러 가능한 키 이름으로 필드 추출.

        Args:
            item: 데이터 딕셔너리
            possible_keys: 시도할 키 이름 리스트
            field_type: 기대하는 타입

        Returns:
            추출된 값 또는 None
        """
        for key in possible_keys:
            if key in item and item[key] is not None:
                value = item[key]
                # 타입 변환 시도
                try:
                    if field_type == int:
                        return int(value)
                    elif field_type == str:
                        return str(value)
                    else:
                        return value
                except (ValueError, TypeError):
                    continue
        return None

