"""AudioNote 요청 처리 Orchestrator (LangGraph 기반).

새 테이블 구조:
- Audio_Notes: commentary_id FK, file_path, voice_type, duration

LangGraph StateGraph로 구현:
- TTS 오디오 생성/조회/관리 워크플로우
- AudioNoteService를 통한 데이터 처리
"""

import logging
from typing import Dict, Any, Optional, TypedDict, List

from langgraph.graph import StateGraph, END, START

from backend.domain.admin.spokes.services.audio_note_service import AudioNoteService
from backend.domain.admin.models.transfers.commentary_transfer import (
    AudioNoteCreateRequest,
)

logger = logging.getLogger(__name__)


# ============================================================================
# State 정의
# ============================================================================

class AudioNoteProcessingState(TypedDict, total=False):
    """AudioNote 처리 상태."""
    request_text: str
    request_data: Dict[str, Any]
    action: str  # create, read, list, delete, generate_tts
    audio_id: Optional[int]
    commentary_id: Optional[int]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]
    # TTS 생성용
    generated_file_path: Optional[str]


# ============================================================================
# AudioNoteFlow
# ============================================================================

class AudioNoteFlow:
    """AudioNote 요청 처리 Orchestrator (LangGraph 기반)."""

    def __init__(self):
        """초기화."""
        self._service = AudioNoteService()
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph 빌드."""
        graph = StateGraph(AudioNoteProcessingState)

        # 노드 추가
        graph.add_node("validate", self._validate_node)
        graph.add_node("determine_action", self._determine_action_node)
        graph.add_node("process_create", self._process_create_node)
        graph.add_node("process_read", self._process_read_node)
        graph.add_node("process_list", self._process_list_node)
        graph.add_node("process_delete", self._process_delete_node)
        graph.add_node("process_generate_tts", self._process_generate_tts_node)
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
                "list": "process_list",
                "delete": "process_delete",
                "generate_tts": "process_generate_tts",
            }
        )
        graph.add_edge("process_create", "finalize")
        graph.add_edge("process_read", "finalize")
        graph.add_edge("process_list", "finalize")
        graph.add_edge("process_delete", "finalize")
        graph.add_edge("process_generate_tts", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    async def _validate_node(self, state: AudioNoteProcessingState) -> AudioNoteProcessingState:
        """데이터 검증 노드."""
        request_data = state.get("request_data", {})

        if not request_data:
            return {**state, "error": "요청 데이터가 비어있습니다."}

        return state

    async def _determine_action_node(self, state: AudioNoteProcessingState) -> AudioNoteProcessingState:
        """액션 판단 노드."""
        request_data = state.get("request_data", {})
        action = request_data.get("action", "list")

        logger.info(f"[AudioNoteFlow] 액션 판단: {action}")

        return {
            **state,
            "action": action,
            "audio_id": request_data.get("audio_id"),
            "commentary_id": request_data.get("commentary_id"),
        }

    def _route_action(self, state: AudioNoteProcessingState) -> str:
        """액션에 따른 라우팅."""
        action = state.get("action", "list")
        if action in ("create", "read", "list", "delete", "generate_tts"):
            return action
        return "list"

    async def _process_create_node(self, state: AudioNoteProcessingState) -> AudioNoteProcessingState:
        """오디오 노트 생성 노드 (Service 사용)."""
        request_data = state.get("request_data", {})

        try:
            request = AudioNoteCreateRequest(
                commentary_id=request_data.get("commentary_id"),
                file_path=request_data.get("file_path", ""),
                voice_type=request_data.get("voice_type", "female"),
                duration=request_data.get("duration"),
            )
            result = self._service.create_audio(request)
            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[AudioNoteFlow] 오디오 노트 생성 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _process_read_node(self, state: AudioNoteProcessingState) -> AudioNoteProcessingState:
        """오디오 노트 조회 노드 (Service 사용)."""
        audio_id = state.get("audio_id")

        try:
            if not audio_id:
                return {**state, "result": {"success": False, "error": "audio_id가 필요합니다."}}

            result = self._service.get_audio(audio_id)
            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[AudioNoteFlow] 오디오 노트 조회 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _process_list_node(self, state: AudioNoteProcessingState) -> AudioNoteProcessingState:
        """오디오 노트 목록 조회 노드 (Service 사용)."""
        commentary_id = state.get("commentary_id")

        try:
            if not commentary_id:
                return {**state, "result": {"success": False, "error": "commentary_id가 필요합니다."}}

            result = self._service.get_commentary_audios(commentary_id)
            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[AudioNoteFlow] 오디오 노트 목록 조회 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _process_delete_node(self, state: AudioNoteProcessingState) -> AudioNoteProcessingState:
        """오디오 노트 삭제 노드 (Service 사용)."""
        audio_id = state.get("audio_id")

        try:
            if not audio_id:
                return {**state, "result": {"success": False, "error": "audio_id가 필요합니다."}}

            result = self._service.delete_audio(audio_id)
            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[AudioNoteFlow] 오디오 노트 삭제 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _process_generate_tts_node(self, state: AudioNoteProcessingState) -> AudioNoteProcessingState:
        """TTS 오디오 생성 노드.

        Edge-TTS 엔진으로 해설 본문을 MP3 음성으로 변환합니다.
        실패 시 gTTS로 자동 폴백합니다.
        """
        request_data = state.get("request_data", {})
        commentary_id = state.get("commentary_id")

        try:
            if not commentary_id:
                return {**state, "result": {"success": False, "error": "commentary_id가 필요합니다."}}

            voice_type = request_data.get("voice_type", "female")

            # AudioNoteService의 TTS 생성 메서드 호출
            result = await self._service.generate_tts_for_commentary(
                commentary_id=commentary_id,
                voice_type=voice_type,
            )

            if result.get("success"):
                result["message"] = "TTS 오디오가 생성되었습니다."
                file_path = result.get("audio", {}).get("file_path", "")
                return {**state, "result": result, "generated_file_path": file_path}

            return {**state, "result": result}

        except Exception as e:
            logger.error(f"[AudioNoteFlow] TTS 생성 오류: {e}", exc_info=True)
            return {**state, "result": {"success": False, "error": str(e)}, "error": str(e)}

    async def _finalize_node(self, state: AudioNoteProcessingState) -> AudioNoteProcessingState:
        """최종 정리 노드."""
        return state

    async def process_audio_note_request(
        self, request_text: str, request_data: dict
    ) -> dict:
        """AudioNote 요청 처리.

        Args:
            request_text: 요청 텍스트
            request_data: 요청 데이터 (action, audio_id, commentary_id 등)

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[AudioNoteFlow] 요청 처리 시작")

        initial_state: AudioNoteProcessingState = {
            "request_text": request_text,
            "request_data": request_data,
            "action": None,
            "audio_id": None,
            "commentary_id": None,
            "result": None,
            "error": None,
            "metadata": None,
            "generated_file_path": None,
        }

        try:
            final_state = await self._graph.ainvoke(initial_state)
            result = final_state.get("result")
            return result if result else {"success": False, "error": "처리 결과가 없습니다."}
        except Exception as e:
            logger.error(f"[AudioNoteFlow] 처리 오류: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
