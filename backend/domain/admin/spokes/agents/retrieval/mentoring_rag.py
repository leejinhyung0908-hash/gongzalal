"""멘토링 지식 RAG (Retrieval-Augmented Generation) 모듈.

mentoring_knowledge 테이블(합격 수기 원문)의 KURE-v1 임베딩(1024차원)을 활용하여
사용자 질문과 가장 유사한 합격 수기를 검색하고,
EXAONE LLM을 통해 답변을 생성합니다.

테이블 컬럼 구조 (success stories 1:1 매핑):
  id, source, exam_info(JSONB), study_style(JSONB), daily_plan(TEXT),
  subject_methods(JSONB), interview_prep(TEXT), difficulties(TEXT),
  key_points(TEXT), search_text(TEXT), source_url(TEXT), crawled_at,
  created_at, knowledge_vector(vector(1024))
"""

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Dict, Any, List, Optional

import psycopg
import torch

from backend.core.utils.embedding import generate_embedding
from backend.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)
# Transformers: pipeline max_time. GGUF 경로는 max_time 미적용 → 바깥 타임아웃이 사실상 상한.
# 바깥( EXAONE_CALL ) ≥ 안쪽( GENERATION_MAX ) 로 맞추는 것을 권장.
_MENTORING_GENERATION_MAX_TIME_SEC = float(os.getenv("MENTORING_GENERATION_MAX_TIME_SEC", "90"))
_MENTORING_EXAONE_CALL_TIMEOUT_SEC = float(os.getenv("MENTORING_EXAONE_CALL_TIMEOUT_SEC", "120"))
_MENTORING_MAX_NEW_TOKENS_CPU = int(os.getenv("MENTORING_MAX_NEW_TOKENS_CPU", "20"))
_MENTORING_MAX_NEW_TOKENS_GPU = int(os.getenv("MENTORING_MAX_NEW_TOKENS_GPU", "96"))


_STORY_NOISE_MARKERS: List[str] = [
    "목록 다음글",
    "이전글",
    "회사소개",
    "이용약관",
    "개인정보처리방침",
    "copyright",
    "all rights reserved",
    "사업자등록번호",
    "통신판매업신고번호",
    "호스팅제공자",
    "원격평생교육시설",
    "대표이사",
    "개인정보보호책임자",
    "가입사실 확인",
    "서울특별시 구로구",
]


def _sanitize_story_text(text: Any) -> str:
    """합격 수기 원문에서 사이트 보일러플레이트를 제거합니다."""
    if not isinstance(text, str):
        return ""

    cleaned = text.strip()
    if not cleaned:
        return ""

    # 푸터/이전글/다음글 등 잡문구가 섞이면 해당 지점부터 절단
    lowered = cleaned.lower()
    cut_positions = [
        lowered.find(marker.lower())
        for marker in _STORY_NOISE_MARKERS
        if lowered.find(marker.lower()) >= 0
    ]
    if cut_positions:
        cleaned = cleaned[:min(cut_positions)].strip()

    # 과도한 공백 정리
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# ============================================================================
# 헬퍼: DB row → dict
# ============================================================================

def _row_to_dict(row: tuple) -> Dict[str, Any]:
    """SELECT 결과 row를 dict로 변환합니다.

    SELECT 순서:
      0:id, 1:source, 2:exam_info, 3:study_style, 4:daily_plan,
      5:subject_methods, 6:difficulties, 7:key_points,
      8:search_text, 9:source_url, 10:similarity
    """
    def _parse_json(val: Any) -> Any:
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        return val or {}

    exam_info = _parse_json(row[2])
    study_style = _parse_json(row[3])
    subject_methods = _parse_json(row[5])

    if isinstance(study_style, dict):
        study_style = {
            k: _sanitize_story_text(v) if isinstance(v, str) else v
            for k, v in study_style.items()
        }
    if isinstance(subject_methods, dict):
        subject_methods = {
            k: _sanitize_story_text(v) if isinstance(v, str) else v
            for k, v in subject_methods.items()
        }

    return {
        "id": row[0],
        "source": row[1],
        "exam_info": exam_info,
        "study_style": study_style,
        "daily_plan": _sanitize_story_text(row[4]),
        "subject_methods": subject_methods,
        "difficulties": _sanitize_story_text(row[6]),
        "key_points": _sanitize_story_text(row[7]),
        "search_text": _sanitize_story_text(row[8]),
        "source_url": row[9],
        "similarity": round(float(row[10]), 4) if row[10] is not None else 0.0,
    }


def _format_exam_title(exam_info: Dict[str, Any]) -> str:
    """exam_info에서 사람이 읽을 수 있는 제목을 생성합니다."""
    parts: List[str] = []
    if exam_info.get("year"):
        parts.append(f"{exam_info['year']}년")
    if exam_info.get("exam_type"):
        parts.append(exam_info["exam_type"])
    if exam_info.get("grade"):
        parts.append(f"{exam_info['grade']}급")
    if exam_info.get("job_series"):
        parts.append(exam_info["job_series"])
    return " ".join(parts) if parts else "합격 수기"


