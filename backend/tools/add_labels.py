#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데이터셋에 숫자 라벨 추가 스크립트

라벨 매핑:
- 0: BLOCK (서비스 범위 밖)
- 1: POLICY_BASED (정책 기반, LLM 필요)
- 2: RULE_BASED (규칙 기반, DB 쿼리)
"""

import json
import os
from pathlib import Path

# 라벨 매핑
LABEL_MAPPING = {
    "BLOCK": 0,
    "POLICY_BASED": 1,
    "RULE_BASED": 2,
}

def add_labels(input_file: str, output_file: str = None):
    """데이터셋에 라벨 추가"""
    if output_file is None:
        output_file = input_file

    input_path = Path(input_file)
    output_path = Path(output_file)

    # 백업 파일 생성
    backup_path = input_path.with_suffix('.jsonl.backup')
    if not backup_path.exists():
        print(f"백업 파일 생성: {backup_path}")
        backup_path.write_bytes(input_path.read_bytes())

    # 데이터 읽기 및 라벨 추가
    updated_data = []
    stats = {"BLOCK": 0, "POLICY_BASED": 0, "RULE_BASED": 0, "ERROR": 0}

    with open(input_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
                action = item.get('output', {}).get('action')

                if action not in LABEL_MAPPING:
                    print(f"경고: 라인 {line_num}에 알 수 없는 action: {action}")
                    stats["ERROR"] += 1
                    continue

                # 라벨 추가
                label = LABEL_MAPPING[action]
                item['label'] = label

                # output에도 라벨 추가 (일관성 유지)
                if 'output' in item:
                    item['output']['label'] = label

                updated_data.append(item)
                stats[action] += 1

            except json.JSONDecodeError as e:
                print(f"오류: 라인 {line_num} JSON 파싱 실패: {e}")
                stats["ERROR"] += 1
                continue

    # 업데이트된 데이터 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in updated_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    # 통계 출력
    print(f"\n처리 완료: {output_path}")
    print(f"총 라인 수: {len(updated_data)}")
    print(f"\n라벨 분포:")
    print(f"  BLOCK (0): {stats['BLOCK']}개")
    print(f"  POLICY_BASED (1): {stats['POLICY_BASED']}개")
    print(f"  RULE_BASED (2): {stats['RULE_BASED']}개")
    if stats['ERROR'] > 0:
        print(f"  오류: {stats['ERROR']}개")

    # 샘플 출력
    print(f"\n샘플 데이터 (처음 3개):")
    for i, item in enumerate(updated_data[:3], 1):
        print(f"  [{i}] action={item['output']['action']}, label={item['label']}, question={item['input']['question'][:50]}...")

if __name__ == "__main__":
    import sys
    from pathlib import Path

    # 스크립트가 있는 디렉토리로 이동
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    input_file = "intent_training_data_final_merged.gateway.sft.jsonl"
    add_labels(input_file)

