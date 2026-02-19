"""멘토링 지식 RAG (Retrieval-Augmented Generation) 모듈.

mentoring_knowledge 테이블의 임베딩(KURE-v1, 1024차원)을 활용하여
사용자 질문과 가장 유사한 합격 수기 기반 멘토링 지식을 검색하고,
EXAONE LLM을 통해 답변을 생성합니다.
"""

import logging
from typing import Dict, Any, List, Optional

import psycopg

from backend.core.utils.embedding import generate_embedding
from backend.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)


def search_mentoring_knowledge(
    conn: psycopg.Connection,
    query: str,
    *,
    top_k: int = 5,
    similarity_threshold: float = 0.3,
) -> List[Dict[str, Any]]:
    """KURE-v1 임베딩 + pgvector로 유사한 멘토링 지식을 검색합니다.

    Args:
        conn: PostgreSQL 연결
        query: 사용자 질문
        top_k: 검색할 최대 건수
        similarity_threshold: 최소 유사도 (코사인 유사도, 0~1)

    Returns:
        유사한 멘토링 지식 리스트 (유사도 내림차순)
    """
    try:
        # 1) 사용자 질문을 KURE-v1로 임베딩
        query_vector = generate_embedding(query)
        embedding_str = "[" + ",".join(map(str, query_vector)) + "]"

        # 2) pgvector 코사인 유사도 검색
        #    <=> 연산자: cosine distance (0=동일, 2=정반대)
        #    1 - distance = similarity (0~1)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, instruction, question, intent, context,
                       thought_process, response,
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
            sim = float(r[7]) if r[7] is not None else 0.0
            if sim < similarity_threshold:
                continue
            results.append({
                "id": r[0],
                "instruction": r[1],
                "question": r[2],
                "intent": r[3],
                "context": r[4],
                "thought_process": r[5],
                "response": r[6],
                "similarity": round(sim, 4),
            })

        logger.info(
            f"[MentoringRAG] 검색 완료: query='{query[:50]}...', "
            f"결과={len(results)}건 (threshold={similarity_threshold})"
        )
        return results

    except Exception as e:
        logger.error(f"[MentoringRAG] 벡터 검색 실패: {e}", exc_info=True)
        return []


def build_mentoring_context(results: List[Dict[str, Any]], max_results: int = 3) -> str:
    """검색된 멘토링 지식을 LLM 컨텍스트 문자열로 조합합니다."""
    if not results:
        return ""

    context_parts = []
    for i, r in enumerate(results[:max_results], 1):
        part = f"[참고 수기 {i}] (유사도: {r['similarity']:.1%})\n"
        part += f"질문: {r['question']}\n"
        if r.get("intent"):
            part += f"의도: {r['intent']}\n"
        if r.get("thought_process"):
            tp = r["thought_process"]
            if len(tp) > 300:
                tp = tp[:300] + "..."
            part += f"분석: {tp}\n"
        part += f"답변: {r['response']}\n"
        context_parts.append(part)

    return "\n---\n".join(context_parts)


def build_mentoring_prompt(
    question: str,
    context: str,
    chat_history: list | None = None,
    context_summary: str = "",
) -> str:
    """멘토링 RAG용 EXAONE 프롬프트를 생성합니다.

    멀티턴 대화인 경우 이전 대화 맥락을 포함하여 연속적인 답변이 가능합니다.

    Args:
        question: 현재 사용자 질문
        context: RAG 검색 결과 컨텍스트
        chat_history: 이전 대화 이력 (선택)
        context_summary: 대화 맥락 요약 (선택)
    """
    parts = [
        "당신은 공무원 시험 합격을 위한 멘토입니다. "
        "아래 제공된 정보를 바탕으로, 사용자의 질문에 "
        "따뜻하고 구체적인 학습 조언을 해주세요.\n",
        "규칙:\n"
        "1. 참고 자료의 내용을 바탕으로 답변하되, 자연스럽게 재구성해서 답하세요.\n"
        "2. 참고 자료에 없는 내용은 추측하지 말고 \"추가 정보가 필요합니다\"라고 안내하세요.\n"
        "3. 공무원 시험 준비에 실질적으로 도움이 되는 조언을 우선해주세요.\n"
        "4. 이전 대화 맥락이 있으면 자연스럽게 이어서 답변하세요.\n"
        "5. 답변은 한국어로 작성하세요.\n",
    ]

    # ── 이전 대화 요약 ──
    if context_summary:
        parts.append(f"===== 이전 대화 요약 =====\n{context_summary}\n")

    # ── 이전 대화 이력 (최근 3턴만) ──
    if chat_history:
        recent = chat_history[-6:]  # 최근 6개 메시지 (≈3턴)
        history_lines = []
        for msg in recent:
            role_label = "사용자" if msg.get("role") == "user" else "멘토"
            text = msg.get("text", "")
            # 너무 긴 메시지는 요약
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
        "위 참고 자료와 대화 맥락을 바탕으로 사용자의 질문에 답변해주세요:"
    )

    return "\n".join(parts)


