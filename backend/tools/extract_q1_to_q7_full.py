#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1번부터 7번까지의 전체 내용을 추출합니다.
- 9페이지: 빠른 정답 체크 테이블 + 1번 문항
- 10페이지: 2번, 3번 문항
- 11페이지: 3번(이어짐), 4번 문항
- 12페이지: 5번 문항
- 13페이지: 6-7번 문항
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

def parse_answer_table(text: str) -> Dict[int, str]:
    """9페이지의 빠른 정답 체크 테이블을 파싱합니다."""
    answers = {}
    # "빠른 정답 Check" 테이블 찾기
    table_match = re.search(r'빠른\s*정답\s*Check\s*([\s\S]+?)(?=\d+\.|$)', text, re.IGNORECASE)
    if not table_match:
        return answers

    table_text = table_match.group(1)
    # "01번 ② 06번 ④ ..." 형식 파싱
    # "01번", "02번" 등으로 시작하는 패턴
    pattern = r'(\d+)번\s*([①②③④⑤➀➁➂➃➄])'
    matches = re.finditer(pattern, table_text)

    for match in matches:
        q_no = int(match.group(1))
        answer = match.group(2)
        # ➀➁➂➃➄를 ①②③④⑤로 변환
        answer_map = {'➀': '①', '➁': '②', '➂': '③', '➃': '④', '➄': '⑤'}
        answer = answer_map.get(answer, answer)
        if answer in ['①', '②', '③', '④', '⑤']:
            answers[q_no] = answer

    return answers

