"""
3단계: YOLO 모델 학습

YOLO11 Nano 모델을 사용하여 문항 영역을 감지하는 모델을 학습합니다.

RTX 3050 (6-8GB VRAM) 최적화:
- YOLO11n (Nano) 모델 사용
- 배치 사이즈: 8-16
- 이미지 크기: 640

사용법:
    python step3_train_yolo.py --data data/yolo_dataset/dataset.yaml
    python step3_train_yolo.py --resume  # 학습 재개
"""

import os
import sys
from pathlib import Path
import argparse

try:
    from ultralytics import YOLO
except ImportError:
    print("ultralytics 설치 필요: pip install ultralytics")
    sys.exit(1)

import torch

from config import MODELS_DIR, DATA_DIR


def check_gpu():
    """GPU 상태 확인."""
    print("\n🖥️  하드웨어 정보:")
    print(f"   PyTorch 버전: {torch.__version__}")
    print(f"   CUDA 사용 가능: {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        print(f"   VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        return True
    else:
        print("   ⚠️  GPU가 감지되지 않았습니다. CPU로 학습합니다.")
        return False


def train_yolo(
    data_yaml: Path,
    epochs: int = 100,
    batch_size: int = 8,
    img_size: int = 640,
    model_name: str = "yolo11n.pt",
    project_name: str = "question_detection",
    resume: bool = False
):
    """YOLO 모델 학습.

    Args:
        data_yaml: 데이터셋 설정 파일 경로
        epochs: 학습 에포크 수
        batch_size: 배치 크기
        img_size: 입력 이미지 크기
        model_name: 기본 모델 (yolo11n/s/m/l/x)
        project_name: 프로젝트 이름
        resume: 이전 학습 재개 여부
    """
    print("\n" + "=" * 50)
    print(" 🚀 YOLO 모델 학습 시작")
    print("=" * 50)

    # GPU 확인
    has_gpu = check_gpu()

    # 모델 로드
    if resume:
        # 가장 최근 학습된 모델 찾기
        last_model = MODELS_DIR / "runs" / project_name / "train" / "weights" / "last.pt"
        if last_model.exists():
            print(f"\n📂 이전 모델 로드: {last_model}")
            model = YOLO(str(last_model))
        else:
            print("⚠️  이전 학습 모델을 찾을 수 없습니다. 새로 시작합니다.")
            model = YOLO(model_name)
    else:
        print(f"\n📂 기본 모델 로드: {model_name}")
        model = YOLO(model_name)

    # 학습 설정
    print(f"\n📊 학습 설정:")
    print(f"   데이터셋: {data_yaml}")
    print(f"   에포크: {epochs}")
    print(f"   배치 크기: {batch_size}")
    print(f"   이미지 크기: {img_size}")
    print(f"   디바이스: {'cuda' if has_gpu else 'cpu'}")

    # 학습 실행
    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        batch=batch_size,
        imgsz=img_size,
        project=str(MODELS_DIR / "runs"),
        name=project_name,
        exist_ok=True,
        pretrained=True,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
        box=7.5,
        cls=0.5,
        dfl=1.5,
        device=0 if has_gpu else "cpu",
        workers=4 if has_gpu else 2,
        patience=20,  # Early stopping
        save=True,
        save_period=10,
        plots=True,
        verbose=True,
    )

    # 결과 저장
    best_model = MODELS_DIR / "runs" / project_name / "train" / "weights" / "best.pt"
    final_model = MODELS_DIR / "yolo_questions.pt"

    if best_model.exists():
        import shutil
        shutil.copy2(best_model, final_model)
        print(f"\n✅ 최종 모델 저장: {final_model}")

    return results


def validate_model(model_path: Path, data_yaml: Path):
    """학습된 모델 검증.

    Args:
        model_path: 모델 경로
        data_yaml: 데이터셋 설정 파일
    """
    print("\n" + "=" * 50)
    print(" 🔍 모델 검증")
    print("=" * 50)

    model = YOLO(str(model_path))
    results = model.val(data=str(data_yaml))

    print("\n📊 검증 결과:")
    print(f"   mAP50: {results.box.map50:.4f}")
    print(f"   mAP50-95: {results.box.map:.4f}")

    return results


def main():
    parser = argparse.ArgumentParser(description="YOLO 모델 학습")
    parser.add_argument(
        "--data", type=str,
        default=str(DATA_DIR / "yolo_dataset" / "dataset.yaml"),
        help="데이터셋 YAML 경로"
    )
    parser.add_argument("--epochs", type=int, default=100, help="에포크 수")
    parser.add_argument("--batch", type=int, default=8, help="배치 크기 (RTX 3050: 8-16)")
    parser.add_argument("--img-size", type=int, default=640, help="이미지 크기")
    parser.add_argument("--model", type=str, default="yolo11n.pt",
                        choices=["yolo11n.pt", "yolo11s.pt", "yolo11m.pt"],
                        help="기본 모델 (n=nano, s=small, m=medium)")
    parser.add_argument("--resume", action="store_true", help="이전 학습 재개")
    parser.add_argument("--validate", action="store_true", help="검증만 실행")

    args = parser.parse_args()

    data_yaml = Path(args.data)

    if not data_yaml.exists():
        print(f"❌ 데이터셋 파일을 찾을 수 없습니다: {data_yaml}")
        print("\n먼저 step2_prepare_dataset.py를 실행하세요.")
        return

    if args.validate:
        model_path = MODELS_DIR / "yolo_questions.pt"
        if model_path.exists():
            validate_model(model_path, data_yaml)
        else:
            print(f"❌ 모델을 찾을 수 없습니다: {model_path}")
    else:
        train_yolo(
            data_yaml=data_yaml,
            epochs=args.epochs,
            batch_size=args.batch,
            img_size=args.img_size,
            model_name=args.model,
            resume=args.resume
        )


if __name__ == "__main__":
    main()


