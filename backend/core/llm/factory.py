"""LLM 팩토리 패턴 구현."""
from typing import Any, Dict, Optional, Type

from backend.core.llm.base import BaseLLM
from backend.core.llm.registry import ModelRegistry


class LLMFactory:
    """LLM 인스턴스를 생성하는 팩토리 클래스."""

    def __init__(self, registry: Optional[ModelRegistry] = None):
        """팩토리 초기화.

        Args:
            registry: 모델 레지스트리 (기본값: None, 새 인스턴스 생성)
        """
        self.registry = registry or ModelRegistry()

    def create(
        self,
        model_type: str,
        model_path: Optional[str] = None,
        **kwargs: Any
    ) -> BaseLLM:
        """지정된 타입의 LLM 인스턴스를 생성합니다.

        Args:
            model_type: 모델 타입 (예: "local", "openai", "huggingface")
            model_path: 모델 파일 경로
            **kwargs: 모델별 추가 설정

        Returns:
            LLM 인스턴스

        Raises:
            ValueError: 지원하지 않는 모델 타입인 경우
        """
        llm_class = self.registry.get(model_type)
        if llm_class is None:
            raise ValueError(
                f"지원하지 않는 모델 타입: {model_type}. "
                f"사용 가능한 타입: {list(self.registry.list_types())}"
            )

        return llm_class(model_path=model_path, **kwargs)

    def register(self, model_type: str, llm_class: Type[BaseLLM]) -> None:
        """새로운 모델 타입을 등록합니다.

        Args:
            model_type: 모델 타입 이름
            llm_class: BaseLLM을 상속받은 클래스
        """
        self.registry.register(model_type, llm_class)

    def list_available_types(self) -> list[str]:
        """사용 가능한 모델 타입 목록을 반환합니다.

        Returns:
            모델 타입 목록
        """
        return list(self.registry.list_types())


# 전역 팩토리 인스턴스
_factory: Optional[LLMFactory] = None


def get_factory() -> LLMFactory:
    """전역 LLM 팩토리 인스턴스를 반환합니다.

    Returns:
        LLMFactory 인스턴스
    """
    global _factory
    if _factory is None:
        _factory = LLMFactory()
    return _factory


def set_factory(factory: LLMFactory) -> None:
    """전역 LLM 팩토리 인스턴스를 설정합니다.

    Args:
        factory: 설정할 팩토리 인스턴스
    """
    global _factory
    _factory = factory

