"""
4단계: YOLO로 문항 영역 감지 및 크롭

학습된 YOLO 모델을 사용하여:
1. 시험지 이미지에서 문항 영역 감지
2. 개별 문항 이미지로 크롭
3. DB에 메타데이터 저장

사용법:
    python step4_crop_questions.py --image ./page_001.png
    python step4_crop_questions.py --dir ./data/images/2024_국가직
    python step4_crop_questions.py --all
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import argparse

try:
    from ultralytics import YOLO
except ImportError:
    print("ultralytics 설치 필요: pip install ultralytics")
    sys.exit(1)

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm

from config import (
    IMAGE_OUTPUT_DIR, CROP_OUTPUT_DIR, MODELS_DIR,
    YOLO_MODEL_PATH, YOLO_CONFIDENCE, IMAGE_FORMAT, IMAGE_QUALITY
)


class QuestionCropper:
    """YOLO 기반 문항 크롭 도구."""

    def __init__(self, model_path: Path = YOLO_MODEL_PATH, confidence: float = YOLO_CONFIDENCE):
        """초기화.

        Args:
            model_path: YOLO 모델 경로
            confidence: 감지 신뢰도 임계값
        """
        if not model_path.exists():
            raise FileNotFoundError(f"모델을 찾을 수 없습니다: {model_path}")

        self.model = YOLO(str(model_path))
        self.confidence = confidence
        print(f"✅ YOLO 모델 로드: {model_path}")

    def calculate_iou(self, box1: List[float], box2: List[float]) -> float:
        """두 박스의 IoU (Intersection over Union) 계산.

        Args:
            box1, box2: [x1, y1, x2, y2] 형식

        Returns:
            IoU 값 (0~1)
        """
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def remove_duplicates(self, detections: List[Dict[str, Any]], iou_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """IoU 기반 중복 박스 제거 (높은 confidence 유지).

        Args:
            detections: 감지 결과 리스트
            iou_threshold: 중복으로 간주할 IoU 임계값

        Returns:
            중복 제거된 리스트
        """
        if not detections:
            return []

        # confidence 높은 순으로 정렬
        sorted_dets = sorted(detections, key=lambda d: d["confidence"], reverse=True)

        keep = []
        while sorted_dets:
            best = sorted_dets.pop(0)
            keep.append(best)

            # 나머지 중 best와 IoU가 높은 것들 제거
            sorted_dets = [
                det for det in sorted_dets
                if self.calculate_iou(best["bbox"], det["bbox"]) < iou_threshold
            ]

        return keep

    def sort_two_column_layout(self, detections: List[Dict[str, Any]], image_path: Path) -> List[Dict[str, Any]]:
        """2단 레이아웃 기준 정렬 (왼쪽 열 → 오른쪽 열, 각각 위→아래).

        Args:
            detections: 감지 결과 리스트
            image_path: 이미지 경로 (중앙선 계산용)

        Returns:
            정렬된 리스트
        """
        if not detections:
            return []

        # 이미지 너비 확인
        img = cv2.imread(str(image_path))
        img_width = img.shape[1]
        mid_x = img_width / 2

        # 왼쪽/오른쪽 열 분리 (박스 중심 x좌표 기준)
        left_column = []
        right_column = []

        for det in detections:
            bbox = det["bbox"]
            center_x = (bbox[0] + bbox[2]) / 2

            if center_x < mid_x:
                left_column.append(det)
            else:
                right_column.append(det)

        # 각 열 내에서 y좌표 기준 정렬
        left_column.sort(key=lambda d: d["bbox"][1])
        right_column.sort(key=lambda d: d["bbox"][1])

        # 왼쪽 → 오른쪽 순으로 결합
        return left_column + right_column

    def detect_questions(self, image_path: Path) -> List[Dict[str, Any]]:
        """이미지에서 문항 영역 감지.

        Args:
            image_path: 이미지 경로

        Returns:
            감지된 영역 리스트 [{class, confidence, bbox: [x1,y1,x2,y2]}, ...]
        """
        results = self.model(str(image_path), conf=self.confidence, verbose=False)

        detections = []
        for result in results:
            boxes = result.boxes
            for i, box in enumerate(boxes):
                detection = {
                    "class_id": int(box.cls[0]),
                    "class_name": result.names[int(box.cls[0])],
                    "confidence": float(box.conf[0]),
                    "bbox": box.xyxy[0].tolist(),  # [x1, y1, x2, y2]
                }
                detections.append(detection)

        # 1. IoU 기반 중복 제거 (더 엄격하게)
        detections = self.remove_duplicates(detections, iou_threshold=0.3)

        # 2. 2단 레이아웃 기준 정렬 (왼쪽 열 → 오른쪽 열)
        detections = self.sort_two_column_layout(detections, image_path)

        return detections

    def crop_region(
        self,
        image_path: Path,
        bbox: List[float],
        padding: int = 10
    ) -> np.ndarray:
        """이미지에서 영역 크롭.

        Args:
            image_path: 이미지 경로
            bbox: [x1, y1, x2, y2] 좌표
            padding: 여백 (픽셀)

        Returns:
            크롭된 이미지 (numpy array)
        """
        img = cv2.imread(str(image_path))
        h, w = img.shape[:2]

        x1, y1, x2, y2 = [int(v) for v in bbox]

        # 패딩 적용 (이미지 경계 확인)
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(w, x2 + padding)
        y2 = min(h, y2 + padding)

        cropped = img[y1:y2, x1:x2]
        return cropped

    def process_image(
        self,
        image_path: Path,
        output_dir: Path,
        exam_info: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """이미지 처리 및 문항 크롭.

        Args:
            image_path: 이미지 경로
            output_dir: 출력 디렉토리
            exam_info: 시험 정보 (year, subject 등)

        Returns:
            처리 결과 리스트
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # 문항 감지
        detections = self.detect_questions(image_path)

        if not detections:
            print(f"   ⚠️  감지된 문항 없음: {image_path.name}")
            return []

        results = []
        question_num = 1

        for det in detections:
            # 문항 클래스만 크롭 (question, question_number 등)
            if det["class_name"] not in ["question", "question_number"]:
                continue

            # 크롭
            cropped = self.crop_region(image_path, det["bbox"])

            # 파일명 생성
            stem = image_path.stem
            crop_filename = f"{stem}_q{question_num:02d}.{IMAGE_FORMAT}"
            crop_path = output_dir / crop_filename

            # 저장
            if IMAGE_FORMAT == "webp":
                # OpenCV → PIL로 변환하여 WebP 저장
                cropped_rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(cropped_rgb)
                pil_img.save(crop_path, "WEBP", quality=IMAGE_QUALITY)
            else:
                cv2.imwrite(str(crop_path), cropped)

            # 결과 기록
            result = {
                "source_image": str(image_path),
                "crop_path": str(crop_path),
                "question_no": question_num,
                "bbox": det["bbox"],
                "confidence": det["confidence"],
                "class_name": det["class_name"],
                **(exam_info or {})
            }
            results.append(result)

            question_num += 1

        return results

    def process_directory(
        self,
        images_dir: Path,
        output_dir: Path,
        exam_info: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """디렉토리 내 모든 이미지 처리.

        Args:
            images_dir: 이미지 디렉토리
            output_dir: 출력 디렉토리
            exam_info: 시험 정보

        Returns:
            전체 처리 결과 리스트
        """
        image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
        images = sorted([
            f for f in images_dir.iterdir()
            if f.suffix.lower() in image_extensions
        ])

        if not images:
            print(f"⚠️  이미지 파일이 없습니다: {images_dir}")
            return []

        print(f"\n📂 디렉토리 처리: {images_dir}")
        print(f"   이미지 수: {len(images)}개")

        all_results = []

        for img_path in tqdm(images, desc="문항 추출"):
            results = self.process_image(img_path, output_dir, exam_info)
            all_results.extend(results)

        return all_results


def save_results_json(results: List[Dict[str, Any]], output_path: Path):
    """결과를 JSON으로 저장.

    Args:
        results: 처리 결과 리스트
        output_path: 출력 파일 경로
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"✅ 결과 저장: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="YOLO로 문항 영역 크롭")
    parser.add_argument("--image", type=str, help="단일 이미지 처리")
    parser.add_argument("--dir", type=str, help="디렉토리 내 이미지 처리")
    parser.add_argument("--all", action="store_true", help="data/images 전체 처리")
    parser.add_argument("--model", type=str, default=str(YOLO_MODEL_PATH), help="모델 경로")
    parser.add_argument("--conf", type=float, default=YOLO_CONFIDENCE, help="신뢰도 임계값")
    parser.add_argument("--year", type=int, help="시험 연도")
    parser.add_argument("--subject", type=str, help="과목명")

    args = parser.parse_args()

    print("=" * 50)
    print(" ✂️  YOLO 문항 크롭 도구")
    print("=" * 50)

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"\n❌ 모델을 찾을 수 없습니다: {model_path}")
        print("   먼저 step3_train_yolo.py로 모델을 학습하세요.")
        return

    # 크로퍼 초기화
    cropper = QuestionCropper(model_path, args.conf)

    # 시험 정보
    exam_info = {}
    if args.year:
        exam_info["year"] = args.year
    if args.subject:
        exam_info["subject"] = args.subject

    all_results = []

    if args.image:
        # 단일 이미지
        img_path = Path(args.image)
        if not img_path.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {img_path}")
            return

        output_dir = CROP_OUTPUT_DIR / img_path.stem
        results = cropper.process_image(img_path, output_dir, exam_info)
        all_results.extend(results)
        print(f"\n✅ 추출 완료: {len(results)}개 문항")

    elif args.dir:
        # 디렉토리
        images_dir = Path(args.dir)
        if not images_dir.exists():
            print(f"❌ 디렉토리를 찾을 수 없습니다: {images_dir}")
            return

        output_dir = CROP_OUTPUT_DIR / images_dir.name
        results = cropper.process_directory(images_dir, output_dir, exam_info)
        all_results.extend(results)

    elif args.all:
        # 전체 처리
        for subdir in IMAGE_OUTPUT_DIR.iterdir():
            if subdir.is_dir():
                output_dir = CROP_OUTPUT_DIR / subdir.name
                results = cropper.process_directory(subdir, output_dir, exam_info)
                all_results.extend(results)

    else:
        print("\n사용법:")
        print("  단일 이미지:  python step4_crop_questions.py --image ./page.png")
        print("  디렉토리:     python step4_crop_questions.py --dir ./data/images/2024_국가직")
        print("  전체:         python step4_crop_questions.py --all")
        return

    # 결과 저장
    if all_results:
        json_path = CROP_OUTPUT_DIR / "crop_results.json"
        save_results_json(all_results, json_path)

        print("\n" + "=" * 50)
        print(f" ✅ 총 {len(all_results)}개 문항 추출 완료!")
        print("=" * 50)
        print(f"\n📁 출력 디렉토리: {CROP_OUTPUT_DIR}")
        print(f"📄 결과 JSON: {json_path}")
        print("\n다음 단계: DB에 저장")
        print("  python step5_save_to_db.py")


if __name__ == "__main__":
    main()

