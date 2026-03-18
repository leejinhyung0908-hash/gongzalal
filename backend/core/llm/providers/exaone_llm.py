"""EXAONE 모델 LLM 구현체.

GGUF 파일이 있으면 llama-cpp-python으로 로드 (CPU 최적화, AVX512).
없으면 transformers pipeline으로 자동 폴백.
"""
import gc
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

from backend.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)

# GGUF 모델 위치 설정 (환경변수로 재정의 가능)
_GGUF_DIR = os.getenv("EXAONE_GGUF_DIR", "artifacts/base-models/exaone-gguf")
_GGUF_FILENAME = os.getenv(
    "EXAONE_GGUF_FILENAME", "EXAONE-3.5-2.4B-Instruct-Q4_K_M.gguf"
)


def _find_gguf_path(model_path: str) -> Optional[str]:
    """GGUF 파일 경로 탐색.

    우선순위:
    1. model_path 자체가 .gguf 파일인 경우
    2. EXAONE_GGUF_DIR / EXAONE_GGUF_FILENAME
    3. model_path 디렉토리 내 첫 번째 .gguf 파일
    4. EXAONE_GGUF_DIR 내 첫 번째 .gguf 파일
    """
    if model_path.endswith(".gguf") and os.path.isfile(model_path):
        return model_path

    explicit = os.path.join(_GGUF_DIR, _GGUF_FILENAME)
    if os.path.isfile(explicit):
        return explicit

    for search_dir in [model_path, _GGUF_DIR]:
        if os.path.isdir(search_dir):
            for fname in sorted(os.listdir(search_dir)):
                if fname.endswith(".gguf"):
                    return os.path.join(search_dir, fname)

    return None


