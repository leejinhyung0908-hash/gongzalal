#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
의도 분류 데이터를 게이트웨이 판단용 데이터셋으로 변환

의도 → 게이트웨이 판단:
- DB_QUERY → RULE_BASED (규칙 기반)
- EXPLAIN, ADVICE → POLICY_BASED (정책 기반, LLM 필요)
- OUT_OF_DOMAIN → BLOCK (차단)

출력 형식:
1. KoELECTRA 학습용: {"text": "...", "label": "RULE_BASED" | "POLICY_BASED" | "BLOCK"}
2. SFT 형식: {"instruction": "...", "input": {...}, "output": {...}}
3. Chat 형식: {"messages": [...]}
"""

import argparse
import json
import random
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter


# 의도 → 게이트웨이 라우팅 매핑
INTENT_TO_GATEWAY = {
    "DB_QUERY": "RULE_BASED",      # 규칙 기반 (exam_service)
    "EXPLAIN": "POLICY_BASED",     # 정책 기반 (exam_agent, LLM)
    "ADVICE": "POLICY_BASED",      # 정책 기반 (exam_agent, LLM)
    "OUT_OF_DOMAIN": "BLOCK",      # 차단
}

GATEWAY_LABELS = ["RULE_BASED", "POLICY_BASED", "BLOCK"]


def convert_to_koelectra_format(input_path: str, output_path: str):
    """KoELECTRA 학습용 형식으로 변환

    형식: {"text": "...", "label": "RULE_BASED" | "POLICY_BASED" | "BLOCK"}
    """
    data = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            text = item.get("text", "").strip()
            intent = item.get("intent", "").strip()

            if not text or not intent:
                continue

            gateway_label = INTENT_TO_GATEWAY.get(intent)
            if not gateway_label:
                continue

            data.append({
                "text": text,
                "label": gateway_label
            })

    # 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 통계
    labels = [item["label"] for item in data]
    counter = Counter(labels)

    print(f"KoELECTRA 형식 변환 완료:")
    print(f"  총 데이터: {len(data)}개")
    print(f"  라벨별 분포:")
    for label in GATEWAY_LABELS:
        count = counter.get(label, 0)
        print(f"    {label}: {count}개 ({count/len(data)*100:.1f}%)")
    print(f"  저장 위치: {output_path}")


def convert_to_sft_format(input_path: str, output_path: str):
    """SFT (Supervised Fine-Tuning) 형식으로 변환

    형식: {"instruction": "...", "input": {...}, "output": {...}}
    """
    data = []

    instruction_template = "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고 JSON 형식으로만 답하세요."

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            text = item.get("text", "").strip()
            intent = item.get("intent", "").strip()

            if not text or not intent:
                continue

            gateway_label = INTENT_TO_GATEWAY.get(intent)
            if not gateway_label:
                continue

            # 출력 생성
            if gateway_label == "RULE_BASED":
                reason = "명확한 데이터 조회 요청으로 규칙 기반 처리 가능"
                confidence = 0.95
            elif gateway_label == "POLICY_BASED":
                reason = "복잡한 추론이 필요한 요청으로 정책 기반 처리 필요 (LLM 사용)"
                confidence = 0.90
            else:  # BLOCK
                reason = "서비스 범위 밖의 질문으로 차단"
                confidence = 0.95

            output = {
                "action": gateway_label,
                "reason": reason,
                "confidence": confidence,
                "intent": intent
            }

            data.append({
                "instruction": instruction_template,
                "input": {
                    "question": text,
                    "intent": intent
                },
                "output": output
            })

    # 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 통계
    labels = [item["output"]["action"] for item in data]
    counter = Counter(labels)

    print(f"\nSFT 형식 변환 완료:")
    print(f"  총 데이터: {len(data)}개")
    print(f"  라벨별 분포:")
    for label in GATEWAY_LABELS:
        count = counter.get(label, 0)
        print(f"    {label}: {count}개 ({count/len(data)*100:.1f}%)")
    print(f"  저장 위치: {output_path}")


def convert_to_chat_format(input_path: str, output_path: str):
    """Chat 형식으로 변환 (EXAONE 학습용)

    형식: {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
    """
    data = []

    system_prompt = "다음 시험 관련 질문을 분석하여 처리 방식을 판단하고, 다음 JSON 형식으로만 답변하세요:\n\n{\n  \"action\": \"RULE_BASED\" 또는 \"POLICY_BASED\" 또는 \"BLOCK\",\n  \"reason\": \"판정 근거\",\n  \"confidence\": 0.0~1.0 사이의 신뢰도,\n  \"intent\": \"의도\"\n}\n\n중요: JSON 형식으로만 답변하세요. 다른 텍스트는 포함하지 마세요."

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            text = item.get("text", "").strip()
            intent = item.get("intent", "").strip()

            if not text or not intent:
                continue

            gateway_label = INTENT_TO_GATEWAY.get(intent)
            if not gateway_label:
                continue

            # 출력 생성
            if gateway_label == "RULE_BASED":
                reason = "명확한 데이터 조회 요청으로 규칙 기반 처리 가능"
                confidence = 0.95
            elif gateway_label == "POLICY_BASED":
                reason = "복잡한 추론이 필요한 요청으로 정책 기반 처리 필요 (LLM 사용)"
                confidence = 0.90
            else:  # BLOCK
                reason = "서비스 범위 밖의 질문으로 차단"
                confidence = 0.95

            output_json = json.dumps({
                "action": gateway_label,
                "reason": reason,
                "confidence": confidence,
                "intent": intent
            }, ensure_ascii=False)

            user_content = f"{system_prompt}\n\n시험 관련 질문:\n{text}"

            data.append({
                "messages": [
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": output_json}
                ]
            })

    # 저장
    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 통계
    labels = []
    for item in data:
        try:
            output = json.loads(item["messages"][1]["content"])
            labels.append(output.get("action", "UNKNOWN"))
        except:
            pass

    counter = Counter(labels)

    print(f"\nChat 형식 변환 완료:")
    print(f"  총 데이터: {len(data)}개")
    print(f"  라벨별 분포:")
    for label in GATEWAY_LABELS:
        count = counter.get(label, 0)
        print(f"    {label}: {count}개 ({count/len(data)*100:.1f}%)")
    print(f"  저장 위치: {output_path}")


def split_dataset(input_path: str, train_path: str, val_path: str, train_ratio: float = 0.8):
    """데이터셋을 학습/검증으로 분할"""
    data = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(line)

    # 셔플
    random.shuffle(data)

    # 분할
    split_idx = int(len(data) * train_ratio)
    train_data = data[:split_idx]
    val_data = data[split_idx:]

    # 저장
    with open(train_path, "w", encoding="utf-8") as f:
        for line in train_data:
            f.write(line)

    with open(val_path, "w", encoding="utf-8") as f:
        for line in val_data:
            f.write(line)

    print(f"\n데이터셋 분할 완료:")
    print(f"  학습 데이터: {len(train_data)}개")
    print(f"  검증 데이터: {len(val_data)}개")
    print(f"  저장 위치:")
    print(f"    학습: {train_path}")
    print(f"    검증: {val_path}")


def main():
    parser = argparse.ArgumentParser(description="의도 분류 데이터를 게이트웨이 판단용 데이터셋으로 변환")
    parser.add_argument("--input", type=str, required=True, help="입력 파일 경로 (intent_training_data_400.jsonl)")
    parser.add_argument("--output-dir", type=str, default="data/spamdata", help="출력 디렉토리")
    parser.add_argument("--format", type=str, choices=["koelectra", "sft", "chat", "all"], default="all", help="출력 형식")
    parser.add_argument("--split", action="store_true", help="학습/검증 데이터로 분할")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="학습 데이터 비율")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 생성
    base_name = Path(args.input).stem

    if args.format in ["koelectra", "all"]:
        koelectra_path = output_dir / f"{base_name}.gateway.koelectra.jsonl"
        convert_to_koelectra_format(args.input, str(koelectra_path))

        if args.split:
            train_path = output_dir / f"{base_name}.gateway.koelectra.train.jsonl"
            val_path = output_dir / f"{base_name}.gateway.koelectra.val.jsonl"
            split_dataset(str(koelectra_path), str(train_path), str(val_path), args.train_ratio)

    if args.format in ["sft", "all"]:
        sft_path = output_dir / f"{base_name}.gateway.sft.jsonl"
        convert_to_sft_format(args.input, str(sft_path))

        if args.split:
            train_path = output_dir / f"{base_name}.gateway.sft.train.jsonl"
            val_path = output_dir / f"{base_name}.gateway.sft.val.jsonl"
            split_dataset(str(sft_path), str(train_path), str(val_path), args.train_ratio)

    if args.format in ["chat", "all"]:
        chat_path = output_dir / f"{base_name}.gateway.chat.jsonl"
        convert_to_chat_format(args.input, str(chat_path))

        if args.split:
            train_path = output_dir / f"{base_name}.gateway.chat.train.jsonl"
            val_path = output_dir / f"{base_name}.gateway.chat.val.jsonl"
            split_dataset(str(chat_path), str(train_path), str(val_path), args.train_ratio)

    print("\n변환 완료!")


if __name__ == "__main__":
    main()

