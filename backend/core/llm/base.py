"""LLM 추상 베이스 클래스."""
from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseLLM(ABC):
    """LLM 모델의 추상 베이스 클래스.
    
    모든 LLM 구현체는 이 클래스를 상속받아야 합니다.
    """

    def __init__(self, model_path: Optional[str] = None, **kwargs: Any):
        """LLM 초기화.
        
        Args:
            model_path: 모델 파일 경로 (로컬 모델의 경우)
            **kwargs: 모델별 추가 설정
        """
        self.model_path = model_path
        self.config = kwargs
        self._model: Any = None

    @abstractmethod
    def load(self) -> None:
        """모델을 메모리에 로드합니다."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """모델을 메모리에서 해제합니다."""
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """텍스트를 생성합니다.
        
        Args:
            prompt: 입력 프롬프트
            **kwargs: 생성 파라미터 (temperature, max_tokens 등)
            
        Returns:
            생성된 텍스트
        """
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """모델이 로드되었는지 확인합니다.
        
        Returns:
            모델 로드 여부
        """
        pass

    @property
    def model(self) -> Any:
        """로드된 모델 인스턴스를 반환합니다."""
        if not self.is_loaded():
            raise RuntimeError("모델이 로드되지 않았습니다. load()를 먼저 호출하세요.")
        return self._model