class ExaoneLLM(BaseLLM):
    """EXAONE 모델 LLM.

    GGUF 파일 존재 시  → llama-cpp-python (AVX512, ~10배 빠름)
    GGUF 없을 시       → transformers pipeline (기존 방식)
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        lora_adapter_path: Optional[str] = None,
        **kwargs: Any,
    ):
        if model_path is None:
            model_path = "artifacts/base-models/exaone"

        super().__init__(model_path, **kwargs)

        self.lora_adapter_path = lora_adapter_path
        self.load_in_4bit = kwargs.get("load_in_4bit", True)
        self.load_in_8bit = kwargs.get("load_in_8bit", False)
        self.device_map = kwargs.get("device_map", "auto")
        self.trust_remote_code = kwargs.get("trust_remote_code", True)

        # 실행 모드: "gguf" | "transformers" | "unloaded"
        self._mode: str = "unloaded"
        self._llama = None        # llama-cpp-python Llama 인스턴스
        self._model = None        # transformers 모델
        self._tokenizer = None
        self._pipeline = None

    # ────────────────────────────────────────────
    # 로드
    # ────────────────────────────────────────────

    def load(self) -> None:
        """모델을 로드합니다. GGUF가 있으면 우선 사용합니다."""
        if self.is_loaded():
            print(f"[ExaoneLLM] 이미 로드됨 ({self._mode})", flush=True)
            return

        gc.collect()

        gguf_path = _find_gguf_path(self.model_path)
        if gguf_path:
            self._load_gguf(gguf_path)
        else:
            logger.warning(
                "[ExaoneLLM] GGUF 파일 없음 → transformers fallback "
                f"(GGUF_DIR={_GGUF_DIR})"
            )
            self._load_transformers()

    def _load_gguf(self, gguf_path: str) -> None:
        """llama-cpp-python으로 GGUF 모델을 로드합니다."""
        try:
            from llama_cpp import Llama
        except ImportError:
            print(
                "[ExaoneLLM] llama-cpp-python 미설치 → transformers fallback",
                flush=True,
            )
            self._load_transformers()
            return

        cpu_count = os.cpu_count() or 1
        print(f"[ExaoneLLM] GGUF 로드 시작: {gguf_path}", flush=True)

        self._llama = Llama(
            model_path=gguf_path,
            n_ctx=4096,               # 학습계획(~4K 토큰) 등 긴 프롬프트 지원
            n_threads=cpu_count,      # 추론 스레드
            n_threads_batch=cpu_count,# 배치 인코딩 스레드
            n_gpu_layers=0,           # CPU 전용
            verbose=False,
        )
        self._mode = "gguf"
        logger.info(f"[ExaoneLLM] GGUF 로드 완료 (threads={cpu_count}, path={gguf_path})")
        print(f"[ExaoneLLM] GGUF 로드 완료 (threads={cpu_count})", flush=True)

    def _load_transformers(self) -> None:
        """transformers pipeline으로 모델을 로드합니다 (GGUF 없을 때 폴백)."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

        print(f"[ExaoneLLM] Transformers 모드 로드 시작: {self.model_path}", flush=True)

        load_dtype = torch.bfloat16 if not torch.cuda.is_available() else torch.float16

        model_kwargs: dict = {
            "device_map": self.device_map,
            "trust_remote_code": self.trust_remote_code,
            "low_cpu_mem_usage": True,
            "torch_dtype": load_dtype,
        }

        if self.load_in_4bit:
            try:
                from transformers import BitsAndBytesConfig
                model_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )
                print("[ExaoneLLM] 4-bit NF4 양자화 활성화", flush=True)
            except ImportError:
                print("[ExaoneLLM] bitsandbytes 미설치 → 양자화 없이 로드", flush=True)

        self._model = AutoModelForCausalLM.from_pretrained(
            self.model_path, **model_kwargs
        )
        gc.collect()

        if self.lora_adapter_path:
            from peft import PeftModel
            lp = Path(self.lora_adapter_path)
            if lp.exists():
                print(f"[ExaoneLLM] LoRA 어댑터 로드: {lp}", flush=True)
                self._model = PeftModel.from_pretrained(self._model, str(lp))

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.model_path, trust_remote_code=self.trust_remote_code
        )
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        if not torch.cuda.is_available():
            cpu_count = os.cpu_count() or 1
            try:
                torch.set_num_threads(cpu_count)
            except RuntimeError:
                pass
            try:
                torch.set_num_interop_threads(max(1, cpu_count // 2))
            except RuntimeError:
                pass

        self._pipeline = pipeline(
            "text-generation", model=self._model, tokenizer=self._tokenizer
        )
        self._mode = "transformers"
        print(f"[ExaoneLLM] Transformers 로드 완료 (dtype={load_dtype})", flush=True)

    # ────────────────────────────────────────────
    # 생성
    # ────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 50,
        **kwargs: Any,
    ) -> str:
        """텍스트를 생성합니다."""
        if not self.is_loaded():
            raise RuntimeError("모델이 로드되지 않았습니다. load()를 먼저 호출하세요.")

        if self._mode == "gguf":
            return self._generate_gguf(prompt, max_new_tokens, **kwargs)
        return self._generate_transformers(
            prompt, max_new_tokens, temperature, top_p, top_k, **kwargs
        )

    def _generate_gguf(self, prompt: str, max_new_tokens: int, **kwargs: Any) -> str:
        """llama-cpp-python으로 텍스트를 생성합니다."""
        kwargs.pop("max_time", None)  # llama-cpp에 없는 파라미터 제거

        try:
            response = self._llama.create_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 공무원 시험 합격을 위한 AI 멘토입니다. "
                            "합격자 수기를 바탕으로 구체적이고 따뜻한 조언을 해주세요."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_new_tokens,
                temperature=0.0,       # greedy decoding (do_sample=False 동일)
                top_p=1.0,
                repeat_penalty=1.1,
                stop=["[|endofturn|]", "[|user|]", "[|system|]"],
            )
            text = response["choices"][0]["message"]["content"]
            return text.strip()
        except Exception as e:
            logger.error(f"[ExaoneLLM] GGUF 생성 오류: {e}")
            return f"생성 중 오류가 발생했습니다: {e}"

    def _generate_transformers(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
        **kwargs: Any,
    ) -> str:
        """transformers pipeline으로 텍스트를 생성합니다."""
        import torch

        formatted_prompt = f"[INST] {prompt} [/INST]"
        max_time = kwargs.pop("max_time", None)

        try:
            with torch.inference_mode():
                outputs = self._pipeline(
                    formatted_prompt,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    max_time=max_time,
                    return_full_text=False,
                    **kwargs,
                )
            if outputs and len(outputs) > 0:
                return self._clean_response(outputs[0]["generated_text"])
            return "응답을 생성하지 못했습니다."
        except Exception as e:
            logger.error(f"[ExaoneLLM] Transformers 생성 오류: {e}")
            return f"생성 중 오류가 발생했습니다: {e}"

    def _clean_response(self, text: str) -> str:
        """생성된 응답에서 프롬프트 태그를 제거합니다."""
        text = text.strip()
        if "[/INST]" in text:
            text = text.split("[/INST]")[-1].strip()
        text = re.sub(r"\[INST\].*?\[/INST\]", "", text, flags=re.DOTALL).strip()
        return text

    # ────────────────────────────────────────────
    # 상태 조회
    # ────────────────────────────────────────────

    def is_loaded(self) -> bool:
        return self._mode in ("gguf", "transformers")

    def get_mode(self) -> str:
        """현재 실행 모드를 반환합니다: 'gguf' | 'transformers' | 'unloaded'"""
        return self._mode

    # ────────────────────────────────────────────
    # 언로드
    # ────────────────────────────────────────────

    def unload(self) -> None:
        """모델을 메모리에서 해제합니다."""
        if self._llama is not None:
            del self._llama
            self._llama = None
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None

        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

        self._mode = "unloaded"
        print(f"[ExaoneLLM] 모델 언로드 완료: {self.model_path}", flush=True)

    def get_model(self):
        """로드된 모델 인스턴스를 반환합니다."""
        return self._model or self._llama
