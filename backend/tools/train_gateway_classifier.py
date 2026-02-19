#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KoELECTRA 게이트웨이 분류기 학습 스크립트

3가지 게이트웨이 라우팅으로 분류:
- RULE_BASED: 규칙 기반 처리 (exam_service)
- POLICY_BASED: 정책 기반 처리 (exam_agent, LLM)
- BLOCK: 차단

사용법:
    python train_gateway_classifier.py \
        --data data/spamdata/intent_training_data_400.gateway.koelectra.jsonl \
        --output artifacts/lora-adapters/koelectra-gateway \
        --epochs 5 \
        --batch-size 16 \
        --learning-rate 2e-5
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


# 게이트웨이 레이블 정의
GATEWAY_LABELS = {
    "RULE_BASED": 0,    # 규칙 기반 (DB_QUERY)
    "POLICY_BASED": 1,  # 정책 기반 (EXPLAIN, ADVICE)
    "BLOCK": 2,         # 차단 (OUT_OF_DOMAIN)
}

LABEL_TO_GATEWAY = {v: k for k, v in GATEWAY_LABELS.items()}


class GatewayDataset(Dataset):
    """게이트웨이 분류 데이터셋"""

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

    지원 형식:
    1. KoELECTRA 형식:
       {"text": "2024년 지방직 9급 회계학 3번 정답 뭐야?", "label": "RULE_BASED"}

    2. SFT 형식:
       {"instruction": "...", "input": {"question": "..."}, "output": {"action": "RULE_BASED", ...}}
    """
    texts = []
    labels = []

    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)

            # KoELECTRA 형식 처리
            if "text" in data and "label" in data:
                text = data.get("text", "").strip()
                label = data.get("label", "").strip()

            # SFT 형식 처리
            elif "input" in data and "output" in data:
                text = data.get("input", {}).get("question", "").strip()
                label = data.get("output", {}).get("action", "").strip()

            else:
                continue

            if not text or not label:
                continue

            if label not in GATEWAY_LABELS:
                print(f"경고: 알 수 없는 라벨 '{label}' 건너뜀")
                continue

            texts.append(text)
            labels.append(GATEWAY_LABELS[label])

    print(f"로드된 데이터: {len(texts)}개")
    print(f"게이트웨이별 분포:")
    for gateway, label_id in GATEWAY_LABELS.items():
        count = labels.count(label_id)
        print(f"  {gateway}: {count}개 ({count/len(labels)*100:.1f}%)")

    return texts, labels


def compute_metrics(eval_pred):
    """평가 메트릭 계산"""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)

    accuracy = accuracy_score(labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="weighted", zero_division=0
    )

    # 클래스별 성능 (평가 데이터셋에 실제로 존재하는 클래스만)
    unique_labels = np.unique(labels)
    per_class_metrics = precision_recall_fscore_support(
        labels, predictions, labels=unique_labels, average=None, zero_division=0
    )

    metrics = {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }

    # 클래스별 상세 메트릭 (안전하게 처리)
    # 평가 데이터셋에 있는 클래스만 메트릭 계산
    label_to_index = {label: idx for idx, label in enumerate(unique_labels)}

    for i, gateway in LABEL_TO_GATEWAY.items():
        if i in label_to_index:
            idx = label_to_index[i]
            metrics[f"{gateway}_precision"] = per_class_metrics[0][idx]
            metrics[f"{gateway}_recall"] = per_class_metrics[1][idx]
            metrics[f"{gateway}_f1"] = per_class_metrics[2][idx]
        else:
            # 평가 데이터셋에 없는 클래스는 0으로 설정
            metrics[f"{gateway}_precision"] = 0.0
            metrics[f"{gateway}_recall"] = 0.0
            metrics[f"{gateway}_f1"] = 0.0

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
    use_weighted_loss: bool = True,
):
    """게이트웨이 분류기 학습"""

    print("=" * 60)
    print("KoELECTRA 게이트웨이 분류기 학습 시작")
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

    # 클래스 가중치 계산 (불균형 해소)
    if use_weighted_loss:
        from collections import Counter
        label_counts = Counter(train_labels)
        total = len(train_labels)

        # 기본 역빈도 가중치 (균형잡힌 학습)
        class_weights = torch.tensor([
            total / (len(GATEWAY_LABELS) * label_counts.get(i, 1))
            for i in range(len(GATEWAY_LABELS))
        ], dtype=torch.float32)

        if torch.cuda.is_available():
            class_weights = class_weights.cuda()
        print(f"\n클래스 가중치 (Weighted Loss):")
        for i, gateway in enumerate(GATEWAY_LABELS.keys()):
            count = label_counts.get(i, 0)
            weight = class_weights[i].item()
            print(f"  {gateway}: {count}개, 가중치: {weight:.3f}")
    else:
        class_weights = None

    # 3. 토크나이저 및 모델 로드
    print("\n[3/5] 모델 로드 중...")
    tokenizer = AutoTokenizer.from_pretrained(base_model)

    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=len(GATEWAY_LABELS),
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
    train_dataset = GatewayDataset(train_texts, train_labels, tokenizer, max_length)
    eval_dataset = GatewayDataset(eval_texts, eval_labels, tokenizer, max_length)

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

    # 가중치 손실 함수 적용
    if use_weighted_loss and class_weights is not None:
        from torch.nn import CrossEntropyLoss

        class WeightedTrainer(Trainer):
            def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
                labels = inputs.get("labels")
                outputs = model(**inputs)
                logits = outputs.get("logits")
                loss_fct = CrossEntropyLoss(weight=class_weights)
                loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))
                return (loss, outputs) if return_outputs else loss

        trainer = WeightedTrainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            compute_metrics=compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
        )
    else:
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

    print(f"\n게이트웨이별 성능:")
    for gateway in GATEWAY_LABELS.keys():
        precision = eval_result.get(f"eval_{gateway}_precision", 0)
        recall = eval_result.get(f"eval_{gateway}_recall", 0)
        f1 = eval_result.get(f"eval_{gateway}_f1", 0)
        print(f"  {gateway}:")
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
        "gateway_labels": GATEWAY_LABELS,
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

    print(f"\n학습 완료! 모델 경로: {run_dir}")
    print(f"\n사용 방법:")
    print(f"  환경 변수 설정:")
    print(f"    KOELECTRA_GATEWAY_LORA_PATH={run_dir}")

    return run_dir


def main():
    parser = argparse.ArgumentParser(description="KoELECTRA 게이트웨이 분류기 학습")
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="학습 데이터 JSONL 파일 경로",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./artifacts/lora-adapters/koelectra-gateway",
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
    parser.add_argument(
        "--use-weighted-loss",
        action="store_true",
        help="클래스 불균형 해소를 위한 가중치 손실 함수 사용",
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
        use_weighted_loss=args.use_weighted_loss,
    )


if __name__ == "__main__":
    main()

