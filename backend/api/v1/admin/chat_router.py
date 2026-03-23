"""채팅 라우터 (종합 라우터).

모든 요청을 ChatFlow로 전달하여 적절한 Flow로 라우팅합니다.
- exam 관련: ExamFlow로 라우팅
- 그 외: 일반 chat 처리
"""
from fastapi import APIRouter, Depends, HTTPException, Request
import psycopg

from backend.dependencies import get_db_connection, get_llm, get_qlora_service
from backend.domain.admin.models.transfers.chat_model import (
    ChatRequest,
    ChatResponse,
    KoELECTRAMeta,
    QLoRARequest,
    QLoRAResponse,
)
from backend.core.utils.database import search_similar
from backend.domain.admin.spokes.agents.retrieval import (
    local_only,
    openai_only,
    rag_answer,
    rag_with_llm,
    rag_with_local_llm,
)
from backend.config import settings
from backend.domain.admin.hub.orchestrators.chat_flow import ChatFlow

router = APIRouter(prefix="/api", tags=["chat"])

# Orchestrator 인스턴스 (싱글톤 패턴)
_chat_flow = ChatFlow()


def _extract_user_id_from_cookie(http_request: Request, conn: psycopg.Connection) -> int | None:
    """JWT 쿠키(또는 Authorization 헤더)에서 로그인된 사용자의 DB user_id를 추출한다."""
    import logging
    _logger = logging.getLogger(__name__)
    try:
        # 1) 쿠키에서 토큰 추출 (httponly 쿠키)
        token = http_request.cookies.get("Authorization")

        # 2) 폴백: Authorization 헤더에서 Bearer 토큰 추출
        if not token:
            auth_header = http_request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]

        if not token:
            _logger.warning(
                f"[ChatRouter] 쿠키/헤더에 Authorization 없음 "
                f"(cookies={list(http_request.cookies.keys())})"
            )
            return None

        from backend.api.v1.admin.auth_router import verify_jwt
        payload = verify_jwt(token)
        if not payload:
            _logger.warning("[ChatRouter] JWT 서명 검증 실패 또는 만료")
            return None
        if payload.get("type") != "access":
            _logger.warning(f"[ChatRouter] JWT type 불일치: {payload.get('type')}")
            return None

        social_id = payload.get("sub")
        if not social_id:
            _logger.warning("[ChatRouter] JWT payload에 sub(social_id) 없음")
            return None

        with conn.cursor() as cur:
            # social_accounts → users 조인 (소셜 로그인 계정 기준)
            cur.execute(
                """
                SELECT sa.user_id
                FROM social_accounts sa
                JOIN users u ON u.id = sa.user_id
                WHERE sa.social_id = %s
                LIMIT 1
                """,
                (social_id,),
            )
            row = cur.fetchone()
            # 레거시: social_accounts에 없으면 users.social_id 직접 조회
            if not row:
                cur.execute("SELECT id FROM users WHERE social_id = %s", (social_id,))
                row = cur.fetchone()
            if row:
                _logger.info(f"[ChatRouter] JWT에서 DB user_id 추출 성공: {row[0]} (social_id={social_id})")
                return row[0]
            _logger.warning(f"[ChatRouter] social_id={social_id} 에 해당하는 user 없음")
    except Exception as e:
        _logger.warning(f"[ChatRouter] user_id 추출 실패: {e}", exc_info=True)
    return None


