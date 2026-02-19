"""
1단계: PDF → 이미지 변환 파이프라인

기출 시험지 PDF를 고해상도 이미지로 변환합니다.
- 300 DPI로 변환 (YOLO 인식 정확도 향상)
- PNG/WebP 포맷으로 저장

사용법:
    python step1_pdf_to_images.py [--pdf PATH] [--all]
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
import argparse

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF 설치 필요: pip install PyMuPDF")
    sys.exit(1)

from PIL import Image
from tqdm import tqdm

from config import PDF_INPUT_DIR, IMAGE_OUTPUT_DIR, IMAGE_DPI


def pdf_to_images(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = IMAGE_DPI,
    output_format: str = "png"
) -> List[Path]:
    """PDF 파일을 이미지로 변환.

    Args:
        pdf_path: PDF 파일 경로
        output_dir: 출력 디렉토리
        dpi: 해상도 (기본 300)
        output_format: 출력 포맷 (png, webp, jpg)

    Returns:
        생성된 이미지 파일 경로 리스트
    """
    pdf_name = pdf_path.stem
    pdf_output_dir = output_dir / pdf_name
    pdf_output_dir.mkdir(parents=True, exist_ok=True)

    saved_images = []

    print(f"\n📄 PDF 변환 시작: {pdf_path.name}")

    # PDF 열기
    doc = fitz.open(pdf_path)

    # 해상도 설정 (72 DPI 기준 스케일)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for page_num in tqdm(range(len(doc)), desc="페이지 변환"):
        page = doc[page_num]

        # 이미지로 렌더링
        pix = page.get_pixmap(matrix=matrix)

        # PIL Image로 변환
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # 저장
        output_path = pdf_output_dir / f"page_{page_num + 1:03d}.{output_format}"

        if output_format == "webp":
            img.save(output_path, "WEBP", quality=85)
        elif output_format == "jpg":
            img.save(output_path, "JPEG", quality=90)
        else:
            img.save(output_path, "PNG")

        saved_images.append(output_path)

    doc.close()

    print(f"✅ 완료: {len(saved_images)}개 이미지 생성")
    print(f"   저장 위치: {pdf_output_dir}")

    return saved_images


def convert_all_pdfs(input_dir: Path, output_dir: Path) -> dict:
    """디렉토리 내 모든 PDF 변환.

    Args:
        input_dir: PDF 디렉토리
        output_dir: 출력 디렉토리

    Returns:
        {pdf_name: [image_paths]} 형태의 딕셔너리
    """
    results = {}
    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"⚠️  PDF 파일이 없습니다: {input_dir}")
        return results

    print(f"\n🔍 발견된 PDF: {len(pdf_files)}개")

    for pdf_path in pdf_files:
        images = pdf_to_images(pdf_path, output_dir)
        results[pdf_path.stem] = images

    return results


def main():
    parser = argparse.ArgumentParser(description="PDF를 이미지로 변환")
    parser.add_argument("--pdf", type=str, help="변환할 PDF 파일 경로")
    parser.add_argument("--all", action="store_true", help="data/pdfs 내 모든 PDF 변환")
    parser.add_argument("--dpi", type=int, default=IMAGE_DPI, help=f"해상도 (기본: {IMAGE_DPI})")
    parser.add_argument("--format", type=str, default="png", choices=["png", "webp", "jpg"])

    args = parser.parse_args()

    print("=" * 50)
    print(" 📚 PDF → 이미지 변환 도구")
    print("=" * 50)

    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"❌ 파일을 찾을 수 없습니다: {pdf_path}")
            return
        pdf_to_images(pdf_path, IMAGE_OUTPUT_DIR, args.dpi, args.format)

    elif args.all:
        convert_all_pdfs(PDF_INPUT_DIR, IMAGE_OUTPUT_DIR)

    else:
        print("\n사용법:")
        print("  단일 PDF:  python step1_pdf_to_images.py --pdf ./시험지.pdf")
        print("  전체 PDF:  python step1_pdf_to_images.py --all")
        print(f"\n📁 PDF 디렉토리: {PDF_INPUT_DIR}")
        print(f"📁 출력 디렉토리: {IMAGE_OUTPUT_DIR}")


if __name__ == "__main__":
    main()


