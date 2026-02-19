#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
시험지(PDF) + 정답지(PDF) → 학습용 데이터셋(JSON/JSONL) 생성 스크립트 (Marker 버전)

파이프라인:
1) Marker: 시험지 PDF를 Markdown으로 변환
2) pdfplumber: 정답지 PDF에서 {문항번호: 정답} 추출
3) 정규표현식: Markdown에서 문항 분리 (문 1. / 1. / 1) 등)
4) 병합: 문항 + 정답 매칭 후 JSON/JSONL 저장

사용 예:
  python -m backend.tools.build_exam_dataset_marker ^
    --exam-pdf data/exam.pdf ^
    --answer-pdf data/answer.pdf ^
    --out data/final_training_data.jsonl ^
    --format jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class QuestionItem:
    id: str
    question: str
    answer: str
    subject: Optional[str] = None
    source_pdf: Optional[str] = None


# Marker 마크다운은 줄마다 "5. ① ..." 같은 줄번호/세부항목(㉠㉡...)을 붙이는 경우가 있어,
# 보기/세부항목 라인에서 잘못 분리되지 않도록 negative lookahead를 둔다.
# (예: "3. ㉠ ...", "5. ① ...")
DEFAULT_SPLIT_REGEX = (
    r"(?:^|\n)\s*(?:#+\s*)?(?:문\s*)?(\d{1,3})\s*[.)]\s*"
    r"(?![①②③④⑤⑥⑦⑧⑨⑩㉠㉡㉢㉣㉤㉥㉦㉧㉨㉩㉪㉫㉬㉭㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷㉸㉹㉺㉻])"
)


def convert_exam_pdf_to_markdown_with_marker(exam_pdf_path: str) -> str:
    """
    Marker를 사용하여 PDF를 마크다운으로 변환합니다.

    Marker는 폴더 단위로 처리하므로, 임시 폴더를 만들어서 처리합니다.
    """
    # Marker 실행 파일 확인 (타임아웃 없이 빠르게 체크)
    import shutil
    marker_path = shutil.which("marker")
    if not marker_path:
        raise RuntimeError(
            "Marker가 설치되어 있지 않습니다. "
            "conda activate marker 환경에서 pip install marker-pdf 를 먼저 진행하세요."
        )

    # 임시 폴더 생성
    with tempfile.TemporaryDirectory() as temp_dir:
        # PDF 파일을 임시 폴더로 복사
        import shutil
        temp_pdf_path = os.path.join(temp_dir, os.path.basename(exam_pdf_path))
        shutil.copy2(exam_pdf_path, temp_pdf_path)

        # Marker로 변환 (마크다운 형식으로 출력)
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        try:
            result = subprocess.run(
                [
                    "marker",
                    temp_dir,
                    "--output_dir", output_dir,
                    "--output_format", "markdown",
                    "--disable_multiprocessing",  # Windows에서 안정성을 위해
                ],
                capture_output=True,
                text=True,
                timeout=600,  # 10분 타임아웃 (Marker는 첫 실행 시 모델 다운로드 시간 필요)
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Marker 변환 실패: {e.stderr}\n"
                f"stdout: {e.stdout}"
            ) from e
        except subprocess.TimeoutExpired:
            raise RuntimeError("Marker 변환 시간 초과 (5분 이상 소요)")

        # 변환된 마크다운 파일 찾기
        pdf_basename = os.path.splitext(os.path.basename(exam_pdf_path))[0]
        md_file = os.path.join(output_dir, f"{pdf_basename}.md")

        if not os.path.exists(md_file):
            # 파일명이 다를 수 있으므로 output_dir에서 .md 파일 찾기
            md_files = [f for f in os.listdir(output_dir) if f.endswith('.md')]
            if md_files:
                md_file = os.path.join(output_dir, md_files[0])
            else:
                raise RuntimeError(
                    f"변환된 마크다운 파일을 찾을 수 없습니다. "
                    f"출력 디렉토리: {output_dir}\n"
                    f"Marker 출력: {result.stdout}\n"
                    f"Marker 에러: {result.stderr}"
                )

        # 마크다운 파일 읽기
        with open(md_file, "r", encoding="utf-8") as f:
            return f.read()


def _normalize_subject_name(s: str) -> str:
    """
    정답표 과목명 셀은 줄바꿈/괄호 설명이 섞일 수 있어,
    파일명에서 추출한 과목명과 매칭되도록 정규화한다.
    """
    s = (s or "").strip()
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    # 괄호 설명 제거: "행정학개론 (지방행정 포함)" -> "행정학개론"
    s = re.sub(r"\s*\(.*?\)\s*", "", s).strip()
    return s


