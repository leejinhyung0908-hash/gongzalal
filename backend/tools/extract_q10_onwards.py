#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10번부터 끝까지 문항을 추출합니다.
"""
import pdfplumber
import re
from typing import Optional, Dict, List

def remove_footer_header(text: str) -> str:
    """푸터와 헤더 텍스트를 제거합니다."""
    text = re.sub(
        r'성정혜\s*영어\s*[\s\S]*?2025\s*Sung\s*Jung\s*hye\.[\s\S]*?법률로\s*금지되어\s*있습니다\.',
        '',
        text,
        flags=re.DOTALL
    )
    text = re.sub(
        r'해당\s*콘텐츠는[\s\S]*?법률로\s*금지되어\s*있습니다\.',
        '',
        text,
        flags=re.DOTALL
    )
    return text.strip()

def extract_section_content(text: str, section_name: str, next_section: Optional[str] = None) -> str:
    """특정 섹션의 내용을 추출합니다."""
    if next_section:
        pattern = rf'[❚■]?{section_name}\s*([\s\S]+?)(?=[❚■]?{next_section}|$)'
    else:
        pattern = rf'[❚■]?{section_name}\s*([\s\S]+?)(?=[❚■]?정답해설|[❚■]?오답해설|[❚■]?해석|[❚■]?어휘|\d+\.|성정혜|2025|해당|$)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        content = remove_footer_header(content)
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not re.match(r'성정혜', line) and not re.match(r'2025', line) and not re.match(r'해당', line):
                cleaned_lines.append(line)
        content = '\n'.join(cleaned_lines)
        content = re.sub(r'➀', '①', content)
        content = re.sub(r'➁', '②', content)
        content = re.sub(r'➂', '③', content)
        content = re.sub(r'➃', '④', content)
        content = re.sub(r'➄', '⑤', content)
        content = re.sub(r'[ \t]+', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()
    return ""

def extract_vocabulary_from_text(text: str) -> str:
    """어휘 섹션을 추출합니다."""
    vocab_match = re.search(r'[❚■]?어휘\s*([\s\S]+?)(?=\d+\.|성정혜|2025|해당|$)', text, re.DOTALL)
    if vocab_match:
        vocab_text = vocab_match.group(1).strip()
        vocab_text = remove_footer_header(vocab_text)
        vocab_text = re.sub(r'þ', '☑', vocab_text)
        vocab_text = re.sub(r'✔', '☑', vocab_text)
        vocab_text = re.sub(r'성정혜\s*영어.*', '', vocab_text, flags=re.DOTALL)
        vocab_text = re.sub(r'2025\s*Sung\s*Jung\s*hye.*', '', vocab_text, flags=re.DOTALL)
        vocab_text = re.sub(r'해당\s*콘텐츠는.*', '', vocab_text, flags=re.DOTALL)
        vocab_text_combined = re.sub(r'\n+', ' ', vocab_text)
        vocab_text_combined = re.sub(r'\s+', ' ', vocab_text_combined)
        vocab_items = []
        seen_words = set()
        pattern = r'☑\s*([^\s☑]+(?:\s+[^\s☑]+)*?)\s+([^☑]+?)(?=\s*☑|성정혜|2025|해당|$)'
        matches = re.finditer(pattern, vocab_text_combined)
        for match in matches:
            word = match.group(1).strip()
            meaning = match.group(2).strip()
            if re.search(r'성정혜|2025|해당', meaning):
                continue
            if not meaning:
                continue
            word_lower = word.lower()
            if word_lower and word_lower not in seen_words:
                seen_words.add(word_lower)
                vocab_items.append(f'☑ {word} {meaning}')
        if vocab_items:
            return '\n'.join(vocab_items)
    return ""

def parse_single_question(text: str, question_no: int, next_question_no: Optional[int] = None, next_page_text: Optional[str] = None) -> Dict:
    """단일 문항을 파싱합니다."""
    question_data = {
        'question_no': str(question_no),
        'answer': None,
        'area': None,
        'answer_explanation': None,
        'wrong_explanation': None,
        'translation': None,
        'vocabulary': None,
    }

    q_pattern = rf'(?:^|\n){question_no}\.'
    q_match = re.search(q_pattern, text)
    if not q_match:
        return question_data

    q_start = q_match.start()

    if next_question_no:
        next_q_pattern = rf'(?:^|\n){next_question_no}\.'
        next_q_match = re.search(next_q_pattern, text[q_start + 1:])
        if next_q_match:
            q_text = text[q_start:q_start + 1 + next_q_match.start()]
        else:
            q_text = text[q_start:]
    else:
        q_text = text[q_start:]

    answer_match = re.search(r'[❚■]?정답\s*([①②③④⑤➀➁➂➃➄])', q_text)
    if answer_match:
        answer_map = {'➀': '①', '➁': '②', '➂': '③', '➃': '④', '➄': '⑤'}
        answer = answer_match.group(1)
        question_data['answer'] = answer_map.get(answer, answer)

    area_match = re.search(r'[❚■]?영역\s*([^\n❚■]+?)(?=\n[❚■]|$)', q_text)
    if area_match:
        question_data['area'] = area_match.group(1).strip()

    question_data['answer_explanation'] = extract_section_content(q_text, '정답해설', '오답해설')
    question_data['wrong_explanation'] = extract_section_content(q_text, '오답해설', '해석')
    question_data['translation'] = extract_section_content(q_text, '해석', '어휘')

    vocab_text = extract_vocabulary_from_text(q_text)
    if not vocab_text and next_page_text:
        vocab_text = extract_vocabulary_from_text(next_page_text)
    question_data['vocabulary'] = vocab_text

    return question_data

def format_question_markdown(question_data: Dict, answer_table: Optional[Dict[int, str]] = None) -> str:
    """문항 데이터를 마크다운 형식으로 변환합니다."""
    lines = []

    if 'question_no' in question_data:
        lines.append(f"## {question_data['question_no']}번")
    else:
        lines.append(f"## {question_data.get('question_no', '?')}번")
    lines.append("")

    if question_data.get('answer'):
        lines.append(f"**정답:** {question_data['answer']}")
    elif answer_table:
        q_no = int(question_data['question_no']) if question_data['question_no'].isdigit() else None
        if q_no and q_no in answer_table:
            lines.append(f"**정답:** {answer_table[q_no]}")
    lines.append("")

    if question_data.get('area'):
        lines.append(f"**영역:** {question_data['area']}")
        lines.append("")

    if question_data.get('answer_explanation'):
        lines.append("### 정답해설")
        lines.append("")
        lines.append(question_data['answer_explanation'])
        lines.append("")

    if question_data.get('wrong_explanation'):
        lines.append("### 오답해설")
        lines.append("")
        lines.append(question_data['wrong_explanation'])
        lines.append("")

    if question_data.get('translation'):
        lines.append("### 해석")
        lines.append("")
        lines.append(question_data['translation'])
        lines.append("")

    if question_data.get('vocabulary'):
        lines.append("### 어휘")
        lines.append("")
        lines.append(question_data['vocabulary'])
        lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)

def main():
    pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'
    output_path = 'data/gongmuwon/intermediate/markdown/commentary_md/page9_test.md'

    print(f"[1/5] PDF에서 페이지 텍스트 추출 중...")

    # 15페이지부터 끝까지 추출 (10번은 15페이지부터 시작)
    page_texts = {}
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"  → 총 {total_pages}페이지")
        # 15페이지부터 끝까지 (0-based: 14부터)
        for page_idx in range(14, total_pages):
            page = pdf.pages[page_idx]
            page_text = page.extract_text()
            if page_text:
                page_texts[page_idx + 1] = page_text  # 1-based page number

    if not page_texts:
        print("오류: 텍스트를 추출할 수 없습니다.")
        return

    print(f"[2/5] 9페이지에서 빠른 정답 체크 테이블 파싱 중...")
    # 빠른 정답 테이블 읽기
    answer_table = {}
    with pdfplumber.open(pdf_path) as pdf:
        if 8 < len(pdf.pages):
            page9 = pdf.pages[8]
            page9_text = page9.extract_text()
            table_match = re.search(r'빠른\s*정답\s*Check\s*([\s\S]+?)(?=\d+\.|$)', page9_text, re.IGNORECASE)
            if table_match:
                table_text = table_match.group(1)
                pattern = r'(\d+)번\s*([①②③④⑤➀➁➂➃➄])'
                matches = re.finditer(pattern, table_text)
                for match in matches:
                    q_no = int(match.group(1))
                    answer = match.group(2)
                    answer_map = {'➀': '①', '➁': '②', '➂': '③', '➃': '④', '➄': '⑤'}
                    answer = answer_map.get(answer, answer)
                    if answer in ['①', '②', '③', '④', '⑤']:
                        answer_table[q_no] = answer

    print(f"[3/5] 각 문항 파싱 중...")

    questions = []

    # 전체 텍스트를 합쳐서 문항 번호 찾기
    all_text = ""
    for page_no in sorted(page_texts.keys()):
        all_text += "\n" + page_texts[page_no]

    # 10번부터 20번까지 찾기
    for q_no in range(10, 21):
        q_pattern = rf'(?:^|\n){q_no}\.'
        q_match = re.search(q_pattern, all_text)
        if q_match:
            # 다음 문항 찾기
            next_q_no = q_no + 1
            next_q_pattern = rf'(?:^|\n){next_q_no}\.'
            next_q_match = re.search(next_q_pattern, all_text[q_match.start() + 1:])

            # 해당 문항이 있는 페이지 찾기
            q_start_pos = q_match.start()
            current_page = None
            next_page = None
            for page_no in sorted(page_texts.keys()):
                # 페이지 시작 위치 계산 (대략적으로)
                if current_page is None:
                    current_page = page_no
                if next_q_match:
                    next_start_pos = q_match.start() + 1 + next_q_match.start()
                    # 다음 문항이 다음 페이지에 있을 수 있음
                    if next_start_pos > len(all_text[:all_text.find(page_texts[page_no])]):
                        next_page = page_no + 1
                        break

            # 현재 페이지와 다음 페이지 텍스트
            current_text = page_texts.get(current_page, "")
            next_text = page_texts.get(next_page, "") if next_page else None

            # 문항 텍스트 추출
            if next_q_match:
                q_text = all_text[q_match.start():q_match.start() + 1 + next_q_match.start()]
            else:
                q_text = all_text[q_match.start():]

            q = parse_single_question(q_text, q_no, next_q_no if next_q_match else None, next_text)
            if q.get('answer') or q.get('area') or q.get('answer_explanation'):
                questions.append(q)
                print(f"  → {q_no}번 파싱 완료")

    print(f"[4/5] 마크다운 형식으로 변환 중...")

    markdown_content = []
    for q in questions:
        markdown_content.append(format_question_markdown(q, answer_table))

    print(f"[5/5] 기존 파일에 추가 중...")

    # 기존 파일 읽기
    with open(output_path, 'r', encoding='utf-8') as f:
        existing_content = f.read()

    # 새 내용 추가
    final_content = existing_content.rstrip() + "\n\n" + "".join(markdown_content)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"[완료] 저장 완료: {output_path}")
    print(f"  → {len(questions)}개 문항이 추가되었습니다.")

if __name__ == "__main__":
    main()

