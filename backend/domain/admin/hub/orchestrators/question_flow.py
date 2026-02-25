"""Question 요청 처리 Orchestrator (LangGraph 기반).

새 테이블 구조:
- Questions: exam_id FK, question_no, question_text, answer_key 등
- Question_Images: question_id FK, file_path, coordinates_json

LangGraph StateGraph로 구현:
- 노드 기반 워크플로우로 전환
- QuestionService를 통한 데이터 처리
- YOLO crop_results.json 업로드 처리
"""

import re
import logging
from typing import Dict, Any, Optional, TypedDict, List

from langgraph.graph import StateGraph, END, START

from backend.domain.admin.hub.repositories.exam_repository import ExamRepository

logger = logging.getLogger(__name__)


# ============================================================================
# State 정의
# ============================================================================

class QuestionProcessingState(TypedDict, total=False):
    """Question 처리 상태."""
    request_text: str
    request_data: Dict[str, Any]
    action: str  # create, read, search, update, delete
    question_id: Optional[int]
    exam_id: Optional[int]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]


# ============================================================================
# 폴더명 파서 유틸리티
# ============================================================================

def _infer_job_series(subject: str) -> str:
    """과목명으로 직렬을 추론합니다 (all_subjects_from_md.jsonl 파싱과 동일 규칙).

    Args:
        subject: 과목명 (예: '교육학개론', '행정법총론')

    Returns:
        직렬명 (예: '교육행정직', '일반행정직')
    """
    s = subject.replace(" ", "")
    if "교육학" in s:
        return "교육행정직"
    elif "행정법" in s or "행정학" in s:
        return "일반행정직"
    elif "사회복지" in s:
        return "사회복지직"
    elif "지방세" in s or "세법" in s:
        return "지방세(세무)직"
    elif "사서" in s or "자료조직" in s or "정보봉사" in s:
        return "사서직"
    elif "전산" in s or "컴퓨터" in s or "정보보호" in s:
        return "전산직"
    elif "토목" in s or "측량" in s or "응용역학" in s:
        return "일반토목직"
    elif "건축" in s and "계획" in s:
        return "건축직"
    elif "전기" in s:
        return "일반전기직"
    elif "기계" in s:
        return "일반기계직"
    elif "보건" in s:
        return "보건직"
    elif "환경" in s:
        return "일반환경직"
    elif "농업" in s or "재배학" in s or "식용작물" in s:
        return "일반농업직"
    elif "한국사" in s or "국사" in s:
        return "일반행정직"
    else:
        return "일반행정직"


def parse_folder_name(folder_name: str) -> Dict[str, Any]:
    """YOLO crop 폴더명에서 시험 메타데이터를 추출합니다.

    폴더명 예시: '250621+지방+9급+교육학개론-B'
    - 250621 → year: 2025
    - 지방 → exam_type: '지방직'
    - 9급 → grade: '9급'
    - 교육학개론-B → subject: '교육학개론'

    Args:
        folder_name: YOLO crop 폴더명

    Returns:
        파싱된 메타데이터 딕셔너리
    """
    result = {
        "year": 2025,
        "exam_type": "지방직",
        "grade": "9급",
        "subject": "",
        "series": None,
    }

    # '+'로 최대 3번 분리 (4번째부터는 과목명에 '+'가 포함될 수 있음)
    parts = folder_name.split('+', 3)

    if len(parts) < 4:
        logger.warning(f"[QuestionFlow] 폴더명 파싱 실패 (파트 부족): {folder_name}")
        result["subject"] = folder_name
        return result

    # 1) 날짜 → 연도
    date_str = parts[0].strip()
    if len(date_str) >= 2 and date_str[:2].isdigit():
        year_prefix = int(date_str[:2])
        result["year"] = 2000 + year_prefix

    # 2) 시험 유형
    exam_type_raw = parts[1].strip()
    exam_type_map = {
        "지방": "지방직",
        "국가": "국가직",
        "서울": "서울시",
        "경찰": "경찰직",
        "소방": "소방직",
        "군무원": "군무원",
        "국회": "국회직",
        "법원": "법원직",
    }
    result["exam_type"] = exam_type_map.get(exam_type_raw, exam_type_raw)

    # 3) 등급
    result["grade"] = parts[2].strip()

    # 4) 과목명 (접미사 제거: -B, -A, -B (2) 등)
    subject_raw = parts[3].strip()
    # 접미사 패턴: -A, -B, -C, -B (2), -A (3) 등
    subject = re.sub(r'\s*-[A-Z]\s*(\(\d+\))?$', '', subject_raw)
    # 괄호 부분 제거: 행정학개론(지방행정+포함) → 행정학개론
    subject = re.sub(r'\(.*?\)', '', subject)
    result["subject"] = subject.strip()

    # series: 과목명 기반 직렬 매핑 (all_subjects_from_md.jsonl 파싱과 동일)
    result["series"] = _infer_job_series(result["subject"])

    logger.info(
        f"[QuestionFlow] 폴더명 파싱: {folder_name} → "
        f"year={result['year']}, exam_type={result['exam_type']}, "
        f"grade={result['grade']}, subject={result['subject']}, "
        f"series={result['series']}"
    )

    return result