def _generation_method_from_flow_result(flow_result: dict) -> str | None:
    """멘토링 RAG metadata.generation_method (exaone / raw / raw_fallback)."""
    meta = flow_result.get("metadata")
    if isinstance(meta, dict):
        gm = meta.get("generation_method")
        if isinstance(gm, str) and gm:
            return gm
    return None


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    http_request: Request,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> ChatResponse:
    """챗봇 엔드포인트 (종합 라우터).

    ChatFlow를 통해 요청을 분석하여 적절한 Flow로 라우팅:
    - exam 관련: ExamFlow로 라우팅
    - 그 외: 일반 chat 처리 (기존 RAG/OpenAI 로직)

    mode 옵션:
    - "rag": RAG만 사용 (규칙 기반, OpenAI 없이)
    - "openai": OpenAI만 사용 (RAG 없이)
    - "rag_openai": RAG + OpenAI (기본값)
    - "rag_local": RAG + 로컬 LLM (backend.llm)
    - "local": 로컬 LLM만 사용 (RAG 없이, backend.llm)
    - "graph": LangGraph + 로컬 midm 모델 (Agent 워크플로우)
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="질문이 비어있습니다.")

        mode = request.mode.lower()
        if mode not in ("rag", "openai", "rag_openai", "rag_local", "local", "graph"):
            raise HTTPException(
                status_code=400,
                detail='mode는 "rag", "openai", "rag_openai", "rag_local", "local", "graph" 중 하나여야 합니다.',
            )

        # EXAONE LLM 로드 (멘토링 RAG 및 로컬 LLM 모드에서 사용)
        llm = None
        try:
            llm = get_llm()
            if not llm.is_loaded():
                llm.load()
        except Exception as llm_err:
            logger.warning(f"[ChatRouter] EXAONE 로드 실패 (폴백 처리됨): {llm_err}")

        # JWT 쿠키에서 로그인된 사용자의 DB user_id 추출
        db_user_id = _extract_user_id_from_cookie(http_request, conn)

        # ChatFlow를 통해 요청 처리 (DB 연결 + EXAONE LLM을 전달하여 멘토링 RAG 사용 가능)
        logger.info(f"[ChatRouter] ChatFlow로 요청 전달: {question[:50]}... (user_id={db_user_id})")
        flow_result = await _chat_flow.process_chat_request(
            request_text=question,
            request_data={
                "question": question,
                "top_k": request.top_k,
                "thread_id": request.thread_id,
                "user_id": db_user_id,
            },
            mode=mode,
            conn=conn,
            llm=llm,
        )

        # ChatFlow 결과 확인
        result_mode = flow_result.get("mode", "chat")

        # KoELECTRA 메타데이터 추출
        koelectra_raw = flow_result.get("koelectra")
        koelectra_meta = KoELECTRAMeta(**koelectra_raw) if koelectra_raw else None
        generation_method = _generation_method_from_flow_result(flow_result)

        # BLOCK 처리 (KoELECTRA가 도메인 외 질문으로 판단)
        if result_mode == "block":
            answer = flow_result.get("answer", "공무원 시험 준비에 관한 질문을 해주세요.")
            return ChatResponse(
                answer=answer,
                retrieved_docs=None,
                mode="block",
                top_k=request.top_k,
                koelectra=koelectra_meta,
                generation_method=generation_method,
            )

        # ExamFlow에서 처리된 경우 (exam 관련 요청)
        if result_mode == "exam":
            answer = flow_result.get("answer", flow_result.get("error", "응답을 생성하지 못했습니다."))
            return ChatResponse(
                answer=answer,
                retrieved_docs=None,
                mode="exam",
                top_k=request.top_k,
                koelectra=koelectra_meta,
                generation_method=generation_method,
            )

        # 멘토링 RAG에서 처리된 경우 (합격 수기 기반 답변)
        if result_mode == "mentoring":
            answer = flow_result.get("answer", flow_result.get("error", "응답을 생성하지 못했습니다."))
            retrieved_docs = flow_result.get("retrieved_docs")
            return ChatResponse(
                answer=answer,
                retrieved_docs=retrieved_docs,
                mode="mentoring",
                top_k=request.top_k,
                koelectra=koelectra_meta,
                generation_method=generation_method,
            )

        # ChatFlow에서 답변이 생성된 경우 (study_plan, solving_log, chat 등)
        flow_answer = flow_result.get("answer")
        if flow_answer is not None:
            return ChatResponse(
                answer=flow_answer,
                retrieved_docs=flow_result.get("retrieved_docs"),
                mode=result_mode,
                top_k=request.top_k,
                koelectra=koelectra_meta,
                generation_method=generation_method,
            )

        # 일반 chat 처리 (ChatFlow에서 처리되지 않은 경우)
        # 기존 RAG/OpenAI 로직 사용
        answer: str
        retrieved_docs: list[str] | None = None

        if mode == "openai":
            # OpenAI만 사용 (RAG 없이)
            if not settings.OPENAI_API_KEY:
                raise HTTPException(
                    status_code=400,
                    detail="OPENAI_API_KEY가 설정되지 않아 OpenAI 모드를 사용할 수 없습니다.",
                )
            answer = openai_only(question)

        elif mode == "local":
            # 로컬 EXAONE LLM만 사용 (RAG 없이)
            if llm is None or not llm.is_loaded():
                raise HTTPException(
                    status_code=503,
                    detail="EXAONE 모델이 로드되지 않아 local 모드를 사용할 수 없습니다.",
                )
            answer = local_only(question, llm)

        elif mode == "graph":
            # TODO: LangGraph + 로컬 midm 모델 (verdict_agent 추후 구현 예정)
            raise HTTPException(
                status_code=501,
                detail="graph 모드는 현재 구현 예정입니다."
            )

        elif mode == "rag":
            # RAG만 사용 (규칙 기반, OpenAI 없이)
            results = search_similar(conn, question, top_k=request.top_k)
            retrieved_docs = [content for content, _ in results]
            answer = rag_answer(question, retrieved_docs)

        elif mode == "rag_openai":
            # RAG + OpenAI
            results = search_similar(conn, question, top_k=request.top_k)
            retrieved_docs = [content for content, _ in results]

            if settings.OPENAI_API_KEY:
                answer = rag_with_llm(question, retrieved_docs)
            else:
                # OpenAI 키가 없으면 RAG만 사용
                answer = rag_answer(question, retrieved_docs)

        else:  # mode == "rag_local"
            # RAG + EXAONE 로컬 LLM
            results = search_similar(conn, question, top_k=request.top_k)
            retrieved_docs = [content for content, _ in results]

            if llm is not None and llm.is_loaded():
                answer = rag_with_local_llm(question, retrieved_docs, llm)
            else:
                # EXAONE 미로드 시 RAG만으로 답변
                answer = rag_answer(question, retrieved_docs)

        return ChatResponse(
            answer=answer,
            retrieved_docs=retrieved_docs,
            mode=mode,
            top_k=request.top_k,
            koelectra=koelectra_meta,
            generation_method=None,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error(f"[ChatRouter] /chat 오류: {exc}", exc_info=True)
        print(f"[FastAPI] /chat 오류: {exc}", flush=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(exc)}")


@router.post("/chat/qlora", response_model=QLoRAResponse)
async def qlora_chat_endpoint(
    request: QLoRARequest,
    qlora_service=Depends(get_qlora_service),
) -> QLoRAResponse:
    """QLoRA 모델을 사용한 채팅 엔드포인트.

    LoRA 어댑터가 적용된 모델을 사용하여 텍스트를 생성합니다.
    """
    try:
        prompt = request.prompt.strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="프롬프트가 비어있습니다.")

        # 모델이 로드되지 않았으면 로드
        if not qlora_service.is_loaded():
            qlora_service.load()

        # 텍스트 생성
        response_text = qlora_service.generate(
            prompt=prompt,
            max_new_tokens=request.max_new_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
        )

        return QLoRAResponse(response=response_text)

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        print(f"[FastAPI] /chat/qlora 오류: {exc}", flush=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(exc)}")

