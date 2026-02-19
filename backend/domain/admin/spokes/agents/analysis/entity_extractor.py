"""시험 질문 엔티티 추출 모듈.

기존 파싱 함수들을 모듈화하고 개선한 버전.
"""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any
import psycopg
from typing_extensions import TypedDict


class ExamEntities(TypedDict, total=False):
    """추출된 시험 관련 엔티티"""
    year: Optional[int]
    exam_type: Optional[str]  # "국가직" | "지방직"
    job_series: Optional[str]
    grade: Optional[str]
    subject: Optional[str]
    question_no: Optional[int]
    has_all_required: bool  # 필수 엔티티 모두 있는지


def extract_year(text: str, now_year: int = None) -> Optional[int]:
    """연도 추출.

    Args:
        text: 분석할 텍스트
        now_year: 현재 연도 (기본값: datetime.now().year)

    Returns:
        추출된 연도 또는 None
    """
    if now_year is None:
        now_year = datetime.now().year

    # 2025년 / 25년 형태
    m = re.search(r"(?:(20)?(\d{2}))\s*년", text)
    if m:
        y2 = int(m.group(2))
        return 2000 + y2

    # 상대 연도
    if "올해" in text:
        return now_year
    if "작년" in text:
        return now_year - 1
    if "재작년" in text or "그저께" in text:
        return now_year - 2

    return None


def extract_exam_type(text: str) -> Optional[str]:
    """시험 구분 추출.

    Args:
        text: 분석할 텍스트

    Returns:
        "국가직" | "지방직" | None
    """
    if "국가직" in text:
        return "국가직"
    if "지방직" in text or "지방" in text:
        return "지방직"
    return None


def extract_grade(text: str) -> Optional[str]:
    """급수 추출.

    Args:
        text: 분석할 텍스트

    Returns:
        "9급" | "7급" | None
    """
    m = re.search(r"(\d)\s*급", text)
    if m:
        return f"{m.group(1)}급"
    return None


def extract_question_no(text: str) -> Optional[int]:
    """문항 번호 추출.

    Args:
        text: 분석할 텍스트

    Returns:
        추출된 문항 번호 또는 None
    """
    m = re.search(r"(\d{1,3})\s*번", text)
    if not m:
        return None
    return int(m.group(1))


def extract_subject(text: str, conn: psycopg.Connection) -> Optional[str]:
    """과목명 추출 (DB 기반).

    Args:
        text: 분석할 텍스트
        conn: 데이터베이스 연결

    Returns:
        추출된 과목명 또는 None
    """
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT subject FROM exams ORDER BY subject")
        subjects = [str(r[0]) for r in cur.fetchall() if r and r[0]]

    # 긴 과목명부터 매칭 (예: "행정법총론"이 "행정법"보다 우선)
    subjects_sorted = sorted(subjects, key=len, reverse=True)

    for s in subjects_sorted:
        if s in text:
            return s

    return None


def extract_job_series(text: str) -> Optional[str]:
    """직렬 추출.

    Args:
        text: 분석할 텍스트

    Returns:
        추출된 직렬 또는 None
    """
    # 예: 교육행정직 / 일반행정직
    m = re.search(r"([가-힣]+행정직)", text)
    if m:
        return m.group(1)

    # 축약형
    if "교육행정" in text:
        return "교육행정직"
    if "일반행정" in text:
        return "일반행정직"

    return None


def extract_all_entities(text: str, conn: psycopg.Connection, now_year: int = None) -> ExamEntities:
    """모든 엔티티를 한 번에 추출.

    Args:
        text: 분석할 텍스트
        conn: 데이터베이스 연결
        now_year: 현재 연도 (기본값: datetime.now().year)

    Returns:
        ExamEntities 딕셔너리
    """
    if now_year is None:
        now_year = datetime.now().year

    entities: ExamEntities = {
        "year": extract_year(text, now_year),
        "exam_type": extract_exam_type(text),
        "grade": extract_grade(text),
        "subject": extract_subject(text, conn),
        "question_no": extract_question_no(text),
        "job_series": extract_job_series(text),
    }

    # 필수 엔티티 확인 (과목, 문항번호는 필수)
    required = ["subject", "question_no"]
    entities["has_all_required"] = all(entities.get(k) is not None for k in required)

    return entities


def get_missing_entities(entities: ExamEntities) -> List[str]:
    """누락된 필수 엔티티 목록 반환.

    Args:
        entities: 추출된 엔티티

    Returns:
        누락된 필수 엔티티 목록
    """
    required = ["subject", "question_no"]
    return [k for k in required if entities.get(k) is None]


def get_found_entities(entities: ExamEntities) -> List[str]:
    """추출된 엔티티 목록 반환.

    Args:
        entities: 추출된 엔티티

    Returns:
        추출된 엔티티 키 목록
    """
    return [k for k, v in entities.items() if v is not None and k != "has_all_required"]