# ============================================================================
# 사용자 프로필 ↔ 합격 수기 유사 환경 매핑
# ============================================================================

# employment_status(영문 ENUM) → 합격 수기의 수험생활 키워드 매핑
_EMP_TO_STUDY_STYLE_KEYWORDS = {
    "EMPLOYED": ["직장", "재직", "퇴근", "병행", "직장인"],
    "UNEMPLOYED": ["전업", "전념", "풀타임"],
    "STUDENT": ["학생", "대학", "졸업"],
    "SELF_EMPLOYED": ["자영업", "사업"],
}


def _compute_profile_bonus(
    row_dict: Dict[str, Any],
    user_info: Optional[Dict[str, Any]],
) -> float:
    """사용자 프로필과 합격 수기 메타데이터의 환경 유사도 보너스를 계산합니다.

    반환: 0.0 ~ 0.20 사이의 보너스 점수
    """
    if not user_info:
        return 0.0

    bonus = 0.0
    exam_info = row_dict.get("exam_info", {})
    study_style = row_dict.get("study_style", {})

    # 1) 목표 직렬 일치 (+0.05)
    target_pos = user_info.get("target_position")
    if target_pos and exam_info.get("job_series"):
        job_series = exam_info["job_series"]
        if target_pos in job_series or job_series in target_pos:
            bonus += 0.05

    # 2) 직장 상태 유사 (+0.04)
    emp_status = user_info.get("employment_status")
    if emp_status:
        keywords = _EMP_TO_STUDY_STYLE_KEYWORDS.get(emp_status, [])
        study_life = study_style.get("수험생활", "")
        if any(kw in study_life for kw in keywords):
            bonus += 0.04

    # 3) 초시/재시 매칭 (+0.03)
    is_first = user_info.get("is_first_timer")
    if is_first is not None:
        study_period = exam_info.get("총 수험기간", "")
        study_life_txt = study_style.get("수험생활", "")
        combined = study_period + study_life_txt
        if is_first:
            # 초시생: 단기, 1년 미만 수험기간과 매칭
            if any(kw in combined for kw in ["단기", "6개월", "1년", "초시"]):
                bonus += 0.03
        else:
            # 재시생: 장기, 재도전, N수와 매칭
            if any(kw in combined for kw in ["재도전", "재시", "2년", "3년", "장기", "N수"]):
                bonus += 0.03

    # 4) 총 수험기간 유사도 매칭 (+0.05)
    # 사용자 목표 기간과 합격 수기의 exam_info["총 수험기간"] 비교
    user_duration = user_info.get("study_duration", "")
    story_duration = exam_info.get("총 수험기간", "")
    if user_duration and story_duration:
        bonus += _compute_duration_bonus(user_duration, story_duration)

    # 5) 취약 과목 관련 학습법 존재 (+0.03)
    user_weak = user_info.get("weak_subjects", []) or []
    subject_methods = row_dict.get("subject_methods") or {}
    if isinstance(subject_methods, dict) and user_weak:
        matched_subjects = [
            s for s in user_weak
            if any(s in key for key in subject_methods.keys())
        ]
        if matched_subjects:
            bonus += min(0.03, len(matched_subjects) * 0.015)

    # 6) 강점 과목 관련 학습법 존재 (+0.02)
    #    강점 과목의 고급 학습법/노하우가 포함된 수기를 우선 참조
    user_strong = user_info.get("strong_subjects", []) or []
    if isinstance(subject_methods, dict) and user_strong:
        matched_strong = [
            s for s in user_strong
            if any(s in key for key in subject_methods.keys())
        ]
        if matched_strong:
            bonus += min(0.02, len(matched_strong) * 0.01)

    # 7) 응시 과목 일치 (+0.02)
    #    합격 수기의 응시 과목과 사용자의 취약/강점 과목 전체가 겹칠수록 보너스
    story_subjects = exam_info.get("subjects", []) or []
    if story_subjects:
        all_user_subjects = set(user_weak + user_strong)
        if all_user_subjects:
            overlap = sum(
                1 for subj in all_user_subjects
                if any(subj in s or s in subj for s in story_subjects)
            )
            if overlap >= 2:
                bonus += 0.02
            elif overlap == 1:
                bonus += 0.01

    return bonus


# 수험기간 → 개월 수 매핑 (중앙값 기준)
_DURATION_TO_MONTHS: Dict[str, float] = {
    "3개월 이내": 3,
    "6개월": 6,
    "6개월 이내": 6,
    "6개월~ 1년": 9,
    "6개월~1년": 9,
    "9개월": 9,
    "1년": 12,
    "1년 미만": 9,
    "1년~1년 6개월": 15,
    "1년 6개월": 18,
    "1년~2년": 18,
    "1년 6개월~2년": 21,
    "2년": 24,
    "2년~3년": 30,
    "2년 이상": 30,
    "3년": 36,
    "3년 이상": 42,
}


