"""Query Rewriter — 멀티턴 대화 맥락을 반영하여 검색 쿼리를 재구성합니다.

규칙 기반(키워드 추출) 방식으로 동작하며,
필요 시 EXAONE LLM으로 업그레이드할 수 있는 구조입니다.

사용 예시:
    rewritten = rewrite_query(
        current_question="학습 계획 짜줘",
        chat_history=[
            {"role": "user", "text": "나 노베이스 1년 일행직 준비해"},
            {"role": "bot", "text": "노베이스 1년 일반행정직 준비..."},
        ],
        context_summary="노베이스 1년 일반행정직",
    )
    # → "노베이스 1년 일반행정직 학습 계획"
"""

import logging
import re
from typing import Dict, Any, List, Optional

from backend.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)

# 검색에 유의미한 도메인 키워드 사전
_DOMAIN_KEYWORDS = {
    # 직렬
    "일행직", "일반행정", "교육행정", "세무직", "관세직", "출입국",
    "경찰", "소방", "교정", "보호", "검찰", "법원", "우정",
    # 시험 구분
    "9급", "7급", "5급", "국가직", "지방직", "서울시", "군무원",
    # 과목
    "국어", "영어", "한국사", "행정법", "행정학", "경제학",
    "헌법", "민법", "세법", "회계학", "사회", "과학", "수학",
    # 학습 관련
    "노베이스", "유베이스", "초시생", "재시생", "N수",
    "독학", "학원", "인강", "기출", "모의고사",
    "단기", "장기", "1년", "2년", "6개월", "3개월",
    "커리큘럼", "교재", "강의", "기본서", "문제집",
    # 기타
    "합격", "불합격", "슬럼프", "멘탈", "동기부여",
    "오답", "약점", "취약", "보완", "전략",
}

# 현재 질문에 명시된 과목만 검색어에 남기기 (멀티턴에서 타 과목명이 섞이는 것 방지)
_SUBJECT_NAMES_FOR_QUERY_FILTER = frozenset(
    {
        "국어",
        "영어",
        "한국사",
        "행정법",
        "행정학",
        "경제학",
        "헌법",
        "민법",
        "세법",
        "회계학",
        "사회",
        "과학",
        "수학",
        "교육학",
    }
)

_FOLLOW_UP_QUERY_MARKERS = (
    "다른",
    "또",
    "말고",
    "추가",
    "더",
    "없어?",
    "없나?",
    "있어?",
    "있나?",
)


def _subjects_in_text(text: str) -> set:
    return {s for s in _SUBJECT_NAMES_FOR_QUERY_FILTER if s in text}


def _is_follow_up_question_text(text: str) -> bool:
    return any(marker in text for marker in _FOLLOW_UP_QUERY_MARKERS)


def _latest_subject_from_user_history(chat_history: List[Dict[str, Any]]) -> Optional[str]:
    """최근 사용자 발화에서 가장 마지막 과목 1개를 추출합니다."""
    for msg in reversed(chat_history):
        if msg.get("role") != "user":
            continue
        txt = msg.get("text", "")
        subjects = [s for s in _SUBJECT_NAMES_FOR_QUERY_FILTER if s in txt]
        if subjects:
            # 동일 문장에 여러 과목이 있어도 마지막 하나만 상속
            return subjects[-1]
    return None


