#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스캔(이미지) 기반 PDF(행정법총론 해설)를 Windows 내장 OCR(WinRT)로 텍스트 추출 후 Markdown으로 저장합니다.

요구사항/특징
- pdfplumber로 chars가 0인 스캔 PDF를 대상으로 함
- PyMuPDF로 페이지 렌더링 → Windows OCR로 인식
- 문항 구분(01~20)을 감지해 `## 01 ...` 형태로 섹션 분리

사용 예:
  python -m backend.tools.extract_adminlaw_pdf_to_md \
    --pdf "data/gongmuwon/raw/commentary/250621 지방직 9급 행정법총론 해설 이승철.pdf" \
    --out "data/gongmuwon/intermediate/markdown/commentary_md/250621 지방직 9급 행정법총론 해설 이승철.md"
"""

from __future__ import annotations

import argparse
import os
import re
from typing import List, Tuple, Optional

import fitz  # PyMuPDF


def _lazy_import_winrt():
    # winrt는 Windows에서만 동작하므로 지연 import
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import InMemoryRandomAccessStream

    return BitmapDecoder, OcrEngine, InMemoryRandomAccessStream


def ocr_page_to_text(
    doc: fitz.Document,
    page_index: int,
    *,
    zoom: float = 2.0,
    lang_tag: str = "ko-KR",
) -> str:
    """단일 페이지를 OCR하여 텍스트를 반환."""
    BitmapDecoder, OcrEngine, InMemoryRandomAccessStream = _lazy_import_winrt()

    page = doc.load_page(page_index)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_bytes = pix.tobytes("png")

    # bytes → WinRT BitmapDecoder
    stream = InMemoryRandomAccessStream()
    stream.write_async(img_bytes).get()
    stream.seek(0)
    decoder = BitmapDecoder.create_async(stream).get()
    bitmap = decoder.get_software_bitmap_async().get()

    # Language(winrt.windows.globalization)가 환경에 따라 없을 수 있어
    # 사용자 프로필 언어 기반 엔진을 우선 사용
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("Windows OCR 엔진을 초기화할 수 없습니다.")

    result = engine.recognize_async(bitmap).get()
    return (result.text or "").strip()


def clean_ocr_text(text: str) -> str:
    """OCR 결과 텍스트를 문서화하기 좋게 정리."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 흔한 OCR 오인식 기호 정리
    text = text.replace("•", "- ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 페이지 하단 불필요 구분선(____ 등) 완화
    text = re.sub(r"\n_{3,}\n", "\n\n", text)
    return text.strip()


_Q_START_RE = re.compile(
    r"(?m)^\s*(\d{2})\s+(행정법|행정쟁송|행정|법|총론|[가-힣].+)"
)


def split_into_questions(full_text: str) -> List[Tuple[str, str]]:
    """
    전체 OCR 텍스트를 문항별로 분리.
    반환: [(q_no_str, q_block_text), ...]
    """
    # 문항 시작 후보: "01 ..." 형태
    starts = []
    for m in re.finditer(r"(?m)^\s*(\d{2})\s+", full_text):
        q_no = m.group(1)
        if 1 <= int(q_no) <= 20:
            starts.append((m.start(), q_no))

    if not starts:
        return []

    blocks: List[Tuple[str, str]] = []
    for idx, (pos, q_no) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(full_text)
        block = full_text[pos:end].strip()
        blocks.append((q_no, block))

    # 같은 문항이 여러 페이지에서 반복 감지되면 이어붙이기(보수적)
    merged: List[Tuple[str, str]] = []
    for q_no, block in blocks:
        if merged and merged[-1][0] == q_no:
            merged[-1] = (q_no, (merged[-1][1] + "\n\n" + block).strip())
        else:
            merged.append((q_no, block))
    return merged


def format_markdown(question_blocks: List[Tuple[str, str]]) -> str:
    out: List[str] = []
    for q_no, block in question_blocks:
        # 제목 줄: 첫 줄을 헤더로
        lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not lines:
            continue

        title = lines[0]
        body = "\n".join(lines[1:]).strip()

        out.append(f"## {q_no} {title}")
        out.append("")
        if body:
            out.append(body)
            out.append("")
        out.append("---")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def extract_pdf_to_md(
    pdf_path: str,
    out_path: str,
    *,
    start_page: int = 1,
    end_page: Optional[int] = None,
    zoom: float = 2.0,
    lang_tag: str = "ko-KR",
) -> None:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF를 찾을 수 없습니다: {pdf_path}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with fitz.open(pdf_path) as doc:
        total = doc.page_count
        if end_page is None:
            end_page = total
        start_idx = max(0, start_page - 1)
        end_idx = min(total, end_page)

        page_texts: List[str] = []
        for page_idx in range(start_idx, end_idx):
            text = ocr_page_to_text(doc, page_idx, zoom=zoom, lang_tag=lang_tag)
            page_texts.append(clean_ocr_text(text))

    full_text = "\n\n".join([t for t in page_texts if t]).strip()
    if not full_text:
        raise RuntimeError("OCR 결과가 비어 있습니다. (렌더링/언어 설정을 확인하세요)")

    question_blocks = split_into_questions(full_text)
    if not question_blocks:
        # fallback: 문항 분리를 못 하면 전체를 그대로 저장
        md = full_text + "\n"
    else:
        md = format_markdown(question_blocks)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="행정법총론 해설 PDF(OCR) → Markdown")
    parser.add_argument("--pdf", required=True, type=str, help="입력 PDF 경로")
    parser.add_argument("--out", required=True, type=str, help="출력 md 경로")
    parser.add_argument("--start-page", type=int, default=1, help="시작 페이지(1-based)")
    parser.add_argument("--end-page", type=int, default=None, help="끝 페이지(1-based, 포함)")
    parser.add_argument("--zoom", type=float, default=2.0, help="렌더링 배율(기본 2.0)")
    parser.add_argument("--lang", type=str, default="ko-KR", help="OCR 언어 태그(기본 ko-KR)")
    args = parser.parse_args()

    try:
        extract_pdf_to_md(
            pdf_path=args.pdf,
            out_path=args.out,
            start_page=args.start_page,
            end_page=args.end_page,
            zoom=args.zoom,
            lang_tag=args.lang,
        )
        print(f"[완료] md 생성: {args.out}")
        return 0
    except Exception as e:
        # Windows 기본 콘솔(cp949) 환경에서도 깨지지 않게 ASCII로 출력
        print(f"ERROR: {e}", flush=True)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


