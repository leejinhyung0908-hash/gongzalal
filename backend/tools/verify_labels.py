#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""라벨 검증 스크립트"""

import json
from pathlib import Path
from collections import Counter

def verify_labels(input_file: str):
    """라벨 검증"""
    input_path = Path(input_file)

    labels = []
    action_to_label = {}
    errors = []

    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
                action = item.get('output', {}).get('action')
                label = item.get('label')
                output_label = item.get('output', {}).get('label')

                # 라벨 매핑 확인
                expected_label = {
                    "BLOCK": 0,
                    "POLICY_BASED": 1,
                    "RULE_BASED": 2,
                }.get(action)

                if label is None:
                    errors.append(f"라인 {line_num}: label 필드 없음")
                elif label != expected_label:
                    errors.append(f"라인 {line_num}: label 불일치 (action={action}, label={label}, expected={expected_label})")

                if output_label is not None and output_label != label:
                    errors.append(f"라인 {line_num}: output.label과 label 불일치")

                labels.append(label)
                if action:
                    action_to_label[action] = label

            except json.JSONDecodeError as e:
                errors.append(f"라인 {line_num}: JSON 파싱 오류 - {e}")
                continue

    # 통계 출력
    label_counts = Counter(labels)
    print(f"총 라인 수: {len(labels)}")
    print(f"\n라벨 분포:")
    for label in sorted(label_counts.keys()):
        label_name = {0: "BLOCK", 1: "POLICY_BASED", 2: "RULE_BASED"}.get(label, "UNKNOWN")
        print(f"  {label} ({label_name}): {label_counts[label]}개")

    print(f"\nAction → Label 매핑:")
    for action, label in sorted(action_to_label.items()):
        print(f"  {action} → {label}")

    if errors:
        print(f"\n오류 발견: {len(errors)}개")
        for error in errors[:10]:  # 처음 10개만 출력
            print(f"  {error}")
        if len(errors) > 10:
            print(f"  ... 외 {len(errors) - 10}개 오류")
    else:
        print(f"\n[OK] 모든 라벨이 정상적으로 추가되었습니다!")

if __name__ == "__main__":
    import os
    from pathlib import Path

    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    input_file = "intent_training_data_final_merged.gateway.sft.jsonl"
    verify_labels(input_file)