def _normalize_subject_for_follow_up(
    current_question: str,
    rewritten: str,
    chat_history: List[Dict[str, Any]],
) -> str:
    """후속 질문에서 과목 상속/단일 과목 정규화를 적용합니다."""
    cur_subjects = _subjects_in_text(current_question)
    rewritten_subjects = _subjects_in_text(rewritten)

    # 현재 질문에 과목이 없는 후속 질문이면, 직전 사용자 과목 1개를 상속
    if not cur_subjects and _is_follow_up_question_text(current_question):
        inherited = _latest_subject_from_user_history(chat_history)
        if inherited:
            # 재작성 결과에서 다른 과목 제거 후 단일 과목으로 고정
            cleaned = rewritten
            for s in _SUBJECT_NAMES_FOR_QUERY_FILTER:
                if s != inherited and s in cleaned:
                    cleaned = cleaned.replace(s, " ")
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if inherited not in cleaned:
                cleaned = f"{inherited} {cleaned}".strip()
            return cleaned

    # 후속 질문 재작성에 과목이 2개 이상 섞이면 직전 과목으로 강제 정규화
    if _is_follow_up_question_text(current_question) and len(rewritten_subjects) >= 2:
        inherited = _latest_subject_from_user_history(chat_history)
        if inherited:
            cleaned = rewritten
            for s in _SUBJECT_NAMES_FOR_QUERY_FILTER:
                if s != inherited and s in cleaned:
                    cleaned = cleaned.replace(s, " ")
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if inherited not in cleaned:
                cleaned = f"{inherited} {cleaned}".strip()
            return cleaned

    return rewritten


def _filter_subject_keywords_for_current(current_question: str, keywords: List[str]) -> List[str]:
    """현재 질문에 과목이 있으면, 맥락에서 추출한 다른 과목 키워드는 제외합니다."""
    cur = _subjects_in_text(current_question)
    if not cur:
        return keywords
    out: List[str] = []
    for kw in keywords:
        if kw in _SUBJECT_NAMES_FOR_QUERY_FILTER and kw not in cur:
            continue
        out.append(kw)
    return out


def _sanitize_subjects_in_rewritten(current_question: str, rewritten: str) -> str:
    """LLM/규칙 재작성 결과에서 현재 질문과 충돌하는 과목명을 제거합니다."""
    cur = _subjects_in_text(current_question)
    if not cur:
        return rewritten
    out = rewritten
    for s in _SUBJECT_NAMES_FOR_QUERY_FILTER:
        if s in cur:
            continue
        if s in out:
            out = out.replace(s, " ")
    out = re.sub(r"\s+", " ", out).strip()
    if len(out) < 3:
        return current_question
    return out


# 불용어 (검색 쿼리에서 제거)
_STOPWORDS = {
    "해줘", "해 줘", "해주세요", "알려줘", "알려 줘", "어떻게",
    "뭐가", "뭘", "좀", "하고", "싶어", "인데", "거야",
    "나", "나는", "내가", "저", "제가", "이제",
    "그래서", "그런데", "그리고", "또",
}


def _extract_keywords_from_messages(
    messages: List[Dict[str, Any]],
    max_messages: int = 6,
) -> List[str]:
    """최근 대화 메시지에서 도메인 키워드를 추출합니다."""
    keywords = []
    seen = set()

    # 최근 N개 메시지만 확인
    recent = messages[-max_messages:] if len(messages) > max_messages else messages

    for msg in recent:
        text = msg.get("text", "")
        for kw in _DOMAIN_KEYWORDS:
            if kw in text and kw not in seen:
                keywords.append(kw)
                seen.add(kw)

    return keywords


