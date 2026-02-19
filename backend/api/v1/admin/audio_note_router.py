"""오디오 노트(Audio_Notes) 라우터.

Edge-TTS / gTTS 기반 해설 TTS 음성 생성 및 관리.

테이블 구조:
- Audio_Notes: commentary_id FK, file_path, voice_type, duration, commentary(텍스트)

기능:
- 해설 TTS 생성 (Edge-TTS 우선, gTTS 폴백)
- 오디오 파일 서빙 (FileResponse)
- 오답 보이스 피드백 (오답 문제 해설 일괄 TTS 생성)
- CRUD 엔드포인트
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.config import settings
from backend.dependencies import get_db_connection
from backend.domain.admin.models.transfers.commentary_transfer import (
    AudioNoteTransfer,
    AudioNoteCreateRequest,
    AudioNoteResponse,
)

router = APIRouter(tags=["audio-notes"])
logger = logging.getLogger(__name__)

# TTS 서비스 인스턴스 (lazy init)
_tts_service = None


def _get_tts_service():
    """TTSService 인스턴스를 lazy load 합니다."""
    global _tts_service
    if _tts_service is None:
        from backend.core.tts.tts_service import TTSService
        _tts_service = TTSService(audio_dir=settings.AUDIO_STORAGE_PATH)
    return _tts_service


# ============================================================================
# 오디오 파일 서빙
# ============================================================================

@router.get("/serve/{audio_note_id}")
async def serve_audio_file(
    audio_note_id: int,
    conn: psycopg.Connection = Depends(get_db_connection),
):
    """오디오 MP3 파일을 직접 서빙합니다.

    프론트엔드의 <audio> 태그에서 직접 재생 가능합니다.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT file_path FROM audio_notes WHERE id = %s",
            (audio_note_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="오디오 노트를 찾을 수 없습니다.")

    file_path = row[0]

    # 절대 경로이면 그대로, 상대 경로이면 audio_dir 기준으로 해석
    if not os.path.isabs(file_path):
        file_path = os.path.join(settings.AUDIO_STORAGE_PATH, file_path)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"오디오 파일을 찾을 수 없습니다: {os.path.basename(file_path)}",
        )

    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=os.path.basename(file_path),
    )


# ============================================================================
# TTS 생성 엔드포인트
# ============================================================================

class TTSGenerateRequest(BaseModel):
    """TTS 생성 요청."""
    commentary_id: int = Field(..., ge=1, description="해설 ID")
    voice_type: str = Field(default="female", description="음성 유형 (male/female/male2/female2)")


class TTSBatchRequest(BaseModel):
    """오답 보이스 일괄 TTS 생성 요청."""
    user_id: int = Field(..., ge=1, description="사용자 ID")
    voice_type: str = Field(default="female", description="음성 유형")
    limit: int = Field(default=20, ge=1, le=50, description="최대 생성 건수")


