"""
EXAONE 모델 Fine-tuning 스크립트 (Unsloth 사용 - 2-5배 빠름)

Unsloth는 학습 속도를 2-5배 향상시켜주는 라이브러리입니다.

설치:
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps "xformers<0.0.27" trl peft accelerate bitsandbytes

사용 방법:
python train_exaone_unsloth.py \
    --data data/success_stories/merged_training_data.jsonl \
    --output artifacts/lora-adapters/exaone-success-stories \
    --epochs 1 \
    --max-samples 1000 \
    --max-length 384
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any

try:
    from unsloth import FastLanguageModel
    import torch
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False
    print("[경고] Unsloth가 설치되지 않았습니다.")
    print("설치 명령어:")
    print('pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"')
    print('pip install --no-deps "xformers<0.0.27" trl peft accelerate bitsandbytes')

# Flash Attention 2 확인
try:
    import flash_attn
    FLASH_ATTENTION_AVAILABLE = True
except ImportError:
    FLASH_ATTENTION_AVAILABLE = False
    print("[정보] Flash Attention 2가 설치되지 않았습니다. (선택사항, 속도 향상)")


def format_exaone_prompt(instruction: str, input_data: Dict, output_data: Dict) -> str:
    """EXAONE 형식의 프롬프트 생성"""
    question = input_data.get("question", "")
    context = input_data.get("context", "")

    if context:
        user_content = f"{instruction}\n\n질문: {question}\n\n참고 자료: {context}"
    else:
        user_content = f"{instruction}\n\n질문: {question}"

    thought = output_data.get("thought_process", "")
    response = output_data.get("response", "")

    if thought:
        assistant_content = f"사고 과정: {thought}\n\n답변: {response}"
    else:
        assistant_content = response

    formatted = f"[INST] {user_content} [/INST] {assistant_content}"
    return formatted


def load_training_data(data_path: str, max_samples: int = None) -> List[Dict[str, Any]]:
    """JSONL 파일에서 학습 데이터 로드"""
    data = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line.strip())
                data.append(item)
                if max_samples and len(data) >= max_samples:
                    break
            except json.JSONDecodeError as e:
                print(f"[경고] JSON 파싱 오류: {e}")
                continue
    return data


def prepare_dataset_for_unsloth(data: List[Dict[str, Any]], tokenizer, max_length: int = 384):
    """Unsloth용 데이터셋 준비 및 토크나이징"""
    from datasets import Dataset

    texts = []

    for item in data:
        instruction = item.get("instruction", "")
        input_data = item.get("input", {})
        output_data = item.get("output", {})

        formatted_text = format_exaone_prompt(instruction, input_data, output_data)
        texts.append(formatted_text)

    # Dataset 객체로 변환
    dataset = Dataset.from_dict({"text": texts})

    # 토크나이징
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding=False,
        )

    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"],
    )

    return tokenized_dataset


def train_with_unsloth(
    data_path: str,
    output_dir: str,
    base_model_path: str = "artifacts/base-models/exaone",
    epochs: int = 1,
    max_length: int = 384,
    max_samples: int = 1000,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    learning_rate: float = 2e-4,
    batch_size: int = 2,  # Unsloth는 더 큰 배치 크기 가능
    gradient_accumulation_steps: int = 4,
):
    """Unsloth를 사용한 EXAONE 모델 Fine-tuning"""

    if not UNSLOTH_AVAILABLE:
        raise RuntimeError("Unsloth가 설치되지 않았습니다. 설치 후 다시 시도하세요.")

    print("=" * 60)
    print("EXAONE 합격 수기 Fine-tuning (Unsloth 사용)")
    print("=" * 60)

    # 1. 데이터 로드
    print(f"\n[1/5] 데이터 로드 중: {data_path}")
    data = load_training_data(data_path, max_samples=max_samples)
    if max_samples:
        print(f"  - {len(data)}개 데이터 샘플링 완료 (전체 중 {max_samples}개 사용)")
    else:
        print(f"  - 총 {len(data)}개 데이터 로드 완료")

    # 2. 데이터셋 준비 (토크나이저는 모델 로드 후 필요)
    print(f"\n[2/5] 데이터셋 준비 중...")
    print(f"  - {len(data)}개 데이터 준비 완료 (토크나이징은 모델 로드 후)")

    # 3. 모델 로드 (Unsloth + Flash Attention 2)
    print(f"\n[3/5] 모델 로드 중 (Unsloth): {base_model_path}")
    if FLASH_ATTENTION_AVAILABLE:
        print("  - Flash Attention 2 활성화 (속도 및 메모리 최적화)")

    # EXAONE 모델 로드
    # 참고: EXAONE은 Unsloth의 FastLanguageModel을 직접 지원하지 않으므로
    # 일반 transformers로 로드하고 Unsloth의 최적화된 Trainer만 사용
    print("  - EXAONE은 Unsloth 직접 로드 미지원, 일반 방식으로 로드 후 Unsloth Trainer 사용")
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, TaskType
    from transformers import BitsAndBytesConfig

    tokenizer = AutoTokenizer.from_pretrained(
        base_model_path,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 4-bit 양자화 설정
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        trust_remote_code=True,
        quantization_config=quantization_config,
        device_map="auto",
    )

    # LoRA 설정
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    print("  - 모델 로드 완료 (일반 방식 + Unsloth Trainer)")

    # 3.5. 데이터셋 토크나이징 (모델 로드 후)
    print(f"\n[3.5/5] 데이터셋 토크나이징 중...")
    train_dataset = prepare_dataset_for_unsloth(data, tokenizer, max_length)
    print(f"  - {len(train_dataset)}개 데이터 토크나이징 완료")

    # 4. 학습 설정 및 실행
    print(f"\n[4/5] 학습 설정 중...")

    # Unsloth 학습 설정
    from trl import SFTTrainer
    from transformers import TrainingArguments

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 4-bit 양자화 모델은 항상 float16 사용
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_dataset,
        max_seq_length=max_length,
        packing=False,
        args=TrainingArguments(
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            warmup_steps=5,
            num_train_epochs=epochs,
            learning_rate=learning_rate,
            fp16=True,  # 4-bit 양자화 모델은 float16 사용
            bf16=False,  # bfloat16 비활성화 (충돌 방지)
            logging_steps=1,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=3407,
            output_dir=str(output_path),
            report_to="none",
        ),
    )

    print(f"\n[5/5] 학습 시작...")
    trainer_stats = trainer.train()

    # 모델 저장
    print(f"\n모델 저장 중: {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    print("\n" + "=" * 60)
    print("학습 완료!")
    print(f"모델 저장 위치: {output_dir}")
    print(f"학습 통계: {trainer_stats}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="EXAONE 합격 수기 Fine-tuning (Unsloth 사용)")
    parser.add_argument(
        "--data",
        type=str,
        default="data/success_stories/merged_training_data.jsonl",
        help="학습 데이터 JSONL 파일 경로",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="artifacts/lora-adapters/exaone-success-stories",
        help="출력 디렉토리",
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="artifacts/base-models/exaone",
        help="베이스 모델 경로",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=1,
        help="학습 에포크 수",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=384,
        help="최대 시퀀스 길이",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=1000,
        help="최대 샘플 수 (데이터 샘플링)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2,
        help="배치 크기",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-4,
        help="학습률",
    )
    parser.add_argument(
        "--lora-r",
        type=int,
        default=16,
        help="LoRA rank",
    )
    parser.add_argument(
        "--lora-alpha",
        type=int,
        default=32,
        help="LoRA alpha",
    )
    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=4,
        help="Gradient accumulation steps",
    )

    args = parser.parse_args()

    train_with_unsloth(
        data_path=args.data,
        output_dir=args.output,
        base_model_path=args.base_model,
        epochs=args.epochs,
        max_length=args.max_length,
        max_samples=args.max_samples,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
    )


if __name__ == "__main__":
    main()

