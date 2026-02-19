"""모델 타입 등록 모듈.

애플리케이션 시작 시 호출하여 모델 타입을 등록합니다.
"""
from backend.core.llm.factory import get_factory
from backend.core.llm.providers.midm_llm import MidmLLM
from backend.core.llm.providers.exaone_llm import ExaoneLLM


def register_all_models() -> None:
    """모든 모델 타입을 레지스트리에 등록합니다."""
    factory = get_factory()

    # Mi:dm 모델 등록
    factory.register("midm", MidmLLM)
    factory.register("local", MidmLLM)  # 기본 로컬 모델로도 사용 가능

    # EXAONE 모델 등록
    factory.register("exaone", ExaoneLLM)
    factory.register("exaone-2.4b", ExaoneLLM)
    factory.register("exaone-3.5b", ExaoneLLM)  # 3.5B 추가
    factory.register("exaone-7.8b", ExaoneLLM)

    print("[ModelRegistry] 모델 타입 등록 완료: midm, local, exaone (2.4b, 3.5b, 7.8b)", flush=True)