@router.post("/generate-tts", response_model=dict)
async def generate_tts(
    request: TTSGenerateRequest,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """해설 TTS 생성 엔드포인트.

    Edge-TTS로 해설 본문을 MP3 음성 파일로 변환합니다.
    이미 동일한 (commentary_id, voice_type) 조합이 존재하면 기존 파일을 반환합니다.
    """
    try:
        # 1) 이미 존재하는지 확인 (중복 생성 방지)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, commentary_id, file_path, voice_type, duration, created_at
                FROM audio_notes
                WHERE commentary_id = %s AND voice_type = %s
                LIMIT 1
                """,
                (request.commentary_id, request.voice_type),
            )
            existing = cur.fetchone()

        if existing:
            # 파일이 실제로 존재하는지 확인
            existing_path = existing[2]
            if not os.path.isabs(existing_path):
                existing_path = os.path.join(settings.AUDIO_STORAGE_PATH, existing_path)

            if os.path.exists(existing_path) and os.path.getsize(existing_path) > 0:
                logger.info(
                    f"[AudioNoteRouter] 기존 TTS 재사용: "
                    f"commentary_id={request.commentary_id}, voice={request.voice_type}"
                )
                return {
                    "success": True,
                    "message": "기존에 생성된 오디오를 반환합니다.",
                    "audio_note": AudioNoteResponse(
                        id=existing[0],
                        commentary_id=existing[1],
                        file_path=existing[2],
                        voice_type=existing[3],
                        duration=existing[4],
                        created_at=existing[5].isoformat() if existing[5] else None,
                    ).model_dump(),
                    "cached": True,
                }
            else:
                # 파일이 없으면 DB 레코드 삭제 후 재생성
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM audio_notes WHERE id = %s", (existing[0],))
                    conn.commit()

        # 2) 해설 본문 조회
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, body FROM commentaries WHERE id = %s",
                (request.commentary_id,),
            )
            commentary = cur.fetchone()

        if not commentary:
            raise HTTPException(status_code=404, detail="해설을 찾을 수 없습니다.")

        commentary_id = commentary[0]
        body_text = commentary[1]

        if not body_text or not body_text.strip():
            raise HTTPException(status_code=400, detail="해설 본문이 비어있습니다.")

        # 3) TTS 변환
        tts_service = _get_tts_service()
        tts_result = await tts_service.synthesize(
            body_text,
            commentary_id=commentary_id,
            voice_type=request.voice_type,
        )

        if not tts_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"TTS 변환 실패: {tts_result.error}",
            )

        # 4) DB에 오디오 노트 저장
        # file_path는 파일명만 저장 (서빙 시 audio_dir 기준으로 해석)
        relative_path = os.path.basename(tts_result.file_path)

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
                    request.voice_type,
                    tts_result.duration_seconds,
                    body_text,
                ),
            )
            row = cur.fetchone()
            conn.commit()

        logger.info(
            f"[AudioNoteRouter] TTS 생성 완료: commentary_id={commentary_id}, "
            f"voice={request.voice_type}, engine={tts_result.engine}, "
            f"size={tts_result.file_size_bytes:,} bytes"
        )

        return {
            "success": True,
            "message": f"TTS 생성 완료 ({tts_result.engine})",
            "audio_note": AudioNoteResponse(
                id=row[0],
                commentary_id=row[1],
                file_path=row[2],
                voice_type=row[3],
                duration=row[4],
                created_at=row[5].isoformat() if row[5] else None,
            ).model_dump(),
            "tts_info": {
                "engine": tts_result.engine,
                "file_size_bytes": tts_result.file_size_bytes,
                "duration_seconds": tts_result.duration_seconds,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"[AudioNoteRouter] TTS 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS 생성 실패: {str(e)}")


# ============================================================================
# 오답 보이스 피드백 엔드포인트
# ============================================================================

@router.post("/generate-wrong-note-audio", response_model=dict)
async def generate_wrong_note_audio(
    request: TTSBatchRequest,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """오답 문제 해설을 일괄 TTS 생성합니다.

    user_solving_logs에서 is_wrong_note=TRUE인 문제 중
    commentaries가 있는 문제의 해설을 TTS로 변환합니다.
    """
    try:
        # 1) 오답 문제 중 해설이 있고 아직 TTS가 없는 항목 조회
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT c.id AS commentary_id, c.body, e.subject,
                       q.question_no, q.id AS question_id
                FROM user_solving_logs usl
                JOIN questions q ON usl.question_id = q.id
                JOIN exams e ON q.exam_id = e.id
                JOIN commentaries c ON q.id = c.question_id
                LEFT JOIN audio_notes an
                    ON c.id = an.commentary_id AND an.voice_type = %s
                WHERE usl.user_id = %s
                  AND usl.is_wrong_note = TRUE
                  AND an.id IS NULL
                ORDER BY e.subject, q.question_no
                LIMIT %s
                """,
                (request.voice_type, request.user_id, request.limit),
            )
            pending_rows = cur.fetchall()

        if not pending_rows:
            # 이미 전부 생성됨 → 기존 목록 반환
            return await _get_user_wrong_note_audios(conn, request.user_id, request.voice_type)

        # 2) 일괄 TTS 생성
        tts_service = _get_tts_service()
        created = []
        errors = []

        for row in pending_rows:
            commentary_id = row[0]
            body_text = row[1]
            subject = row[2]
            question_no = row[3]

            try:
                tts_result = await tts_service.synthesize(
                    body_text,
                    commentary_id=commentary_id,
                    voice_type=request.voice_type,
                )

                if not tts_result.success:
                    errors.append({
                        "commentary_id": commentary_id,
                        "error": tts_result.error,
                    })
                    continue

                relative_path = os.path.basename(tts_result.file_path)

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO audio_notes (
                            commentary_id, file_path, voice_type, duration, commentary
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            commentary_id,
                            relative_path,
                            request.voice_type,
                            tts_result.duration_seconds,
                            body_text,
                        ),
                    )
                    audio_id = cur.fetchone()[0]
                    conn.commit()

                created.append({
                    "audio_id": audio_id,
                    "commentary_id": commentary_id,
                    "subject": subject,
                    "question_no": question_no,
                    "duration": tts_result.duration_seconds,
                    "engine": tts_result.engine,
                })

            except Exception as e:
                logger.error(
                    f"[AudioNoteRouter] 오답 TTS 생성 실패 (commentary_id={commentary_id}): {e}"
                )
                errors.append({"commentary_id": commentary_id, "error": str(e)})

        logger.info(
            f"[AudioNoteRouter] 오답 TTS 일괄 생성: "
            f"성공={len(created)}, 실패={len(errors)}, user_id={request.user_id}"
        )

        return {
            "success": True,
            "message": f"오답 해설 TTS {len(created)}건 생성 완료",
            "created": created,
            "errors": errors if errors else None,
            "created_count": len(created),
            "error_count": len(errors),
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"[AudioNoteRouter] 오답 TTS 일괄 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"오답 TTS 일괄 생성 실패: {str(e)}")


@router.get("/user/{user_id}/wrong-note-audios", response_model=dict)
async def get_user_wrong_note_audios(
    user_id: int,
    voice_type: str = Query(default="female", description="음성 유형"),
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """사용자의 오답 해설 오디오 목록을 조회합니다.

    과목별로 그룹핑하여 반환합니다.
    """
    return await _get_user_wrong_note_audios(conn, user_id, voice_type)


async def _get_user_wrong_note_audios(
    conn: psycopg.Connection,
    user_id: int,
    voice_type: str,
) -> dict:
    """오답 해설 오디오 목록 조회 내부 함수."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT an.id, an.commentary_id, an.file_path, an.voice_type,
                   an.duration, an.created_at,
                   e.subject, q.question_no, q.id AS question_id
            FROM user_solving_logs usl
            JOIN questions q ON usl.question_id = q.id
            JOIN exams e ON q.exam_id = e.id
            JOIN commentaries c ON q.id = c.question_id
            JOIN audio_notes an ON c.id = an.commentary_id AND an.voice_type = %s
            WHERE usl.user_id = %s
              AND usl.is_wrong_note = TRUE
            ORDER BY e.subject, q.question_no
            """,
            (voice_type, user_id),
        )
        rows = cur.fetchall()

    # 과목별 그룹핑
    by_subject: dict = {}
    total_duration = 0

    for r in rows:
        subject = r[6] or "기타"
        duration = r[4] or 0
        total_duration += duration

        if subject not in by_subject:
            by_subject[subject] = []

        by_subject[subject].append({
            "audio_id": r[0],
            "commentary_id": r[1],
            "file_path": r[2],
            "voice_type": r[3],
            "duration": duration,
            "created_at": r[5].isoformat() if r[5] else None,
            "question_no": r[7],
            "question_id": r[8],
        })

    # 미생성 오답 건수 확인
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(DISTINCT c.id)
            FROM user_solving_logs usl
            JOIN questions q ON usl.question_id = q.id
            JOIN commentaries c ON q.id = c.question_id
            LEFT JOIN audio_notes an
                ON c.id = an.commentary_id AND an.voice_type = %s
            WHERE usl.user_id = %s
              AND usl.is_wrong_note = TRUE
              AND an.id IS NULL
            """,
            (voice_type, user_id),
        )
        pending_count = cur.fetchone()[0]

    return {
        "success": True,
        "user_id": user_id,
        "voice_type": voice_type,
        "by_subject": by_subject,
        "total_audios": sum(len(v) for v in by_subject.values()),
        "total_duration_seconds": total_duration,
        "total_duration_display": f"{total_duration // 60}분 {total_duration % 60}초",
        "pending_count": pending_count,
    }


# ============================================================================
# 음성 옵션 조회
# ============================================================================

@router.get("/voices", response_model=dict)
async def get_available_voices() -> dict:
    """사용 가능한 한국어 TTS 음성 목록을 반환합니다."""
    tts_service = _get_tts_service()
    voices = tts_service.get_available_voices()
    return {"success": True, "voices": voices}


# ============================================================================
# Audio Note CRUD 엔드포인트
# ============================================================================

@router.post("/", response_model=dict)
async def create_audio_note(
    request: AudioNoteCreateRequest,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """오디오 노트 생성 엔드포인트."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audio_notes (commentary_id, file_path, voice_type, duration)
                VALUES (%s, %s, %s, %s)
                RETURNING id, commentary_id, file_path, voice_type, duration, created_at
                """,
                (
                    request.commentary_id,
                    request.file_path,
                    request.voice_type,
                    request.duration,
                ),
            )
            row = cur.fetchone()
            conn.commit()

        return {
            "success": True,
            "audio_note": AudioNoteResponse(
                id=row[0],
                commentary_id=row[1],
                file_path=row[2],
                voice_type=row[3],
                duration=row[4],
                created_at=row[5].isoformat() if row[5] else None,
            ).model_dump(),
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"[AudioNoteRouter] 오디오 노트 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"오디오 노트 생성 실패: {str(e)}")


@router.get("/{audio_note_id}", response_model=dict)
async def get_audio_note(
    audio_note_id: int,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """오디오 노트 조회 엔드포인트."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, commentary_id, file_path, voice_type, duration, created_at
            FROM audio_notes WHERE id = %s
            """,
            (audio_note_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="오디오 노트를 찾을 수 없습니다.")

    return {
        "success": True,
        "audio_note": AudioNoteResponse(
            id=row[0],
            commentary_id=row[1],
            file_path=row[2],
            voice_type=row[3],
            duration=row[4],
            created_at=row[5].isoformat() if row[5] else None,
        ).model_dump(),
    }


@router.get("/commentary/{commentary_id}", response_model=dict)
async def get_audio_notes_by_commentary(
    commentary_id: int,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """해설의 오디오 노트 목록 조회."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, commentary_id, file_path, voice_type, duration, created_at
            FROM audio_notes
            WHERE commentary_id = %s
            ORDER BY created_at
            """,
            (commentary_id,),
        )
        rows = cur.fetchall()

    audio_notes = [
        AudioNoteResponse(
            id=r[0], commentary_id=r[1], file_path=r[2],
            voice_type=r[3], duration=r[4],
            created_at=r[5].isoformat() if r[5] else None,
        ).model_dump()
        for r in rows
    ]

    return {"success": True, "audio_notes": audio_notes, "count": len(audio_notes)}


@router.delete("/{audio_note_id}", response_model=dict)
async def delete_audio_note(
    audio_note_id: int,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """오디오 노트 삭제 엔드포인트.

    DB 레코드와 함께 실제 MP3 파일도 삭제합니다.
    """
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM audio_notes WHERE id = %s RETURNING id, file_path",
                (audio_note_id,),
            )
            deleted = cur.fetchone()
            conn.commit()

        if not deleted:
            raise HTTPException(status_code=404, detail="오디오 노트를 찾을 수 없습니다.")

        # MP3 파일 삭제 시도
        file_path = deleted[1]
        if file_path:
            if not os.path.isabs(file_path):
                file_path = os.path.join(settings.AUDIO_STORAGE_PATH, file_path)
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"[AudioNoteRouter] MP3 파일 삭제: {file_path}")
            except OSError as e:
                logger.warning(f"[AudioNoteRouter] MP3 파일 삭제 실패: {e}")

        return {"success": True, "message": "오디오 노트가 삭제되었습니다."}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"[AudioNoteRouter] 오디오 노트 삭제 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"오디오 노트 삭제 실패: {str(e)}")