def _parse_duration_months(text: str) -> Optional[float]:
    """수험기간 텍스트를 대략적인 개월 수로 변환합니다."""
    text = text.strip()
    # 직접 매핑 시도
    if text in _DURATION_TO_MONTHS:
        return _DURATION_TO_MONTHS[text]
    # 부분 매칭 시도
    for pattern, months in _DURATION_TO_MONTHS.items():
        if pattern in text or text in pattern:
            return months
    # 숫자 추출 시도 (예: "약 2년")
    import re
    m = re.search(r'(\d+)\s*년', text)
    if m:
        return float(m.group(1)) * 12
    m = re.search(r'(\d+)\s*개월', text)
    if m:
        return float(m.group(1))
    return None


def _compute_duration_bonus(user_duration: str, story_duration: str) -> float:
    """사용자 목표 기간과 합격 수기 수험기간의 유사도 보너스를 계산합니다.

    반환: 0.0 ~ 0.05
    - 동일 범위: +0.05
    - ±6개월 이내: +0.03
    - ±12개월 이내: +0.01
    """
    user_months = _parse_duration_months(user_duration)
    story_months = _parse_duration_months(story_duration)

    if user_months is None or story_months is None:
        return 0.0

    diff = abs(user_months - story_months)
    if diff <= 3:
        return 0.05  # 거의 동일한 기간
    elif diff <= 6:
        return 0.03  # 유사한 기간
    elif diff <= 12:
        return 0.01  # 비슷한 범위
    return 0.0


# ============================================================================
# 벡터 검색
# ============================================================================

