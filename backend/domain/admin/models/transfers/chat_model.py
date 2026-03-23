"""채팅 도메인 Pydantic 모델."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """채팅 요청 모델."""

    question: str = Field(..., description="사용자의 질문", min_length=1)
    mode: str = Field(
        default="rag_openai",
        description=(
            "응답 모드: "
            "'rag' (RAG만), "
            "'openai' (OpenAI만), "
            "'rag_openai' (RAG+OpenAI), "
            "'rag_local' (RAG+로컬 LLM), "
            "'local' (로컬 LLM만), "
            "'graph' (LangGraph+로컬 midm)"
        ),
    )
    top_k: int = Field(default=3, description="검색할 문서 개수", ge=1, le=10)
    thread_id: str | None = Field(
        default=None,
        description="대화 세션 ID (graph 모드에서 대화 기록 유지용)"
    )


class KoELECTRAMeta(BaseModel):
    """KoELECTRA 1차 분류 메타데이터."""

    gateway: str | None = Field(default=None, description="게이트웨이 분류 결과 (BLOCK/POLICY_BASED/RULE_BASED)")
    confidence: float | None = Field(default=None, description="분류 신뢰도 (0.0~1.0)")
    method: str | None = Field(default=None, description="분류 방법 (koelectra_gateway/keyword_fallback)")


class ChatResponse(BaseModel):
    """채팅 응답 모델."""

    answer: str = Field(..., description="생성된 답변")
    retrieved_docs: list[str] | None = Field(
        default=None, description="검색된 문서 목록 (RAG 모드일 때만)"
    )
    mode: str = Field(..., description="사용된 응답 모드")
    top_k: int = Field(default=3, description="검색된 문서 개수")
    koelectra: KoELECTRAMeta | None = Field(
        default=None, description="KoELECTRA 1차 분류 메타데이터 (디버그용)"
    )
    generation_method: str | None = Field(
        default=None,
        description="멘토링 RAG 등: exaone | raw | raw_fallback (EXAONE 미사용/폴백 구분)",
    )


class QLoRARequest(BaseModel):
    """QLoRA 채팅 요청 모델."""

    prompt: str = Field(..., description="입력 프롬프트", min_length=1)
    max_new_tokens: int = Field(
        default=512, description="생성할 최대 토큰 수", ge=1, le=2048
    )
    temperature: float = Field(
        default=0.7, description="생성 온도", ge=0.0, le=2.0
    )
    top_p: float = Field(default=0.9, description="top-p 샘플링", ge=0.0, le=1.0)


class QLoRAResponse(BaseModel):
    """QLoRA 채팅 응답 모델."""

    response: str = Field(..., description="생성된 응답")

