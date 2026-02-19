#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
해설 마크다운 파일을 JSONL 형식으로 변환합니다.

사용 예:
  python -m backend.tools.convert_commentary_md_to_jsonl \
    --md "data/gongmuwon/intermediate/markdown/commentary_md/2025 지방직 9급 한국사 해설 한pro.md" \
    --out "data/gongmuwon/dataset/commentary_korean_history.jsonl"
"""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Dict, List, Optional


def parse_answer_table(content: str) -> Dict[int, str]:
    """정답표에서 문제 번호와 정답을 추출합니다.

    Args:
        content: 마크다운 파일 내용

    Returns:
        {문제번호: 정답} 딕셔너리 (예: {1: "1", 2: "3"})
    """
    answer_map: Dict[int, str] = {}

    # 정답표 패턴 찾기
    answer_table_pattern = r'\[정답표\]\s*\n((?:\d+\s+)+)\n((?:[①②③④]\s+)+)'
    match = re.search(answer_table_pattern, content)

    if match:
        question_nums_line = match.group(1).strip()
        answers_line = match.group(2).strip()

        # 문제 번호 추출
        question_nums = re.findall(r'\d+', question_nums_line)
        # 정답 추출 (①②③④를 1,2,3,4로 변환)
        answers = re.findall(r'[①②③④]', answers_line)

        # 한글 숫자 기호를 아라비아 숫자로 변환
        korean_to_num = {'①': '1', '②': '2', '③': '3', '④': '4'}

        for i, (q_num, answer) in enumerate(zip(question_nums, answers)):
            question_id = int(q_num)
            answer_num = korean_to_num.get(answer, answer)
            answer_map[question_id] = answer_num

    return answer_map


def parse_commentary_sections(content: str) -> Dict[int, Dict[str, str]]:
    """해설 섹션에서 문제별 해설을 추출합니다.

    Args:
        content: 마크다운 파일 내용

    Returns:
        {문제번호: {"topic": 주제, "answer": 정답, "commentary": 해설}} 딕셔너리
    """
    commentary_map: Dict[int, Dict[str, str]] = {}

    # 페이지별로 분리
    pages = re.split(r'## 페이지 \d+', content)

    korean_to_num = {'①': '1', '②': '2', '③': '3', '④': '4'}

    for page in pages:
        # 왼쪽 영역과 오른쪽 영역 모두 찾기
        left_section_match = re.search(r'### 왼쪽 영역\s*\n\n(.*?)(?=\n### 오른쪽 영역|\n## 페이지|\Z)', page, re.DOTALL)
        right_section_match = re.search(r'### 오른쪽 영역\s*\n\n(.*?)(?=\n## 페이지|\Z)', page, re.DOTALL)

        # 왼쪽 영역 파싱
        if left_section_match:
            left_content = left_section_match.group(1).strip()
            # 문제 번호 패턴 찾기 (예: "2\n– 초기 국가, 부여")
            question_pattern = r'^(\d+)\s*\n\s*[–\-]\s*(.+?)\s*\n\s*정답>\s*([①②③④])\s*\n(.*?)(?=\n\d+\s*\n\s*[–\-]|\n### 오른쪽 영역|\Z)'
            matches = re.finditer(question_pattern, left_content, re.MULTILINE | re.DOTALL)

            for match in matches:
                question_id = int(match.group(1))
                topic = match.group(2).strip()
                answer_korean = match.group(3).strip()
                commentary = match.group(4).strip()

                answer_num = korean_to_num.get(answer_korean, answer_korean)

                # URL 및 불필요한 구분선 제거
                commentary = re.sub(r'https://[^\s]+', '', commentary)
                commentary = re.sub(r'^[-–]\s*이\s*상\s*[-–]', '', commentary, flags=re.MULTILINE)
                commentary = re.sub(r'^[-–]\s*$', '', commentary, flags=re.MULTILINE)
                commentary = re.sub(r'9급 공무원 한국사\[한Pro\]', '', commentary)
                commentary = re.sub(r'\n{3,}', '\n\n', commentary)  # 연속된 줄바꿈 정리
                commentary = commentary.strip()

                commentary_map[question_id] = {
                    "topic": topic,
                    "answer": answer_num,
                    "commentary": commentary
                }

        # 오른쪽 영역 파싱
        if right_section_match:
            right_content = right_section_match.group(1).strip()
            # 문제 번호 패턴 찾기 (예: "3\n– 발해")
            question_pattern = r'^(\d+)\s*\n\s*[–\-]\s*(.+?)\s*\n\s*정답>\s*([①②③④])\s*\n(.*?)(?=\n\d+\s*\n\s*[–\-]|\n## 페이지|\Z)'
            matches = re.finditer(question_pattern, right_content, re.MULTILINE | re.DOTALL)

            for match in matches:
                question_id = int(match.group(1))
                topic = match.group(2).strip()
                answer_korean = match.group(3).strip()
                commentary = match.group(4).strip()

                answer_num = korean_to_num.get(answer_korean, answer_korean)

                # URL 및 불필요한 구분선 제거
                commentary = re.sub(r'https://[^\s]+', '', commentary)
                commentary = re.sub(r'^[-–]\s*이\s*상\s*[-–]', '', commentary, flags=re.MULTILINE)
                commentary = re.sub(r'^[-–]\s*$', '', commentary, flags=re.MULTILINE)
                commentary = re.sub(r'9급 공무원 한국사\[한Pro\]', '', commentary)
                commentary = re.sub(r'\n{3,}', '\n\n', commentary)  # 연속된 줄바꿈 정리
                commentary = commentary.strip()

                commentary_map[question_id] = {
                    "topic": topic,
                    "answer": answer_num,
                    "commentary": commentary
                }

    return commentary_map


def convert_commentary_md_to_jsonl(
    md_path: str,
    output_path: str,
    subject: Optional[str] = None
) -> int:
    """해설 마크다운 파일을 JSONL 형식으로 변환합니다.

    Args:
        md_path: 입력 마크다운 파일 경로
        output_path: 출력 JSONL 파일 경로
        subject: 과목명 (None이면 파일명에서 추론)

    Returns:
        생성된 항목 수
    """
    if not os.path.exists(md_path):
        raise FileNotFoundError(f"마크다운 파일을 찾을 수 없습니다: {md_path}")

    # 파일명에서 과목 추론
    if subject is None:
        if "한국사" in md_path:
            subject = "한국사"
        elif "국어" in md_path:
            subject = "국어"
        elif "영어" in md_path:
            subject = "영어"
        elif "교육학개론" in md_path:
            subject = "교육학개론"
        elif "행정법" in md_path:
            subject = "행정법총론"
        elif "행정학" in md_path:
            subject = "행정학개론"
        elif "지방세법" in md_path:
            subject = "지방세법"
        elif "정보봉사개론" in md_path:
            subject = "정보봉사개론"
        elif "회계학" in md_path:
            subject = "회계학"
        else:
            subject = "기타"

    # 마크다운 파일 읽기
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 정답표 파싱
    answer_map = parse_answer_table(content)

    # 해설 섹션 파싱
    commentary_map = parse_commentary_sections(content)

    # JSONL 파일 작성
    md_basename = os.path.basename(md_path)
    pdf_basename = md_basename.replace('.md', '.pdf')

    items: List[Dict[str, any]] = []

    # 1번부터 20번까지 순회
    for question_id in range(1, 21):
        # 정답 확인 (정답표 우선, 없으면 해설에서)
        answer = answer_map.get(question_id)
        if not answer and question_id in commentary_map:
            answer = commentary_map[question_id].get("answer")

        # 해설 정보 가져오기
        commentary_info = commentary_map.get(question_id, {})
        topic = commentary_info.get("topic", "")
        commentary = commentary_info.get("commentary", "")

        # question 필드 구성 (해설 내용 포함)
        question_parts = []
        if topic:
            question_parts.append(f"주제: {topic}")
        if commentary:
            question_parts.append(f"\n해설:\n{commentary}")

        question_text = "\n".join(question_parts) if question_parts else "해설 정보 없음"

        # JSON 객체 생성
        item = {
            "id": str(question_id),
            "question": question_text,
            "answer": answer or "정답 정보 없음",
            "subject": subject,
            "source_md": md_basename,
            "source_pdf": pdf_basename if pdf_basename != md_basename else None
        }

        items.append(item)

    # JSONL 파일 저장
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[완료] {len(items)}개 항목 생성 → {output_path}")
    return len(items)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="해설 마크다운 파일을 JSONL 형식으로 변환합니다."
    )
    parser.add_argument(
        "--md",
        type=str,
        required=True,
        help="입력 마크다운 파일 경로"
    )
    parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="출력 JSONL 파일 경로"
    )
    parser.add_argument(
        "--subject",
        type=str,
        default=None,
        help="과목명 (지정하지 않으면 파일명에서 추론)"
    )

    args = parser.parse_args()

    try:
        convert_commentary_md_to_jsonl(
            md_path=args.md,
            output_path=args.out,
            subject=args.subject
        )
        return 0
    except Exception as e:
        print(f"❌ 오류 발생: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