def search_mentoring_knowledge(
    conn: psycopg.Connection,
    query: str,
    *,
    top_k: int = 5,
    similarity_threshold: float = 0.3,
) -> List[Dict[str, Any]]:
    """KURE-v1 임베딩 + pgvector로 유사한 합격 수기를 검색합니다.

    Args:
        conn: PostgreSQL 연결
        query: 사용자 질문 / RAG 쿼리
        top_k: 검색할 최대 건수
        similarity_threshold: 최소 코사인 유사도 (0~1)

    Returns:
        유사한 합격 수기 리스트 (유사도 내림차순)
    """
    try:
        # 1) 쿼리를 KURE-v1로 임베딩
        query_vector = generate_embedding(query)
        embedding_str = "[" + ",".join(map(str, query_vector)) + "]"

        # 2) pgvector 코사인 유사도 검색
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, source, exam_info, study_style, daily_plan,
                       subject_methods, difficulties, key_points,
                       search_text, source_url,
                       1 - (knowledge_vector <=> %s::vector) AS similarity
                FROM mentoring_knowledge
                WHERE knowledge_vector IS NOT NULL
                ORDER BY knowledge_vector <=> %s::vector
                LIMIT %s
                """,
                (embedding_str, embedding_str, top_k),
            )
            rows = cur.fetchall()

        results = []
        for r in rows:
            d = _row_to_dict(r)
            if d["similarity"] < similarity_threshold:
                continue
            results.append(d)

        logger.info(
            f"[MentoringRAG] 검색 완료: query='{query[:50]}...', "
            f"결과={len(results)}건 (threshold={similarity_threshold})"
        )
        return results

    except Exception as e:
        logger.error(f"[MentoringRAG] 벡터 검색 실패: {e}", exc_info=True)
        return []


def search_with_profile_matching(
    conn: psycopg.Connection,
    queries: List[str],
    user_info: Optional[Dict[str, Any]] = None,
    *,
    top_k_per_query: int = 4,
    final_top_k: int = 5,
    similarity_threshold: float = 0.20,
) -> List[Dict[str, Any]]:
    """여러 RAG 쿼리의 벡터 검색 결과를 사용자 프로필 유사도 보너스와 결합하여
    가장 환경이 비슷한 합격 수기를 우선 반환합니다.

    Args:
        conn: DB 연결
        queries: RAG 검색 쿼리 리스트
        user_info: 사용자 프로필 정보
        top_k_per_query: 쿼리당 검색 건수
        final_top_k: 최종 반환 건수
        similarity_threshold: 최소 유사도

    Returns:
        프로필 보너스가 반영된 유사도 순 합격 수기 리스트
    """
    all_results: Dict[int, Dict[str, Any]] = {}  # id → result dict

    for query in queries[:3]:  # 최대 3개 쿼리 (임베딩 시간 최적화)
        results = search_mentoring_knowledge(
            conn, query, top_k=top_k_per_query,
            similarity_threshold=similarity_threshold,
        )
        for r in results:
            rid = r["id"]
            if rid not in all_results or r["similarity"] > all_results[rid]["similarity"]:
                all_results[rid] = r

    # 프로필 보너스 적용
    for rid, r in all_results.items():
        profile_bonus = _compute_profile_bonus(r, user_info)
        r["profile_bonus"] = round(profile_bonus, 4)
        r["final_score"] = round(r["similarity"] + profile_bonus, 4)

    # 최종 점수 기준 정렬
    ranked = sorted(all_results.values(), key=lambda x: x["final_score"], reverse=True)

    logger.info(
        f"[MentoringRAG] 프로필 매칭 검색 완료: "
        f"총 {len(ranked)}건 중 상위 {final_top_k}건 반환 "
        f"(쿼리 {len(queries)}개, user_info={'있음' if user_info else '없음'})"
    )

    return ranked[:final_top_k]


# ============================================================================
# LLM 컨텍스트 빌더 (상세 버전)
# ============================================================================

_SUBJECT_KEYWORDS: List[str] = [
    "행정법", "행정학", "국어", "영어", "한국사", "경제학", "경제",
    "노동법", "세법", "회계", "사회", "과학", "수학", "헌법",
    "공직선거법", "형법", "형사소송법", "민법", "교육학",
]


def _extract_subject_section(full_text: str, target: str, max_chars: int = 400) -> str:
    """합쳐진 과목 학습법 텍스트에서 특정 과목 부분을 추출합니다."""
    import re

    # 대상 과목 위치 탐색
    idx = -1
    for pat in [rf"{target}[교재강의\s]*[:：]", rf"{target}[은는이가]", target]:
        m = re.search(pat, full_text)
        if m:
            idx = m.start()
            break

    if idx == -1:
        return full_text[:max_chars]

    section = full_text[idx: idx + max_chars]

    # 다음 과목 시작 지점에서 자르기
    for other in _SUBJECT_KEYWORDS:
        if other == target:
            continue
        m = re.search(rf"\n?{other}[교재강의\s]*[:：]|^{other}[은는이가]", section[20:])
        if m:
            section = section[: 20 + m.start()]
            break

    return section.strip()


def build_mentoring_context(
    results: List[Dict[str, Any]],
    max_results: int = 5,
    include_details: bool = False,
    question: str = "",
) -> str:
    """검색된 합격 수기를 LLM 컨텍스트 문자열로 조합합니다.

    include_details=True 일 때 모든 컬럼의 원문을 최대한 포함합니다.
    question이 주어지면 관련 과목 섹션을 우선 추출합니다.
    """
    # 질문에서 언급된 과목 탐지
    target_subject = next(
        (s for s in _SUBJECT_KEYWORDS if s in question), None
    )
    if not results:
        return ""

    context_parts = []
    for i, r in enumerate(results[:max_results], 1):
        exam_info = r.get("exam_info", {})
        study_style = r.get("study_style", {})
        title = _format_exam_title(exam_info)

        sim_label = f"{r['similarity']:.1%}"
        bonus = r.get("profile_bonus", 0)
        if bonus > 0:
            sim_label += f" (+환경유사도 {bonus:.1%})"

        # 합격자 프로필 레이블 (EXAONE이 이 값으로 합격자를 지칭하도록)
        profile_parts: List[str] = []
        if exam_info.get("year"):
            profile_parts.append(f"{exam_info['year']}년")
        if exam_info.get("exam_type"):
            profile_parts.append(exam_info["exam_type"])
        if exam_info.get("grade"):
            profile_parts.append(f"{exam_info['grade']}급")
        if exam_info.get("job_series"):
            profile_parts.append(exam_info["job_series"])
        if exam_info.get("총 수험기간"):
            profile_parts.append(f"수험기간 {exam_info['총 수험기간']}")
        profile_label = " ".join(profile_parts) + " 합격자" if profile_parts else "합격자"

        part = f"[합격 수기 {i}] (유사도: {sim_label})\n"
        part += f"합격자 프로필: {profile_label}\n"

        # ── 시험 정보 상세 ──
        info_parts: List[str] = []
        if exam_info.get("year"):
            info_parts.append(f"합격연도: {exam_info['year']}")
        if exam_info.get("grade"):
            info_parts.append(f"등급: {exam_info['grade']}급")
        if exam_info.get("job_series"):
            info_parts.append(f"직렬: {exam_info['job_series']}")
        if exam_info.get("총 수험기간"):
            info_parts.append(f"수험기간: {exam_info['총 수험기간']}")
        if exam_info.get("exam_type"):
            info_parts.append(f"시험유형: {exam_info['exam_type']}")
        if info_parts:
            part += f"시험 정보: {' | '.join(info_parts)}\n"

        # ── 수험 스타일 상세 ──
        style_parts: List[str] = []
        if study_style.get("수험생활"):
            style_parts.append(f"수험생활: {study_style['수험생활']}")
        if study_style.get("평균 회독수"):
            style_parts.append(f"평균 회독수: {study_style['평균 회독수']}")
        if study_style.get("수험기간"):
            style_parts.append(f"수험기간: {study_style['수험기간']}")
        if study_style.get("하루 공부시간"):
            style_parts.append(f"하루 공부시간: {study_style['하루 공부시간']}")
        # 나머지 study_style 키도 포함
        for k, v in study_style.items():
            if k not in ("수험생활", "평균 회독수", "수험기간", "하루 공부시간") and v:
                style_parts.append(f"{k}: {v}")
        if style_parts:
            part += f"수험 스타일: {' | '.join(style_parts)}\n"

        # ── 핵심 합격 전략 (우선 노출) ──
        if r.get("key_points"):
            kp = r["key_points"]
            max_kp = 1000 if include_details else 250
            if len(kp) > max_kp:
                kp = kp[:max_kp] + "..."
            part += f"\n[핵심 합격 전략]\n{kp}\n"

        # ── 과목별 학습법 (교재·강사 정보 포함) ──
        subject_methods = r.get("subject_methods") or {}
        if isinstance(subject_methods, dict) and subject_methods:
            part += "\n[과목별 학습법]\n"
            for subj, method in subject_methods.items():
                if not method or not isinstance(method, str) or len(method.strip()) <= 5:
                    continue
                m = method.strip()
                if include_details:
                    # include_details 모드: 전체 텍스트
                    if len(m) > 800:
                        m = m[:800] + "..."
                elif target_subject and subj in ("전체", "전체 학습법"):
                    # 질문에 특정 과목이 있고 [전체] 키인 경우 → 해당 과목 섹션만 추출
                    m = _extract_subject_section(m, target_subject, max_chars=400)
                    subj = target_subject  # 키 이름도 해당 과목으로 변경
                else:
                    if len(m) > 200:
                        m = m[:200] + "..."
                part += f"  • {subj}: {m}\n"

        # ── 일일 학습 계획 (요약만) ──
        if r.get("daily_plan"):
            plan = r["daily_plan"]
            max_len = 2000 if include_details else 150
            if len(plan) > max_len:
                plan = plan[:max_len] + "..."
            part += f"\n[일일 학습 계획]\n{plan}\n"

        # ── 어려웠던 점과 극복 방법 ──
        if r.get("difficulties"):
            diff = r["difficulties"]
            max_diff = 1000 if include_details else 200
            if len(diff) > max_diff:
                diff = diff[:max_diff] + "..."
            part += f"\n[어려웠던 점과 극복 방법]\n{diff}\n"

        # ── 면접 준비 (있으면) ──
        if include_details and r.get("interview_prep"):
            ip = r["interview_prep"]
            if len(ip) > 500:
                ip = ip[:500] + "..."
            part += f"\n[면접 준비]\n{ip}\n"

        context_parts.append(part)

    return "\n{'='*60}\n".join(context_parts)


# ============================================================================
# 프론트엔드 출처 정보 (확장)
# ============================================================================

def extract_rag_sources(
    results: List[Dict[str, Any]],
    max_results: int = 5,
    user_info: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """RAG 검색 결과에서 프론트엔드 표시용 출처 정보를 추출합니다."""
    sources = []
    for i, r in enumerate(results[:max_results], 1):
        exam_info = r.get("exam_info", {})
        study_style = r.get("study_style", {})

        # 수험 스타일 요약 문자열
        style_parts: List[str] = []
        if study_style.get("수험생활"):
            style_parts.append(study_style["수험생활"])
        if study_style.get("평균 회독수"):
            style_parts.append(f"회독수 {study_style['평균 회독수']}")
        if exam_info.get("총 수험기간"):
            style_parts.append(f"수험기간 {exam_info['총 수험기간']}")
        if study_style.get("하루 공부시간"):
            style_parts.append(f"하루 {study_style['하루 공부시간']}")
        study_info = " | ".join(style_parts) if style_parts else None

        # 과목별 학습법 미리보기 (과목명만)
        subject_methods = r.get("subject_methods") or {}
        method_subjects = []
        if isinstance(subject_methods, dict):
            method_subjects = [
                k for k, v in subject_methods.items()
                if v and isinstance(v, str) and len(v.strip()) > 10
            ]

        # 프로필 매칭 정보 — user_info 기반 정확한 추적
        profile_bonus = r.get("profile_bonus", 0)
        match_reasons: List[str] = []
        if profile_bonus > 0 and user_info:
            # 1) 직렬 일치
            u_target = user_info.get("target_position", "")
            s_job = exam_info.get("job_series", "")
            if u_target and s_job and (u_target in s_job or s_job in u_target):
                match_reasons.append(f"직렬 일치 ({s_job})")

            # 2) 직장 상태 유사
            u_emp = user_info.get("employment_status", "")
            s_life = study_style.get("수험생활", "")
            if u_emp and s_life:
                kws = _EMP_TO_STUDY_STYLE_KEYWORDS.get(u_emp, [])
                if any(kw in s_life for kw in kws):
                    match_reasons.append(f"수험 환경 유사 ({s_life})")

            # 3) 초시/재시 매칭
            u_first = user_info.get("is_first_timer")
            if u_first is not None:
                if u_first:
                    match_reasons.append("초시생 매칭")
                else:
                    match_reasons.append("재시생 매칭")

            # 4) 수험기간 매칭
            u_dur = user_info.get("study_duration", "")
            s_dur = exam_info.get("총 수험기간", "")
            if u_dur and s_dur:
                match_reasons.append(f"수험기간 {s_dur}")

            # 5) 취약 과목 학습법 존재
            u_weak = user_info.get("weak_subjects", []) or []
            s_methods = r.get("subject_methods") or {}
            if isinstance(s_methods, dict) and u_weak:
                matched_w = [s for s in u_weak if any(s in k for k in s_methods)]
                if matched_w:
                    match_reasons.append(f"취약 과목 학습법 ({', '.join(matched_w)})")

            # 6) 강점 과목 학습법 존재
            u_strong = user_info.get("strong_subjects", []) or []
            if isinstance(s_methods, dict) and u_strong:
                matched_s = [s for s in u_strong if any(s in k for k in s_methods)]
                if matched_s:
                    match_reasons.append(f"강점 과목 포함 ({', '.join(matched_s)})")

            # 7) 응시 과목 겹침
            s_subjects = exam_info.get("subjects", []) or []
            all_user_subj = set(u_weak + u_strong)
            if s_subjects and all_user_subj:
                overlap_subj = [
                    subj for subj in all_user_subj
                    if any(subj in s or s in subj for s in s_subjects)
                ]
                if overlap_subj:
                    match_reasons.append(
                        f"응시 과목 일치 ({', '.join(overlap_subj[:3])})"
                    )
        elif profile_bonus > 0:
            # user_info 없는 경우 기존 방식 폴백
            if exam_info.get("job_series"):
                match_reasons.append("직렬 관련")
            if study_style.get("수험생활"):
                match_reasons.append("수험 환경 참고")
            if exam_info.get("총 수험기간"):
                match_reasons.append(f"수험기간 {exam_info['총 수험기간']}")

        source: Dict[str, Any] = {
            "id": r.get("id"),
            "rank": i,
            "similarity": r.get("similarity", 0.0),
            "final_score": r.get("final_score", r.get("similarity", 0.0)),
            "profile_bonus": profile_bonus,
            "match_reasons": match_reasons,
            "title": _format_exam_title(exam_info),
            "source_name": r.get("source"),
            "source_url": r.get("source_url"),
            "exam_info": exam_info,
            "study_info": study_info,
            "method_subjects": method_subjects,
            "context_preview": None,
            "key_points_preview": None,
            "difficulties_preview": None,
            "subject_methods_preview": None,
        }

        # 일일 학습 계획 — 원문 전체
        if r.get("daily_plan"):
            source["context_preview"] = r["daily_plan"].strip()

        # 핵심 전략 — 원문 전체
        if r.get("key_points"):
            source["key_points_preview"] = r["key_points"].strip()

        # 어려움 극복 — 원문 전체
        if r.get("difficulties"):
            source["difficulties_preview"] = r["difficulties"].strip()

        # 과목별 학습법 — 전체 과목, 원문 전체
        if isinstance(subject_methods, dict) and subject_methods:
            preview = {}
            for subj, method in subject_methods.items():
                if method and isinstance(method, str) and len(method.strip()) > 10:
                    preview[subj] = method.strip()
            if preview:
                source["subject_methods_preview"] = preview

        sources.append(source)
    return sources


# ============================================================================
# 프롬프트 빌더
# ============================================================================

def build_mentoring_prompt(
    question: str,
    context: str,
    chat_history: list | None = None,
    context_summary: str = "",
) -> str:
    """멘토링 RAG용 EXAONE 프롬프트를 생성합니다.

    멀티턴 대화인 경우 이전 대화 맥락을 포함하여 연속적인 답변이 가능합니다.
    """
    parts = [
        "당신은 공무원 시험 합격을 위한 멘토입니다. "
        "아래 제공된 합격자 수기를 바탕으로, 사용자의 질문에 "
        "따뜻하고 구체적인 학습 조언을 해주세요.\n",
        "규칙:\n"
        "1. 합격자 수기의 내용(교재명·강사명·학습법 등)을 최대한 구체적으로 반영하여 자연스럽게 재구성하세요.\n"
        "2. 수기에 없는 내용은 추측하지 말고 \"추가 정보가 필요합니다\"라고 안내하세요.\n"
        "3. 공무원 시험 준비에 실질적으로 도움이 되는 조언을 우선하세요.\n"
        "4. 이전 대화 맥락이 있으면 자연스럽게 이어서 답변하세요.\n"
        "5. 마크다운 헤더(###, ##)는 사용하지 말고 자연스러운 문장으로 작성하세요.\n"
        "6. 반드시 완전한 문장으로 끝내세요 (문장 중간에 끊기지 않도록).\n"
        "7. 합격자를 언급할 때는 '합격자 프로필'에 명시된 내용(예: '2025년 국가직 9급 세무직 합격자')을 사용하고, 출처 플랫폼명(megagong 등)은 절대 사용하지 마세요.\n"
        "8. 답변은 한국어로 작성하세요.\n",
    ]

    # ── 이전 대화 요약 ──
    if context_summary:
        parts.append(f"===== 이전 대화 요약 =====\n{context_summary}\n")

    # ── 이전 대화 이력 (최근 3턴만) ──
    if chat_history:
        recent = chat_history[-6:]
        history_lines = []
        for msg in recent:
            role_label = "사용자" if msg.get("role") == "user" else "멘토"
            text = msg.get("text", "")
            if len(text) > 200:
                text = text[:200] + "..."
            history_lines.append(f"{role_label}: {text}")
        if history_lines:
            parts.append(
                "===== 이전 대화 이력 =====\n"
                + "\n".join(history_lines)
                + "\n"
            )

    # ── 합격 수기 참고 자료 ──
    parts.append(f"===== 합격 수기 참고 자료 =====\n{context}\n")

    # ── 현재 질문 ──
    parts.append(
        f"===== 사용자 질문 =====\n{question}\n\n"
        "위 합격 수기를 바탕으로 구체적이고 따뜻하게 답변해주세요 (반드시 완전한 문장으로 끝낼 것):"
    )

    return "\n".join(parts)


# ============================================================================
# 답변 생성
# ============================================================================

def generate_mentoring_answer_raw(
    question: str,
    results: List[Dict[str, Any]],
) -> str:
    """LLM 없이, 검색된 합격 수기를 기반으로 답변을 포맷팅합니다."""
    if not results:
        return (
            "관련된 합격 수기를 찾지 못했습니다. "
            "질문을 더 구체적으로 해주시면 도움이 될 수 있습니다.\n\n"
            "예시: \"노베이스 1년 일반행정직 어떻게 준비해?\", "
            "\"행정법 교재 추천해줘\", \"단기 합격 학습 계획 짜줘\""
        )

    top = results[0]
    exam_info = top.get("exam_info", {})
    title = _format_exam_title(exam_info)

    answer_parts = []
    answer_parts.append(f"📋 관련 합격 수기: {title} (유사도: {top['similarity']:.1%})\n")

    if top.get("key_points"):
        answer_parts.append(f"💡 핵심 전략:\n{top['key_points']}\n")

    if top.get("daily_plan"):
        dp = top["daily_plan"]
        if len(dp) > 500:
            dp = dp[:500] + "..."
        answer_parts.append(f"📅 일일 학습 계획:\n{dp}\n")

    study_style = top.get("study_style", {})
    if study_style.get("수험생활"):
        answer_parts.append(f"📝 수험 스타일: {study_style['수험생활']}")

    if len(results) > 1:
        answer_parts.append(
            f"\n---\n📌 관련 수기 {len(results)}건 중 가장 유사한 수기를 보여드렸습니다."
        )
        for i, r in enumerate(results[1:3], 2):
            r_title = _format_exam_title(r.get("exam_info", {}))
            answer_parts.append(f"  {i}. {r_title} (유사도: {r['similarity']:.1%})")

    return "\n".join(answer_parts)


def generate_mentoring_answer_with_exaone(
    question: str,
    results: List[Dict[str, Any]],
    llm: BaseLLM,
    chat_history: list | None = None,
    context_summary: str = "",
) -> str:
    """EXAONE LLM을 사용하여 멘토링 RAG 답변을 생성합니다."""
    # 입력이 길수록 prefill 시간이 증가하므로 컨텍스트를 압축합니다.
    # question을 전달해 해당 과목 섹션을 우선 추출합니다.
    context = build_mentoring_context(
        results, max_results=2, include_details=False, question=question
    )
    if len(context) > 1000:
        context = context[:1000] + "..."
    if not context:
        return generate_mentoring_answer_raw(question, results)

    prompt = build_mentoring_prompt(
        question, context,
        chat_history=chat_history,
        context_summary=context_summary,
    )

    logger.info("[MentoringRAG] EXAONE에 답변 생성 요청 중...")
    started_at = time.time()
    max_new_tokens = (
        _MENTORING_MAX_NEW_TOKENS_GPU if torch.cuda.is_available() else _MENTORING_MAX_NEW_TOKENS_CPU
    )

    def _run_generate() -> str:
        return llm.generate(
            prompt,
            max_new_tokens=max_new_tokens,
            max_time=_MENTORING_GENERATION_MAX_TIME_SEC,
        )

    # with 컨텍스트 매니저를 사용하면 FutureTimeoutError 발생 후에도
    # executor.__exit__ → shutdown(wait=True) 로 스레드 종료를 기다린다.
    # 따라서 컨텍스트 매니저 없이 생성하고, 타임아웃 시 shutdown(wait=False) 로 즉시 포기.
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_run_generate)
    try:
        answer = future.result(timeout=_MENTORING_EXAONE_CALL_TIMEOUT_SEC)
        executor.shutdown(wait=False)
    except FutureTimeoutError:
        executor.shutdown(wait=False, cancel_futures=True)
        elapsed = time.time() - started_at
        logger.warning(
            "[MentoringRAG] EXAONE 생성 타임아웃 - raw 폴백 "
            f"(timeout={_MENTORING_EXAONE_CALL_TIMEOUT_SEC}s, elapsed={elapsed:.1f}s)"
        )
        return generate_mentoring_answer_raw(question, results)

    elapsed = time.time() - started_at

    # ── EXAONE 출력 마크다운 정제 ──
    import re as _re

    # 헤더 제거: ### 텍스트: → 텍스트:
    answer = _re.sub(r'^#{1,3}\s*', '', answer, flags=_re.MULTILINE)
    # 볼드/이탤릭 제거: **text** → text
    answer = _re.sub(r'\*{1,2}([^*\n]+)\*{1,2}', r'\1', answer)
    # 불릿 제거: - 텍스트 → 텍스트 (줄 시작 하이픈)
    answer = _re.sub(r'^\s*[-•]\s+', '', answer, flags=_re.MULTILINE)
    # 연속 빈줄 정리
    answer = _re.sub(r'\n{3,}', '\n\n', answer).strip()

    # ── 문장이 중간에 잘렸으면 마지막 완전한 문장까지만 반환 ──
    # 한국어 문장 종결: "다.", "요.", "다!", "요!", "다?", "다\n", "습니다." 등
    last_end = -1
    for m in _re.finditer(r'(?:습니다|입니다|합니다|됩니다|드립니다|겠습니다|바랍니다)[.!]'
                          r'|(?:[다요])[.!]'
                          r'|\.$', answer):
        last_end = m.end()
    # 응답의 70% 이상 지점에서 완전한 문장 종결을 찾은 경우에만 자르기
    if 0 < last_end < len(answer) and last_end >= len(answer) * 0.6:
        answer = answer[:last_end].strip()

    # max_time에 걸리거나 모델 이상으로 의미 있는 답변이 생성되지 않으면 즉시 폴백
    if not answer or answer.strip() in ("응답을 생성하지 못했습니다.",):
        logger.warning(
            "[MentoringRAG] EXAONE 응답 비어있음/부실 - raw 폴백 "
            f"(elapsed={elapsed:.1f}s)"
        )
        return generate_mentoring_answer_raw(question, results)

    logger.info(f"[MentoringRAG] EXAONE 답변 생성 완료 ({elapsed:.1f}s)")
    return answer


# ============================================================================
# 통합 파이프라인
# ============================================================================

async def process_mentoring_rag(
    conn: psycopg.Connection,
    question: str,
    *,
    top_k: int = 5,
    use_llm: bool = True,
    llm: Optional[BaseLLM] = None,
    chat_history: list | None = None,
    context_summary: str = "",
    rewritten_query: str | None = None,
) -> Dict[str, Any]:
    """멘토링 RAG 전체 파이프라인을 실행합니다."""
    logger.info(f"[MentoringRAG] 파이프라인 시작: '{question[:50]}...'")

    search_query = rewritten_query or question
    if rewritten_query and rewritten_query != question:
        logger.info(f"[MentoringRAG] 재구성된 쿼리로 검색: '{search_query[:60]}...'")

    results = search_mentoring_knowledge(conn, search_query, top_k=top_k)

    retrieved_docs = [
        f"[{r['similarity']:.1%}] {_format_exam_title(r.get('exam_info', {}))}"
        for r in results
    ]

    answer = ""
    generation_method = "raw"

    if use_llm and results:
        if llm is None:
            try:
                from backend.dependencies import get_llm
                llm = get_llm()
                if not llm.is_loaded():
                    llm.load()
                logger.info("[MentoringRAG] EXAONE 모델 자동 로드 완료")
            except Exception as e:
                logger.warning(f"[MentoringRAG] EXAONE 자동 로드 실패: {e}")
                llm = None

        if llm is not None and llm.is_loaded():
            try:
                answer = generate_mentoring_answer_with_exaone(
                    question, results, llm,
                    chat_history=chat_history,
                    context_summary=context_summary,
                )
                if answer and answer.strip().startswith("📋 관련 합격 수기:"):
                    generation_method = "raw_fallback"
                    logger.info("[MentoringRAG] EXAONE 타임아웃/부실 응답으로 raw 폴백 완료")
                else:
                    generation_method = "exaone"
                    logger.info("[MentoringRAG] EXAONE으로 답변 생성 완료")
            except Exception as e:
                logger.warning(
                    f"[MentoringRAG] EXAONE 생성 실패, raw 모드로 폴백: {e}"
                )
                answer = generate_mentoring_answer_raw(question, results)
                generation_method = "raw_fallback"
        else:
            logger.info("[MentoringRAG] EXAONE 미로드 → raw 모드로 답변 생성")
            answer = generate_mentoring_answer_raw(question, results)
            generation_method = "raw"
    else:
        answer = generate_mentoring_answer_raw(question, results)
        generation_method = "raw"

    return {
        "success": True,
        "answer": answer,
        "retrieved_docs": retrieved_docs,
        "mode": "mentoring",
        "metadata": {
            "result_count": len(results),
            "generation_method": generation_method,
            "top_similarity": results[0]["similarity"] if results else 0.0,
            "rewritten_query": rewritten_query,
            "has_chat_history": bool(chat_history),
        },
    }