def extract_section_content(text: str, section_name: str, next_section: Optional[str] = None) -> str:
    """특정 섹션의 내용을 추출합니다."""
    # 섹션 패턴: "❚정답해설", "❚오답해설", "❚해석", "❚어휘" 등
    if next_section:
        pattern = rf'[❚■]?{section_name}\s*([\s\S]+?)(?=[❚■]?{next_section}|$)'
    else:
        pattern = rf'[❚■]?{section_name}\s*([\s\S]+?)(?=[❚■]?정답해설|[❚■]?오답해설|[❚■]?해석|[❚■]?어휘|\d+\.|성정혜|2025|해당|$)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        content = match.group(1).strip()
        # 푸터 제거
        content = remove_footer_header(content)
        # 줄 단위로 정리
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not re.match(r'성정혜', line) and not re.match(r'2025', line) and not re.match(r'해당', line):
                cleaned_lines.append(line)
        content = '\n'.join(cleaned_lines)
        # ➀➁➂➃➄를 ①②③④⑤로 변환
        content = re.sub(r'➀', '①', content)
        content = re.sub(r'➁', '②', content)
        content = re.sub(r'➂', '③', content)
        content = re.sub(r'➃', '④', content)
        content = re.sub(r'➄', '⑤', content)
        # 공백 정규화
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

        # "þ", "✔" 기호를 "☑"로 변환
        vocab_text = re.sub(r'þ', '☑', vocab_text)
        vocab_text = re.sub(r'✔', '☑', vocab_text)

        # 푸터 제거
        vocab_text = re.sub(r'성정혜\s*영어.*', '', vocab_text, flags=re.DOTALL)
        vocab_text = re.sub(r'2025\s*Sung\s*Jung\s*hye.*', '', vocab_text, flags=re.DOTALL)
        vocab_text = re.sub(r'해당\s*콘텐츠는.*', '', vocab_text, flags=re.DOTALL)

        # 줄바꿈을 공백으로 변환하여 여러 줄에 걸친 어휘 처리
        vocab_text_combined = re.sub(r'\n+', ' ', vocab_text)
        vocab_text_combined = re.sub(r'\s+', ' ', vocab_text_combined)

        # 모든 어휘 항목 찾기: "☑ word 뜻" 패턴
        # 다음 "☑" 전까지 또는 끝까지가 하나의 어휘 항목
        vocab_items = []
        seen_words = set()

        # "☑"로 시작하는 모든 항목 찾기
        # 패턴: "☑ word 뜻" (다음 "☑" 전까지)
        pattern = r'☑\s*([^\s☑]+(?:\s+[^\s☑]+)*?)\s+([^☑]+?)(?=\s*☑|성정혜|2025|해당|$)'
        matches = re.finditer(pattern, vocab_text_combined)

        for match in matches:
            word = match.group(1).strip()
            meaning = match.group(2).strip()

            # 푸터 관련 텍스트 제거
            if re.search(r'성정혜|2025|해당', meaning):
                continue

            # 의미가 비어있으면 스킵
            if not meaning:
                continue

            # 중복 방지
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

    # 문항 시작 패턴 찾기
    q_pattern = rf'(?:^|\n){question_no}\.'
    q_match = re.search(q_pattern, text)
    if not q_match:
        return question_data

    q_start = q_match.start()

    # 다음 문항 시작 위치 찾기
    if next_question_no:
        next_q_pattern = rf'(?:^|\n){next_question_no}\.'
        next_q_match = re.search(next_q_pattern, text[q_start + 1:])
        if next_q_match:
            q_text = text[q_start:q_start + 1 + next_q_match.start()]
        else:
            q_text = text[q_start:]
    else:
        q_text = text[q_start:]

    # 정답 추출: "❚정답 ②" 형식
    answer_match = re.search(r'[❚■]?정답\s*([①②③④⑤➀➁➂➃➄])', q_text)
    if answer_match:
        answer_map = {'➀': '①', '➁': '②', '➂': '③', '➃': '④', '➄': '⑤'}
        answer = answer_match.group(1)
        question_data['answer'] = answer_map.get(answer, answer)

    # 영역 추출
    area_match = re.search(r'[❚■]?영역\s*([^\n❚■]+?)(?=\n[❚■]|$)', q_text)
    if area_match:
        question_data['area'] = area_match.group(1).strip()

    # 정답해설 추출
    question_data['answer_explanation'] = extract_section_content(q_text, '정답해설', '오답해설')

    # 오답해설 추출
    question_data['wrong_explanation'] = extract_section_content(q_text, '오답해설', '해석')

    # 해석 추출
    question_data['translation'] = extract_section_content(q_text, '해석', '어휘')

    # 어휘 추출 (현재 페이지 또는 다음 페이지)
    # 먼저 현재 페이지에서 어휘 찾기
    vocab_text = extract_vocabulary_from_text(q_text)

    # 현재 페이지에 어휘가 없고 다음 페이지가 있으면 다음 페이지에서 찾기
    if not vocab_text and next_page_text:
        vocab_text = extract_vocabulary_from_text(next_page_text)

    # 여전히 없으면 전체 텍스트에서 찾기 (문항 번호 이후의 어휘)
    if not vocab_text:
        # 문항 번호 이후의 텍스트에서 어휘 찾기
        after_q = text[q_start:]
        vocab_text = extract_vocabulary_from_text(after_q)

    question_data['vocabulary'] = vocab_text

    return question_data

