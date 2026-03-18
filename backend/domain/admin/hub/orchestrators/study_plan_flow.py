"""StudyPlan 요청 처리 Orchestrator (LangGraph 기반).

하이브리드 학습 계획 생성 파이프라인:
1. SolvingLogAnalyzer: 풀이 로그 분석 (SQL + Python)
2. UserProfile: 사용자 프로필 조회 (나이, 직장상태, 초시여부, 목표직렬, 취약/강점 과목)
3. MentoringRAG: 분석 + 프로필 기반 검색 쿼리 → 유사 환경 합격 수기 우선 매칭
4. EXAONE: 프로필 + 분석 결과 + RAG 컨텍스트 → 종합적 개인화 학습 계획 생성
5. StudyPlanService: 생성된 계획을 study_plans 테이블에 저장

테이블 구조:
- Study_Plans: user_id FK, plan_json, version
"""

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.domain.admin.models.transfers.user_transfer import (
    StudyPlanCreateRequest,
    StudyPlanUpdateRequest,
)
from backend.domain.admin.spokes.agents.analysis.solving_log_analyzer import (
    SolvingLogAnalyzer,
)
from backend.domain.admin.spokes.agents.analysis.study_plan_prompt_builder import (
    StudyPlanPromptBuilder,
)
from backend.domain.admin.spokes.agents.retrieval.mentoring_rag import (
    build_mentoring_context,
    extract_rag_sources,
    search_mentoring_knowledge,
    search_with_profile_matching,
)
from backend.domain.admin.spokes.services.study_plan_service import StudyPlanService

logger = logging.getLogger(__name__)

_LLM_GENERATION_TIMEOUT_SEC = 90
_MAX_RAG_CONTEXT_CHARS = 2500
_EXAONE_MAX_NEW_TOKENS = 120  # 최소 프롬프트 방식: 요약+전략+동기만 생성

