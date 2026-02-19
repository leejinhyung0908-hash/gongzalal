"""게이트웨이 데이터셋 병합 스크립트

기존 데이터와 새로 생성한 POLICY_BASED 데이터를 병합합니다.
"""

import json
import sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')


def load_jsonl(file_path: Path) -> list:
    """JSONL 파일 로드"""
    data = []
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
    return data


def save_jsonl(data: list, file_path: Path):
    """JSONL 파일 저장"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def get_action_from_item(item: dict) -> str:
    """아이템에서 action 추출"""
    if "output" in item and isinstance(item["output"], dict):
        return item["output"].get("action", "UNKNOWN")
    elif "label" in item:
        return item["label"]
    return "UNKNOWN"


def main():
    """데이터셋 병합"""

    # 기존 데이터셋
    existing_data_path = Path("data/spamdata/intent_training_data_3000.gateway.sft.jsonl")

    # 새로 생성한 데이터
    policy_based_data_path = Path("data/spamdata/intent_training_data_policy_based_augmented.jsonl")
    block_data_path = Path("data/spamdata/intent_training_data_block_augmented.jsonl")

    # 출력 경로
    output_path = Path("data/spamdata/intent_training_data_final_merged.gateway.sft.jsonl")

    print("📊 데이터셋 병합 시작...")

    # 기존 데이터 로드
    existing_data = load_jsonl(existing_data_path)
    print(f"  기존 데이터: {len(existing_data)}개")

    # 새로 생성한 데이터 로드
    policy_based_data = load_jsonl(policy_based_data_path)
    print(f"  POLICY_BASED 증강 데이터: {len(policy_based_data)}개")

    block_data = load_jsonl(block_data_path)
    print(f"  BLOCK 증강 데이터: {len(block_data)}개")

    # 데이터 병합
    merged_data = existing_data + policy_based_data + block_data

    print(f"  병합된 데이터: {len(merged_data)}개")

    # 클래스별 분포 확인
    action_counter = Counter()
    for item in merged_data:
        action = get_action_from_item(item)
        action_counter[action] += 1

    print(f"\n📈 클래스별 분포:")
    for action, count in action_counter.most_common():
        print(f"  {action}: {count}개 ({count/len(merged_data)*100:.1f}%)")

    # 저장
    save_jsonl(merged_data, output_path)
    print(f"\n✅ 데이터 병합 완료!")
    print(f"📁 저장 위치: {output_path}")


if __name__ == "__main__":
    main()