def parse_questions_6_7(text: str, next_page_text: Optional[str] = None) -> Dict:
    """6-7번 문항을 파싱합니다."""
    question_data = {
        'question_no': '6 - 7',
        'answers': {},
        'area': None,
        'answer_explanation': None,
        'wrong_explanation': None,
        'translation': None,
        'vocabulary': None,
    }

    # "6. - 7." 또는 "6." 패턴 찾기
    q6_match = re.search(r'6\.\s*(?:-\s*7\.)?\s*([\s\S]+?)(?=8\.|$)', text)
    if not q6_match:
        return question_data

    q6_7_text = q6_match.group(1)

    # 각 문항의 정답 추출
    answer6_match = re.search(r'6\.\s*([①②③④⑤➀➁➂➃➄])', text)
    answer7_match = re.search(r'7\.\s*([①②③④⑤➀➁➂➃➄])', text)
    answer_map = {'➀': '①', '➁': '②', '➂': '③', '➃': '④', '➄': '⑤'}
    if answer6_match:
        question_data['answers'][6] = answer_map.get(answer6_match.group(1), answer6_match.group(1))
    if answer7_match:
        question_data['answers'][7] = answer_map.get(answer7_match.group(1), answer7_match.group(1))

    # 영역 추출
    area_match = re.search(r'[❚■]?영역\s*([^\n❚■]+?)(?=\n[❚■]|$)', q6_7_text)
    if area_match:
        question_data['area'] = area_match.group(1).strip()

    # 정답해설 추출
    question_data['answer_explanation'] = extract_section_content(q6_7_text, '정답해설', '오답해설')

    # 오답해설 추출
    question_data['wrong_explanation'] = extract_section_content(q6_7_text, '오답해설', '해석')

    # 해석 추출
    question_data['translation'] = extract_section_content(q6_7_text, '해석', '어휘')

    # 어휘 추출
    vocab_text = extract_vocabulary_from_text(q6_7_text)
    if not vocab_text and next_page_text:
        vocab_text = extract_vocabulary_from_text(next_page_text)
    question_data['vocabulary'] = vocab_text

    return question_data

