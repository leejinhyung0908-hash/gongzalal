"""
두 개의 학습 데이터셋을 하나로 통합하는 스크립트

사용 방법:
python merge_training_data.py
"""

import json
from pathlib import Path

def merge_jsonl_files():
    """gongdanki와 megagong 학습 데이터를 통합"""

    base_dir = Path(__file__).parent
    gongdanki_file = base_dir / "data" / "success_stories" / "gongdanki" / "success_stories_training.jsonl"
    megagong_file = base_dir / "data" / "success_stories" / "megagong" / "megagong_stories_training.jsonl"
    output_file = base_dir / "data" / "success_stories" / "merged_training_data.jsonl"

    all_data = []

    # gongdanki 데이터 읽기
    if gongdanki_file.exists():
        print(f"[gongdanki] 데이터 읽는 중...")
        with open(gongdanki_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    all_data.append(data)
                except json.JSONDecodeError as e:
                    print(f"[경고] JSON 파싱 오류 (gongdanki): {e}")
        print(f"[gongdanki] {len(all_data)}개 데이터 로드 완료")
    else:
        print(f"[경고] 파일을 찾을 수 없습니다: {gongdanki_file}")

    gongdanki_count = len(all_data)

    # megagong 데이터 읽기
    if megagong_file.exists():
        print(f"[megagong] 데이터 읽는 중...")
        with open(megagong_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    all_data.append(data)
                except json.JSONDecodeError as e:
                    print(f"[경고] JSON 파싱 오류 (megagong): {e}")
        print(f"[megagong] {len(all_data) - gongdanki_count}개 데이터 로드 완료")
    else:
        print(f"[경고] 파일을 찾을 수 없습니다: {megagong_file}")

    # 통합 데이터 저장
    print(f"\n[통합] 총 {len(all_data)}개 데이터를 {output_file}에 저장 중...")
    with open(output_file, "w", encoding="utf-8") as f:
        for data in all_data:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    print(f"[완료] 통합 완료!")
    print(f"  - gongdanki: {gongdanki_count}개")
    print(f"  - megagong: {len(all_data) - gongdanki_count}개")
    print(f"  - 총: {len(all_data)}개")
    print(f"  - 저장 위치: {output_file}")

    return output_file, len(all_data)


def validate_data_format(file_path: Path):
    """데이터 형식 검증"""
    print(f"\n[검증] 데이터 형식 확인 중...")

    required_fields = ["instruction", "input", "output"]
    required_input_fields = ["question", "intent", "context"]
    required_output_fields = ["thought_process", "response"]

    issues = []
    valid_count = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())

                # 필수 필드 확인
                for field in required_fields:
                    if field not in data:
                        issues.append(f"라인 {idx}: {field} 필드 없음")
                        break
                else:
                    # input 필드 확인
                    if "input" in data:
                        for field in required_input_fields:
                            if field not in data["input"]:
                                issues.append(f"라인 {idx}: input.{field} 필드 없음")
                                break
                        else:
                            # output 필드 확인
                            if "output" in data:
                                for field in required_output_fields:
                                    if field not in data["output"]:
                                        issues.append(f"라인 {idx}: output.{field} 필드 없음")
                                        break
                                else:
                                    valid_count += 1
            except json.JSONDecodeError as e:
                issues.append(f"라인 {idx}: JSON 파싱 오류 - {e}")

    if issues:
        print(f"[경고] {len(issues)}개 문제 발견 (처음 10개만 표시):")
        for issue in issues[:10]:
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... 외 {len(issues) - 10}개")
    else:
        print(f"[OK] 모든 데이터가 올바른 형식입니다!")

    print(f"[검증] 유효한 데이터: {valid_count}개")

    return len(issues) == 0


if __name__ == "__main__":
    print("=" * 60)
    print("합격 수기 학습 데이터 통합 스크립트")
    print("=" * 60)

    output_file, total_count = merge_jsonl_files()

    # 데이터 형식 검증
    validate_data_format(output_file)

    print("\n" + "=" * 60)
    print("통합 완료! 이제 EXAONE 모델에 학습시킬 수 있습니다.")
    print("=" * 60)

