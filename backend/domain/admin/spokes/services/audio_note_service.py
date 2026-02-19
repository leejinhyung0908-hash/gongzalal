"""AudioNote 서비스.

해설 오디오를 관리합니다.
TTS 생성 음성 파일을 제공합니다.

주요 기능:
- CRUD (오디오 노트 생성/조회/삭제)
- TTS 음성 생성 (Edge-TTS / gTTS)
- 오답 약점 분석 + 일괄 TTS 생성
"""

import logging
import os
from typing import Dict, Any, List, Optional

from backend.config import settings
from backend.dependencies import get_db_connection
from backend.domain.admin.models.transfers.commentary_transfer import (
    AudioNoteTransfer,
    AudioNoteCreateRequest,
    AudioNoteResponse,
)

logger = logging.getLogger(__name__)


class AudioNoteService:
    """AudioNote 서비스."""

    def __init__(self):
        """초기화."""
        self._tts_service = None

    def _get_tts(self):
        """TTSService lazy load."""
        if self._tts_service is None:
            from backend.core.tts.tts_service import TTSService
            self._tts_service = TTSService(audio_dir=settings.AUDIO_STORAGE_PATH)
        return self._tts_service

    def create_audio(self, request: AudioNoteCreateRequest) -> Dict[str, Any]:
        """오디오 노트 생성.

        Args:
            request: 오디오 생성 요청

        Returns:
            생성 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audio_notes (
                        commentary_id, file_path, voice_type, duration
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, commentary_id, file_path, voice_type, duration, created_at
                    """,
                    (
                        request.commentary_id,
                        request.file_path,
                        request.voice_type,
                        request.duration
                    )
                )
                row = cur.fetchone()
                conn.commit()

                return {
                    "success": True,
                    "audio": AudioNoteResponse(
                        id=row[0],
                        commentary_id=row[1],
                        file_path=row[2],
                        voice_type=row[3],
                        duration=row[4],
                        created_at=row[5].isoformat() if row[5] else None,
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[AudioNoteService] 생성 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_audio(self, audio_id: int) -> Dict[str, Any]:
        """오디오 노트 조회.

        Args:
            audio_id: 오디오 ID

        Returns:
            조회 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, commentary_id, file_path, voice_type, duration, created_at
                    FROM audio_notes WHERE id = %s
                    """,
                    (audio_id,)
                )
                row = cur.fetchone()

                if not row:
                    return {"success": False, "error": "오디오를 찾을 수 없습니다."}

                return {
                    "success": True,
                    "audio": AudioNoteResponse(
                        id=row[0],
                        commentary_id=row[1],
                        file_path=row[2],
                        voice_type=row[3],
                        duration=row[4],
                        created_at=row[5].isoformat() if row[5] else None,
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[AudioNoteService] 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_commentary_audios(self, commentary_id: int) -> Dict[str, Any]:
        """해설별 오디오 목록 조회.

        Args:
            commentary_id: 해설 ID

        Returns:
            조회 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, commentary_id, file_path, voice_type, duration, created_at
                    FROM audio_notes
                    WHERE commentary_id = %s
                    ORDER BY id
                    """,
                    (commentary_id,)
                )
                rows = cur.fetchall()

                audios = [
                    AudioNoteResponse(
                        id=row[0],
                        commentary_id=row[1],
                        file_path=row[2],
                        voice_type=row[3],
                        duration=row[4],
                        created_at=row[5].isoformat() if row[5] else None,
                    ).model_dump()
                    for row in rows
                ]

                return {"success": True, "audios": audios, "count": len(audios)}
        except Exception as e:
            logger.error(f"[AudioNoteService] 목록 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def delete_audio(self, audio_id: int) -> Dict[str, Any]:
        """오디오 노트 삭제.

        Args:
            audio_id: 오디오 ID

        Returns:
            삭제 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM audio_notes WHERE id = %s RETURNING id, file_path",
                    (audio_id,)
                )
                row = cur.fetchone()
                conn.commit()

                if not row:
                    return {"success": False, "error": "오디오를 찾을 수 없습니다."}

                return {
                    "success": True,
                    "deleted_id": row[0],
                    "deleted_file_path": row[1]
                }
        except Exception as e:
            logger.error(f"[AudioNoteService] 삭제 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def update_duration(self, audio_id: int, duration: int) -> Dict[str, Any]:
        """오디오 지속 시간 수정.

        Args:
            audio_id: 오디오 ID
            duration: 새 지속 시간 (초)

        Returns:
            수정 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE audio_notes
                    SET duration = %s
                    WHERE id = %s
                    RETURNING id, commentary_id, file_path, voice_type, duration, created_at
                    """,
                    (duration, audio_id)
                )
                row = cur.fetchone()
                conn.commit()

                if not row:
                    return {"success": False, "error": "오디오를 찾을 수 없습니다."}

                return {
                    "success": True,
                    "audio": AudioNoteResponse(
                        id=row[0],
                        commentary_id=row[1],
                        file_path=row[2],
                        voice_type=row[3],
                        duration=row[4],
                        created_at=row[5].isoformat() if row[5] else None,
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[AudioNoteService] 지속 시간 수정 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_total_duration(self, commentary_id: int) -> Dict[str, Any]:
        """해설의 총 오디오 재생 시간 조회.

        Args:
            commentary_id: 해설 ID

        Returns:
            총 재생 시간
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COALESCE(SUM(duration), 0), COUNT(*)
                    FROM audio_notes
                    WHERE commentary_id = %s
                    """,
                    (commentary_id,)
                )
                row = cur.fetchone()

                return {
                    "success": True,
                    "commentary_id": commentary_id,
                    "total_duration_seconds": row[0],
                    "audio_count": row[1]
                }
        except Exception as e:
            logger.error(f"[AudioNoteService] 총 재생 시간 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ====================================================================
    # TTS 생성 메서드
    # ====================================================================

    async def generate_tts_for_commentary(
        self,
        commentary_id: int,
        voice_type: str = "female",
    ) -> Dict[str, Any]:
        """해설의 TTS 음성을 생성합니다.

        Args:
            commentary_id: 해설 ID
            voice_type: 음성 유형

        Returns:
            생성 결과 (audio_note 포함)
        """
        conn = get_db_connection()

        try:
            # 1) 해설 본문 조회
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, body FROM commentaries WHERE id = %s",
                    (commentary_id,),
                )
                row = cur.fetchone()

            if not row:
                return {"success": False, "error": "해설을 찾을 수 없습니다."}

            body_text = row[1]
            if not body_text or not body_text.strip():
                return {"success": False, "error": "해설 본문이 비어있습니다."}

            # 2) TTS 변환
            tts = self._get_tts()
            result = await tts.synthesize(
                body_text,
                commentary_id=commentary_id,
                voice_type=voice_type,
            )

            if not result.success:
                return {"success": False, "error": result.error}

            # 3) DB 저장
            relative_path = os.path.basename(result.file_path)

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audio_notes (
                        commentary_id, file_path, voice_type, duration, commentary
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, commentary_id, file_path, voice_type, duration, created_at
                    """,
                    (
                        commentary_id,
                        relative_path,
                        voice_type,
                        result.duration_seconds,
                        body_text,
                    ),
                )
                saved = cur.fetchone()
                conn.commit()

            return {
                "success": True,
                "audio": AudioNoteResponse(
                    id=saved[0],
                    commentary_id=saved[1],
                    file_path=saved[2],
                    voice_type=saved[3],
                    duration=saved[4],
                    created_at=saved[5].isoformat() if saved[5] else None,
                ).model_dump(),
                "engine": result.engine,
                "file_size": result.file_size_bytes,
            }

        except Exception as e:
            logger.error(f"[AudioNoteService] TTS 생성 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_user_weakness_commentaries(
        self,
        user_id: int,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """사용자의 약점 분석 기반 해설 목록을 반환합니다.

        user_solving_logs에서 오답률이 높거나 풀이 시간이 긴 문제의
        해설 목록을 우선순위로 정렬하여 반환합니다.

        Args:
            user_id: 사용자 ID
            limit: 최대 건수

        Returns:
            약점 해설 목록
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    WITH wrong_stats AS (
                        SELECT
                            usl.question_id,
                            COUNT(*) AS attempt_count,
                            SUM(CASE WHEN usl.is_correct = FALSE THEN 1 ELSE 0 END) AS wrong_count,
                            AVG(usl.time_spent) AS avg_time,
                            MAX(usl.is_wrong_note::int) AS has_wrong_note
                        FROM user_solving_logs usl
                        WHERE usl.user_id = %s
                        GROUP BY usl.question_id
                    )
                    SELECT
                        c.id AS commentary_id,
                        c.body,
                        e.subject,
                        q.question_no,
                        q.id AS question_id,
                        ws.wrong_count,
                        ws.attempt_count,
                        ws.avg_time,
                        ws.has_wrong_note,
                        ROUND(ws.wrong_count::numeric / GREATEST(ws.attempt_count, 1) * 100, 1) AS error_rate
                    FROM wrong_stats ws
                    JOIN questions q ON ws.question_id = q.id
                    JOIN exams e ON q.exam_id = e.id
                    JOIN commentaries c ON q.id = c.question_id
                    WHERE ws.wrong_count > 0
                    ORDER BY
                        ws.has_wrong_note DESC,
                        error_rate DESC,
                        ws.avg_time DESC
                    LIMIT %s
                    """,
                    (user_id, limit),
                )
                rows = cur.fetchall()

            items = []
            for r in rows:
                items.append({
                    "commentary_id": r[0],
                    "body_preview": r[1][:100] + "..." if r[1] and len(r[1]) > 100 else r[1],
                    "subject": r[2],
                    "question_no": r[3],
                    "question_id": r[4],
                    "wrong_count": r[5],
                    "attempt_count": r[6],
                    "avg_time_seconds": float(r[7]) if r[7] else 0,
                    "has_wrong_note": bool(r[8]),
                    "error_rate": float(r[9]) if r[9] else 0,
                })

            return {
                "success": True,
                "user_id": user_id,
                "weakness_commentaries": items,
                "count": len(items),
            }

        except Exception as e:
            logger.error(f"[AudioNoteService] 약점 분석 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