def format_question_markdown(question_data: Dict, answer_table: Optional[Dict[int, str]] = None) -> str:
    """문항 데이터를 마크다운 형식으로 변환합니다."""
    lines = []

    # 문항 번호
    if 'question_no' in question_data:
        lines.append(f"## {question_data['question_no']}번")
    else:
        lines.append(f"## {question_data.get('question_no', '?')}번")
    lines.append("")

    # 정답
    if 'answers' in question_data and question_data['answers']:
        # 여러 문항의 정답 (6-7번 같은 경우)
        answer_parts = []
        for q_no, ans in sorted(question_data['answers'].items()):
            answer_parts.append(f"{q_no}번: {ans}")
        lines.append(f"**정답:** {', '.join(answer_parts)}")
    elif question_data.get('answer'):
        lines.append(f"**정답:** {question_data['answer']}")
    elif answer_table:
        q_no = int(question_data['question_no']) if question_data['question_no'].isdigit() else None
        if q_no and q_no in answer_table:
            lines.append(f"**정답:** {answer_table[q_no]}")
    lines.append("")

    # 영역
    if question_data.get('area'):
        lines.append(f"**영역:** {question_data['area']}")
        lines.append("")

    # 정답해설
    if question_data.get('answer_explanation'):
        lines.append("### 정답해설")
        lines.append("")
        lines.append(question_data['answer_explanation'])
        lines.append("")

    # 오답해설
    if question_data.get('wrong_explanation'):
        lines.append("### 오답해설")
        lines.append("")
        lines.append(question_data['wrong_explanation'])
        lines.append("")

    # 해석
    if question_data.get('translation'):
        lines.append("### 해석")
        lines.append("")
        lines.append(question_data['translation'])
        lines.append("")

    # 어휘
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

    print(f"[1/6] PDF에서 페이지 텍스트 추출 중...")

    page_texts = {}
    with pdfplumber.open(pdf_path) as pdf:
        # 9페이지부터 13페이지까지 추출
        for page_idx in range(8, 13):  # 0-based, so 8 = page 9
            if page_idx < len(pdf.pages):
                page = pdf.pages[page_idx]
                page_text = page.extract_text()
                if page_text:
                    page_texts[page_idx + 1] = page_text  # 1-based page number

    if not page_texts:
        print("오류: 텍스트를 추출할 수 없습니다.")
        return

    print(f"[2/6] 9페이지에서 빠른 정답 체크 테이블 파싱 중...")
    answer_table = parse_answer_table(page_texts.get(9, ""))
    print(f"  → {len(answer_table)}개 문항의 정답을 찾았습니다.")

    print(f"[3/6] 각 문항 파싱 중...")

    questions = []

    # 1번: 9페이지 (전체 텍스트에서 어휘 찾기)
    if 9 in page_texts:
        q1 = parse_single_question(page_texts[9], 1, 2, page_texts.get(10))
        # 1번의 어휘는 9페이지 전체에서 찾기
        if not q1.get('vocabulary'):
            q1['vocabulary'] = extract_vocabulary_from_text(page_texts[9])
        if q1.get('answer') or q1.get('area') or q1.get('answer_explanation'):
            questions.append(q1)
            print(f"  → 1번 파싱 완료")

    # 2번: 10페이지
    if 10 in page_texts:
        q2 = parse_single_question(page_texts[10], 2, 3, page_texts.get(11))
        if q2.get('answer') or q2.get('area') or q2.get('answer_explanation'):
            questions.append(q2)
            print(f"  → 2번 파싱 완료")

    # 3번: 10페이지 (11페이지로 이어질 수 있음)
    if 10 in page_texts:
        # 10페이지와 11페이지를 합쳐서 파싱
        combined_text = page_texts[10]
        if 11 in page_texts:
            combined_text += "\n" + page_texts[11]
        q3 = parse_single_question(combined_text, 3, 4, page_texts.get(11))
        if q3.get('answer') or q3.get('area') or q3.get('answer_explanation'):
            questions.append(q3)
            print(f"  → 3번 파싱 완료")

    # 4번: 11페이지
    if 11 in page_texts:
        q4 = parse_single_question(page_texts[11], 4, 5, page_texts.get(12))
        if q4.get('answer') or q4.get('area') or q4.get('answer_explanation'):
            questions.append(q4)
            print(f"  → 4번 파싱 완료")

    # 5번: 12페이지
    if 12 in page_texts:
        q5 = parse_single_question(page_texts[12], 5, 6, page_texts.get(13))
        if q5.get('answer') or q5.get('area') or q5.get('answer_explanation'):
            questions.append(q5)
            print(f"  → 5번 파싱 완료")

    # 6-7번: 13페이지
    if 13 in page_texts:
        q6_7 = parse_questions_6_7(page_texts[13], None)
        if q6_7.get('answers') or q6_7.get('area') or q6_7.get('answer_explanation'):
            questions.append(q6_7)
            print(f"  → 6-7번 파싱 완료")

    print(f"[4/6] 마크다운 형식으로 변환 중...")

    # 빠른 정답 체크 테이블 추가
    markdown_content = []
    if answer_table:
        markdown_content.append("## 빠른 정답 Check")
        markdown_content.append("")
        # 4개씩 한 줄로 표시
        sorted_nos = sorted(answer_table.keys())
        for i in range(0, len(sorted_nos), 4):
            line_parts = []
            for j in range(i, min(i + 4, len(sorted_nos))):
                q_no = sorted_nos[j]
                line_parts.append(f"{q_no:02d}번 {answer_table[q_no]}")
            markdown_content.append(" ".join(line_parts))
        markdown_content.append("")
        markdown_content.append("---")
        markdown_content.append("")
        markdown_content.append("")

    # 각 문항 마크다운 생성
    for q in questions:
        markdown_content.append(format_question_markdown(q, answer_table))

    print(f"[5/6] 기존 파일 읽기 중...")

    # 기존 파일에서 8-9번 이후 내용 읽기
    existing_content = ""
    try:
        with open(output_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
            # 8-9번 이후 내용만 추출
            match = re.search(r'(## 8\s*-\s*9번[\s\S]+)', existing_content)
            if match:
                existing_content = "\n\n" + match.group(1)
            else:
                existing_content = ""
    except FileNotFoundError:
        existing_content = ""

    print(f"[6/6] 파일 저장 중...")

    # 새 내용 + 기존 8-9번 내용
    final_content = "".join(markdown_content) + existing_content

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"[완료] 저장 완료: {output_path}")
    print(f"  → {len(questions)}개 문항이 추출되었습니다.")

if __name__ == "__main__":
    main()

