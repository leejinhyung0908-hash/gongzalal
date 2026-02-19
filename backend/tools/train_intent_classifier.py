#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KoELECTRA 의도 분류기 학습 스크립트

4가지 의도로 분류:
- DB_QUERY: 명확한 데이터 조회 요청
- EXPLAIN: 해설 및 추론 요청
- ADVICE: 학습 상담/가이드 요청
- OUT_OF_DOMAIN: 서비스 범위 밖

사용법:
    python train_intent_classifier.py \
        --data data/intent_training_data.jsonl \
        --output artifacts/lora-adapters/koelectra-intent \
        --epochs 5 \
        --batch_size 16 \
        --learning_rate 2e-5
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
from peft import LoraConfig, get_peft_model, TaskType
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import numpy as np


# 의도 레이블 정의
INTENT_LABELS = {
    "DB_QUERY": 0,
    "EXPLAIN": 1,
    "ADVICE": 2,
    "OUT_OF_DOMAIN": 3,
}

LABEL_TO_INTENT = {v: k for k, v in INTENT_LABELS.items()}


class IntentDataset(Dataset):
    """의도 분류 데이터셋"""

    def __init__(self, texts: List[str], labels: List[int], tokenizer, max_length: int = 256):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].flatten(),
            "attention_mask": encoding["attention_mask"].flatten(),
            "labels": torch.tensor(label, dtype=torch.long),
        }


def load_training_data(data_path: str) -> tuple[List[str], List[int]]:
    """학습 데이터 로드

    JSONL 형식:
    {"text": "2024년 지방직 9급 회계학 3번 정답 뭐야?", "intent": "DB_QUERY"}
    {"text": "신뢰보호의 원칙이 왜 적용 안 돼?", "intent": "EXPLAIN"}
    ...
    """
    texts = []
    labels = []

    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            text = data.get("text", "").strip()
            intent = data.get("intent", "").strip()

            if not text or not intent:
                continue

            if intent not in INTENT_LABELS:
                print(f"경고: 알 수 없는 의도 '{intent}' 건너뜀")
                continue

            texts.append(text)
            labels.append(INTENT_LABELS[intent])

    print(f"로드된 데이터: {len(texts)}개")
    print(f"의도별 분포:")
    for intent, label_id in INTENT_LABELS.items():
        count = labels.count(label_id)
        print(f"  {intent}: {count}개 ({count/len(labels)*100:.1f}%)")

    return texts, labels


def compute_metrics(eval_pred):
    """평가 메트릭 계산"""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)

    accuracy = accuracy_score(labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="weighted", zero_division=0
    )

    # 의도별 성능
    per_class_metrics = precision_recall_fscore_support(
        labels, predictions, average=None, zero_division=0
    )

    metrics = {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }

    # 의도별 상세 메트릭
    for i, intent in LABEL_TO_INTENT.items():
        metrics[f"{intent}_precision"] = per_class_metrics[0][i]
        metrics[f"{intent}_recall"] = per_class_metrics[1][i]
        metrics[f"{intent}_f1"] = per_class_metrics[2][i]

    return metrics