def extract_answer_map_by_subject(
    answer_pdf_path: str,
    pages: Optional[str] = None,
) -> Dict[str, Dict[str, str]]:
    try:
        import pdfplumber  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "pdfplumber가 설치되어 있지 않습니다. "
            "pip install pdfplumber 를 먼저 진행하세요."
        ) from exc

    ans: Dict[str, Dict[str, str]] = {}

    def _parse_pages(total: int) -> List[int]:
        if not pages:
            # 기본: 전체 페이지(정답표가 과목별로 여러 페이지에 분산될 수 있음)
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
            # 헤더: ["연번","과목명","책형","1번",...,"20번"]
            header = table[0] if table else None
            if not header:
                continue
            # 열 인덱스 추정
            try:
                subj_idx = header.index("과목명")
            except ValueError:
                subj_idx = 1
            # "1번"이 시작하는 열 찾기
            start_idx = None
            for i, h in enumerate(header):
                if (h or "").strip() == "1번":
                    start_idx = i
                    break
            if start_idx is None:
                # 테이블 구조가 예상과 다르면 skip
                continue

            for row in table[1:]:
                if not row:
                    continue
                subject_raw = row[subj_idx] if subj_idx < len(row) else ""
                subject = _normalize_subject_name(str(subject_raw))
                if not subject:
                    continue
                subj_map = ans.setdefault(subject, {})

                # 1번~20번 값을 순서대로 수집
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
    """
    Returns list of (question_id, question_text_without_id_prefix)
    """
    # Marker 결과에는 "페이지/라인 번호"가 1~20 범위로 반복되는 경우가 많아서,
    # 단순 split은 과분할이 발생한다.
    # 해결: 1→2→...→max_question_id 순서로 "연속적으로 등장하는 문항 시작"만 채택한다.
    pattern = re.compile(split_regex, flags=re.MULTILINE)
    expected = 1
    starts: List[Tuple[int, int, str]] = []  # (match_start, match_end, qid)

    for m in pattern.finditer(md_text):
        qid = (m.group(1) or "").strip()
        if not qid.isdigit():
            continue
        n = int(qid)
        if n < expected:
            continue
        if n > max_question_id:
            break
        # 일부 과목(특히 영어)에서 4번처럼 지문이 이미지로 들어가 OCR이 누락되어
        # 번호가 건너뛰는 경우가 있음. 이때는 누락된 번호를 건너뛰고 다음 번호부터 계속 추출한다.
        starts.append((m.start(), m.end(), qid))
        expected = n + 1
        if expected > max_question_id:
            break

    if not starts:
        return []

    items: List[Tuple[str, str]] = []
    for i, (m_start, m_end, qid) in enumerate(starts):
        next_start = starts[i + 1][0] if i + 1 < len(starts) else len(md_text)
        body = md_text[m_end:next_start].strip()
        if body:
            items.append((qid, body))
    return items


def build_dataset(
    md_text: str,
    answer_map_by_subject: Dict[str, Dict[str, str]],
    split_regex: str,
    subject: str,
) -> List[QuestionItem]:
    q_pairs = split_questions(md_text, split_regex=split_regex, max_question_id=20)
    out: List[QuestionItem] = []
    subject_norm = _normalize_subject_name(subject)
    subj_answers = answer_map_by_subject.get(subject_norm, {})
    by_id: Dict[str, str] = {qid: body for qid, body in q_pairs if qid}

    # 과목별 시험지는 1~20번이 항상 존재한다는 전제에 맞춰
    # 본문 추출 실패(이미지/OCR 누락)도 문항을 생성해 정답 매칭은 유지한다.
    for n in range(1, 21):
        qid = str(n)
        body = (by_id.get(qid) or "").strip()
        if not body:
            body = "(본문 추출 실패: PDF 이미지/레이아웃/OCR 누락 가능)"
        out.append(
            QuestionItem(
                id=qid,
                question=f"문제 {qid}: {body}",
                answer=subj_answers.get(qid, "정답 정보 없음"),
                subject=subject_norm,
            )
        )
    return out


def write_json(items: List[QuestionItem], out_path: str) -> None:
    data = [item.__dict__ for item in items]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_jsonl(items: List[QuestionItem], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item.__dict__, ensure_ascii=False) + "\n")


def infer_subject_from_filename(filename: str) -> str:
    # 파일명에서 과목명을 대충 추출(사용자 raw 폴더 네이밍 기준)
    # 예: 250621+지방+9급+행정법총론-B.pdf -> 행정법총론
    base = os.path.basename(filename)
    base = os.path.splitext(base)[0]
    # 괄호/버전 제거
    base = re.sub(r"\s*\(\d+\)\s*$", "", base).strip()
    # 사용자 raw 네이밍: "...+9급+과목명-책형" 형태가 많음.
    # 과목명 안에 '+'가 포함될 수 있어(예: 행정학개론(지방행정+포함)) '+'로 단순 split은 위험.
    if "9급+" in base:
        subject_part = base.split("9급+", 1)[1]
        subject_part = re.sub(r"-[A-Za-z]$", "", subject_part).strip()
        if subject_part:
            return subject_part
    return base


