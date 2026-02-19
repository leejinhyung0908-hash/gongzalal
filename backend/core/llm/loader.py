"""모델 로더 - 모델 파일 로드 및 관리."""
import os
from pathlib import Path
from typing import Any, Dict, Optional

from backend.config import settings
from backend.core.llm.base import BaseLLM
from backend.core.llm.factory import get_factory


class ModelLoader:
    """모델 파일을 로드하고 관리하는 클래스."""

    def __init__(self, base_path: Optional[str] = None):
        """로더 초기화.

        Args:
            base_path: 모델 파일의 기본 경로 (기본값: 설정에서 가져옴)
        """
        self.base_path = Path(base_path) if base_path else Path(settings.MODEL_BASE_PATH)
        self._loaded_models: Dict[str, BaseLLM] = {}

    def load_model(
        self,
        model_name: str,
        model_type: str = "local",
        **kwargs: Any
    ) -> BaseLLM:
        """모델을 로드합니다.

        Args:
            model_name: 모델 이름 또는 경로
            model_type: 모델 타입 (기본값: "local")
            **kwargs: 모델별 추가 설정

        Returns:
            로드된 LLM 인스턴스
        """
        # 이미 로드된 모델이 있으면 반환
        cache_key = f"{model_type}:{model_name}"
        if cache_key in self._loaded_models:
            return self._loaded_models[cache_key]

        # 모델 경로 결정
        model_path = self._resolve_model_path(model_name)
        if model_path is None:
            raise FileNotFoundError(
                f"모델 경로를 찾을 수 없습니다: {model_name}. "
                f"base_path: {self.base_path}"
            )

        # 팩토리를 통해 모델 생성
        factory = get_factory()
        llm = factory.create(
            model_type=model_type,
            model_path=str(model_path),
            **kwargs
        )

        # 모델 로드
        llm.load()

        # 캐시에 저장
        self._loaded_models[cache_key] = llm

        return llm

    def unload_model(self, model_name: str, model_type: str = "local") -> None:
        """모델을 언로드합니다.

        Args:
            model_name: 모델 이름
            model_type: 모델 타입
        """
        cache_key = f"{model_type}:{model_name}"
        if cache_key in self._loaded_models:
            llm = self._loaded_models[cache_key]
            llm.unload()
            del self._loaded_models[cache_key]

    def unload_all(self) -> None:
        """모든 로드된 모델을 언로드합니다."""
        for llm in self._loaded_models.values():
            try:
                llm.unload()
            except Exception:
                pass
        self._loaded_models.clear()

    def get_model(self, model_name: str, model_type: str = "local") -> Optional[BaseLLM]:
        """로드된 모델을 가져옵니다.

        Args:
            model_name: 모델 이름
            model_type: 모델 타입

        Returns:
            LLM 인스턴스 또는 None
        """
        cache_key = f"{model_type}:{model_name}"
        return self._loaded_models.get(cache_key)

    def _resolve_model_path(self, model_name: str) -> Optional[Path]:
        """모델 경로를 해석합니다.

        Args:
            model_name: 모델 이름 또는 경로

        Returns:
            모델 경로 또는 None
        """
        # 절대 경로인 경우
        if os.path.isabs(model_name):
            path = Path(model_name)
            return path if path.exists() else None

        # 상대 경로인 경우 - 현재 작업 디렉토리 기준
        current_dir = Path.cwd()
        relative_path = current_dir / model_name
        if relative_path.exists():
            return relative_path

        # base_path 기준으로 해석
        model_path = self.base_path / model_name
        if model_path.exists():
            return model_path

        # backend 디렉토리 기준으로 찾기 (backend/model/midm)
        backend_dir = Path(__file__).parent.parent
        backend_model_path = backend_dir / "model" / model_name
        if backend_model_path.exists():
            return backend_model_path

        return None


# 전역 로더 인스턴스
_loader: Optional[ModelLoader] = None


def get_loader() -> ModelLoader:
    """전역 모델 로더 인스턴스를 반환합니다.

    Returns:
        ModelLoader 인스턴스
    """
    global _loader
    if _loader is None:
        _loader = ModelLoader()
    return _loader


def set_loader(loader: ModelLoader) -> None:
    """전역 모델 로더 인스턴스를 설정합니다.

    Args:
        loader: 설정할 로더 인스턴스
    """
    global _loader
    _loader = loader