def train(
    data_path: str,
    output_dir: str,
    base_model: str = "monologg/koelectra-small-v3-discriminator",
    epochs: int = 5,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    lora_r: int = 8,
    lora_alpha: int = 16,
    lora_dropout: float = 0.1,
    train_split: float = 0.8,
    max_length: int = 256,
):
    """의도 분류기 학습"""

    print("=" * 60)
    print("KoELECTRA 의도 분류기 학습 시작")
    print("=" * 60)

    # 1. 데이터 로드
    print("\n[1/5] 데이터 로드 중...")
    texts, labels = load_training_data(data_path)

    if len(texts) < 100:
        print("경고: 학습 데이터가 부족합니다. 최소 100개 이상 권장합니다.")

    # 2. 데이터 분할
    print("\n[2/5] 데이터 분할 중...")
    split_idx = int(len(texts) * train_split)
    train_texts = texts[:split_idx]
    train_labels = labels[:split_idx]
    eval_texts = texts[split_idx:]
    eval_labels = labels[split_idx:]

    print(f"학습 데이터: {len(train_texts)}개")
    print(f"평가 데이터: {len(eval_texts)}개")

    # 3. 토크나이저 및 모델 로드
    print("\n[3/5] 모델 로드 중...")
    tokenizer = AutoTokenizer.from_pretrained(base_model)

    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=len(INTENT_LABELS),
        problem_type="single_label_classification",
    )

    # 4. LoRA 설정
    print("\n[4/5] LoRA 설정 중...")
    lora_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["query", "value"],  # KoELECTRA의 attention 모듈
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 5. 데이터셋 생성
    print("\n[5/5] 데이터셋 생성 중...")
    train_dataset = IntentDataset(train_texts, train_labels, tokenizer, max_length)
    eval_dataset = IntentDataset(eval_texts, eval_labels, tokenizer, max_length)

    # 6. 학습 설정
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_path / f"run_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(run_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        weight_decay=0.01,
        logging_dir=str(run_dir / "logs"),
        logging_steps=50,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=3,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    # 7. Trainer 생성 및 학습
    print("\n학습 시작...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
    )

    # 학습 실행
    train_result = trainer.train()

    # 8. 평가
    print("\n최종 평가 중...")
    eval_result = trainer.evaluate()

    print("\n" + "=" * 60)
    print("학습 완료!")
    print("=" * 60)
    print(f"\n최종 성능:")
    print(f"  Accuracy: {eval_result['eval_accuracy']:.4f}")
    print(f"  Precision: {eval_result['eval_precision']:.4f}")
    print(f"  Recall: {eval_result['eval_recall']:.4f}")
    print(f"  F1: {eval_result['eval_f1']:.4f}")

    print(f"\n의도별 성능:")
    for intent in INTENT_LABELS.keys():
        precision = eval_result.get(f"eval_{intent}_precision", 0)
        recall = eval_result.get(f"eval_{intent}_recall", 0)
        f1 = eval_result.get(f"eval_{intent}_f1", 0)
        print(f"  {intent}:")
        print(f"    Precision: {precision:.4f}")
        print(f"    Recall: {recall:.4f}")
        print(f"    F1: {f1:.4f}")

    # 9. 모델 저장
    print(f"\n모델 저장 중: {run_dir}")
    trainer.save_model()
    tokenizer.save_pretrained(run_dir)

    # 설정 저장
    config = {
        "base_model": base_model,
        "intent_labels": INTENT_LABELS,
        "training_args": {
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "lora_r": lora_r,
            "lora_alpha": lora_alpha,
            "lora_dropout": lora_dropout,
        },
        "final_metrics": {
            "accuracy": eval_result["eval_accuracy"],
            "precision": eval_result["eval_precision"],
            "recall": eval_result["eval_recall"],
            "f1": eval_result["eval_f1"],
        },
    }

    with open(run_dir / "training_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 학습 완료! 모델 경로: {run_dir}")
    print(f"\n사용 방법:")
    print(f"  환경 변수 설정:")
    print(f"    KOELECTRA_INTENT_LORA_PATH={run_dir}")

    return run_dir


def main():
    parser = argparse.ArgumentParser(description="KoELECTRA 의도 분류기 학습")
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="학습 데이터 JSONL 파일 경로",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./artifacts/lora-adapters/koelectra-intent",
        help="출력 디렉토리",
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="monologg/koelectra-small-v3-discriminator",
        help="베이스 모델",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=5,
        help="학습 에포크 수",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="배치 크기",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-5,
        help="학습률",
    )
    parser.add_argument(
        "--lora-r",
        type=int,
        default=8,
        help="LoRA rank",
    )
    parser.add_argument(
        "--lora-alpha",
        type=int,
        default=16,
        help="LoRA alpha",
    )
    parser.add_argument(
        "--lora-dropout",
        type=float,
        default=0.1,
        help="LoRA dropout",
    )
    parser.add_argument(
        "--train-split",
        type=float,
        default=0.8,
        help="학습 데이터 비율 (나머지는 평가 데이터)",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=256,
        help="최대 시퀀스 길이",
    )

    args = parser.parse_args()

    train(
        data_path=args.data,
        output_dir=args.output,
        base_model=args.base_model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        train_split=args.train_split,
        max_length=args.max_length,
    )


if __name__ == "__main__":
    main()

