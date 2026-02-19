#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Marker로 단일 PDF → Markdown을 재생성하고, 문항 포맷을 정규화해 저장한다.

사용 예 (PowerShell):
  conda activate marker
  python -m backend.tools.rebuild_md_from_pdf_marker `
    --pdf "data/gongmuwon/raw/250621+지방+9급+회계학-B.pdf" `
    --out-md "data/gongmuwon/intermediate/markdown/250621+지방+9급+회계학-B.md"
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import tempfile
from typing import Dict, List, Tuple


_QSTART_RE = re.compile(
    r"(?:^|\n)\s*(?:[-*]\s*)?(?:#+\s*)?(?:문\s*)?(\d{1,3})\s*[.)]\s*",
    flags=re.MULTILINE,
)


def _extract_questions(md: str, max_q: int = 20) -> Dict[int, str]:
    """md에서 1..max_q 문항 본문을 추출(순서 무관)"""
    matches = list(_QSTART_RE.finditer(md))
    if not matches:
        return {}

    spans: List[Tuple[int, int, int]] = []
    for i, m in enumerate(matches):
        qid_s = (m.group(1) or "").strip()
        if not qid_s.isdigit():
            continue
        qid = int(qid_s)
        if qid < 1 or qid > max_q:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        spans.append((qid, start, end))

    out: Dict[int, str] = {}
    for qid, s, e in spans:
        body = md[s:e].strip()
        # 같은 qid가 여러 번 잡히면 더 긴 본문을 선택
        if body and (qid not in out or len(body) > len(out[qid])):
            out[qid] = body
    return out


def normalize_exam_md(md: str, subject: str, max_q: int = 20) -> str:
    """
    다른 과목 md 스타일에 맞추어:
    - 첫 줄에 '## {subject}'
    - 문항을 1..max_q 순서로 '- n. ' 시작
    """
    qmap = _extract_questions(md, max_q=max_q)

    lines: List[str] = [f"## {subject}", ""]
    for n in range(1, max_q + 1):
        body = (qmap.get(n) or "").strip()
        if not body:
            lines.append(f"- {n}. (본문 추출 실패: PDF→md 변환/OCR 누락 가능)")
            continue

        # 첫 줄은 질문으로 보이게 만들기
        body_lines = body.splitlines()
        first = body_lines[0].strip()
        rest = [ln.rstrip() for ln in body_lines[1:]]

        lines.append(f"- {n}. {first}")
        for ln in rest:
            if not ln.strip():
                continue
            # 기존에 이미 bullet이면 2칸 들여쓰기만 보장
            if re.match(r"^\s*[-*]\s+", ln):
                lines.append("  " + ln.strip())
            else:
                # 선택지/설명도 모두 들여쓰기
                lines.append("  " + ln.strip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def marker_pdf_to_md(pdf_path: str, *, page_range: str | None = None, force_ocr: bool = False) -> str:
    """
    marker CLI로 단일 pdf를 md로 변환하고 md 문자열을 반환한다.
    """
    with tempfile.TemporaryDirectory() as tmp:
        in_dir = os.path.join(tmp, "in")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        import shutil

        shutil.copy2(pdf_path, os.path.join(in_dir, os.path.basename(pdf_path)))

        cmd = [
            "marker",
            in_dir,
            "--output_dir",
            out_dir,
            "--output_format",
            "markdown",
            "--disable_multiprocessing",
        ]
        if page_range:
            cmd += ["--page_range", page_range]
        if force_ocr:
            cmd += ["--force_ocr"]
        # 작은 글자/표/수식이 많은 과목은 dpi를 올리는 게 유리할 때가 많다.
        cmd += ["--highres_image_dpi", "300", "--lowres_image_dpi", "150"]

        subprocess.run(cmd, check=True)

        # marker는 보통 out_dir/<pdfname>/<pdfname>.md 형태
        md_files: List[str] = []
        for root, _dirs, files in os.walk(out_dir):
            for fn in files:
                if fn.lower().endswith(".md"):
                    md_files.append(os.path.join(root, fn))
        if not md_files:
            raise RuntimeError(f"marker 출력 md를 찾을 수 없습니다: {out_dir}")
        md_files.sort(key=lambda p: (len(p), p))
        with open(md_files[0], "r", encoding="utf-8") as f:
            return f.read()


def main() -> int:
    ap = argparse.ArgumentParser(description="Marker로 PDF→MD 재생성 + 문항 포맷 정규화")
    ap.add_argument("--pdf", required=True, help="입력 PDF 경로")
    ap.add_argument("--out-md", required=True, help="출력 md 경로")
    ap.add_argument("--subject", default=None, help="과목명(미지정시 파일명에서 추정)")
    ap.add_argument("--max-q", type=int, default=20, help="문항 수(기본 20)")
    ap.add_argument("--page-range", default=None, help="marker page_range (예: 0-1)")
    ap.add_argument("--force-ocr", action="store_true", help="marker 강제 OCR")
    args = ap.parse_args()

    pdf = args.pdf
    subject = args.subject
    if not subject:
        base = os.path.splitext(os.path.basename(pdf))[0]
        if "9급+" in base:
            subject = base.split("9급+", 1)[1]
            subject = re.sub(r"-[A-Za-z]$", "", subject).strip()
        else:
            subject = base

    md_raw = marker_pdf_to_md(pdf, page_range=args.page_range, force_ocr=args.force_ocr)
    md_norm = normalize_exam_md(md_raw, subject=subject, max_q=args.max_q)

    os.makedirs(os.path.dirname(args.out_md) or ".", exist_ok=True)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(md_norm)
    print(f"[OK] rebuilt md → {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


