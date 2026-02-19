#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
영어 해설 마크다운 파일을 JSONL 형식으로 변환하고 한국사 JSONL과 합칩니다.
"""
import json
import re
import os
from typing import Dict, List, Optional

def parse_answer_table(content: str) -> Dict[int, str]:
    """빠른 정답 Check 테이블을 파싱합니다."""
    answer_map = {}
    table_match = re.search(r'## 빠른 정답 Check\s*([\s\S]+?)(?=---|##)', content)
    if table_match:
        table_text = table_match.group(1)
        pattern = r'(\d+)번\s*([①②③④⑤])'
        matches = re.finditer(pattern, table_text)
        for match in matches:
            q_no = int(match.group(1))
            answer = match.group(2)
            answer_map[q_no] = answer
    return answer_map

def parse_question_sections(content: str) -> Dict[int, Dict[str, str]]:
    """각 문항의 섹션을 파싱합니다."""
    questions = {}

    # 문항 번호 패턴: "## 1번", "## 6 - 7번" 등
    pattern = r'##\s*(\d+)(?:\s*-\s*(\d+))?\s*번\s*([\s\S]+?)(?=##\s*\d+|$)'
    matches = re.finditer(pattern, content)

    for match in matches:
        start_no = int(match.group(1))
        end_no = int(match.group(2)) if match.group(2) else start_no
        question_text = match.group(3)

        # 정답 추출
        answer_match = re.search(r'\*\*정답:\*\*\s*([①②③④⑤])', question_text)
        if not answer_match:
            # 여러 문항의 정답 형식: "**정답:** 6번: ④, 7번: ④"
            answer_match = re.search(r'\*\*정답:\*\*\s*(\d+)번:\s*([①②③④⑤])', question_text)
            if answer_match:
                answer = answer_match.group(2)
            else:
                answer = None
        else:
            answer = answer_match.group(1)

        # 영역 추출
        area_match = re.search(r'\*\*영역:\*\*\s*([^\n]+)', question_text)
        area = area_match.group(1).strip() if area_match else ""

        # 정답해설 추출
        answer_explanation_match = re.search(r'### 정답해설\s*([\s\S]+?)(?=### 오답해설|### 해석|### 어휘|---|$)', question_text)
        answer_explanation = answer_explanation_match.group(1).strip() if answer_explanation_match else ""

        # 오답해설 추출
        wrong_explanation_match = re.search(r'### 오답해설\s*([\s\S]+?)(?=### 해석|### 어휘|---|$)', question_text)
        wrong_explanation = wrong_explanation_match.group(1).strip() if wrong_explanation_match else ""

        # 해석 추출
        translation_match = re.search(r'### 해석\s*([\s\S]+?)(?=### 어휘|---|$)', question_text)
        translation = translation_match.group(1).strip() if translation_match else ""

        # 어휘 추출
        vocabulary_match = re.search(r'### 어휘\s*([\s\S]+?)(?=---|$)', question_text)
        vocabulary = vocabulary_match.group(1).strip() if vocabulary_match else ""

        # 각 문항에 대해 저장
        for q_no in range(start_no, end_no + 1):
            # 여러 문항인 경우 각 문항의 정답 찾기
            if start_no != end_no:
                q_answer_match = re.search(rf'{q_no}번:\s*([①②③④⑤])', question_text)
                if q_answer_match:
                    q_answer = q_answer_match.group(1)
                else:
                    q_answer = answer
            else:
                q_answer = answer

            questions[q_no] = {
                "answer": q_answer,
                "area": area,
                "answer_explanation": answer_explanation,
                "wrong_explanation": wrong_explanation,
                "translation": translation,
                "vocabulary": vocabulary
            }

    return questions

def format_question_text(question_data: Dict[str, str], answer_table: Dict[int, str]) -> str:
    """문항 데이터를 question 필드 형식으로 변환합니다."""
    parts = []

    # 영역을 주제로 사용
    if question_data.get("area"):
        parts.append(f"영역: {question_data['area']}")

    parts.append("\n해설:")

    # 정답해설
    if question_data.get("answer_explanation"):
        parts.append(f"\n정답해설:\n{question_data['answer_explanation']}")

    # 오답해설
    if question_data.get("wrong_explanation"):
        parts.append(f"\n오답해설:\n{question_data['wrong_explanation']}")

    # 해석
    if question_data.get("translation"):
        parts.append(f"\n해석:\n{question_data['translation']}")

    # 어휘
    if question_data.get("vocabulary"):
        parts.append(f"\n어휘:\n{question_data['vocabulary']}")

    return "\n".join(parts)

def convert_english_commentary_to_jsonl(
    md_path: str,
    output_path: str,
    answer_table: Optional[Dict[int, str]] = None
) -> List[Dict]:
    """영어 해설 마크다운을 JSONL로 변환합니다."""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 정답표 파싱
    if answer_table is None:
        answer_table = parse_answer_table(content)

    # 문항 섹션 파싱
    questions = parse_question_sections(content)

    # JSONL 항목 생성
    items = []
    md_basename = os.path.basename(md_path)
    pdf_basename = md_path.replace('.md', '.pdf').replace('commentary_md', 'commentary')
    pdf_basename = os.path.basename(pdf_basename) if os.path.exists(pdf_basename.replace('commentary', 'raw/commentary')) else None

    for q_no in range(1, 21):
        question_data = questions.get(q_no, {})

        # 정답 확인 (정답표 우선, 없으면 해설에서)
        answer = answer_table.get(q_no) or question_data.get("answer")

        # question 필드 구성
        question_text = format_question_text(question_data, answer_table)

        item = {
            "id": str(q_no),
            "question": question_text,
            "answer": answer or "정답 정보 없음",
            "subject": "영어",
            "source_md": md_basename,
            "source_pdf": pdf_basename if pdf_basename else None
        }

        items.append(item)

    return items

def merge_jsonl_files(
    jsonl_path1: str,
    jsonl_path2_items: List[Dict],
    output_path: str
) -> int:
    """두 JSONL 파일을 합칩니다."""
    # 첫 번째 파일 읽기
    items1 = []
    if os.path.exists(jsonl_path1):
        with open(jsonl_path1, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    items1.append(json.loads(line))

    # 두 번째 파일의 항목들
    items2 = jsonl_path2_items

    # ID 재할당 (첫 번째 파일의 마지막 ID 이후부터)
    max_id = 0
    for item in items1:
        try:
            item_id = int(item.get("id", "0"))
            max_id = max(max_id, item_id)
        except:
            pass

    # 두 번째 파일의 항목들에 ID 재할당
    for item in items2:
        max_id += 1
        item["id"] = str(max_id)

    # 합치기
    all_items = items1 + items2

    # 출력 디렉토리 생성
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # JSONL 파일 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    return len(all_items)

def main():
    md_path = 'data/gongmuwon/intermediate/markdown/commentary_md/250621 지방직 9급 영어 해설 성.md'
    korean_history_jsonl = 'data/gongmuwon/dataset/commentary_korean_history.jsonl'
    output_path = 'data/gongmuwon/dataset/commentary_korean_history.jsonl'  # 기존 파일에 추가

    print(f"[1/3] 영어 해설 마크다운 파일 읽기 중...")
    english_items = convert_english_commentary_to_jsonl(md_path, None)
    print(f"  → {len(english_items)}개 문항 추출 완료")

    print(f"[2/3] 한국사 JSONL 파일과 합치기 중...")
    total_count = merge_jsonl_files(korean_history_jsonl, english_items, output_path)
    print(f"  → 총 {total_count}개 항목 저장 완료 (한국사 20개 + 영어 20개)")

    print(f"[3/3] 완료: {output_path}")

if __name__ == "__main__":
    main()