_PLAN_NOISE_MARKERS = [
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


def _sanitize_plan_text(text: Any) -> str:
    """학습 계획 문자열에서 사이트 보일러플레이트 잡문구를 제거합니다."""
    if not isinstance(text, str):
        return ""
    cleaned = text.strip()
    if not cleaned:
        return ""

    lowered = cleaned.lower()
    cut_positions = []
    for marker in _PLAN_NOISE_MARKERS:
        idx = lowered.find(marker.lower())
        if idx >= 0:
            cut_positions.append(idx)
    if cut_positions:
        cleaned = cleaned[:min(cut_positions)].strip()

    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _sanitize_plan_payload(payload: Any) -> Any:
    """plan_json 전체를 순회하며 문자열 필드 정제를 적용합니다."""
    if isinstance(payload, dict):
        return {k: _sanitize_plan_payload(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [_sanitize_plan_payload(v) for v in payload]
    if isinstance(payload, str):
        return _sanitize_plan_text(payload)
    return payload


def _truncate_text(text: str, max_chars: int) -> str:
    """프롬프트 과대화를 막기 위해 긴 텍스트를 안전하게 절단합니다."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n...(생략)"


# ============================================================================
# State 정의
# ============================================================================

class StudyPlanProcessingState(TypedDict, total=False):
    """StudyPlan 처리 상태."""

    request_text: str
    request_data: Dict[str, Any]
    action: str  # create, read, generate
    user_id: Optional[int]
    plan_id: Optional[int]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]
    # AI 생성용
    generated_plan: Optional[Dict[str, Any]]
    analysis: Optional[Dict[str, Any]]
    rag_context: Optional[str]



# ============================================================================
# StudyPlanFlow
# ============================================================================

class StudyPlanFlow:
    """StudyPlan 요청 처리 Orchestrator (LangGraph 기반)."""

    def __init__(self):
        """초기화."""
        self._service = StudyPlanService()
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph 빌드."""
        graph = StateGraph(StudyPlanProcessingState)

        # 노드 추가
        graph.add_node("validate", self._validate_node)
        graph.add_node("determine_action", self._determine_action_node)
        graph.add_node("process_create", self._process_create_node)
        graph.add_node("process_read", self._process_read_node)
        graph.add_node("process_generate", self._process_generate_node)
        graph.add_node("process_generate_guest", self._process_generate_guest_node)
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
                "generate": "process_generate",
                "generate_guest": "process_generate_guest",
            },
        )
        graph.add_edge("process_create", "finalize")
        graph.add_edge("process_read", "finalize")
        graph.add_edge("process_generate", "finalize")
        graph.add_edge("process_generate_guest", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    async def _validate_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """데이터 검증 노드."""
        request_data = state.get("request_data", {})

        if not request_data:
            return {**state, "error": "요청 데이터가 비어있습니다."}

        # generate_guest 액션은 user_id 없이 동작
        action = request_data.get("action", "read")
        if action != "generate_guest":
            user_id = request_data.get("user_id")
            if not user_id:
                return {**state, "error": "user_id가 필요합니다."}

        return state

    async def _determine_action_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """액션 판단 노드."""
        request_data = state.get("request_data", {})
        action = request_data.get("action", "read")

        logger.info(f"[StudyPlanFlow] 액션 판단: {action}")

        return {
            **state,
            "action": action,
            "user_id": request_data.get("user_id"),
            "plan_id": request_data.get("plan_id"),
        }

    def _route_action(self, state: StudyPlanProcessingState) -> str:
        """액션에 따른 라우팅."""
        action = state.get("action", "read")
        if action in ("create", "read", "generate", "generate_guest"):
            return action
        return "read"

    async def _process_create_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """학습 계획 생성 노드 (Service 사용)."""
        request_data = state.get("request_data", {})
        user_id = state.get("user_id")

        try:
            request = StudyPlanCreateRequest(
                user_id=user_id,
                plan_json=request_data.get("plan_json", {}),
            )
            result = self._service.create_plan(request)
            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[StudyPlanFlow] 학습 계획 생성 오류: {e}", exc_info=True)
            return {
                **state,
                "result": {"success": False, "error": str(e)},
                "error": str(e),
            }

    async def _process_read_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """학습 계획 조회 노드 (Service 사용)."""
        user_id = state.get("user_id")
        plan_id = state.get("plan_id")

        try:
            if plan_id:
                result = self._service.get_plan(plan_id)
            else:
                result = self._service.get_latest_plan(user_id)

            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[StudyPlanFlow] 학습 계획 조회 오류: {e}", exc_info=True)
            return {
                **state,
                "result": {"success": False, "error": str(e)},
                "error": str(e),
            }

    async def _process_generate_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """AI 학습 계획 생성 노드 — 프로필 + 분석 + RAG + EXAONE 파이프라인.

        1단계: SolvingLogAnalyzer로 풀이 로그 분석
        2단계: 사용자 프로필 조회
        3단계: 분석 + 프로필 기반 RAG 쿼리 → 유사 환경 합격 수기 우선 매칭 검색
        4단계: 프로필 + 분석 + 상세 RAG 컨텍스트를 EXAONE 프롬프트로 조합
        5단계: EXAONE으로 종합 학습 계획 생성
        6단계: study_plans 테이블에 저장
        """
        request_data = state.get("request_data", {})
        request_text = state.get("request_text", "학습 계획을 세워줘")
        user_id = state.get("user_id")
        conn = request_data.get("_conn")
        llm = request_data.get("_llm")

        try:
            _t_total_start = time.time()

            # ============================================================
            # Step 1: 풀이 로그 분석
            # ============================================================
            analysis = {"has_data": False}
            analysis_summary = "풀이 기록이 없어 분석할 수 없습니다."

            if conn is not None:
                try:
                    _t0 = time.time()
                    analyzer = SolvingLogAnalyzer(conn)
                    analysis = analyzer.analyze(user_id)
                    analysis_summary = SolvingLogAnalyzer.summarize_for_prompt(analysis)
                    logger.info(
                        f"[StudyPlanFlow] Step1 풀이 로그 분석 완료 "
                        f"({time.time()-_t0:.1f}s): has_data={analysis.get('has_data')}"
                    )
                except Exception as e:
                    logger.warning(f"[StudyPlanFlow] 풀이 로그 분석 실패: {e}")

            # ============================================================
            # Step 2: 사용자 프로필 정보 조회
            # ============================================================
            user_info = None
            if conn is not None:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT display_name, daily_study_time, study_duration, base_score,
                                   age, employment_status, is_first_timer, target_position,
                                   weak_subjects, strong_subjects
                            FROM users WHERE id = %s
                            """,
                            (user_id,),
                        )
                        row = cur.fetchone()
                        if row:
                            weak_str = row[8]
                            strong_str = row[9]
                            user_info = {
                                "display_name": row[0],
                                "daily_study_time": row[1],
                                "study_duration": str(row[2]) if row[2] else None,
                                "base_score": row[3],
                                "age": row[4],
                                "employment_status": str(row[5]) if row[5] else None,
                                "is_first_timer": bool(row[6]) if row[6] is not None else None,
                                "target_position": str(row[7]) if row[7] else None,
                                "weak_subjects": [
                                    s.strip() for s in weak_str.split(",") if s.strip()
                                ] if weak_str else [],
                                "strong_subjects": [
                                    s.strip() for s in strong_str.split(",") if s.strip()
                                ] if strong_str else [],
                            }
                            logger.info(
                                f"[StudyPlanFlow] 사용자 프로필 조회 완료: "
                                f"name={user_info['display_name']}, "
                                f"target={user_info.get('target_position')}, "
                                f"weak={user_info.get('weak_subjects')}"
                            )
                except Exception as e:
                    logger.warning(f"[StudyPlanFlow] 사용자 정보 조회 실패: {e}")

            # ============================================================
            # Step 3: 프로필 기반 RAG 유사 환경 매칭 검색
            # ============================================================
            rag_context = ""
            matched_results = []
            rag_sources = []

            if conn is not None:
                try:
                    _t0 = time.time()
                    # 분석 결과 + 사용자 프로필 기반 검색 쿼리 생성
                    rag_queries = StudyPlanPromptBuilder.build_rag_queries_from_analysis(
                        analysis, user_info=user_info
                    )

                    # 프로필 매칭 검색: 벡터 유사도 + 환경 유사도 보너스
                    matched_results = search_with_profile_matching(
                        conn,
                        rag_queries,
                        user_info=user_info,
                        top_k_per_query=3,
                        final_top_k=4,
                        similarity_threshold=0.20,
                    )

                    # 컨텍스트를 과도하게 키우지 않도록 요약 모드 사용
                    rag_context = build_mentoring_context(
                        matched_results,
                        max_results=4,
                        include_details=False,
                    )
                    rag_context = _truncate_text(rag_context, _MAX_RAG_CONTEXT_CHARS)

                    # 출처 참조 정보 추출 (프론트엔드 표시용)
                    rag_sources = extract_rag_sources(
                        matched_results, max_results=4, user_info=user_info
                    )

                    _rag_elapsed = time.time() - _t0
                    logger.info(
                        f"[StudyPlanFlow] Step3 RAG 검색 완료 ({_rag_elapsed:.1f}s): "
                        f"{len(matched_results)}건 매칭 "
                        f"(쿼리 {len(rag_queries)}개, "
                        f"top_score={matched_results[0]['final_score']:.3f})"
                        if matched_results else
                        f"[StudyPlanFlow] RAG 검색 결과 없음 ({_rag_elapsed:.1f}s, 쿼리 {len(rag_queries)}개)"
                    )
                except Exception as e:
                    logger.warning(f"[StudyPlanFlow] RAG 검색 실패: {e}")

            # ============================================================
            # Step 4: 하이브리드 학습 계획 생성
            #   4a. 템플릿으로 전체 구조 생성 (Python, 빠르고 안정적)
            #   4b. LLM 보강:
            #       - Gemini: build_prompt()로 전체 JSON 생성 후 템플릿과 병합
            #       - EXAONE: build_summarization_prompt()로 핵심 필드만 요약
            # ============================================================
            generated_plan = self._generate_template_plan(
                analysis, user_info, matched_results
            )
            generation_method = "template"

            if llm is not None:
                _t0 = time.time()
                try:
                    if not llm.is_loaded():
                        llm.load()

                    llm_name = llm.__class__.__name__.lower()
                    is_gemini = "gemini" in llm_name

                    if is_gemini:
                        # Gemini: 상세 프롬프트로 전체 계획 JSON 생성
                        prompt = StudyPlanPromptBuilder.build_prompt(
                            analysis_summary=analysis_summary,
                            rag_context=rag_context,
                            user_question=request_text,
                            user_info=user_info,
                        )
                        max_tokens = 8192
                        logger.info(
                            f"[StudyPlanFlow] Step4 Gemini 전체 계획 생성 요청 "
                            f"(프롬프트: {len(prompt)} chars, max_tokens: {max_tokens})"
                        )
                    else:
                        # EXAONE: 경량 요약 프롬프트
                        prompt = StudyPlanPromptBuilder.build_summarization_prompt(
                            base_plan=generated_plan,
                            analysis=analysis,
                            user_info=user_info,
                        )
                        max_tokens = _EXAONE_MAX_NEW_TOKENS
                        logger.info(
                            f"[StudyPlanFlow] Step4 EXAONE 핵심 필드 생성 요청 "
                            f"(프롬프트: {len(prompt)} chars, max_tokens: {max_tokens})"
                        )

                    # 타임아웃: shutdown(wait=False)로 블로킹 방지
                    generate_kwargs: dict = {
                        "max_new_tokens": max_tokens,
                        "temperature": 0.7,
                        "top_p": 0.9,
                    }
                    if is_gemini:
                        # 신규 google.genai SDK: response_mime_type으로 순수 JSON 강제
                        generate_kwargs["response_mime_type"] = "application/json"

                    executor = ThreadPoolExecutor(max_workers=1)
                    future = executor.submit(
                        llm.generate,
                        prompt,
                        **generate_kwargs,
                    )
                    try:
                        raw_answer = future.result(timeout=_LLM_GENERATION_TIMEOUT_SEC)
                    except FuturesTimeoutError:
                        logger.warning(
                            f"[StudyPlanFlow] LLM 타임아웃({_LLM_GENERATION_TIMEOUT_SEC}s), "
                            "템플릿 유지"
                        )
                        raw_answer = ""
                    finally:
                        executor.shutdown(wait=False)

                    _gen_elapsed = time.time() - _t0
                    if not raw_answer or not raw_answer.strip():
                        logger.warning(
                            f"[StudyPlanFlow] LLM 빈 응답 ({_gen_elapsed:.1f}s), 템플릿 유지"
                        )
                    else:
                        if is_gemini:
                            parsed_plan = self._parse_plan_json(raw_answer)
                            if (
                                isinstance(parsed_plan, dict)
                                and not parsed_plan.get("parse_failed")
                            ):
                                generated_plan = self._merge_plan_with_template(
                                    generated_plan, parsed_plan
                                )
                                generation_method = "gemini_full"
                                logger.info(
                                    f"[StudyPlanFlow] Step4 Gemini 전체 계획 병합 완료 "
                                    f"({_gen_elapsed:.1f}s, {len(raw_answer)} chars)"
                                )
                            else:
                                logger.warning(
                                    f"[StudyPlanFlow] Gemini JSON 파싱 실패 "
                                    f"({_gen_elapsed:.1f}s), 템플릿 유지 "
                                    f"(총 {len(raw_answer)}chars)\n"
                                    f"head: {raw_answer[:200]!r}\n"
                                    f"tail: {raw_answer[-200:]!r}"
                                )
                        else:
                            fields = self._extract_minimal_fields(raw_answer)
                            if fields:
                                generated_plan = dict(generated_plan)

                                # [루틴] → daily_routine.description을 번호 목록 문자열로 교체
                                if "routine" in fields:
                                    bullets = fields["routine"]
                                    desc = "\n".join(
                                        f"{i+1}. {b}" for i, b in enumerate(bullets)
                                    )
                                    dr = dict(generated_plan.get("daily_routine") or {})
                                    dr["description"] = desc
                                    generated_plan["daily_routine"] = dr

                                # [어려움] → difficulty_management 리스트 교체
                                if "difficulty" in fields:
                                    generated_plan["difficulty_management"] = fields["difficulty"]

                                # [전략] → key_strategies 리스트 교체
                                if "strategy" in fields:
                                    generated_plan["key_strategies"] = fields["strategy"]

                                generation_method = "exaone_hybrid"
                                logger.info(
                                    f"[StudyPlanFlow] Step4 EXAONE 요약 병합 완료 "
                                    f"({_gen_elapsed:.1f}s, {len(raw_answer)} chars, "
                                    f"fields={list(fields.keys())})"
                                )
                            else:
                                logger.warning(
                                    f"[StudyPlanFlow] EXAONE 필드 추출 실패 "
                                    f"({_gen_elapsed:.1f}s), 템플릿(원문) 유지\n"
                                    f"raw: {raw_answer[:200]!r}"
                                )
                except Exception as e:
                    logger.warning(
                        f"[StudyPlanFlow] LLM 생성 실패 ({time.time()-_t0:.1f}s), "
                        f"템플릿 유지: {e}"
                    )

            # 최종 저장 전 안전 정제: LLM/템플릿 결과에 남은 잡문구 제거
            generated_plan = _sanitize_plan_payload(generated_plan)

            # ============================================================
            # Step 5: 기존 학습 계획 전체 삭제 후 새로 저장
            # ============================================================
            delete_result = self._service.delete_user_plans(user_id)
            if delete_result.get("success"):
                deleted_count = delete_result.get("deleted_count", 0)
                if deleted_count > 0:
                    logger.info(
                        f"[StudyPlanFlow] 기존 학습 계획 {deleted_count}건 삭제 완료"
                    )

            plan_data = {
                **generated_plan,
                "generated_by": generation_method,
                "analysis_summary": analysis_summary if analysis.get("has_data") else None,
                "rag_results_count": len(matched_results),
                "rag_sources": rag_sources,
                "user_profile_applied": bool(user_info),
                "user_profile_summary": (
                    self._build_profile_summary(user_info) if user_info else None
                ),
            }

            request = StudyPlanCreateRequest(
                user_id=user_id,
                plan_json=plan_data,
            )
            result = self._service.create_plan(request)

            if result.get("success"):
                _total_elapsed = time.time() - _t_total_start
                result["message"] = (
                    f"AI 학습 계획이 생성되었습니다. "
                    f"(방식: {generation_method}, 소요: {_total_elapsed:.1f}초)"
                )
                logger.info(
                    f"[StudyPlanFlow] 전체 파이프라인 완료: {_total_elapsed:.1f}s "
                    f"(방식: {generation_method})"
                )

            # 응답에 분석 요약 및 RAG 출처 포함
            result["analysis"] = analysis if analysis.get("has_data") else None
            result["generation_method"] = generation_method
            result["rag_sources"] = rag_sources

            return {
                **state,
                "result": result,
                "generated_plan": generated_plan,
                "analysis": analysis,
                "rag_context": rag_context,
            }

        except Exception as e:
            logger.error(
                f"[StudyPlanFlow] AI 학습 계획 생성 오류: {e}", exc_info=True
            )
            return {
                **state,
                "result": {"success": False, "error": str(e)},
                "error": str(e),
            }

    # ========================================================================
    # 유틸 메서드
    # ========================================================================

    def _build_profile_summary(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """프론트엔드 표시용 사용자 프로필 요약을 생성합니다."""
        summary = {}
        if user_info.get("display_name"):
            summary["name"] = user_info["display_name"]
        if user_info.get("age"):
            summary["age"] = user_info["age"]
        if user_info.get("employment_status"):
            summary["employment_status"] = user_info["employment_status"]
        if user_info.get("is_first_timer") is not None:
            summary["is_first_timer"] = user_info["is_first_timer"]
        if user_info.get("target_position"):
            summary["target_position"] = user_info["target_position"]
        if user_info.get("weak_subjects"):
            summary["weak_subjects"] = user_info["weak_subjects"]
        if user_info.get("strong_subjects"):
            summary["strong_subjects"] = user_info["strong_subjects"]
        if user_info.get("daily_study_time"):
            summary["daily_study_time"] = user_info["daily_study_time"]
        if user_info.get("study_duration"):
            summary["study_duration"] = user_info["study_duration"]
        return summary

    def _merge_plan_with_template(
        self,
        base_plan: Dict[str, Any],
        generated_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """LLM 생성 계획을 템플릿 구조에 안전하게 병합합니다.

        - 기본 키 누락 방지: base_plan 키를 유지
        - daily_routine은 dict 단위로 부분 병합
        - list/dict/str 타입이 맞는 경우에만 덮어씀
        """
        merged = dict(base_plan)

        for key, value in generated_plan.items():
            if value is None:
                continue

            if key == "daily_routine":
                base_daily = merged.get("daily_routine", {})
                if isinstance(base_daily, dict) and isinstance(value, dict):
                    daily_merged = dict(base_daily)
                    for dk, dv in value.items():
                        if dv not in (None, ""):
                            daily_merged[dk] = dv
                    merged["daily_routine"] = daily_merged
                continue

            if key in merged:
                if isinstance(merged[key], list) and isinstance(value, list) and value:
                    merged[key] = value
                elif isinstance(merged[key], dict) and isinstance(value, dict) and value:
                    merged[key] = value
                elif isinstance(merged[key], str) and isinstance(value, str) and value.strip():
                    merged[key] = value
                elif not isinstance(merged[key], (list, dict, str)):
                    merged[key] = value

        return merged

    def _extract_minimal_fields(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """EXAONE 요약 응답에서 태그별 bullet 목록을 추출합니다.

        [루틴] 1. ... 2. ... / [어려움] 1. ... / [전략] 1. ... 형식을 파싱합니다.
        최소 1개 필드라도 추출되면 성공으로 간주합니다.
        """
        if not raw_text:
            return None

        tag_map = {
            "routine": r"\[루틴\]",
            "difficulty": r"\[어려움\]",
            "strategy": r"\[전략\]",
        }

        # 각 태그의 위치를 찾아 사이의 텍스트 추출
        tag_positions: List[tuple] = []
        for field_key, pattern in tag_map.items():
            m = re.search(pattern, raw_text)
            if m:
                tag_positions.append((m.start(), m.end(), field_key))

        if not tag_positions:
            return None

        tag_positions.sort(key=lambda x: x[0])
        fields: Dict[str, Any] = {}

        for i, (start, end, field_key) in enumerate(tag_positions):
            next_start = (
                tag_positions[i + 1][0] if i + 1 < len(tag_positions) else len(raw_text)
            )
            block = raw_text[end:next_start].strip()

            # "1. 항목 2. 항목" 또는 "1. 항목\n2. 항목" 모두 파싱
            items = re.findall(r"\d+\.\s*(.+?)(?=\d+\.|$)", block, re.DOTALL)
            bullets = []
            for item in items:
                item = re.sub(r"\*+", "", item)
                item = item.strip().rstrip(".")
                if len(item) >= 5:
                    bullets.append(item)

            if bullets:
                fields[field_key] = bullets

        return fields if fields else None

    def _parse_plan_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """LLM 응답에서 JSON 학습 계획을 파싱합니다.

        단계별 파싱 전략:
        1. 직접 json.loads
        2. ```json ... ``` 코드블록 추출 (greedy → 중첩 {} 처리)
        3. 첫 { ~ 마지막 } 추출
        4. 각 단계 실패 시 JSON repair (후행 쉼표·스마트 따옴표 제거) 후 재시도
        """
        def _try_loads(text: str) -> Optional[Dict[str, Any]]:
            try:
                result = json.loads(text)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                pass
            return None

        def _repair(text: str) -> str:
            """최소한의 JSON 문법 보정."""
            # 후행 쉼표 제거: , } 또는 , ]
            text = re.sub(r",\s*([}\]])", r"\1", text)
            # 스마트 따옴표 → 일반 따옴표
            for ch, rep in [("\u201c", '"'), ("\u201d", '"'),
                             ("\u2018", "'"), ("\u2019", "'")]:
                text = text.replace(ch, rep)
            # 불필요한 제어 문자 제거 (탭·개행 제외)
            text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
            return text

        def _try_with_repair(text: str) -> Optional[Dict[str, Any]]:
            result = _try_loads(text)
            if result is not None:
                return result
            return _try_loads(_repair(text))

        # Step 1: 직접 파싱
        result = _try_with_repair(raw_text)
        if result is not None:
            return result

        # Step 2: ```json ... ``` 코드블록 추출 — greedy 매칭으로 마지막 ``` 까지
        code_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", raw_text)
        if code_match:
            result = _try_with_repair(code_match.group(1))
            if result is not None:
                return result

        # Step 3: 첫 { ~ 마지막 } 직접 추출
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end > start:
            result = _try_with_repair(raw_text[start:end + 1])
            if result is not None:
                return result

        logger.warning("[StudyPlanFlow] JSON 파싱 실패, 텍스트 형태로 저장")
        return {
            "raw_answer": raw_text,
            "summary": raw_text[:500],
            "parse_failed": True,
        }

    def _generate_template_plan(
        self,
        analysis: Dict[str, Any],
        user_info: Optional[Dict[str, Any]] = None,
        matched_stories: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """분석 데이터 + 사용자 프로필 + 매칭된 합격 수기 기반 템플릿 학습 계획.

        EXAONE이 사용 불가능할 때의 폴백입니다.
        합격 수기 데이터가 있으면 과목별 학습법/일일 루틴 등을 추출하여 포함합니다.
        """
        daily_minutes = 180  # 기본 3시간
        if user_info and user_info.get("daily_study_time"):
            daily_minutes = user_info["daily_study_time"]

        hours = daily_minutes / 60
        matched_stories = matched_stories or []

        # ── 과목 우선순위 결정 ──
        weak = analysis.get("weak_subjects", [])
        strong = analysis.get("strong_subjects", [])
        weak_names = [w["subject"] for w in weak]
        strong_names = [s["subject"] for s in strong]
        all_subjects = list({s["subject"] for s in analysis.get("subject_stats", [])})

        # 사용자 자가진단 병합
        user_weak = []
        user_strong = []
        if user_info:
            user_weak = user_info.get("weak_subjects", []) or []
            user_strong = user_info.get("strong_subjects", []) or []
            for subj in user_weak:
                if subj not in weak_names:
                    weak_names.append(subj)
                if subj not in all_subjects:
                    all_subjects.append(subj)
            for subj in user_strong:
                if subj not in strong_names:
                    strong_names.append(subj)
                if subj not in all_subjects:
                    all_subjects.append(subj)

        # 과목이 없으면 기본 과목 (목표 직렬 반영)
        if not all_subjects:
            target_pos = user_info.get("target_position") if user_info else None
            if target_pos == "일반행정":
                all_subjects = ["한국사", "행정법", "행정학", "국어", "영어"]
            elif target_pos == "세무":
                all_subjects = ["한국사", "세법", "회계학", "국어", "영어"]
            elif target_pos == "교육행정":
                all_subjects = ["한국사", "교육학", "행정법", "국어", "영어"]
            else:
                all_subjects = ["한국사", "행정법", "행정학", "국어", "영어"]
            weak_names = weak_names or all_subjects[:2]

        # ── 합격 수기에서 과목별 학습법 추출 ──
        story_methods: Dict[str, List[str]] = {}
        story_daily_plans: List[str] = []
        story_difficulties: List[str] = []
        story_key_points: List[str] = []

        for idx, story in enumerate(matched_stories, 1):
            # 과목별 학습법 — 원문 전체 포함
            sm = story.get("subject_methods") or {}
            if isinstance(sm, dict):
                for subj, method in sm.items():
                    if method and isinstance(method, str) and len(method.strip()) > 10:
                        m = method.strip()
                        if subj not in story_methods:
                            story_methods[subj] = []
                        story_methods[subj].append(
                            f"(합격 수기 {idx}) {m}"
                        )

            # 일일 계획 — 원문 전체 포함
            if story.get("daily_plan"):
                dp = story["daily_plan"].strip()
                story_daily_plans.append(f"(합격 수기 {idx}) {dp}")

            # 어려움 — 원문 전체 포함
            if story.get("difficulties"):
                diff = story["difficulties"].strip()
                story_difficulties.append(f"(합격 수기 {idx}) {diff}")

            # 핵심 전략 — 원문 전체 포함
            if story.get("key_points"):
                kp = story["key_points"].strip()
                story_key_points.append(f"(합격 수기 {idx}) {kp}")

        # ── subject_plans 생성 ──
        subject_plans = []
        for subj in all_subjects[:7]:
            is_weak = subj in weak_names
            is_strong = subj in strong_names

            # 분석 데이터에서 정답률
            subj_stat = next(
                (s for s in analysis.get("subject_stats", []) if s["subject"] == subj),
                None,
            )
            current_level = "미측정"
            if subj_stat:
                acc = subj_stat["accuracy"]
                if acc >= 80:
                    current_level = f"우수 ({acc:.0f}%)"
                elif acc >= 60:
                    current_level = f"보통 ({acc:.0f}%)"
                elif acc >= 40:
                    current_level = f"취약 ({acc:.0f}%)"
                else:
                    current_level = f"매우 취약 ({acc:.0f}%)"

            # 합격 수기에서 해당 과목의 학습법
            methods_from_stories = story_methods.get(subj, [])
            strategy = ""
            if methods_from_stories:
                strategy = methods_from_stories[0]  # 가장 첫번째
            elif is_weak:
                strategy = "기초 개념부터 다시 학습하고, 기출문제를 반복 풀이하세요."
            else:
                strategy = "현재 수준을 유지하면서 실전 연습에 집중하세요."

            subject_plans.append({
                "subject": subj,
                "current_level": current_level,
                "strategy": strategy,
                "recommended_materials": (
                    "기출문제 반복 풀이 + 오답노트 정리" if is_weak else "실전 모의고사 위주"
                ),
                "weekly_hours": round(hours * 0.25 if is_weak else hours * 0.15, 1),
                "priority": "높음" if is_weak else ("유지" if is_strong else "보통"),
            })

        # ── daily_routine 생성 ──
        is_employed = False
        if user_info and user_info.get("employment_status") in (
            "EMPLOYED", "재직", "employed"
        ):
            is_employed = True

        if is_employed:
            daily_routine = {
                "description": (
                    "직장인을 위한 효율적인 학습 루틴입니다. "
                    + (story_daily_plans[0] if story_daily_plans else "출퇴근 시간을 최대한 활용하세요.")
                ),
                "morning": "06:00-07:30 출근 전 취약과목 이론 학습 (1.5시간)",
                "afternoon": "12:00-13:00 점심시간 암기과목/단문제 풀이 (1시간)",
                "evening": "19:30-22:00 퇴근 후 기출문제 풀이 + 오답 정리 (2.5시간)",
                "review": "22:00-22:30 하루 학습 내용 복습 및 다음 날 계획 (30분)",
            }
        else:
            daily_routine = {
                "description": (
                    "전업 수험생을 위한 집중 학습 루틴입니다. "
                    + (story_daily_plans[0] if story_daily_plans else "")
                ),
                "morning": "07:00-12:00 취약과목 집중 학습 + 이론 정리 (5시간)",
                "afternoon": "13:00-17:00 기출문제 풀이 + 오답 분석 (4시간)",
                "evening": "19:00-21:00 모의고사/실전 연습 (2시간)",
                "review": "21:00-22:00 하루 복습 + 오답노트 정리 (1시간)",
            }

        # ── weekly_schedule ──
        schedule = []
        days = ["월", "화", "수", "목", "금", "토", "일"]

        for i, day in enumerate(days):
            if day == "토":
                schedule.append({
                    "day": day,
                    "subjects": ["모의고사"],
                    "focus": "실전 연습 및 시간 관리 훈련",
                    "hours": round(hours + 1, 1),
                })
            elif day == "일":
                schedule.append({
                    "day": day,
                    "subjects": ["복습", "오답정리"],
                    "focus": "주간 오답 복습 및 개념 정리",
                    "hours": round(hours * 0.7, 1),
                })
            else:
                day_subjects = []
                if weak_names:
                    day_subjects.append(weak_names[i % len(weak_names)])
                remaining = [s for s in all_subjects if s not in day_subjects]
                if remaining:
                    day_subjects.append(remaining[i % len(remaining)])

                focus = (
                    "취약 과목 집중 보강" if day_subjects[0] in weak_names
                    else "균형 학습"
                )
                day_hours = (
                    round(hours * 0.7, 1) if is_employed else round(hours, 1)
                )
                schedule.append({
                    "day": day,
                    "subjects": day_subjects[:2],
                    "focus": focus,
                    "hours": day_hours,
                })

        # ── study_methods (합격 수기 기반) ──
        study_methods = []
        for subj, methods_list in list(story_methods.items())[:5]:
            if methods_list:
                study_methods.append({
                    "method": f"{subj} 학습법",
                    "description": methods_list[0],
                    "source_story": f"합격 수기",
                })

        # ── difficulty_management ──
        difficulty_management = []
        if story_difficulties:
            for diff in story_difficulties[:3]:
                difficulty_management.append(diff)
        else:
            difficulty_management = [
                "슬럼프가 올 때는 무리하지 말고 가벼운 복습으로 학습 리듬을 유지하세요.",
                "모의고사 점수에 일희일비하지 말고, 틀린 문제의 원인 분석에 집중하세요.",
            ]

        # ── key_strategies ──
        key_strategies = []
        if story_key_points:
            for kp in story_key_points[:3]:
                key_strategies.append(kp)
        else:
            key_strategies = [
                "기출문제를 최소 3회독 하세요. 회독할수록 출제 패턴이 보입니다.",
                "오답노트를 매일 정리하고 주간 복습에 활용하세요.",
            ]

        # ── specific_advice (개인화) ──
        recommendations = []

        if user_info:
            is_first = user_info.get("is_first_timer")
            target_pos = user_info.get("target_position")

            if is_first is True:
                recommendations.append(
                    "초시생이므로 기본 개념 습득에 충분한 시간을 투자하세요. "
                    "이론서를 먼저 완독한 뒤 문제풀이로 넘어가는 것을 권장합니다."
                )
            elif is_first is False:
                recommendations.append(
                    "재시생이므로 이미 학습한 내용의 취약 부분 보완에 집중하세요. "
                    "기출문제 회독 횟수를 늘리고 실전 감각을 유지하세요."
                )

            if is_employed:
                recommendations.append(
                    "직장인이므로 출퇴근 시간에 오디오 강의나 암기 과목을 활용하고, "
                    "점심시간에 단문제 풀이를 진행하면 효율적입니다."
                )

            if target_pos:
                recommendations.append(
                    f"목표 직렬({target_pos})의 필수 과목을 최우선으로 학습하세요."
                )

        if weak_names:
            recommendations.append(
                f"취약 과목({', '.join(weak_names[:5])})에 학습 시간을 더 배분하세요."
            )

        repeated = analysis.get("repeated_wrong", [])
        if repeated:
            rep_subjects = list({rw["subject"] for rw in repeated[:3]})
            recommendations.append(
                f"반복 오답 과목({', '.join(rep_subjects)})의 기본 개념을 다시 점검하세요."
            )

        if not recommendations:
            recommendations = [
                "매일 일정한 시간에 학습하세요.",
                "약점 과목을 집중적으로 보완하세요.",
                "주 1회 모의고사를 통해 실전 감각을 유지하세요.",
            ]

        # ── matched_stories_analysis ──
        matched_analysis = ""
        if matched_stories:
            from backend.domain.admin.spokes.agents.retrieval.mentoring_rag import (
                _format_exam_title,
            )
            story_titles = [
                _format_exam_title(s.get("exam_info", {}))
                for s in matched_stories[:3]
            ]
            matched_analysis = (
                f"사용자와 유사한 환경의 합격자 {len(matched_stories)}명의 수기를 분석했습니다. "
                f"({', '.join(story_titles)}). "
                "이들의 학습법과 전략을 바탕으로 계획을 수립했습니다."
            )

        return {
            "summary": self._generate_template_summary(analysis, user_info),
            "matched_stories_analysis": matched_analysis,
            "priority_subjects": weak_names if weak_names else all_subjects[:3],
            "subject_plans": subject_plans,
            "daily_routine": daily_routine,
            "weekly_schedule": schedule,
            "study_methods": study_methods,
            "difficulty_management": difficulty_management,
            "key_strategies": key_strategies,
            "specific_advice": recommendations,
            "motivation": "꾸준히 노력하면 반드시 합격할 수 있습니다. 화이팅! 💪",
            "user_profile_applied": bool(user_info),
        }

    def _generate_template_summary(
        self,
        analysis: Dict[str, Any],
        user_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """분석 통계 데이터 + 사용자 프로필 기반 서술형 요약을 생성합니다."""
        from backend.domain.admin.spokes.agents.analysis.study_plan_prompt_builder import (
            _EMP_LABEL_MAP,
        )

        # ── 프로필 서술 ──
        profile_desc = ""
        if user_info:
            parts = []
            pos = user_info.get("target_position", "")
            is_first = user_info.get("is_first_timer")
            emp = user_info.get("employment_status", "")
            emp_label = _EMP_LABEL_MAP.get(emp, emp) if emp else ""

            if pos:
                timer_str = "초시생" if is_first else "재시생" if is_first is False else "수험생"
                emp_str = f" {emp_label}" if emp_label else ""
                parts.append(f"{pos} 직렬을 목표로 하는{emp_str} {timer_str}")

            if user_info.get("study_duration"):
                parts.append(f"수험 기간은 {user_info['study_duration']}")
            if user_info.get("daily_study_time"):
                h = user_info["daily_study_time"] / 60
                parts.append(f"일일 학습 가능 시간은 {h:.1f}시간")

            profile_desc = ", ".join(parts) + "입니다." if parts else ""

        # ── 풀이 데이터 없는 경우 ──
        if not analysis.get("has_data"):
            if profile_desc:
                return (
                    f"{profile_desc} "
                    "아직 풀이 기록이 없어 사용자 프로필과 유사 환경 합격자 수기를 "
                    "바탕으로 학습 계획을 수립했습니다."
                )
            return "아직 풀이 기록이 없습니다. 모의고사를 풀고 나면 맞춤 분석이 가능합니다."

        # ── 통계 데이터 서술 ──
        acc = analysis.get("overall_accuracy", 0)
        total = analysis.get("total_solved", 0)
        weak = analysis.get("weak_subjects", [])
        strong = analysis.get("strong_subjects", [])

        sentences: List[str] = []

        # 첫 문장: 프로필 + 성적 현황
        if profile_desc:
            profile_base = profile_desc.rstrip("입니다.").rstrip(".")
            sentences.append(
                f"{profile_base}으로, 총 {total}문제를 풀어 "
                f"전체 정답률 {acc:.1f}%를 기록했습니다."
            )
        else:
            sentences.append(
                f"총 {total}문제를 풀었고, 전체 정답률은 {acc:.1f}%입니다."
            )

        # 두 번째 문장: 취약·강점 과목
        weak_strs = [f"{w['subject']}({w['accuracy']:.0f}%)" for w in weak[:3]]
        strong_strs = [f"{s['subject']}({s['accuracy']:.0f}%)" for s in strong[:2]]
        if weak_strs and strong_strs:
            sentences.append(
                f"분석 결과 {', '.join(weak_strs)} 과목이 취약하며, "
                f"{', '.join(strong_strs)} 과목은 상대적으로 안정적입니다."
            )
        elif weak_strs:
            sentences.append(
                f"분석 결과 {', '.join(weak_strs)} 과목이 취약한 것으로 나타났습니다."
            )

        # 세 번째 문장: 자가진단 일치 여부
        if user_info and user_info.get("weak_subjects") and weak:
            analysis_weak_set = {w["subject"] for w in weak}
            user_weak_set = set(user_info.get("weak_subjects", []))
            overlap = analysis_weak_set & user_weak_set
            if overlap:
                sentences.append(
                    f"특히 {', '.join(overlap)} 과목은 자가진단과 실제 분석 모두에서 "
                    "취약점으로 확인되어 집중 보강이 필요합니다."
                )

        # 마지막 문장: 학습 방향 제시
        if acc >= 80:
            sentences.append(
                "전반적으로 높은 정답률을 보이고 있으므로, "
                "실전 모의고사 위주로 실력을 마무리하는 전략을 권장합니다."
            )
        elif acc >= 60:
            sentences.append(
                "기본기는 갖춰진 수준이므로, 취약 과목 집중 보강과 함께 "
                "오답 분석을 통해 합격선까지 끌어올리는 것이 목표입니다."
            )
        elif acc >= 40:
            sentences.append(
                "기초 개념 학습과 기출문제 반복 풀이에 집중하여 "
                "전체 정답률을 60% 이상으로 끌어올리는 것을 목표로 삼으세요."
            )
        else:
            sentences.append(
                "현재 기초 단계에 해당하므로, 개념 학습을 최우선으로 하고 "
                "오답 복습을 꾸준히 병행하여 실력을 쌓아가세요."
            )

        return " ".join(sentences)

    async def _process_generate_guest_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """게스트 AI 학습 계획 생성 노드 — DB 미저장, 프로필+로그 직접 수신.

        1단계: 전달된 guest_analysis 사용 (DB 조회 없음)
        2단계: 전달된 guest_profile 사용 (DB 조회 없음)
        3단계: 프로필 기반 RAG 검색 (벡터 DB는 사용)
        4단계: LLM/템플릿 학습 계획 생성
        5단계: DB 저장 생략 → 결과만 반환
        """
        request_data = state.get("request_data", {})
        request_text = state.get("request_text", "학습 계획을 세워줘")
        conn = request_data.get("_conn")
        llm = request_data.get("_llm")
        guest_profile_raw = request_data.get("guest_profile") or {}
        guest_analysis = request_data.get("guest_analysis") or {"has_data": False}

        try:
            _t_total_start = time.time()

            # ── Step 1: 게스트 분석 사용 ──
            analysis = guest_analysis
            analysis_summary = SolvingLogAnalyzer.summarize_for_prompt(analysis) if analysis.get("has_data") else "풀이 기록이 없어 분석할 수 없습니다."

            # ── Step 2: 게스트 프로필 변환 ──
            def _str_or_none(v):
                return str(v) if v is not None else None

            weak_raw = guest_profile_raw.get("weak_subjects") or ""
            strong_raw = guest_profile_raw.get("strong_subjects") or ""
            user_info = {
                "display_name": "게스트",
                "daily_study_time": guest_profile_raw.get("daily_study_time"),
                "study_duration": _str_or_none(guest_profile_raw.get("study_duration")),
                "base_score": guest_profile_raw.get("base_score"),
                "age": guest_profile_raw.get("age"),
                "employment_status": _str_or_none(guest_profile_raw.get("employment_status")),
                "is_first_timer": guest_profile_raw.get("is_first_timer"),
                "target_position": _str_or_none(guest_profile_raw.get("target_position")),
                "weak_subjects": [s.strip() for s in str(weak_raw).split(",") if s.strip()] if weak_raw else [],
                "strong_subjects": [s.strip() for s in str(strong_raw).split(",") if s.strip()] if strong_raw else [],
            }
            has_profile = bool(
                user_info.get("target_position") or user_info.get("employment_status")
                or user_info.get("study_duration") or user_info.get("weak_subjects")
            )
            if not has_profile:
                user_info = None

            logger.info(f"[StudyPlanFlow-Guest] 프로필: {user_info}")

            # ── Step 3: RAG 검색 ──
            rag_context = ""
            matched_results = []
            rag_sources = []
            if conn is not None:
                try:
                    rag_queries = StudyPlanPromptBuilder.build_rag_queries_from_analysis(
                        analysis, user_info=user_info
                    )
                    matched_results = search_with_profile_matching(
                        conn, rag_queries, user_info=user_info,
                        top_k_per_query=3, final_top_k=4, similarity_threshold=0.20,
                    )
                    rag_context = build_mentoring_context(matched_results, max_results=4, include_details=False)
                    rag_context = _truncate_text(rag_context, _MAX_RAG_CONTEXT_CHARS)
                    rag_sources = extract_rag_sources(matched_results, max_results=4, user_info=user_info)
                    logger.info(f"[StudyPlanFlow-Guest] RAG {len(matched_results)}건 매칭")
                except Exception as e:
                    logger.warning(f"[StudyPlanFlow-Guest] RAG 검색 실패: {e}")

            # ── Step 4: 학습 계획 생성 (LLM 또는 템플릿) ──
            generated_plan = self._generate_template_plan(analysis, user_info, matched_results)
            generation_method = "template"

            if llm is not None:
                try:
                    if not llm.is_loaded():
                        llm.load()
                    llm_name = llm.__class__.__name__.lower()
                    is_gemini = "gemini" in llm_name
                    if is_gemini:
                        prompt = StudyPlanPromptBuilder.build_prompt(
                            analysis_summary=analysis_summary,
                            rag_context=rag_context,
                            user_question=request_text,
                            user_info=user_info,
                        )
                        generate_kwargs: dict = {
                            "max_new_tokens": 8192,
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "response_mime_type": "application/json",
                        }
                    else:
                        prompt = StudyPlanPromptBuilder.build_summarization_prompt(
                            base_plan=generated_plan, analysis=analysis, user_info=user_info,
                        )
                        generate_kwargs = {
                            "max_new_tokens": _EXAONE_MAX_NEW_TOKENS,
                            "temperature": 0.7,
                            "top_p": 0.9,
                        }

                    executor = ThreadPoolExecutor(max_workers=1)
                    future = executor.submit(llm.generate, prompt, **generate_kwargs)
                    try:
                        raw_answer = future.result(timeout=_LLM_GENERATION_TIMEOUT_SEC)
                    except FuturesTimeoutError:
                        raw_answer = ""
                    finally:
                        executor.shutdown(wait=False)

                    if raw_answer and raw_answer.strip() and is_gemini:
                        parsed_plan = self._parse_plan_json(raw_answer)
                        if isinstance(parsed_plan, dict) and not parsed_plan.get("parse_failed"):
                            generated_plan = self._merge_plan_with_template(generated_plan, parsed_plan)
                            generation_method = "gemini_full"
                            logger.info(f"[StudyPlanFlow-Guest] Gemini 계획 병합 완료")
                except Exception as e:
                    logger.warning(f"[StudyPlanFlow-Guest] LLM 생성 실패, 템플릿 유지: {e}")

            generated_plan = _sanitize_plan_payload(generated_plan)

            # ── Step 5: DB 저장 없이 결과 반환 ──
            plan_data = {
                **generated_plan,
                "generated_by": generation_method,
                "analysis_summary": analysis_summary if analysis.get("has_data") else None,
                "rag_results_count": len(matched_results),
                "rag_sources": rag_sources,
                "user_profile_applied": bool(user_info),
                "user_profile_summary": (self._build_profile_summary(user_info) if user_info else None),
            }

            _total_elapsed = time.time() - _t_total_start
            result = {
                "success": True,
                "message": f"게스트 AI 학습 계획이 생성되었습니다. (방식: {generation_method}, 소요: {_total_elapsed:.1f}초)",
                "plan_json": plan_data,
                "analysis": analysis if analysis.get("has_data") else None,
                "generation_method": generation_method,
                "rag_sources": rag_sources,
            }
            logger.info(f"[StudyPlanFlow-Guest] 완료: {_total_elapsed:.1f}s ({generation_method})")

            return {**state, "result": result, "generated_plan": generated_plan, "analysis": analysis, "rag_context": rag_context}

        except Exception as e:
            logger.error(f"[StudyPlanFlow-Guest] 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _finalize_node(
        self, state: StudyPlanProcessingState
    ) -> StudyPlanProcessingState:
        """최종 정리 노드."""
        return state

    async def process_study_plan_request(
        self, request_text: str, request_data: dict
    ) -> dict:
        """StudyPlan 요청 처리.

        Args:
            request_text: 요청 텍스트
            request_data: 요청 데이터 (action, user_id, plan_id, _conn, _llm 등)

        Returns:
            처리 결과 딕셔너리
        """
        logger.info("[StudyPlanFlow] 요청 처리 시작")

        initial_state: StudyPlanProcessingState = {
            "request_text": request_text,
            "request_data": request_data,
            "action": None,
            "user_id": None,
            "plan_id": None,
            "result": None,
            "error": None,
            "metadata": None,
            "generated_plan": None,
            "analysis": None,
            "rag_context": None,
        }

        try:
            final_state = await self._graph.ainvoke(initial_state)
            result = final_state.get("result")
            return (
                result
                if result
                else {"success": False, "error": "처리 결과가 없습니다."}
            )
        except Exception as e:
            logger.error(f"[StudyPlanFlow] 처리 오류: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
