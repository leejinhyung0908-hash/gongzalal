"""멘토링 지식(MentoringKnowledge) 라우터.

merged_success_stories.jsonl을 업로드하여 mentoring_knowledge 테이블에 삽입하고,
KURE-v1 임베딩 생성 및 RAG 벡터 검색을 제공합니다.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import psycopg
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from backend.dependencies import get_db_connection

router = APIRouter(tags=["mentoring-knowledge"])
logger = logging.getLogger(__name__)

# ============================================================================
# 임베딩 백그라운드 작업 상태 추적
# ============================================================================
_embedding_job: Dict[str, Any] = {
    "running": False,
    "processed": 0,
    "total": 0,
    "errors": 0,
    "started_at": None,
    "message": "",
}


# ============================================================================
# 헬퍼: 합격 수기 → search_text 생성
# ============================================================================

def _build_search_text(story: Dict[str, Any]) -> str:
    """합격 수기 JSON 한 건에서 임베딩/검색용 텍스트를 생성합니다.

    exam_info + study_style + daily_plan + subject_methods + key_points + difficulties
    를 결합하여 의미적으로 풍부한 검색 대상 텍스트를 만듭니다.
    """
    parts: List[str] = []

    # 시험 정보
    exam_info = story.get("exam_info") or {}
    if exam_info:
        ei_parts: List[str] = []
        if exam_info.get("year"):
            ei_parts.append(f"시험 연도: {exam_info['year']}")
        if exam_info.get("exam_type"):
            ei_parts.append(f"시험 유형: {exam_info['exam_type']}")
        if exam_info.get("grade"):
            ei_parts.append(f"등급: {exam_info['grade']}급")
        if exam_info.get("job_series"):
            ei_parts.append(f"직렬: {exam_info['job_series']}")
        if exam_info.get("subjects"):
            subjs = exam_info["subjects"]
            if isinstance(subjs, list):
                ei_parts.append(f"응시 과목: {', '.join(subjs)}")
        if exam_info.get("총 수험기간"):
            ei_parts.append(f"수험 기간: {exam_info['총 수험기간']}")
        if ei_parts:
            parts.append(" ".join(ei_parts))

    # 수험 스타일
    study_style = story.get("study_style") or {}
    if study_style:
        ss_parts: List[str] = []
        if study_style.get("수험생활"):
            ss_parts.append(f"수험생활: {study_style['수험생활']}")
        if study_style.get("평균 회독수"):
            ss_parts.append(f"평균 회독수: {study_style['평균 회독수']}")
        if ss_parts:
            parts.append(" ".join(ss_parts))

    # 일일 학습 계획
    if story.get("daily_plan"):
        parts.append(f"일일 학습 계획: {story['daily_plan']}")

    # 과목별 학습법
    subj_methods = story.get("subject_methods") or {}
    if isinstance(subj_methods, dict):
        for subj, method in subj_methods.items():
            if method and isinstance(method, str) and len(method.strip()) > 10:
                parts.append(f"{subj} 학습법: {method.strip()[:500]}")
    elif isinstance(subj_methods, str) and subj_methods.strip():
        parts.append(f"과목별 학습법: {subj_methods[:1000]}")

    # 어려웠던 점
    if story.get("difficulties"):
        parts.append(f"어려웠던 점: {story['difficulties']}")

    # 핵심 포인트
    if story.get("key_points"):
        parts.append(f"핵심 포인트: {story['key_points']}")

    return "\n".join(parts)


# ============================================================================
# JSONL 업로드 (merged_success_stories.jsonl)
# ============================================================================

@router.post("/upload-jsonl")
async def upload_success_stories_jsonl(
    file: UploadFile = File(...),
    clear_existing: bool = Query(
        default=False,
        description="True이면 기존 데이터를 모두 삭제 후 업로드",
    ),
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """merged_success_stories.jsonl 업로드 엔드포인트.

    합격 수기 원문 JSONL을 mentoring_knowledge 테이블에 1:1 삽입합니다.
    업로드 후 /enqueue-embeddings 를 호출하면 KURE-v1 임베딩이 생성됩니다.

    JSONL 한 줄 형식:
    {
      "exam_info": {"year":"2025", "exam_type":"국가직", ...},
      "study_style": {"수험생활":"전업 수험생", ...},
      "daily_plan": "...",
      "subject_methods": {"전체": "..."},
      "interview_prep": "...",
      "difficulties": "...",
      "key_points": "...",
      "raw_text": "...",
      "source_url": "...",
      "crawled_at": "...",
      "source": "gongdanki"
    }
    """
    logger.info(
        f"[MentoringKnowledge] /upload-jsonl 호출: "
        f"filename={getattr(file, 'filename', None)}, clear_existing={clear_existing}"
    )

    if not file.filename or not file.filename.endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="JSONL 파일만 업로드할 수 있습니다.")

    try:
        contents = await file.read()
        text = contents.decode("utf-8")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # 기존 데이터 삭제 옵션
        deleted_count = 0
        if clear_existing:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM mentoring_knowledge")
                deleted_count = cur.rowcount
            conn.commit()
            logger.info(f"[MentoringKnowledge] 기존 데이터 {deleted_count}건 삭제")

        inserted_count = 0
        skipped_count = 0
        duplicate_count = 0
        errors: List[Dict[str, Any]] = []

        with conn.cursor() as cur:
            for i, line in enumerate(lines, start=1):
                try:
                    story = json.loads(line)

                    # search_text 생성
                    search_text = _build_search_text(story)
                    if not search_text or len(search_text.strip()) < 30:
                        skipped_count += 1
                        errors.append({"line": i, "error": "내용이 너무 짧습니다."})
                        continue

                    source = story.get("source", "unknown")
                    exam_info = story.get("exam_info") or {}
                    study_style = story.get("study_style") or {}
                    subject_methods = story.get("subject_methods") or {}
                    source_url = story.get("source_url")

                    # source_url 기반 중복 체크 (ON CONFLICT)
                    # source_url이 NULL이면 항상 삽입 (PostgreSQL UNIQUE는 NULL 허용)
                    cur.execute(
                        """
                        INSERT INTO mentoring_knowledge
                            (source, exam_info, study_style, daily_plan, subject_methods,
                             interview_prep, difficulties, key_points, search_text,
                             source_url, crawled_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (source_url) DO NOTHING
                        """,
                        (
                            source,
                            json.dumps(exam_info, ensure_ascii=False),
                            json.dumps(study_style, ensure_ascii=False),
                            story.get("daily_plan"),
                            json.dumps(subject_methods, ensure_ascii=False),
                            story.get("interview_prep"),
                            story.get("difficulties"),
                            story.get("key_points"),
                            search_text,
                            source_url,
                            story.get("crawled_at"),
                        ),
                    )
                    # rowcount = 0이면 ON CONFLICT로 스킵된 것 (중복)
                    if cur.rowcount == 0:
                        duplicate_count += 1
                    else:
                        inserted_count += 1

                except json.JSONDecodeError as e:
                    skipped_count += 1
                    errors.append({"line": i, "error": f"JSON 파싱 오류: {str(e)}"})
                except Exception as e:
                    skipped_count += 1
                    errors.append({"line": i, "error": str(e)})

        conn.commit()

        logger.info(
            f"[MentoringKnowledge] 업로드 완료: "
            f"{inserted_count}건 삽입, {duplicate_count}건 중복 스킵, {skipped_count}건 오류 스킵"
            + (f", {deleted_count}건 기존 삭제" if deleted_count else "")
        )

        msg_parts = [f"{inserted_count}건의 합격 수기가 저장되었습니다."]
        if duplicate_count > 0:
            msg_parts.append(f"{duplicate_count}건은 이미 존재하여 스킵됨.")
        msg_parts.append("임베딩 생성은 /enqueue-embeddings 를 호출하세요.")

        return {
            "success": True,
            "filename": file.filename,
            "total_lines": len(lines),
            "inserted_count": inserted_count,
            "duplicate_count": duplicate_count,
            "skipped_count": skipped_count,
            "deleted_existing": deleted_count,
            "errors": errors[:10] if errors else None,
            "message": " ".join(msg_parts),
            "next_step": "POST /api/v1/admin/mentoring-knowledge/enqueue-embeddings",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MentoringKnowledge] 업로드 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류: {str(e)}")


# ============================================================================
# 조회 엔드포인트
# ============================================================================

def _format_exam_title(exam_info: Dict[str, Any] | None) -> str:
    """exam_info JSONB에서 사람이 읽을 수 있는 제목을 생성합니다."""
    if not exam_info:
        return "합격 수기"
    parts: List[str] = []
    if exam_info.get("year"):
        parts.append(f"{exam_info['year']}년")
    if exam_info.get("exam_type"):
        parts.append(exam_info["exam_type"])
    if exam_info.get("grade"):
        parts.append(f"{exam_info['grade']}급")
    if exam_info.get("job_series"):
        parts.append(exam_info["job_series"])
    return " ".join(parts) if parts else "합격 수기"


@router.get("/", response_model=dict)
async def list_mentoring_knowledge(
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    size: int = Query(default=20, ge=1, le=100, description="페이지 크기"),
    source: Optional[str] = Query(default=None, description="출처 필터 (gongdanki / megagong)"),
    job_series: Optional[str] = Query(default=None, description="직렬 필터"),
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식(합격 수기) 목록 조회."""
    offset = (page - 1) * size

    conditions: List[str] = []
    params: List[Any] = []

    if source:
        conditions.append("source = %s")
        params.append(source)
    if job_series:
        conditions.append("exam_info->>'job_series' = %s")
        params.append(job_series)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM mentoring_knowledge {where}", params)
        total = cur.fetchone()[0]

        cur.execute(
            f"""
            SELECT id, source, exam_info, study_style, daily_plan,
                   key_points, source_url, created_at
            FROM mentoring_knowledge
            {where}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
            """,
            params + [size, offset],
        )
        rows = cur.fetchall()

    items = []
    for r in rows:
        exam_info = r[2] if isinstance(r[2], dict) else (json.loads(r[2]) if r[2] else {})
        study_style = r[3] if isinstance(r[3], dict) else (json.loads(r[3]) if r[3] else {})
        items.append({
            "id": r[0],
            "source": r[1],
            "title": _format_exam_title(exam_info),
            "exam_info": exam_info,
            "study_style": study_style,
            "daily_plan_preview": (r[4][:150] + "...") if r[4] and len(r[4]) > 150 else r[4],
            "key_points_preview": (r[5][:200] + "...") if r[5] and len(r[5]) > 200 else r[5],
            "source_url": r[6],
            "created_at": str(r[7]) if r[7] else None,
        })

    return {
        "success": True,
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "total_pages": (total + size - 1) // size,
    }


@router.get("/stats", response_model=dict)
async def get_mentoring_stats(
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식 통계."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM mentoring_knowledge")
        total = cur.fetchone()[0]

        cur.execute(
            """
            SELECT source, COUNT(*) as cnt
            FROM mentoring_knowledge
            GROUP BY source
            ORDER BY cnt DESC
            """
        )
        source_stats = [{"source": r[0], "count": r[1]} for r in cur.fetchall()]

        cur.execute(
            """
            SELECT exam_info->>'job_series' as job, COUNT(*) as cnt
            FROM mentoring_knowledge
            WHERE exam_info->>'job_series' IS NOT NULL
            GROUP BY exam_info->>'job_series'
            ORDER BY cnt DESC
            LIMIT 20
            """
        )
        job_stats = [{"job_series": r[0], "count": r[1]} for r in cur.fetchall()]

        cur.execute(
            "SELECT COUNT(*) FROM mentoring_knowledge WHERE knowledge_vector IS NOT NULL"
        )
        embedded_count = cur.fetchone()[0]

    return {
        "success": True,
        "total": total,
        "embedded_count": embedded_count,
        "source_distribution": source_stats,
        "job_series_distribution": job_stats,
    }


@router.get("/{knowledge_id}", response_model=dict)
async def get_mentoring_knowledge(
    knowledge_id: int,
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식(합격 수기) 상세 조회."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, source, exam_info, study_style, daily_plan,
                   subject_methods, interview_prep, difficulties, key_points,
                   source_url, crawled_at, created_at
            FROM mentoring_knowledge
            WHERE id = %s
            """,
            (knowledge_id,),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="멘토링 지식을 찾을 수 없습니다.")

    def _parse_json(val: Any) -> Any:
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val

    return {
        "success": True,
        "item": {
            "id": row[0],
            "source": row[1],
            "exam_info": _parse_json(row[2]),
            "study_style": _parse_json(row[3]),
            "daily_plan": row[4],
            "subject_methods": _parse_json(row[5]),
            "interview_prep": row[6],
            "difficulties": row[7],
            "key_points": row[8],
            "source_url": row[9],
            "crawled_at": str(row[10]) if row[10] else None,
            "created_at": str(row[11]) if row[11] else None,
        },
    }


# ============================================================================
# 텍스트 기반 검색 (벡터 임베딩 전 사용 가능)
# ============================================================================

@router.get("/search/text", response_model=dict)
async def search_mentoring_text(
    q: str = Query(..., description="검색 키워드"),
    top_k: int = Query(default=5, ge=1, le=20),
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """키워드 기반 멘토링 지식 검색 (ILIKE)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, source, exam_info, study_style,
                   daily_plan, key_points, source_url, created_at
            FROM mentoring_knowledge
            WHERE search_text ILIKE %s
               OR key_points ILIKE %s
               OR daily_plan ILIKE %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (f"%{q}%", f"%{q}%", f"%{q}%", top_k),
        )
        rows = cur.fetchall()

    items = []
    for r in rows:
        exam_info = r[2] if isinstance(r[2], dict) else (json.loads(r[2]) if r[2] else {})
        items.append({
            "id": r[0],
            "source": r[1],
            "title": _format_exam_title(exam_info),
            "exam_info": exam_info,
            "daily_plan_preview": (r[4][:150] + "...") if r[4] and len(r[4]) > 150 else r[4],
            "key_points_preview": (r[5][:200] + "...") if r[5] and len(r[5]) > 200 else r[5],
            "source_url": r[6],
            "created_at": str(r[7]) if r[7] else None,
        })

    return {
        "success": True,
        "query": q,
        "count": len(items),
        "items": items,
    }


# ============================================================================
# 임베딩 생성 (백그라운드 처리)
# ============================================================================

class MentoringEmbeddingRequest(BaseModel):
    """임베딩 생성 요청."""
    batch_size: int = Field(default=50, ge=1, le=500, description="내부 배치 크기 (한 번에 처리할 건수)")


def _run_embedding_background(batch_size: int = 50) -> None:
    """백그라운드에서 mentoring_knowledge 임베딩을 생성합니다.

    이벤트 루프를 블로킹하지 않도록 별도 스레드에서 실행됩니다.
    전체 미처리 레코드를 batch_size 단위로 나누어 처리합니다.

    주의: 별도 스레드이므로 전역 DB 연결을 공유하지 않고
    전용 커넥션을 생성하여 thread-safety를 보장합니다.
    """
    global _embedding_job

    from backend.core.utils.embedding import generate_embeddings_batch
    from backend.config import settings

    # ★ 별도 스레드 전용 DB 연결 생성 (전역 커넥션 공유 금지 - thread-safety)
    try:
        dsn = settings.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")
        conn = psycopg.connect(dsn, autocommit=True)
        # pgvector 어댑터 등록 (vector 타입 지원)
        try:
            from pgvector.psycopg import register_vector
            register_vector(conn)
            print("[MentoringEmbedding] pgvector 어댑터 등록 완료", flush=True)
        except Exception as vec_err:
            print(f"[MentoringEmbedding] ⚠️ pgvector 등록 실패(무시): {vec_err}", flush=True)
        print("[MentoringEmbedding] 백그라운드 전용 DB 연결 생성 완료", flush=True)
    except Exception as e:
        _embedding_job["running"] = False
        _embedding_job["message"] = f"DB 연결 실패: {e}"
        print(f"[MentoringEmbedding] ❌ 백그라운드 DB 연결 실패: {e}", flush=True)
        logger.error(f"[MentoringEmbedding] 백그라운드 DB 연결 실패: {e}")
        return

    _embedding_job["processed"] = 0
    _embedding_job["errors"] = 0
    _embedding_job["message"] = "임베딩 생성 중..."

    try:
        # 전체 미처리 건수
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge WHERE knowledge_vector IS NULL")
            total_pending = cur.fetchone()[0]

        _embedding_job["total"] = total_pending

        if total_pending == 0:
            _embedding_job["running"] = False
            _embedding_job["message"] = "임베딩이 필요한 데이터가 없습니다."
            return

        logger.info(
            f"[MentoringEmbedding] 백그라운드 임베딩 시작: "
            f"전체 {total_pending}건, batch_size={batch_size}"
        )
        print(
            f"[MentoringEmbedding] 백그라운드 임베딩 시작: "
            f"전체 {total_pending}건, batch_size={batch_size}",
            flush=True,
        )

        while _embedding_job["running"]:
            # 미처리 레코드 가져오기
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, search_text
                    FROM mentoring_knowledge
                    WHERE knowledge_vector IS NULL
                    ORDER BY id
                    LIMIT %s
                    """,
                    (batch_size,),
                )
                rows = cur.fetchall()

            if not rows:
                break

            # 텍스트 준비
            ids: List[int] = []
            texts: List[str] = []
            for row in rows:
                mk_id = row[0]
                search_text = row[1] or ""
                # KURE-v1 최대 512토큰 ≈ ~1500자
                if len(search_text) > 1500:
                    search_text = search_text[:1500]
                ids.append(mk_id)
                texts.append(search_text)

            # KURE-v1 배치 임베딩 생성 (동기 - 별도 스레드에서 실행)
            try:
                print(f"[MentoringEmbedding] KURE-v1 배치 임베딩 생성 중... ({len(texts)}건)", flush=True)
                vectors = generate_embeddings_batch(texts, batch_size=32)
                print(f"[MentoringEmbedding] KURE-v1 임베딩 생성 완료: {len(vectors)}건, 차원={len(vectors[0]) if vectors else 0}", flush=True)
            except Exception as e:
                import traceback
                print(f"[MentoringEmbedding] ❌ KURE-v1 임베딩 실패: {e}", flush=True)
                traceback.print_exc()
                logger.error(f"[MentoringEmbedding] KURE-v1 임베딩 실패: {e}")
                _embedding_job["message"] = f"KURE-v1 오류: {e}"
                _embedding_job["errors"] += len(ids)
                break

            # DB에 저장 (autocommit=True이므로 commit 불필요)
            save_ok = 0
            save_fail = 0
            for mk_id, vec in zip(ids, vectors):
                try:
                    embedding_str = "[" + ",".join(map(str, vec)) + "]"
                    with conn.cursor() as update_cur:
                        update_cur.execute(
                            """
                            UPDATE mentoring_knowledge
                            SET knowledge_vector = %s::vector
                            WHERE id = %s
                            """,
                            (embedding_str, mk_id),
                        )
                    _embedding_job["processed"] += 1
                    save_ok += 1
                except Exception as e:
                    if save_fail == 0:  # 첫 번째 에러만 상세 출력
                        print(f"[MentoringEmbedding] ❌ ID {mk_id} DB 저장 실패: {type(e).__name__}: {e}", flush=True)
                    logger.error(f"[MentoringEmbedding] ID {mk_id} DB 저장 실패: {e}")
                    _embedding_job["errors"] += 1
                    save_fail += 1

            print(f"[MentoringEmbedding] 배치 DB 저장 결과: 성공={save_ok}, 실패={save_fail}", flush=True)

            current = _embedding_job["processed"]
            _embedding_job["message"] = f"{current}건 처리 완료 (전체 {total_pending}건 중)"
            logger.info(f"[MentoringEmbedding] 진행: {current}/{total_pending}건 완료")
            print(
                f"[MentoringEmbedding] 진행: {current}/{total_pending}건 완료",
                flush=True,
            )

    except Exception as e:
        import traceback
        print(f"[MentoringEmbedding] ❌ 백그라운드 전체 오류: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        logger.error(f"[MentoringEmbedding] 백그라운드 오류: {e}", exc_info=True)
        _embedding_job["message"] = f"오류: {e}"
    finally:
        # 전용 커넥션 반드시 닫기
        try:
            conn.close()
            logger.info("[MentoringEmbedding] 백그라운드 전용 DB 연결 종료")
        except Exception:
            pass

        _embedding_job["running"] = False
        total_done = _embedding_job["processed"]
        total_err = _embedding_job["errors"]
        _embedding_job["message"] = (
            f"완료: {total_done}건 임베딩 생성, {total_err}건 실패"
        )
        logger.info(
            f"[MentoringEmbedding] 백그라운드 완료: "
            f"{total_done}건 성공, {total_err}건 실패"
        )
        print(
            f"[MentoringEmbedding] 백그라운드 완료: "
            f"{total_done}건 성공, {total_err}건 실패",
            flush=True,
        )


@router.post("/enqueue-embeddings")
async def enqueue_mentoring_embeddings(
    request: MentoringEmbeddingRequest = MentoringEmbeddingRequest(),
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식 임베딩 생성 엔드포인트.

    knowledge_vector가 NULL인 레코드의 search_text를 KURE-v1로 임베딩합니다.
    백그라운드 스레드에서 처리하며, 즉시 응답을 반환합니다.
    진행 상황은 /embedding-status 또는 /embedding-job-status 로 확인하세요.
    """
    global _embedding_job

    # 이미 실행 중이면 중복 실행 방지
    if _embedding_job["running"]:
        return {
            "success": True,
            "message": f"이미 임베딩 작업이 진행 중입니다. ({_embedding_job['processed']}건 처리됨)",
            "processed_count": _embedding_job["processed"],
            "total_count": _embedding_job["total"],
            "remaining_count": _embedding_job["total"] - _embedding_job["processed"],
            "mode": "background_running",
        }

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge WHERE knowledge_vector IS NULL")
            pending_count = cur.fetchone()[0]

        if pending_count == 0:
            return {
                "success": True,
                "message": "임베딩이 필요한 멘토링 지식이 없습니다.",
                "processed_count": 0,
                "total_count": 0,
                "remaining_count": 0,
                "mode": "none",
            }

        # 백그라운드 작업 상태 초기화
        _embedding_job = {
            "running": True,
            "processed": 0,
            "total": pending_count,
            "errors": 0,
            "started_at": time.time(),
            "message": "임베딩 생성 시작 중...",
        }

        # 별도 스레드에서 임베딩 실행 (이벤트 루프 블로킹 방지)
        batch_size = request.batch_size
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _run_embedding_background, batch_size)

        logger.info(
            f"[MentoringKnowledge] 백그라운드 임베딩 스케줄됨: "
            f"{pending_count}건, batch_size={batch_size}"
        )

        return {
            "success": True,
            "message": f"{pending_count}건의 임베딩 생성을 백그라운드에서 시작했습니다.",
            "processed_count": 0,
            "total_count": pending_count,
            "remaining_count": pending_count,
            "mode": "background",
        }

    except Exception as e:
        logger.error(f"[MentoringKnowledge] 임베딩 스케줄 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"임베딩 생성 오류: {str(e)}")


@router.post("/stop-embeddings")
async def stop_mentoring_embeddings() -> dict:
    """진행 중인 백그라운드 임베딩 작업을 중단합니다."""
    global _embedding_job

    if not _embedding_job["running"]:
        return {
            "success": True,
            "message": "진행 중인 임베딩 작업이 없습니다.",
        }

    _embedding_job["running"] = False
    return {
        "success": True,
        "message": f"임베딩 작업 중단 요청됨 ({_embedding_job['processed']}건 처리됨)",
        "processed_count": _embedding_job["processed"],
    }


@router.get("/embedding-job-status")
async def get_embedding_job_status() -> dict:
    """백그라운드 임베딩 작업 상태 조회."""
    elapsed = 0.0
    if _embedding_job["started_at"]:
        elapsed = time.time() - _embedding_job["started_at"]

    return {
        "success": True,
        "running": _embedding_job["running"],
        "processed": _embedding_job["processed"],
        "total": _embedding_job["total"],
        "errors": _embedding_job["errors"],
        "elapsed_seconds": round(elapsed, 1),
        "message": _embedding_job["message"],
    }


@router.get("/embedding-status")
async def get_mentoring_embedding_status(
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식 임베딩 상태 조회."""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge")
            total_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge WHERE knowledge_vector IS NOT NULL")
            embedded_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM mentoring_knowledge WHERE knowledge_vector IS NULL")
            remaining_count = cur.fetchone()[0]

        return {
            "success": True,
            "is_complete": remaining_count == 0,
            "total_count": total_count,
            "embedded_count": embedded_count,
            "remaining_count": remaining_count,
            "progress_percent": round(embedded_count / total_count * 100, 1) if total_count > 0 else 0,
            "message": "완료" if remaining_count == 0 else f"{remaining_count}건 남음",
        }

    except Exception as e:
        logger.error(f"[MentoringKnowledge] 임베딩 상태 조회 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 삭제
# ============================================================================

@router.delete("/all", response_model=dict)
async def delete_all_mentoring_knowledge(
    conn: psycopg.Connection = Depends(get_db_connection),
) -> dict:
    """멘토링 지식 전체 삭제."""
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM mentoring_knowledge")
            deleted_count = cur.rowcount

        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"{deleted_count}건의 멘토링 지식이 삭제되었습니다.",
        }
    except Exception as e:
        logger.error(f"[MentoringKnowledge] 전체 삭제 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
