"""RAG 서비스."""
from typing import Sequence

from langchain_openai import ChatOpenAI

from backend.config import settings
from backend.core.llm.base import BaseLLM


def rag_answer(question: str, retrieved_docs: Sequence[str]) -> str:
    """OpenAI 키가 없을 때 사용할 단순 RAG 스타일 응답 생성."""

    if not retrieved_docs:
        return "관련 문서를 찾지 못했습니다. 질문을 조금 더 구체적으로 해 주세요."

    summary = " / ".join(retrieved_docs)
    return (
        "다음은 검색된 문서를 기반으로 한 요약형 답변입니다.\n"
        f"- 질문: {question}\n"
        f"- 검색된 내용 요약: {summary}"
    )


def _build_rag_prompt(question: str, retrieved_docs: Sequence[str]) -> str:
    """RAG 공통 프롬프트를 생성한다."""
    context = "\n\n".join(f"- {doc}" for doc in retrieved_docs)
    return (
        f"컨텍스트:\n{context}\n\n"
        f"질문: {question}"
    )


def rag_with_llm(question: str, retrieved_docs: Sequence[str]) -> str:
    """OpenAI Chat 모델을 사용한 RAG 응답."""

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

    llm = ChatOpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY)
    prompt = _build_rag_prompt(question, retrieved_docs)
    resp = llm.invoke(prompt)
    return resp.content


def rag_with_local_llm(
    question: str, retrieved_docs: Sequence[str], llm: BaseLLM
) -> str:
    """로컬 LLM(`backend.llm`)을 사용한 RAG 응답."""

    if not retrieved_docs:
        return rag_answer(question, retrieved_docs)

    prompt = _build_rag_prompt(question, retrieved_docs)
    # BaseLLM 인터페이스에 맞게 generate 사용
    return llm.generate(prompt)


def openai_only(question: str) -> str:
    """OpenAI만 사용하는 응답 (RAG 없이)."""

    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

    llm = ChatOpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY)
    resp = llm.invoke(question)
    return resp.content


def local_only(question: str, llm: BaseLLM) -> str:
    """로컬 LLM(`backend.llm`)만 사용하는 응답 (RAG 없이)."""
    return llm.generate(question)