def load_markdown_from_pdf(exam_pdf: str, dump_md_dir: Optional[str]) -> str:
    md_text = convert_exam_pdf_to_markdown_with_marker(exam_pdf)
    if dump_md_dir:
        os.makedirs(dump_md_dir, exist_ok=True)
        out_md = os.path.join(
            dump_md_dir,
            os.path.splitext(os.path.basename(exam_pdf))[0] + ".md",
        )
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(md_text)
    return md_text


def main() -> int:
    parser = argparse.ArgumentParser(description="시험지+정답지 PDF를 학습용 JSON/JSONL로 변환합니다. (Marker 버전)")
    parser.add_argument("--exam-pdf", default=None, help="시험지 PDF 경로(단일)")
    parser.add_argument("--exam-dir", default=None, help="시험지 PDF 폴더(배치)")
    parser.add_argument("--exam-glob", default="*.pdf", help="배치 모드에서 시험지 파일 glob(기본: *.pdf)")
    parser.add_argument("--answer-pdf", required=True, help="정답지 PDF 경로")
    parser.add_argument("--out", required=True, help="출력 파일 경로 (.json 또는 .jsonl)")
    parser.add_argument("--format", choices=["json", "jsonl"], default=None, help="출력 포맷(미지정시 확장자로 판단)")
    parser.add_argument("--split-regex", default=DEFAULT_SPLIT_REGEX, help="문항 분리 정규표현식(캡처 그룹으로 문항번호)")
    parser.add_argument("--answer-pages", default=None, help="정답지 페이지 범위(예: 1,2 또는 1-3). 기본: 전체")
    parser.add_argument("--dump-md", default=None, help="시험지 Markdown을 저장할 경로(단일 모드, 선택)")
    parser.add_argument("--dump-md-dir", default=None, help="배치 모드에서 Markdown 저장 폴더(선택)")
    args = parser.parse_args()

    if not args.exam_pdf and not args.exam_dir:
        raise SystemExit("ERROR: --exam-pdf 또는 --exam-dir 중 하나는 필수입니다.")
    if args.exam_pdf and args.exam_dir:
        raise SystemExit("ERROR: --exam-pdf 와 --exam-dir 은 동시에 사용할 수 없습니다.")

    answer_pdf = args.answer_pdf
    out_path = args.out
    out_format = args.format
    split_regex = args.split_regex

    if out_format is None:
        _, ext = os.path.splitext(out_path.lower())
        out_format = "jsonl" if ext == ".jsonl" else "json"

    answer_map_by_subject = extract_answer_map_by_subject(answer_pdf, pages=args.answer_pages)
    items: List[QuestionItem] = []

    # 단일 모드
    if args.exam_pdf:
        md_text = convert_exam_pdf_to_markdown_with_marker(args.exam_pdf)
        if args.dump_md:
            os.makedirs(os.path.dirname(args.dump_md) or ".", exist_ok=True)
            with open(args.dump_md, "w", encoding="utf-8") as f:
                f.write(md_text)
        subject = infer_subject_from_filename(args.exam_pdf)
        items = build_dataset(md_text, answer_map_by_subject, split_regex=split_regex, subject=subject)
        for it in items:
            it.source_pdf = os.path.basename(args.exam_pdf)

    # 배치 모드
    if args.exam_dir:
        import glob

        pattern = os.path.join(args.exam_dir, args.exam_glob)
        exam_files = sorted(glob.glob(pattern))

        # 정답가안 PDF는 배치 대상에서 제외 (같은 폴더에 있을 수 있음)
        answer_base = os.path.basename(answer_pdf)
        exam_files = [p for p in exam_files if os.path.basename(p) != answer_base]

        for exam_pdf in exam_files:
            print(f"[처리 중] {os.path.basename(exam_pdf)}")
            md_text = load_markdown_from_pdf(exam_pdf, dump_md_dir=args.dump_md_dir)
            subject = infer_subject_from_filename(exam_pdf)
            one = build_dataset(md_text, answer_map_by_subject, split_regex=split_regex, subject=subject)
            for it in one:
                it.source_pdf = os.path.basename(exam_pdf)
            items.extend(one)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if out_format == "json":
        write_json(items, out_path)
    else:
        write_jsonl(items, out_path)

    print(f"[OK] 문항 {len(items)}개 생성 → {out_path}")
    missing = sum(1 for it in items if it.answer == "정답 정보 없음")
    if missing:
        print(f"[WARN] 정답 매칭 실패: {missing}개 (정답지 파싱/정규식 점검 필요)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