def _clean_query(text: str) -> str:
    """불용어를 제거하고 검색에 적합한 형태로 정리합니다."""
    cleaned = text
    for sw in _STOPWORDS:
        cleaned = cleaned.replace(sw, " ")

    # 연속 공백 제거
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def rewrite_query_rule_based(
    current_question: str,
    chat_history: List[Dict[str, Any]],
    context_summary: str = "",
) -> str:
    """규칙 기반으로 검색 쿼리를 재구성합니다.

    1. 이전 대화에서 도메인 키워드 추출
    2. context_summary에서 키워드 추출
    3. 현재 질문 정리
    4. 중복 제거 후 결합

    Args:
        current_question: 현재 사용자 질문
        chat_history: 이전 대화 이력 리스트
        context_summary: 대화 맥락 요약

    Returns:
        재구성된 검색 쿼리
    """
    # 현재 질문에 이미 충분한 맥락이 있는지 확인
    current_keywords = [kw for kw in _DOMAIN_KEYWORDS if kw in current_question]
    if len(current_keywords) >= 3:
        # 이미 구체적인 질문이면 그대로 반환
        return current_question

    # 이전 대화에서 키워드 추출 (현재 질문에 과목이 있으면 충돌 과목 제외)
    history_keywords = _filter_subject_keywords_for_current(
        current_question, _extract_keywords_from_messages(chat_history)
    )

    # context_summary에서 키워드 추출
    # 후속 질문 + 과목 미명시 상황에서는 summary 전역 키워드 주입을 줄여 과목 오염 방지
    if _is_follow_up_question_text(current_question) and not _subjects_in_text(current_question):
        summary_keywords = []
    else:
        summary_keywords = _filter_subject_keywords_for_current(
            current_question, [kw for kw in _DOMAIN_KEYWORDS if kw in context_summary]
        )

    # 현재 질문 정리
    cleaned_question = _clean_query(current_question)

    # 키워드 결합 (중복 제거, 순서: summary → history → question)
    all_keywords = []
    seen = set()

    for kw in summary_keywords + history_keywords:
        if kw not in seen and kw not in cleaned_question:
            all_keywords.append(kw)
            seen.add(kw)

    # 맥락 키워드가 있으면 질문 앞에 추가
    if all_keywords:
        rewritten = " ".join(all_keywords) + " " + cleaned_question
    else:
        rewritten = cleaned_question

    rewritten = _sanitize_subjects_in_rewritten(current_question, rewritten)
    rewritten = _normalize_subject_for_follow_up(current_question, rewritten, chat_history)

    logger.info(
        f"[QueryRewriter] 규칙 기반 재구성: "
        f"'{current_question[:40]}...' → '{rewritten[:60]}...'"
    )
    return rewritten


def rewrite_query_with_llm(
    current_question: str,
    chat_history: List[Dict[str, Any]],
    context_summary: str,
    llm: BaseLLM,
) -> str:
    """EXAONE LLM을 사용하여 검색 쿼리를 재구성합니다.

    규칙 기반보다 정확하지만 추론 시간이 추가됩니다.
    max_new_tokens=64로 짧게 생성합니다.

    Args:
        current_question: 현재 사용자 질문
        chat_history: 이전 대화 이력
        context_summary: 대화 맥락 요약
        llm: EXAONE BaseLLM 인스턴스

    Returns:
        재구성된 검색 쿼리
    """
    # 최근 대화 요약 (최대 3턴)
    recent_turns = []
    recent = chat_history[-6:] if len(chat_history) > 6 else chat_history
    for msg in recent:
        role = "사용자" if msg["role"] == "user" else "멘토"
        text = msg["text"][:100]
        recent_turns.append(f"{role}: {text}")

    history_text = "\n".join(recent_turns) if recent_turns else "(첫 질문)"

    prompt = (
        "당신은 검색 쿼리 최적화 전문가입니다.\n"
        "아래 대화 맥락과 현재 질문을 보고, "
        "벡터 검색에 적합한 독립적인 검색 쿼리를 한 문장으로 작성하세요.\n"
        "규칙:\n"
        "- 마크다운(**,##,\"\") 없이 평문 한국어로만 작성하세요.\n"
        "- 현재 질문에 이미 과목명(국어·영어·한국사·행정법 등)이 있으면 그 과목만 사용하고, "
        "대화 맥락에 있더라도 다른 과목명을 검색어에 새로 넣지 마세요.\n"
        "- 예: 현재 질문이 '영어 교재 추천'이면 행정법·국어 등 다른 과목을 쓰지 마세요.\n\n"
        f"[대화 맥락 요약]\n{context_summary or '없음'}\n\n"
        f"[최근 대화]\n{history_text}\n\n"
        f"[현재 질문]\n{current_question}\n\n"
        "검색 쿼리:"
    )

    try:
        rewritten = llm.generate(
            prompt,
            max_new_tokens=64,
            temperature=0.3,
            top_p=0.9,
        ).strip()

        # 마크다운 포맷 제거 (**"..."**, ##, 따옴표 등)
        import re
        rewritten = re.sub(r'\*+|#+|"', '', rewritten).strip()
        rewritten = _sanitize_subjects_in_rewritten(current_question, rewritten)
        rewritten = _normalize_subject_for_follow_up(current_question, rewritten, chat_history)

        # 빈 결과이거나 너무 짧으면 규칙 기반 폴백
        if not rewritten or len(rewritten) < 5:
            return rewrite_query_rule_based(current_question, chat_history, context_summary)

        logger.info(
            f"[QueryRewriter] LLM 재구성: "
            f"'{current_question[:40]}...' → '{rewritten[:60]}...'"
        )
        return rewritten

    except Exception as e:
        logger.warning(f"[QueryRewriter] LLM 재구성 실패, 규칙 기반 폴백: {e}")
        return rewrite_query_rule_based(current_question, chat_history, context_summary)


