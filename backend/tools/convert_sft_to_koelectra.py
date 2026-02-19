#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SFT 형식 데이터를 KoELECTRA 학습용 형식으로 변환

사용법:
    python backend/tools/convert_sft_to_koelectra.py \
        --input data/spamdata/intent_training_data_400.gateway.sft.train.jsonl \
        --output data/spamdata/intent_training_data_400.gateway.koelectra.train.jsonl
"""

import argparse
import json
from pathlib import Path
from collections import Counter


GATEWAY_LABELS = ["RULE_BASED", "POLICY_BASED", "BLOCK"]


def convert_sft_to_koelectra(input_path: str, output_path: str):
    """SFT 형식을 KoELECTRA 형식으로 변환

    입력 형식 (SFT):
    {
        "instruction": "...",
        "input": {"question": "...", "intent": "..."},
        "output": {"action": "RULE_BASED", ...}
    }

    출력 형식 (KoELECTRA):
    {
        "text": "...",
        "label": "RULE_BASED"
    }
    """
    data = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)

            # question 추출
            question = item.get("input", {}).get("question", "").strip()
            if not question:
                continue

            # action 추출 (label)
            action = item.get("output", {}).get("action", "").strip()
            if action not in GATEWAY_LABELS:
                continue

            data.append({
                "text": question,
                "label": action
            })

    # 저장
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 통계
    labels = [item["label"] for item in data]
    counter = Counter(labels)

    print(f"변환 완료:")
    print(f"  총 데이터: {len(data)}개")
    print(f"  라벨별 분포:")
    for label in GATEWAY_LABELS:
        count = counter.get(label, 0)
        print(f"    {label}: {count}개 ({count/len(data)*100:.1f}%)")
    print(f"  저장 위치: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="SFT 형식을 KoELECTRA 형식으로 변환")
    parser.add_argument("--input", type=str, required=True, help="입력 SFT 파일 경로")
    parser.add_argument("--output", type=str, required=True, help="출력 KoELECTRA 파일 경로")

    args = parser.parse_args()

    convert_sft_to_koelectra(args.input, args.output)


if __name__ == "__main__":
    main()