def extract_folder_name(path: str) -> str:
    """crop_path에서 폴더명을 추출합니다.

    Args:
        path: crop_path (예: 'data\\crops\\250621+지방+9급+교육학개론-B\\page_001_q01.webp')

    Returns:
        폴더명 (예: '250621+지방+9급+교육학개론-B')
    """
    # 윈도우/유닉스 경로 구분자 모두 지원
    normalized = path.replace('\\', '/')
    parts = normalized.split('/')

    # 마지막 부분은 파일명, 그 직전이 폴더명
    if len(parts) >= 2:
        return parts[-2]
    return ""


def extract_question_nos_from_filename(file_name: str) -> List[int]:
    """파일명 규칙에서 복수 문항 번호를 추출합니다.

    지원 예시:
    - gook_q01.webp -> [1]
    - gook_q07_q08.webp -> [7, 8]

    주의:
    - 기존 page_001_q01.webp 같은 페이지 기반 파일명은 중복 번호가 발생하므로
      여기서는 자동 번호 추출 대상으로 사용하지 않습니다.
    """
    lower_name = file_name.lower()
    if lower_name.startswith("page_"):
        return []

    nums = [int(n) for n in re.findall(r"_q(\d{1,3})", lower_name)]
    nums = [n for n in nums if n > 0]
    if not nums:
        return []
    return sorted(set(nums))


# ============================================================================
# QuestionFlow
# ============================================================================

