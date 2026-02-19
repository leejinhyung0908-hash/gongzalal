"""공통 LLM 모듈."""
from backend.core.llm.base import BaseLLM
from backend.core.llm.factory import LLMFactory
from backend.core.llm.registry import ModelRegistry

# 호환성을 위한 alias
LLMRegistry = ModelRegistry

__all__ = ["BaseLLM", "LLMFactory", "LLMRegistry", "ModelRegistry"]
