"""AudioNote 데이터 저장소 (Repository 패턴).

테이블 구조:
- audio_notes: 해설 오디오 파일 정보
  - id, commentary_id
  - file_path, voice_type, duration
  - created_at
"""

import logging
from typing import List, Dict, Any, Optional

import psycopg

from backend.dependencies import get_db_connection

logger = logging.getLogger(__name__)


class AudioNoteRepository:
    """AudioNote 데이터 저장소."""

    def __init__(self, conn: Optional[psycopg.Connection] = None):
        """초기화.

        Args:
            conn: DB 연결 (None이면 get_db_connection() 사용)
        """
        self._conn = conn

    def _get_connection(self) -> psycopg.Connection:
        """DB 연결 가져오기."""
        if self._conn is not None:
            return self._conn
        return get_db_connection()

    # ========================================================================
    # CRUD 메서드
    # ========================================================================

    def create(
        self,
        commentary_id: int,
        file_path: str,
        voice_type: Optional[str] = None,
        duration: Optional[int] = None,
    ) -> Dict[str, Any]:
        """오디오 노트 생성.

        Args:
            commentary_id: 해설 ID
            file_path: 오디오 파일 경로
            voice_type: 음성 유형 ('male', 'female', 등)
            duration: 오디오 길이 (초)

        Returns:
            생성된 오디오 노트 데이터
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audio_notes (commentary_id, file_path, voice_type, duration)
                VALUES (%s, %s, %s, %s)
                RETURNING id, commentary_id, file_path, voice_type, duration, created_at
                """,
                (commentary_id, file_path, voice_type, duration)
            )
            row = cur.fetchone()
            conn.commit()

        logger.info(f"[AudioNoteRepository] 오디오 노트 생성: id={row[0]}, commentary_id={commentary_id}")

        return self._row_to_dict(row)

    def get_by_id(self, audio_note_id: int) -> Optional[Dict[str, Any]]:
        """ID로 오디오 노트 조회.

        Args:
            audio_note_id: 오디오 노트 ID

        Returns:
            오디오 노트 데이터 또는 None
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, commentary_id, file_path, voice_type, duration, created_at
                FROM audio_notes
                WHERE id = %s
                """,
                (audio_note_id,)
            )
            row = cur.fetchone()

        if not row:
            return None

        return self._row_to_dict(row)

    def get_by_commentary_id(self, commentary_id: int) -> List[Dict[str, Any]]:
        """해설 ID로 오디오 노트 목록 조회.

        Args:
            commentary_id: 해설 ID

        Returns:
            오디오 노트 리스트
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, commentary_id, file_path, voice_type, duration, created_at
                FROM audio_notes
                WHERE commentary_id = %s
                ORDER BY created_at
                """,
                (commentary_id,)
            )
            rows = cur.fetchall()

        return [self._row_to_dict(r) for r in rows]

    def delete(self, audio_note_id: int) -> bool:
        """오디오 노트 삭제.

        Args:
            audio_note_id: 오디오 노트 ID

        Returns:
            삭제 성공 여부
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM audio_notes WHERE id = %s RETURNING id",
                (audio_note_id,)
            )
            result = cur.fetchone()
            conn.commit()

        return result is not None

    def delete_by_commentary_id(self, commentary_id: int) -> int:
        """해설의 모든 오디오 노트 삭제.

        Args:
            commentary_id: 해설 ID

        Returns:
            삭제된 개수
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM audio_notes WHERE commentary_id = %s",
                (commentary_id,)
            )
            deleted = cur.rowcount
            conn.commit()

        logger.info(f"[AudioNoteRepository] 해설 오디오 노트 삭제: commentary_id={commentary_id}, deleted={deleted}")
        return deleted

    # ========================================================================
    # TTS 관련 메서드
    # ========================================================================

    def exists_for_commentary(
        self, commentary_id: int, voice_type: Optional[str] = None
    ) -> bool:
        """해설에 대한 오디오 노트 존재 여부 확인.

        Args:
            commentary_id: 해설 ID
            voice_type: 음성 유형 (옵션)

        Returns:
            존재 여부
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            if voice_type:
                cur.execute(
                    "SELECT 1 FROM audio_notes WHERE commentary_id = %s AND voice_type = %s LIMIT 1",
                    (commentary_id, voice_type)
                )
            else:
                cur.execute(
                    "SELECT 1 FROM audio_notes WHERE commentary_id = %s LIMIT 1",
                    (commentary_id,)
                )
            return cur.fetchone() is not None

    def get_commentaries_without_audio(self, limit: int = 100) -> List[Dict[str, Any]]:
        """오디오가 없는 해설 목록 조회.

        Args:
            limit: 조회 개수

        Returns:
            오디오가 없는 해설 리스트
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.body, c.type
                FROM commentaries c
                LEFT JOIN audio_notes a ON c.id = a.commentary_id
                WHERE a.id IS NULL
                ORDER BY c.id
                LIMIT %s
                """,
                (limit,)
            )
            rows = cur.fetchall()

        return [
            {
                "commentary_id": r[0],
                "body": r[1],
                "type": r[2],
            }
            for r in rows
        ]

    def get_total_duration_by_commentary_id(self, commentary_id: int) -> int:
        """해설의 총 오디오 길이 조회.

        Args:
            commentary_id: 해설 ID

        Returns:
            총 길이 (초)
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(duration), 0)
                FROM audio_notes
                WHERE commentary_id = %s AND duration IS NOT NULL
                """,
                (commentary_id,)
            )
            return cur.fetchone()[0]

    def list_all(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """전체 오디오 노트 목록 조회.

        Args:
            limit: 조회 개수
            offset: 오프셋

        Returns:
            오디오 노트 리스트
        """
        conn = self._get_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, commentary_id, file_path, voice_type, duration, created_at
                FROM audio_notes
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            rows = cur.fetchall()

        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """DB row를 딕셔너리로 변환."""
        return {
            "id": row[0],
            "commentary_id": row[1],
            "file_path": row[2],
            "voice_type": row[3],
            "duration": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
        }