def generate_mentoring_answer_raw(
    question: str,
    results: List[Dict[str, Any]],
) -> str:
    """LLM 없이, 검색된 멘토링 지식을 기반으로 답변을 포맷팅합니다.

    EXAONE이 로드되지 않았을 때 사용하는 폴백 답변 생성기입니다.
    """
    if not results:
        return (
            "관련된 합격 수기를 찾지 못했습니다. "
            "질문을 더 구체적으로 해주시면 도움이 될 수 있습니다.\n\n"
            "예시: \"노베이스 1년 일반행정직 어떻게 준비해?\", "
            "\"행정법 교재 추천해줘\", \"단기 합격 학습 계획 짜줘\""
        )

    # 가장 유사한 결과 기반 답변 구성
    top = results[0]
    answer_parts = []

    # 메인 답변
    answer_parts.append(f"📋 관련 멘토링 답변 (유사도: {top['similarity']:.1%})\n")
    answer_parts.append(top["response"])

    # 사고 과정이 있으면 추가
    if top.get("thought_process"):
        tp = top["thought_process"]
        if len(tp) > 500:
            tp = tp[:500] + "..."
        answer_parts.append(f"\n\n💡 분석 과정:\n{tp}")

    # 추가 관련 답변이 있으면 힌트
    if len(results) > 1:
        answer_parts.append(f"\n\n---\n📌 관련 수기 {len(results)}건 중 가장 유사한 답변을 보여드렸습니다.")
        for i, r in enumerate(results[1:3], 2):
            q_preview = r["question"][:60] + "..." if len(r["question"]) > 60 else r["question"]
            answer_parts.append(f"\n  {i}. {q_preview} (유사도: {r['similarity']:.1%})")

    return "\n".join(answer_parts)


def generate_mentoring_answer_with_exaone(
    question: str,
    results: List[Dict[str, Any]],
    llm: BaseLLM,
    chat_history: list | None = None,
    context_summary: str = "",
) -> str:
    """EXAONE LLM을 사용하여 멘토링 RAG 답변을 생성합니다.

    Args:
        question: 사용자 질문
        results: 검색된 멘토링 지식 리스트
        llm: EXAONE BaseLLM 인스턴스 (이미 로드된 상태)
        chat_history: 이전 대화 이력 (멀티턴 지원)
        context_summary: 대화 맥락 요약

    Returns:
        EXAONE이 생성한 자연스러운 답변
    """
    context = build_mentoring_context(results)
    if not context:
        return generate_mentoring_answer_raw(question, results)

    prompt = build_mentoring_prompt(
        question, context,
        chat_history=chat_history,
        context_summary=context_summary,
    )

    logger.info("[MentoringRAG] EXAONE에 답변 생성 요청 중...")
    answer = llm.generate(
        prompt,
        max_new_tokens=1024,
        temperature=0.7,
        top_p=0.9,
    )
    logger.info("[MentoringRAG] EXAONE 답변 생성 완료")
    return answer


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
    """멘토링 RAG 전체 파이프라인을 실행합니다.

    1. KURE-v1로 질문 임베딩 (재구성된 쿼리가 있으면 사용)
    2. pgvector로 멘토링 지식 검색
    3. EXAONE LLM으로 자연스러운 답변 생성 (대화 이력 포함)

    Args:
        conn: DB 연결
        question: 사용자 원래 질문
        top_k: 검색할 최대 건수
        use_llm: LLM 사용 여부
        llm: EXAONE BaseLLM 인스턴스 (None이면 자동 로드 시도)
        chat_history: 이전 대화 이력 (멀티턴 지원)
        context_summary: 대화 맥락 요약
        rewritten_query: Query Rewriter가 재구성한 쿼리 (None이면 원래 질문 사용)

    Returns:
        { success, answer, retrieved_docs, mode, metadata }
    """
    logger.info(f"[MentoringRAG] 파이프라인 시작: '{question[:50]}...'")

    # 1) 벡터 검색 (재구성된 쿼리가 있으면 그것으로 검색)
    search_query = rewritten_query or question
    if rewritten_query and rewritten_query != question:
        logger.info(f"[MentoringRAG] 재구성된 쿼리로 검색: '{search_query[:60]}...'")

    results = search_mentoring_knowledge(conn, search_query, top_k=top_k)

    retrieved_docs = [
        f"[{r['similarity']:.1%}] {r['question']}: {r['response'][:200]}..."
        if len(r['response']) > 200 else f"[{r['similarity']:.1%}] {r['question']}: {r['response']}"
        for r in results
    ]

    # 2) 답변 생성
    answer = ""
    generation_method = "raw"

    if use_llm and results:
        # LLM 인스턴스가 제공되지 않은 경우 자동 로드 시도
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

        # EXAONE이 사용 가능하면 LLM으로 답변 생성 (대화 이력 포함)
        if llm is not None and llm.is_loaded():
            try:
                answer = generate_mentoring_answer_with_exaone(
                    question, results, llm,
                    chat_history=chat_history,
                    context_summary=context_summary,
                )
                generation_method = "exaone"
                logger.info("[MentoringRAG] EXAONE으로 답변 생성 완료")
            except Exception as e:
                logger.warning(f"[MentoringRAG] EXAONE 생성 실패, raw 모드로 폴백: {e}")
                answer = generate_mentoring_answer_raw(question, results)
                generation_method = "raw_fallback"
        else:
            # EXAONE 미로드 시 포맷팅된 답변
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
