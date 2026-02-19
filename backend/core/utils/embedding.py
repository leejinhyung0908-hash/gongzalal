"""KURE-v1 기반 임베딩 서비스.

한국어 특화 SentenceTransformer 모델(nlpai-lab/KURE-v1)을 사용하여
텍스트를 1024차원 벡터로 변환합니다.

- 싱글 텍스트 임베딩: generate_embedding()
- 배치 텍스트 임베딩: generate_embeddings_batch()
- 모델 lazy loading (최초 호출 시 1회 로드)
"""

from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# KURE-v1 모델 (lazy loading)
# ─────────────────────────────────────────────────────────────
_model = None
KURE_MODEL_NAME = "nlpai-lab/KURE-v1"
KURE_EMBED_DIM = 1024  # KURE-v1 출력 차원


def _load_model():
    """SentenceTransformer 모델을 lazy load 합니다."""
    global _model
    if _model is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer

        logger.info("[Embedding] KURE-v1 모델 로딩 중...")
        print("[Embedding] KURE-v1 모델 로딩 중...", flush=True)
        _model = SentenceTransformer(KURE_MODEL_NAME)
        dim = _model.get_sentence_embedding_dimension()
        logger.info(f"[Embedding] KURE-v1 로드 완료 (차원: {dim})")
        print(f"[Embedding] KURE-v1 로드 완료 (차원: {dim})", flush=True)

        if dim != KURE_EMBED_DIM:
            logger.warning(
                f"[Embedding] ⚠️ 예상 차원({KURE_EMBED_DIM})과 실제 차원({dim})이 다릅니다!"
            )

        return _model

    except ImportError:
        logger.error(
            "[Embedding] sentence-transformers 미설치. "
            "pip install sentence-transformers 를 실행하세요."
        )
        raise
    except Exception as e:
        logger.error(f"[Embedding] KURE-v1 모델 로드 실패: {e}")
        raise


# ─────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────

def get_embed_dim() -> int:
    """현재 임베딩 모델의 출력 차원을 반환합니다."""
    return KURE_EMBED_DIM


def generate_embedding(text: str) -> List[float]:
    """단일 텍스트를 KURE-v1 임베딩 벡터로 변환합니다.

    Args:
        text: 임베딩할 텍스트

    Returns:
        1024차원 float 리스트
    """
    if not text or not isinstance(text, str):
        return [0.0] * KURE_EMBED_DIM

    model = _load_model()
    embedding = model.encode(
        text,
        convert_to_tensor=False,
        normalize_embeddings=True,
    )
    return embedding.tolist()


def generate_embeddings_batch(
    texts: List[str],
    batch_size: int = 32,
) -> List[List[float]]:
    """여러 텍스트를 배치로 임베딩합니다.

    Args:
        texts: 임베딩할 텍스트 리스트
        batch_size: SentenceTransformer 내부 배치 크기

    Returns:
        각 텍스트에 대한 1024차원 벡터 리스트
    """
    if not texts:
        return []

    model = _load_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_tensor=False,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 100,
    )
    return embeddings.tolist()


# ─────────────────────────────────────────────────────────────
# 하위 호환성 (기존 코드에서 simple_embed 호출 시)
# ─────────────────────────────────────────────────────────────

def simple_embed(text: str, *, dim: Optional[int] = None) -> List[float]:
    """하위 호환용 래퍼. KURE-v1으로 임베딩을 생성합니다.

    dim 파라미터는 무시됩니다 (KURE-v1은 항상 1024차원).
    """
    return generate_embedding(text)