def generate_context_summary(
    chat_history: List[Dict[str, Any]],
    current_question: str = "",
    old_summary: str = "",
) -> str:
    """대화 이력에서 맥락 요약을 생성합니다 (규칙 기반 키워드 추출).

    이전 요약에 새 키워드를 누적하여 맥락을 유지합니다.

    Args:
        chat_history: 전체 대화 이력
        current_question: 현재 질문 (추가 키워드 소스)
        old_summary: 이전 맥락 요약

    Returns:
        갱신된 맥락 요약 문자열
    """
    # 이전 요약의 키워드
    existing_keywords = set()
    if old_summary:
        for kw in _DOMAIN_KEYWORDS:
            if kw in old_summary:
                existing_keywords.add(kw)

    # 전체 대화에서 키워드 추출
    all_keywords = _extract_keywords_from_messages(chat_history, max_messages=20)

    # 현재 질문에서 키워드 추출
    for kw in _DOMAIN_KEYWORDS:
        if kw in current_question and kw not in existing_keywords:
            all_keywords.append(kw)

    # 기존 키워드와 합치기 (순서 유지, 중복 제거)
    final_keywords = list(existing_keywords)
    seen = set(existing_keywords)
    for kw in all_keywords:
        if kw not in seen:
            final_keywords.append(kw)
            seen.add(kw)

    # 최대 10개 키워드로 제한
    final_keywords = final_keywords[:10]

    if not final_keywords:
        return old_summary or ""

    summary = ", ".join(final_keywords)
    logger.debug(f"[QueryRewriter] 맥락 요약 갱신: {summary}")
    return summary


def rewrite_query(
    current_question: str,
    chat_history: List[Dict[str, Any]],
    context_summary: str = "",
    llm: Optional[BaseLLM] = None,
    use_llm: bool = False,
) -> str:
    """검색 쿼리를 재구성합니다 (통합 인터페이스).

    use_llm=True 이고 llm이 제공되면 LLM 기반,
    그렇지 않으면 규칙 기반으로 동작합니다.

    Args:
        current_question: 현재 사용자 질문
        chat_history: 이전 대화 이력
        context_summary: 대화 맥락 요약
        llm: EXAONE BaseLLM 인스턴스 (선택)
        use_llm: LLM 사용 여부

    Returns:
        재구성된 검색 쿼리
    """
    # 대화 이력이 없으면 재구성 불필요
    if not chat_history:
        return current_question

    if use_llm and llm is not None and llm.is_loaded():
        return rewrite_query_with_llm(current_question, chat_history, context_summary, llm)
    else:
        return rewrite_query_rule_based(current_question, chat_history, context_summary)

