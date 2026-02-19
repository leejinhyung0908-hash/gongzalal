"""모델 레지스트리 - 모델 타입 등록 및 관리."""
from typing import Dict, Optional, Type

from backend.core.llm.base import BaseLLM


class ModelRegistry:
    """LLM 모델 타입을 등록하고 관리하는 레지스트리."""

    def __init__(self):
        """레지스트리 초기화."""
        self._registry: Dict[str, Type[BaseLLM]] = {}

    def register(self, model_type: str, llm_class: Type[BaseLLM]) -> None:
        """모델 타입을 등록합니다.

        Args:
            model_type: 모델 타입 이름 (예: "local", "openai")
            llm_class: BaseLLM을 상속받은 클래스

        Raises:
            ValueError: llm_class가 BaseLLM을 상속받지 않은 경우
        """
        if not issubclass(llm_class, BaseLLM):
            raise ValueError(
                f"{llm_class.__name__}는 BaseLLM을 상속받아야 합니다."
            )

        self._registry[model_type] = llm_class

    def get(self, model_type: str) -> Optional[Type[BaseLLM]]:
        """등록된 모델 클래스를 가져옵니다.

        Args:
            model_type: 모델 타입 이름

        Returns:
            모델 클래스 또는 None
        """
        return self._registry.get(model_type)

    def unregister(self, model_type: str) -> None:
        """모델 타입을 등록 해제합니다.

        Args:
            model_type: 모델 타입 이름
        """
        self._registry.pop(model_type, None)

    def list_types(self) -> list[str]:
        """등록된 모든 모델 타입 목록을 반환합니다.

        Returns:
            모델 타입 목록
        """
        return list(self._registry.keys())

    def is_registered(self, model_type: str) -> bool:
        """모델 타입이 등록되어 있는지 확인합니다.

        Args:
            model_type: 모델 타입 이름

        Returns:
            등록 여부
        """
        return model_type in self._registry

    def clear(self) -> None:
        """모든 등록을 초기화합니다."""
        self._registry.clear()

