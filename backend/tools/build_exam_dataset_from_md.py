#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
중간 산출물 Markdown(.md) + 정답가안(PDF) → 학습용 JSONL 생성 스크립트

의도:
- Marker/Docling 변환을 이미 완료한 md 파일들을 재활용한다.
- 정답가안 PDF에서 과목별 1~20번 정답을 추출하고,
  각 md에서 1~20번 문항을 분리해 매핑한다.

사용 예 (PowerShell):
  conda activate marker
  python -m backend.tools.build_exam_dataset_from_md `
    --md-dir "data/gongmuwon/intermediate/markdown" `
    --answer-pdf "data/gongmuwon/raw/2025년도+지방공무원+9급+등+공개(경력)경쟁임용+필기시험+정답가안.pdf" `
    --out "data/gongmuwon/dataset/all_subjects_from_md.jsonl"
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class QuestionItem:
    id: str
    question: str
    answer: str
    subject: Optional[str] = None
    source_md: Optional[str] = None
    source_pdf: Optional[str] = None


DEFAULT_SPLIT_REGEX = (
    # md는 "- 1." 처럼 bullet prefix가 있을 수 있어 '-'를 허용한다.
    r"(?:^|\n)\s*(?:[-*]\s*)?(?:#+\s*)?(?:문\s*)?(\d{1,3})\s*[.)]\s*"
    r"(?![①②③④⑤⑥⑦⑧⑨⑩㉠㉡㉢㉣㉤㉥㉦㉧㉨㉩㉪㉫㉬㉭㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷㉸㉹㉺㉻])"
)


def _normalize_subject_name(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s*\(.*?\)\s*", "", s).strip()
    return s


def infer_subject_from_filename(filename: str) -> str:
    base = os.path.basename(filename)
    base = os.path.splitext(base)[0]
    base = re.sub(r"\s*\(\d+\)\s*$", "", base).strip()
    if "9급+" in base:
        subject_part = base.split("9급+", 1)[1]
        subject_part = re.sub(r"-[A-Za-z]$", "", subject_part).strip()
        if subject_part:
            return subject_part
    return base


def extract_answer_map_by_subject(
    answer_pdf_path: str,
    pages: Optional[str] = None,
) -> Dict[str, Dict[str, str]]:
    try:
        import pdfplumber  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "pdfplumber가 설치되어 있지 않습니다. "
            "conda activate marker 후 pip install pdfplumber 를 먼저 진행하세요."
        ) from exc

    ans: Dict[str, Dict[str, str]] = {}

    def _parse_pages(total: int) -> List[int]:
        if not pages:
            return list(range(total))
        out: List[int] = []
        for part in pages.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                start = max(1, int(a))
                end = min(total, int(b))
                out.extend([i - 1 for i in range(start, end + 1)])
            else:
                p = int(part)
                if 1 <= p <= total:
                    out.append(p - 1)
        return sorted(set(out)) if out else [0]

    with pdfplumber.open(answer_pdf_path) as pdf:
        target_pages = _parse_pages(len(pdf.pages))
        for page_idx in target_pages:
            page = pdf.pages[page_idx]
            table = page.extract_table()
            if not table:
                continue
            header = table[0] if table else None
            if not header:
                continue
            try:
                subj_idx = header.index("과목명")
            except ValueError:
                subj_idx = 1
            start_idx = None
            for i, h in enumerate(header):
                if (h or "").strip() == "1번":
                    start_idx = i
                    break
            if start_idx is None:
                continue

            for row in table[1:]:
                if not row:
                    continue
                subject_raw = row[subj_idx] if subj_idx < len(row) else ""
                subject = _normalize_subject_name(str(subject_raw))
                if not subject:
                    continue
                subj_map = ans.setdefault(subject, {})
                for offset in range(0, 20):
                    col = start_idx + offset
                    if col >= len(row):
                        break
                    val = row[col]
                    a = str(val).strip() if val is not None else ""
                    qid = str(offset + 1)
                    if a:
                        subj_map[qid] = a
    return ans


def split_questions(
    md_text: str,
    split_regex: str = DEFAULT_SPLIT_REGEX,
    max_question_id: int = 20,
) -> List[Tuple[str, str]]:
    pattern = re.compile(split_regex, flags=re.MULTILINE)
    expected = 1
    starts: List[Tuple[int, int, str]] = []
    for m in pattern.finditer(md_text):
        qid = (m.group(1) or "").strip()
        if not qid.isdigit():
            continue
        n = int(qid)
        if n < expected:
            continue
        if n > max_question_id:
            break
        starts.append((m.start(), m.end(), qid))
        expected = n + 1
        if expected > max_question_id:
            break
    if not starts:
        return []
    out: List[Tuple[str, str]] = []
    for i, (m_start, m_end, qid) in enumerate(starts):
        next_start = starts[i + 1][0] if i + 1 < len(starts) else len(md_text)
        body = md_text[m_end:next_start].strip()
        if body:
            out.append((qid, body))
    return out


def build_dataset_from_md(
    md_text: str,
    subject: str,
    answer_map_by_subject: Dict[str, Dict[str, str]],
    *,
    split_regex: str = DEFAULT_SPLIT_REGEX,
    max_question_id: int = 20,
) -> List[QuestionItem]:
    q_pairs = split_questions(md_text, split_regex=split_regex, max_question_id=max_question_id)
    by_id: Dict[str, str] = {qid: body for qid, body in q_pairs if qid}

    subject_norm = _normalize_subject_name(subject)
    subj_answers = answer_map_by_subject.get(subject_norm, {})

    items: List[QuestionItem] = []
    for n in range(1, max_question_id + 1):
        qid = str(n)
        body = (by_id.get(qid) or "").strip()
        if not body:
            body = "(본문 추출 실패: md 분리/레이아웃/OCR 누락 가능)"
        items.append(
            QuestionItem(
                id=qid,
                question=f"문제 {qid}: {body}",
                answer=subj_answers.get(qid, "정답 정보 없음"),
                subject=subject_norm,
            )
        )
    return items


def write_jsonl(items: List[QuestionItem], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item.__dict__, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Markdown(.md) + 정답가안(PDF) → 학습용 JSONL 생성")
    parser.add_argument("--md-dir", required=True, help="Markdown 폴더 (예: data/gongmuwon/intermediate/markdown)")
    parser.add_argument("--md-glob", default="*.md", help="md 파일 glob (기본: *.md)")
    parser.add_argument("--answer-pdf", required=True, help="정답가안 PDF 경로")
    parser.add_argument("--answer-pages", default=None, help="정답지 페이지 범위(예: 1,2 또는 1-3). 기본: 전체")
    parser.add_argument("--out", required=True, help="출력 jsonl 경로")
    parser.add_argument("--split-regex", default=DEFAULT_SPLIT_REGEX, help="문항 분리 정규표현식")
    parser.add_argument("--max-question-id", type=int, default=20, help="과목별 문항 수(기본 20)")
    args = parser.parse_args()

    import glob

    md_files = sorted(glob.glob(os.path.join(args.md_dir, args.md_glob)))
    if not md_files:
        raise SystemExit(f"md 파일을 찾을 수 없습니다: {args.md_dir} / {args.md_glob}")

    answer_map_by_subject = extract_answer_map_by_subject(args.answer_pdf, pages=args.answer_pages)

    items: List[QuestionItem] = []
    for md_path in md_files:
        base = os.path.basename(md_path)
        # 혹시 OCR 테스트 산출물 등은 제외하고 싶으면 여기서 필터링 가능
        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()
        subject = infer_subject_from_filename(md_path)
        one = build_dataset_from_md(
            md_text,
            subject=subject,
            answer_map_by_subject=answer_map_by_subject,
            split_regex=args.split_regex,
            max_question_id=args.max_question_id,
        )
        for it in one:
            it.source_md = base
        items.extend(one)

    write_jsonl(items, args.out)
    print(f"[OK] 문항 {len(items)}개 생성 → {args.out}")
    missing = sum(1 for it in items if it.answer == "정답 정보 없음")
    if missing:
        print(f"[WARN] 정답 매칭 실패: {missing}개 (정답지 과목명 매칭/정규화 필요)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


