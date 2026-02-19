"""QuestionImage 서비스.

문제 관련 이미지를 관리합니다.
YOLO 기반 cropping된 시각 자료를 제공합니다.
"""

import logging
from typing import Dict, Any, List, Optional

from backend.dependencies import get_db_connection
from backend.domain.admin.models.transfers.question_transfer import QuestionImageTransfer

logger = logging.getLogger(__name__)


class QuestionImageService:
    """QuestionImage 서비스."""

    def __init__(self):
        """초기화."""
        pass

    def create_image(
        self,
        question_id: int,
        file_path: str,
        coordinates_json: Optional[Dict[str, Any]] = None,
        image_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """문제 이미지 생성.

        Args:
            question_id: 문제 ID
            file_path: 이미지 파일 경로
            coordinates_json: YOLO cropping 좌표
            image_type: 이미지 유형

        Returns:
            생성 결과
        """
        conn = get_db_connection()
        from psycopg.types.json import Json

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO question_images (
                        question_id, file_path, coordinates_json, image_type
                    )
                    VALUES (%s, %s, %s::jsonb, %s)
                    RETURNING id, question_id, file_path, coordinates_json, image_type, created_at
                    """,
                    (
                        question_id,
                        file_path,
                        Json(coordinates_json) if coordinates_json else None,
                        image_type
                    )
                )
                row = cur.fetchone()
                conn.commit()

                return {
                    "success": True,
                    "image": QuestionImageTransfer(
                        id=row[0],
                        question_id=row[1],
                        file_path=row[2],
                        coordinates_json=row[3],
                        image_type=row[4],
                        created_at=row[5],
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[QuestionImageService] 생성 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_image(self, image_id: int) -> Dict[str, Any]:
        """이미지 조회.

        Args:
            image_id: 이미지 ID

        Returns:
            조회 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, question_id, file_path, coordinates_json, image_type, created_at
                    FROM question_images WHERE id = %s
                    """,
                    (image_id,)
                )
                row = cur.fetchone()

                if not row:
                    return {"success": False, "error": "이미지를 찾을 수 없습니다."}

                return {
                    "success": True,
                    "image": QuestionImageTransfer(
                        id=row[0],
                        question_id=row[1],
                        file_path=row[2],
                        coordinates_json=row[3],
                        image_type=row[4],
                        created_at=row[5],
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[QuestionImageService] 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def get_question_images(self, question_id: int) -> Dict[str, Any]:
        """문제별 이미지 목록 조회.

        Args:
            question_id: 문제 ID

        Returns:
            조회 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, question_id, file_path, coordinates_json, image_type, created_at
                    FROM question_images
                    WHERE question_id = %s
                    ORDER BY id
                    """,
                    (question_id,)
                )
                rows = cur.fetchall()

                images = [
                    QuestionImageTransfer(
                        id=row[0],
                        question_id=row[1],
                        file_path=row[2],
                        coordinates_json=row[3],
                        image_type=row[4],
                        created_at=row[5],
                    ).model_dump()
                    for row in rows
                ]

                return {"success": True, "images": images, "count": len(images)}
        except Exception as e:
            logger.error(f"[QuestionImageService] 목록 조회 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def update_coordinates(
        self,
        image_id: int,
        coordinates_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """이미지 좌표 수정 (YOLO cropping 결과 업데이트).

        Args:
            image_id: 이미지 ID
            coordinates_json: 새 좌표 데이터

        Returns:
            수정 결과
        """
        conn = get_db_connection()
        from psycopg.types.json import Json

        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE question_images
                    SET coordinates_json = %s::jsonb
                    WHERE id = %s
                    RETURNING id, question_id, file_path, coordinates_json, image_type, created_at
                    """,
                    (Json(coordinates_json), image_id)
                )
                row = cur.fetchone()
                conn.commit()

                if not row:
                    return {"success": False, "error": "이미지를 찾을 수 없습니다."}

                return {
                    "success": True,
                    "image": QuestionImageTransfer(
                        id=row[0],
                        question_id=row[1],
                        file_path=row[2],
                        coordinates_json=row[3],
                        image_type=row[4],
                        created_at=row[5],
                    ).model_dump()
                }
        except Exception as e:
            logger.error(f"[QuestionImageService] 좌표 수정 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def delete_image(self, image_id: int) -> Dict[str, Any]:
        """이미지 삭제.

        Args:
            image_id: 이미지 ID

        Returns:
            삭제 결과
        """
        conn = get_db_connection()

        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM question_images WHERE id = %s RETURNING id, file_path",
                    (image_id,)
                )
                row = cur.fetchone()
                conn.commit()

                if not row:
                    return {"success": False, "error": "이미지를 찾을 수 없습니다."}

                return {
                    "success": True,
                    "deleted_id": row[0],
                    "deleted_file_path": row[1]
                }
        except Exception as e:
            logger.error(f"[QuestionImageService] 삭제 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def bulk_create_images(
        self,
        question_id: int,
        images: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """문제 이미지 일괄 생성.

        Args:
            question_id: 문제 ID
            images: 이미지 정보 리스트 [{"file_path": ..., "coordinates_json": ..., "image_type": ...}]

        Returns:
            생성 결과
        """
        conn = get_db_connection()
        from psycopg.types.json import Json

        created = []
        errors = []

        try:
            with conn.cursor() as cur:
                for idx, img in enumerate(images, start=1):
                    try:
                        cur.execute(
                            """
                            INSERT INTO question_images (
                                question_id, file_path, coordinates_json, image_type
                            )
                            VALUES (%s, %s, %s::jsonb, %s)
                            RETURNING id
                            """,
                            (
                                question_id,
                                img.get("file_path"),
                                Json(img.get("coordinates_json")) if img.get("coordinates_json") else None,
                                img.get("image_type")
                            )
                        )
                        row = cur.fetchone()
                        created.append({"index": idx, "id": row[0]})
                    except Exception as e:
                        errors.append({"index": idx, "error": str(e)})

                conn.commit()

            return {
                "success": len(errors) == 0,
                "created_count": len(created),
                "created": created,
                "errors": errors
            }
        except Exception as e:
            logger.error(f"[QuestionImageService] 일괄 생성 실패: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

