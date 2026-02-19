"""
2단계: YOLO 학습용 데이터셋 준비

이미지를 학습/검증 세트로 분할하고 YOLO 데이터셋 구조를 생성합니다.

데이터셋 구조:
    data/yolo_dataset/
    ├── images/
    │   ├── train/
    │   └── val/
    ├── labels/
    │   ├── train/
    │   └── val/
    └── dataset.yaml

라벨링 도구:
    - LabelImg: pip install labelImg → labelImg
    - Roboflow: https://roboflow.com (온라인)

사용법:
    1. 먼저 step1로 이미지 생성
    2. LabelImg로 라벨링 (YOLO 포맷 선택)
    3. 이 스크립트 실행하여 데이터셋 구성
"""

import os
import shutil
import random
from pathlib import Path
from typing import List, Tuple
import argparse

from tqdm import tqdm
import yaml

from config import IMAGE_OUTPUT_DIR, DATA_DIR


# 데이터셋 경로
DATASET_DIR = DATA_DIR / "yolo_dataset"
TRAIN_IMAGES = DATASET_DIR / "images" / "train"
VAL_IMAGES = DATASET_DIR / "images" / "val"
TRAIN_LABELS = DATASET_DIR / "labels" / "train"
VAL_LABELS = DATASET_DIR / "labels" / "val"


def create_dataset_structure():
    """데이터셋 디렉토리 구조 생성."""
    for dir_path in [TRAIN_IMAGES, VAL_IMAGES, TRAIN_LABELS, VAL_LABELS]:
        dir_path.mkdir(parents=True, exist_ok=True)
    print("✅ 데이터셋 디렉토리 구조 생성 완료")


def split_dataset(
    images_dir: Path,
    labels_dir: Path,
    train_ratio: float = 0.8
) -> Tuple[List[Path], List[Path]]:
    """데이터셋을 학습/검증으로 분할.

    Args:
        images_dir: 이미지 디렉토리
        labels_dir: 라벨 디렉토리 (YOLO txt 파일)
        train_ratio: 학습 데이터 비율

    Returns:
        (train_files, val_files) 튜플
    """
    # 이미지 파일 수집
    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    all_images = [
        f for f in images_dir.rglob("*")
        if f.suffix.lower() in image_extensions
    ]

    # 라벨이 있는 이미지만 필터링
    labeled_images = []
    for img_path in all_images:
        label_path = labels_dir / f"{img_path.stem}.txt"
        if label_path.exists():
            labeled_images.append((img_path, label_path))

    if not labeled_images:
        print("⚠️  라벨이 있는 이미지가 없습니다!")
        print(f"   이미지 디렉토리: {images_dir}")
        print(f"   라벨 디렉토리: {labels_dir}")
        return [], []

    # 셔플 및 분할
    random.shuffle(labeled_images)
    split_idx = int(len(labeled_images) * train_ratio)

    train_files = labeled_images[:split_idx]
    val_files = labeled_images[split_idx:]

    return train_files, val_files


def copy_files_to_dataset(
    files: List[Tuple[Path, Path]],
    images_dest: Path,
    labels_dest: Path,
    desc: str = "복사"
):
    """파일을 데이터셋 디렉토리로 복사.

    Args:
        files: (이미지경로, 라벨경로) 튜플 리스트
        images_dest: 이미지 대상 디렉토리
        labels_dest: 라벨 대상 디렉토리
        desc: 진행바 설명
    """
    for img_path, label_path in tqdm(files, desc=desc):
        # 이미지 복사
        shutil.copy2(img_path, images_dest / img_path.name)
        # 라벨 복사
        shutil.copy2(label_path, labels_dest / label_path.name)


def create_dataset_yaml(class_names: List[str]):
    """YOLO 데이터셋 설정 파일 생성.

    Args:
        class_names: 클래스 이름 리스트
    """
    yaml_content = {
        "path": str(DATASET_DIR.absolute()),
        "train": "images/train",
        "val": "images/val",
        "names": {i: name for i, name in enumerate(class_names)}
    }

    yaml_path = DATASET_DIR / "dataset.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(yaml_content, f, allow_unicode=True, default_flow_style=False)

    print(f"✅ 데이터셋 설정 파일 생성: {yaml_path}")
    return yaml_path


def main():
    parser = argparse.ArgumentParser(description="YOLO 학습용 데이터셋 준비")
    parser.add_argument(
        "--images", type=str, default=str(IMAGE_OUTPUT_DIR),
        help="이미지 디렉토리"
    )
    parser.add_argument(
        "--labels", type=str, default=str(DATA_DIR / "labels"),
        help="라벨 디렉토리 (YOLO txt 파일)"
    )
    parser.add_argument(
        "--train-ratio", type=float, default=0.8,
        help="학습 데이터 비율 (기본: 0.8)"
    )
    parser.add_argument(
        "--classes", type=str, nargs="+",
        default=["question", "question_number", "options", "figure"],
        help="클래스 이름들"
    )

    args = parser.parse_args()

    print("=" * 50)
    print(" 📊 YOLO 데이터셋 준비 도구")
    print("=" * 50)

    # 1. 디렉토리 구조 생성
    create_dataset_structure()

    # 2. 데이터 분할
    images_dir = Path(args.images)
    labels_dir = Path(args.labels)

    print(f"\n📁 이미지 디렉토리: {images_dir}")
    print(f"📁 라벨 디렉토리: {labels_dir}")

    train_files, val_files = split_dataset(images_dir, labels_dir, args.train_ratio)

    if not train_files and not val_files:
        print("\n❌ 데이터셋 생성 실패!")
        print("\n📌 라벨링 방법:")
        print("   1. LabelImg 설치: pip install labelImg")
        print("   2. 실행: labelImg")
        print("   3. Open Dir → 이미지 폴더 선택")
        print("   4. Change Save Dir → data/labels 선택")
        print("   5. YOLO 포맷 선택 (View → YOLO)")
        print("   6. 문항 영역 라벨링 후 저장")
        return

    print(f"\n📈 데이터 분할: 학습 {len(train_files)}개 / 검증 {len(val_files)}개")

    # 3. 파일 복사
    copy_files_to_dataset(train_files, TRAIN_IMAGES, TRAIN_LABELS, "학습 데이터")
    copy_files_to_dataset(val_files, VAL_IMAGES, VAL_LABELS, "검증 데이터")

    # 4. YAML 파일 생성
    yaml_path = create_dataset_yaml(args.classes)

    print("\n" + "=" * 50)
    print(" ✅ 데이터셋 준비 완료!")
    print("=" * 50)
    print(f"\n다음 단계: YOLO 학습")
    print(f"  python step3_train_yolo.py --data {yaml_path}")


if __name__ == "__main__":
    main()