class QuestionFlow:
    """Question 요청 처리 Orchestrator (LangGraph 기반)."""

    def __init__(self):
        """초기화."""
        self._repository = ExamRepository()
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph 빌드."""
        graph = StateGraph(QuestionProcessingState)

        # 노드 추가
        graph.add_node("validate", self._validate_node)
        graph.add_node("determine_action", self._determine_action_node)
        graph.add_node("process_create", self._process_create_node)
        graph.add_node("process_read", self._process_read_node)
        graph.add_node("process_search", self._process_search_node)
        graph.add_node("finalize", self._finalize_node)

        # 엣지 추가
        graph.add_edge(START, "validate")
        graph.add_edge("validate", "determine_action")
        graph.add_conditional_edges(
            "determine_action",
            self._route_action,
            {
                "create": "process_create",
                "read": "process_read",
                "search": "process_search",
            }
        )
        graph.add_edge("process_create", "finalize")
        graph.add_edge("process_read", "finalize")
        graph.add_edge("process_search", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    async def _validate_node(self, state: QuestionProcessingState) -> QuestionProcessingState:
        """데이터 검증 노드."""
        request_data = state.get("request_data", {})

        if not request_data:
            return {
                **state,
                "error": "요청 데이터가 비어있습니다.",
            }

        return state

    async def _determine_action_node(self, state: QuestionProcessingState) -> QuestionProcessingState:
        """액션 판단 노드."""
        request_data = state.get("request_data", {})
        action = request_data.get("action", "search")

        logger.info(f"[QuestionFlow] 액션 판단: {action}")

        return {
            **state,
            "action": action,
            "question_id": request_data.get("question_id"),
            "exam_id": request_data.get("exam_id"),
        }

    def _route_action(self, state: QuestionProcessingState) -> str:
        """액션에 따른 라우팅."""
        action = state.get("action", "search")
        if action in ("create", "read", "search"):
            return action
        return "search"

    async def _process_create_node(self, state: QuestionProcessingState) -> QuestionProcessingState:
        """문제 생성 노드 (Repository 사용)."""
        request_data = state.get("request_data", {})

        try:
            # ExamRepository를 통해 시험 조회/생성
            exam_id = self._repository.get_or_create_exam(
                year=request_data.get("year", 2024),
                exam_type=request_data.get("exam_type", "지방직"),
                subject=request_data.get("subject", ""),
                series=request_data.get("series"),
                grade=request_data.get("grade"),
            )

            # ExamRepository를 통해 문제 삽입
            question_id = self._repository.insert_question(
                exam_id=exam_id,
                question_no=request_data.get("question_no", 1),
                question_text=request_data.get("question_text", ""),
                answer_key=request_data.get("answer_key", ""),
                sub_category=request_data.get("sub_category"),
                source_pdf=request_data.get("source_pdf"),
                extra_json=request_data.get("extra_json", {}),
            )

            result = {
                "success": True,
                "question": {
                    "id": question_id,
                    "exam_id": exam_id,
                    "question_no": request_data.get("question_no"),
                    "question_text": request_data.get("question_text"),
                    "answer_key": request_data.get("answer_key"),
                },
            }

            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[QuestionFlow] 문제 생성 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _process_read_node(self, state: QuestionProcessingState) -> QuestionProcessingState:
        """문제 조회 노드 (Repository 사용)."""
        request_data = state.get("request_data", {})

        try:
            # ExamRepository의 find_question 사용
            question = self._repository.find_question(
                year=request_data.get("year", 2024),
                subject=request_data.get("subject", ""),
                question_no=request_data.get("question_no", 1),
                exam_type=request_data.get("exam_type"),
            )

            if not question:
                return {**state, "result": {"success": False, "error": "문제를 찾을 수 없습니다."}}

            result = {
                "success": True,
                "question": question,
            }

            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[QuestionFlow] 문제 조회 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _process_search_node(self, state: QuestionProcessingState) -> QuestionProcessingState:
        """문제 검색 노드 (Repository 사용)."""
        request_data = state.get("request_data", {})

        try:
            # 과목 목록 조회
            subjects = self._repository.get_subjects()

            # 키워드가 있으면 해당 과목 검색
            keyword = request_data.get("keyword", "")
            if keyword:
                subjects = [s for s in subjects if keyword.lower() in s.lower()]

            result = {
                "success": True,
                "subjects": subjects,
                "message": f"검색 가능한 과목: {len(subjects)}개",
            }

            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[QuestionFlow] 문제 검색 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _finalize_node(self, state: QuestionProcessingState) -> QuestionProcessingState:
        """최종 정리 노드."""
        return state

    async def process_question_request(
        self, request_text: str, request_data: dict
    ) -> dict:
        """Question 요청 처리.

        Args:
            request_text: 요청 텍스트
            request_data: 요청 데이터 (action, question_id, exam_id 등)

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[QuestionFlow] 요청 처리 시작: {request_text[:50] if request_text else 'N/A'}")

        initial_state: QuestionProcessingState = {
            "request_text": request_text,
            "request_data": request_data,
            "action": None,
            "question_id": None,
            "exam_id": None,
            "result": None,
            "error": None,
            "metadata": None,
        }

        try:
            final_state = await self._graph.ainvoke(initial_state)
            result = final_state.get("result")
            return result if result else {"success": False, "error": "처리 결과가 없습니다."}
        except Exception as e:
            logger.error(f"[QuestionFlow] 처리 오류: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ========================================================================
    # YOLO Crop Results 업로드 처리
    # ========================================================================

    async def process_crop_results(
        self,
        crop_results: List[Dict[str, Any]],
        filename: str = "crop_results.json",
    ) -> Dict[str, Any]:
        """YOLO crop_results.json 데이터를 처리하여 DB에 저장합니다.

        처리 흐름:
        1. 각 crop 항목의 폴더명에서 시험 메타데이터 파싱
        2. exams 테이블에 시험 레코드 생성/조회
        3. questions 테이블에 문제 레코드 생성/조회
        4. question_images 테이블에 이미지 레코드 저장

        Args:
            crop_results: crop_results.json 파싱 데이터 리스트
            filename: 원본 파일명

        Returns:
            처리 결과 딕셔너리
        """
        logger.info("=" * 80)
        logger.info(f"[QuestionFlow] crop_results 수신: filename={filename}, items={len(crop_results)}")

        conn = self._repository._get_connection()

        inserted_exams = 0
        inserted_questions = 0
        inserted_images = 0
        skipped_images = 0
        errors: List[Dict[str, Any]] = []

        # 캐시: 폴더명 → exam_id, (exam_id, question_no) → question_id
        exam_cache: Dict[str, int] = {}
        question_cache: Dict[tuple, int] = {}

        # ── question_no 글로벌 재계산 ──
        # crop_results의 question_no는 페이지 내 순번(page마다 1부터)이므로,
        # 같은 폴더(=같은 시험) 내에서 등장 순서대로 글로벌 번호를 매깁니다.
        # 예: page_001 q1-q10, page_002 q1-q10 → 글로벌 1-20
        folder_global_counter: Dict[str, int] = {}  # 폴더명 → 현재까지 부여한 글로벌 번호
        folder_seen_keys: Dict[str, Dict[str, int]] = {}  # 폴더명 → {page_qno_key → 글로벌 번호}

        for idx, item in enumerate(crop_results, start=1):
            try:
                crop_path = item.get("crop_path", "")
                original_qno = int(item.get("question_no", 0))
                bbox = item.get("bbox", [])
                confidence = item.get("confidence", 0.0)
                source_image = item.get("source_image", "")
                raw_question_nos = item.get("question_nos")

                if not crop_path or original_qno <= 0:
                    errors.append({
                        "index": idx,
                        "error": f"crop_path 또는 question_no가 유효하지 않습니다: crop_path={crop_path}, question_no={original_qno}"
                    })
                    continue

                # 1) 폴더명에서 시험 메타데이터 파싱
                folder_name = extract_folder_name(crop_path)
                if not folder_name:
                    errors.append({
                        "index": idx,
                        "error": f"폴더명을 추출할 수 없습니다: {crop_path}"
                    })
                    continue

                # ── 글로벌 question_no 계산 ──
                # crop_path에서 파일명 추출 (예: page_002_q03.webp)
                file_name = crop_path.replace('\\', '/').rsplit('/', 1)[-1]
                # 폴더+파일명을 유니크 키로 사용 (같은 이미지 중복 방지)
                unique_key = f"{folder_name}/{file_name}"

                if folder_name not in folder_seen_keys:
                    folder_seen_keys[folder_name] = {}
                    folder_global_counter[folder_name] = 0

                if unique_key not in folder_seen_keys[folder_name]:
                    folder_global_counter[folder_name] += 1
                    folder_seen_keys[folder_name][unique_key] = folder_global_counter[folder_name]

                question_no = folder_seen_keys[folder_name][unique_key]
                filename_question_nos = extract_question_nos_from_filename(file_name)

                # ── 복수 문항 번호 지원 ──
                # 신규 데이터는 question_nos: [7, 8] 형태를 지원하고,
                # 없으면 기존처럼 재계산한 글로벌 번호 1개를 사용합니다.
                question_nos: List[int] = []
                if isinstance(raw_question_nos, list):
                    for n in raw_question_nos:
                        try:
                            qn = int(n)
                        except (TypeError, ValueError):
                            continue
                        if qn > 0:
                            question_nos.append(qn)
                elif isinstance(raw_question_nos, str):
                    for token in raw_question_nos.split(","):
                        token = token.strip()
                        if not token:
                            continue
                        try:
                            qn = int(token)
                        except ValueError:
                            continue
                        if qn > 0:
                            question_nos.append(qn)

                if question_nos:
                    question_nos = sorted(set(question_nos))
                    question_no = question_nos[0]
                elif filename_question_nos:
                    question_nos = filename_question_nos
                    question_no = question_nos[0]
                else:
                    question_nos = [question_no]

                # 2) Exam 생성/조회 (캐시 사용)
                if folder_name not in exam_cache:
                    meta = parse_folder_name(folder_name)
                    exam_id = self._repository.get_or_create_exam(
                        year=meta["year"],
                        exam_type=meta["exam_type"],
                        subject=meta["subject"],
                        series=meta.get("series"),
                        grade=meta.get("grade"),
                    )
                    exam_cache[folder_name] = exam_id
                    inserted_exams += 1
                    logger.info(
                        f"[QuestionFlow] Exam 생성/조회: folder={folder_name}, exam_id={exam_id}"
                    )
                else:
                    exam_id = exam_cache[folder_name]

                # 3) Question 생성/조회 (캐시 사용)
                q_key = (exam_id, question_no)
                if q_key not in question_cache:
                    question_id = self._get_or_create_question(
                        conn=conn,
                        exam_id=exam_id,
                        question_no=question_no,
                        source_image=source_image,
                    )
                    question_cache[q_key] = question_id
                    inserted_questions += 1
                else:
                    question_id = question_cache[q_key]

                # 4) QuestionImage 저장 (중복 확인)
                # 경로 정규화 (윈도우 → 유닉스)
                normalized_crop_path = crop_path.replace('\\', '/')
                image_type = normalized_crop_path.rsplit('.', 1)[-1] if '.' in normalized_crop_path else "webp"

                coordinates_json = {
                    "bbox": bbox,
                    "confidence": confidence,
                    "question_nos": question_nos,
                }

                is_new = self._insert_question_image(
                    conn=conn,
                    question_id=question_id,
                    file_path=normalized_crop_path,
                    coordinates_json=coordinates_json,
                    image_type=image_type,
                )

                if is_new:
                    inserted_images += 1
                else:
                    skipped_images += 1

                # 진행 로그 (100개마다)
                if idx % 100 == 0:
                    logger.info(
                        f"[QuestionFlow] 진행: {idx}/{len(crop_results)} "
                        f"(exams={inserted_exams}, questions={inserted_questions}, images={inserted_images})"
                    )

            except Exception as e:
                errors.append({
                    "index": idx,
                    "error": str(e),
                })
                logger.error(f"[QuestionFlow] crop 항목 처리 오류 (index={idx}): {e}")

        # 최종 커밋
        try:
            conn.commit()
        except Exception as e:
            logger.error(f"[QuestionFlow] 최종 커밋 실패: {e}")

        logger.info(
            f"[QuestionFlow] crop_results 처리 완료: "
            f"total={len(crop_results)}, exams={inserted_exams}, "
            f"questions={inserted_questions}, images={inserted_images}, "
            f"skipped={skipped_images}, errors={len(errors)}"
        )
        logger.info("=" * 80)

        return {
            "success": len(errors) == 0 or inserted_images > 0,
            "message": (
                f"총 {len(crop_results)}개 항목 처리 완료. "
                f"시험 {inserted_exams}개, 문제 {inserted_questions}개, "
                f"이미지 {inserted_images}개 저장 ({skipped_images}개 중복 건너뜀)."
            ),
            "filename": filename,
            "total_items": len(crop_results),
            "inserted_exams": inserted_exams,
            "inserted_questions": inserted_questions,
            "inserted_images": inserted_images,
            "skipped_images": skipped_images,
            "errors": errors[:50],  # 최대 50개까지 반환
        }

    def _get_or_create_question(
        self,
        conn,
        exam_id: int,
        question_no: int,
        source_image: str = "",
    ) -> int:
        """문제를 조회하거나 생성합니다.

        crop_results에는 question_text, answer_key가 없으므로
        이미지 기반 문제로 placeholder를 사용합니다.

        Args:
            conn: DB 연결
            exam_id: 시험 ID
            question_no: 문제 번호
            source_image: 원본 이미지 경로

        Returns:
            question_id
        """
        from psycopg.types.json import Json

        with conn.cursor() as cur:
            # 기존 문제 조회
            cur.execute(
                "SELECT id FROM questions WHERE exam_id = %s AND question_no = %s LIMIT 1",
                (exam_id, question_no)
            )
            row = cur.fetchone()
            if row:
                return row[0]

            # 새 문제 생성 (이미지 기반 placeholder)
            # 명시적 타입 캐스팅으로 psycopg3 NULL 파라미터 타입 추론 문제 방지
            cur.execute(
                """
                INSERT INTO questions (
                    exam_id, question_no, question_text, answer_key,
                    source_pdf, extra_json
                ) VALUES (%s, %s, %s, %s, %s::text, %s::jsonb)
                RETURNING id
                """,
                (
                    exam_id,
                    question_no,
                    f"[이미지 문제 #{question_no}]",
                    "미정",
                    source_image.replace('\\', '/') if source_image else None,
                    Json({"source": "yolo_crop", "has_image": True}),
                )
            )
            question_id = cur.fetchone()[0]
            logger.info(
                f"[QuestionFlow] 문제 생성: exam_id={exam_id}, "
                f"question_no={question_no}, question_id={question_id}"
            )
            return question_id

    def _insert_question_image(
        self,
        conn,
        question_id: int,
        file_path: str,
        coordinates_json: Dict[str, Any],
        image_type: str,
    ) -> bool:
        """문제 이미지를 삽입합니다 (중복 시 건너뜀).

        Args:
            conn: DB 연결
            question_id: 문제 ID
            file_path: 이미지 파일 경로
            coordinates_json: 좌표 정보
            image_type: 이미지 유형

        Returns:
            True: 새로 삽입됨, False: 중복으로 건너뜀
        """
        from psycopg.types.json import Json

        with conn.cursor() as cur:
            # 중복 확인 (같은 question_id + file_path)
            cur.execute(
                "SELECT id FROM question_images WHERE question_id = %s AND file_path = %s LIMIT 1",
                (question_id, file_path)
            )
            if cur.fetchone():
                return False

            cur.execute(
                """
                INSERT INTO question_images (question_id, file_path, coordinates_json, image_type)
                VALUES (%s, %s, %s::jsonb, %s)
                """,
                (
                    question_id,
                    file_path,
                    Json(coordinates_json),
                    image_type,
                )
            )
            return True
