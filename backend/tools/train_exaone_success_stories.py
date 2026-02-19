"""
EXAONE 모델 Fine-tuning 스크립트 (합격 수기 데이터)

사용 방법:
python train_exaone_success_stories.py \
    --data data/success_stories/merged_training_data.jsonl \
    --output artifacts/lora-adapters/exaone-success-stories \
    --epochs 3 \
    --batch-size 4 \
    --learning-rate 2e-4
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Any
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import Dataset
import os


def format_exaone_prompt(instruction: str, input_data: Dict, output_data: Dict) -> str:
    """EXAONE 형식의 프롬프트 생성

    EXAONE은 [INST] ... [/INST] 형식을 사용합니다.
    """
    # 질문 구성
    question = input_data.get("question", "")
    context = input_data.get("context", "")

    # 컨텍스트가 있으면 포함
    if context:
        user_content = f"{instruction}\n\n질문: {question}\n\n참고 자료: {context}"
    else:
        user_content = f"{instruction}\n\n질문: {question}"

    # 응답 구성 (thought_process + response)
    thought = output_data.get("thought_process", "")
    response = output_data.get("response", "")

    if thought:
        assistant_content = f"사고 과정: {thought}\n\n답변: {response}"
    else:
        assistant_content = response

    # EXAONE 형식: [INST] user_content [/INST] assistant_content
    formatted = f"[INST] {user_content} [/INST] {assistant_content}"

    return formatted


def load_training_data(data_path: str, max_samples: int = None) -> List[Dict[str, Any]]:
    """JSONL 파일에서 학습 데이터 로드

    Args:
        data_path: JSONL 파일 경로
        max_samples: 최대 샘플 수 (None이면 전체 사용)
    """
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


def prepare_dataset(data: List[Dict[str, Any]], tokenizer, max_length: int = 2048):
    """데이터셋 준비"""
    texts = []

    for item in data:
        instruction = item.get("instruction", "")
        input_data = item.get("input", {})
        output_data = item.get("output", {})

        # EXAONE 형식으로 변환
        formatted_text = format_exaone_prompt(instruction, input_data, output_data)
        texts.append(formatted_text)

    # 토크나이징 (동적 패딩으로 속도 향상)
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding=False,  # 동적 패딩으로 변경 (속도 향상)
        )

    dataset = Dataset.from_dict({"text": texts})
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"],
    )

    return tokenized_dataset


def train(
    data_path: str,
    output_dir: str,
    base_model_path: str = "artifacts/base-models/exaone",
    epochs: int = 3,
    batch_size: int = 1,
    learning_rate: float = 2e-4,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.1,
    max_length: int = 1024,
    train_split: float = 0.9,
    gradient_accumulation_steps: int = 8,
    use_4bit: bool = True,
    max_samples: int = None,  # 데이터 샘플링 (None이면 전체 사용)
):
    """EXAONE 모델 Fine-tuning"""

    print("=" * 60)
    print("EXAONE 합격 수기 Fine-tuning")
    print("=" * 60)

    # 1. 데이터 로드
    print(f"\n[1/6] 데이터 로드 중: {data_path}")
    data = load_training_data(data_path, max_samples=max_samples)
    if max_samples:
        print(f"  - {len(data)}개 데이터 샘플링 완료 (전체 중 {max_samples}개 사용)")
    else:
        print(f"  - 총 {len(data)}개 데이터 로드 완료")

    # 2. 모델 및 토크나이저 로드
    print(f"\n[2/6] 모델 로드 중: {base_model_path}")
    tokenizer = AutoTokenizer.from_pretrained(
        base_model_path,
        trust_remote_code=True,
    )

    # 패딩 토큰 설정
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 4-bit 양자화 설정 (6GB VRAM 최적화)
    model_kwargs = {
        "trust_remote_code": True,
        "device_map": "auto",
    }

    if use_4bit:
        try:
            from transformers import BitsAndBytesConfig
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            model_kwargs["quantization_config"] = quantization_config
            print("  - 4-bit 양자화 활성화 (메모리 절약)")
        except ImportError:
            print("  - [경고] bitsandbytes가 없어 float16으로 로드합니다")
            model_kwargs["torch_dtype"] = torch.float16
    else:
        model_kwargs["torch_dtype"] = torch.float16

    model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        **model_kwargs,
    )
    print("  - 모델 로드 완료")

    # 3. 데이터셋 준비
    print(f"\n[3/6] 데이터셋 준비 중...")
    dataset = prepare_dataset(data, tokenizer, max_length)

    # 학습/검증 분할
    split_dataset = dataset.train_test_split(test_size=1 - train_split)
    train_dataset = split_dataset["train"]
    eval_dataset = split_dataset["test"]

    print(f"  - 학습 데이터: {len(train_dataset)}개")
    print(f"  - 검증 데이터: {len(eval_dataset)}개")

    # 4. LoRA 설정
    print(f"\n[4/6] LoRA 설정 중...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],  # EXAONE attention 모듈
        bias="none",
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 5. 학습 설정
    print(f"\n[5/6] 학습 설정 중...")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_path),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_steps=100,
        logging_dir=str(output_path / "logs"),
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        save_total_limit=3,
        fp16=torch.cuda.is_available() and not use_4bit,  # 4-bit 사용 시 fp16 비활성화
        report_to="none",
        remove_unused_columns=False,
        optim="paged_adamw_8bit" if use_4bit else "adamw_torch",  # 4-bit용 최적화
        max_grad_norm=0.3,  # Gradient clipping
        gradient_checkpointing=True,  # 메모리 절약 및 속도 향상
        dataloader_num_workers=0,  # Windows에서 안정성 향상
        dataloader_pin_memory=False,  # 메모리 절약
    )

    # 데이터 콜레이터 (동적 패딩)
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Causal LM이므로 False
        pad_to_multiple_of=8,  # 8의 배수로 패딩 (속도 향상)
    )

    # 6. Trainer 생성 및 학습
    print(f"\n[6/6] 학습 시작...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )

    trainer.train()

    # 모델 저장
    print(f"\n모델 저장 중: {output_dir}")
    trainer.save_model()
    tokenizer.save_pretrained(output_dir)

    print("\n" + "=" * 60)
    print("학습 완료!")
    print(f"모델 저장 위치: {output_dir}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="EXAONE 합격 수기 Fine-tuning")
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
        default=3,
        help="학습 에포크 수",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
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
        "--lora-dropout",
        type=float,
        default=0.1,
        help="LoRA dropout",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=2048,
        help="최대 시퀀스 길이",
    )
    parser.add_argument(
        "--train-split",
        type=float,
        default=0.9,
        help="학습/검증 데이터 분할 비율",
    )
    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=8,
        help="Gradient accumulation steps",
    )
    parser.add_argument(
        "--use-4bit",
        action="store_true",
        default=True,
        help="4-bit 양자화 사용 (메모리 절약)",
    )
    parser.add_argument(
        "--no-4bit",
        dest="use_4bit",
        action="store_false",
        help="4-bit 양자화 비활성화",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="최대 샘플 수 (데이터 샘플링, None이면 전체 사용)",
    )

    args = parser.parse_args()

    train(
        data_path=args.data,
        output_dir=args.output,
        base_model_path=args.base_model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        max_length=args.max_length,
        train_split=args.train_split,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        use_4bit=args.use_4bit,
        max_samples=args.max_samples,
    )


if __name__ == "__main__":
    main()

