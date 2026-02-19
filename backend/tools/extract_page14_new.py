#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
14페이지에서 8번과 9번 문항을 추출하여 기존 md 파일에 추가합니다.
이미지를 기반으로 새로운 로직을 작성합니다.
"""
import pdfplumber
import re
import os
from typing import Optional

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

def extract_vocabulary_from_text(text: str) -> str:
    """텍스트에서 어휘 섹션을 추출합니다."""
    vocab_start = text.find('❚어휘')
    if vocab_start == -1:
        vocab_start = text.find('■어휘')
    if vocab_start == -1:
        vocab_start = text.find('어휘')

    if vocab_start != -1:
        vocab_text = text[vocab_start:]
        # 다음 문항 시작 지점 찾기
        next_q_match = re.search(r'\d+\.', vocab_text)
        if next_q_match:
            vocab_text = vocab_text[:next_q_match.start()]

        # "❚어휘" 또는 "■어휘" 제거
        vocab_text = re.sub(r'[❚■]?어휘\s*', '', vocab_text, count=1)
        vocab_text = vocab_text.strip()

        # "þ", "✔" 기호를 "☑"로 변환
        vocab_text = re.sub(r'þ', '☑', vocab_text)
        vocab_text = re.sub(r'✔', '☑', vocab_text)

        # 푸터 제거
        vocab_text = remove_footer_header(vocab_text)

        # 전체 텍스트를 한 줄로 만들기
        vocab_text_single = re.sub(r'\n+', ' ', vocab_text)

        # 모든 어휘 항목 찾기
        vocab_items = []
        seen_words = set()

        pattern = r'[☑þ✔]\s*([^\s☑þ✔]+(?:\s+[^\s☑þ✔]+)*?)(?=\s*[☑þ✔]|성정혜|2025|해당|$)'
        matches = re.finditer(pattern, vocab_text_single)

        for match in matches:
            item_text = match.group(0).strip()
            # 기호를 ☑로 통일
            item_text = re.sub(r'^[✔þ]', '☑', item_text)

            # 푸터 관련 텍스트 제거
            if re.search(r'성정혜|2025|해당', item_text):
                continue

            # 단어 추출
            word_match = re.search(r'☑\s*([^\s]+(?:\s+[^\s]+)*?)\s+', item_text)
            if word_match:
                word = word_match.group(1).strip().lower()
                if word and word not in seen_words:
                    seen_words.add(word)
                    item_text = re.sub(r'\s+', ' ', item_text)
                    vocab_items.append(item_text)
            elif item_text.startswith('☑'):
                item_text = re.sub(r'\s+', ' ', item_text)
                vocab_items.append(item_text)

        if vocab_items:
            return '\n'.join(vocab_items)

    return ""

def parse_questions_8_9(text: str, next_page_text: Optional[str] = None, full_page_text: Optional[str] = None) -> dict:
    """14페이지에서 8번과 9번 문항을 파싱합니다."""
    question_data = {
        'question_no': '8 - 9',
        'start_no': 8,
        'end_no': 9,
        'answers': {},
        'area': None,
        'answer_explanation': None,
        'wrong_explanation': None,
        'translation': None,
        'vocabulary': None,
    }

    # "8. - 9." 또는 "8." 패턴 찾기
    q8_match = re.search(r'8\.\s*(?:-\s*9\.)?\s*([\s\S]+?)(?=10\.|$)', text)
    if not q8_match:
        return question_data

    q8_9_text = q8_match.group(1)

    # 정답 추출: "8. ➀ / 9. ➂" 형식
    answer_match = re.search(r'정답\s*8\.\s*([①②③④⑤➀➁➂➃➄])\s*/?\s*9\.\s*([①②③④⑤➀➁➂➃➄])', text)
    if answer_match:
        answer_map = {'➀': '①', '➁': '②', '➂': '③', '➃': '④', '➄': '⑤'}
        answer8 = answer_match.group(1)
        answer9 = answer_match.group(2)
        question_data['answers'][8] = answer_map.get(answer8, answer8)
        question_data['answers'][9] = answer_map.get(answer9, answer9)
    else:
        # 개별적으로 찾기
        answer8_match = re.search(r'8\.\s*([①②③④⑤➀➁➂➃➄])', text)
        answer9_match = re.search(r'9\.\s*([①②③④⑤➀➁➂➃➄])', text)
        if answer8_match:
            answer_map = {'➀': '①', '➁': '②', '➂': '③', '➃': '④', '➄': '⑤'}
            answer8 = answer8_match.group(1)
            question_data['answers'][8] = answer_map.get(answer8, answer8)
        if answer9_match:
            answer_map = {'➀': '①', '➁': '②', '➂': '③', '➃': '④', '➄': '⑤'}
            answer9 = answer9_match.group(1)
            question_data['answers'][9] = answer_map.get(answer9, answer9)

    # 영역 추출
    area_match = re.search(r'영역\s*([^\n❚■]+?)(?=\n[❚■]|$)', q8_9_text)
    if area_match:
        area_text = area_match.group(1).strip()
        question_data['area'] = area_text

    # 정답해설 추출
    answer_explanation_match = re.search(r'[❚■]?정답해설\s*([\s\S]+?)(?=[❚■]?오답해설|$)', q8_9_text, re.DOTALL)
    if answer_explanation_match:
        answer_explanation = answer_explanation_match.group(1).strip()
        # 푸터 제거
        answer_explanation = remove_footer_header(answer_explanation)
        # 줄 단위로 정리
        lines = answer_explanation.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not re.match(r'성정혜', line) and not re.match(r'2025', line) and not re.match(r'해당', line):
                cleaned_lines.append(line)
        answer_explanation = '\n'.join(cleaned_lines)
        # ➀➁➂➃➄를 ①②③④⑤로 변환
        answer_explanation = re.sub(r'➀', '①', answer_explanation)
        answer_explanation = re.sub(r'➁', '②', answer_explanation)
        answer_explanation = re.sub(r'➂', '③', answer_explanation)
        answer_explanation = re.sub(r'➃', '④', answer_explanation)
        answer_explanation = re.sub(r'➄', '⑤', answer_explanation)
        answer_explanation = re.sub(r'[ \t]+', ' ', answer_explanation)
        answer_explanation = re.sub(r'\n{3,}', '\n\n', answer_explanation)
        if answer_explanation:
            question_data['answer_explanation'] = answer_explanation.strip()

    # 오답해설 추출
    wrong_explanation_match = re.search(r'[❚■]?오답해설\s*([\s\S]+?)(?=[❚■]?해석|$)', q8_9_text, re.DOTALL)
    if wrong_explanation_match:
        wrong_explanation = wrong_explanation_match.group(1).strip()
        # 푸터 제거
        wrong_explanation = remove_footer_header(wrong_explanation)
        # 줄 단위로 정리
        lines = wrong_explanation.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not re.match(r'성정혜', line) and not re.match(r'2025', line) and not re.match(r'해당', line):
                cleaned_lines.append(line)
        wrong_explanation = '\n'.join(cleaned_lines)
        # ➀➁➂➃➄를 ①②③④⑤로 변환
        wrong_explanation = re.sub(r'➀', '①', wrong_explanation)
        wrong_explanation = re.sub(r'➁', '②', wrong_explanation)
        wrong_explanation = re.sub(r'➂', '③', wrong_explanation)
        wrong_explanation = re.sub(r'➃', '④', wrong_explanation)
        wrong_explanation = re.sub(r'➄', '⑤', wrong_explanation)
        wrong_explanation = re.sub(r'[ \t]+', ' ', wrong_explanation)
        wrong_explanation = re.sub(r'\n{3,}', '\n\n', wrong_explanation)
        if wrong_explanation:
            question_data['wrong_explanation'] = wrong_explanation.strip()

    # 해석 추출 - "사람들을 위한 건강"으로 시작하는 부분을 직접 찾기
    search_text = full_page_text if full_page_text else text

    # "사람들을 위한 건강"이 포함된 부분 찾기
    health_start = search_text.find('사람들을 위한 건강')
    if health_start != -1:
        # "사람들을 위한 건강"부터 시작해서 "❚어휘" 또는 푸터까지 추출
        translation_text = search_text[health_start:]

        # 어휘 섹션 시작 지점 찾기
        vocab_start = translation_text.find('❚어휘')
        if vocab_start == -1:
            vocab_start = translation_text.find('■어휘')
        if vocab_start == -1:
            vocab_start = translation_text.find('어휘')

        if vocab_start != -1:
            translation_text = translation_text[:vocab_start]

        # 푸터 제거
        translation_text = re.sub(r'성정혜\s*영어.*', '', translation_text, flags=re.DOTALL)
        translation_text = re.sub(r'2025\s*Sung\s*Jung\s*hye.*', '', translation_text, flags=re.DOTALL)
        translation_text = re.sub(r'해당\s*콘텐츠는.*', '', translation_text, flags=re.DOTALL)

        # 줄 단위로 정리
        lines = translation_text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # 어휘 섹션 시작 전까지만
            if re.match(r'[❚■]?어휘', line):
                break
            # 푸터 제거
            if re.match(r'성정혜', line) or re.match(r'2025', line) or re.match(r'해당', line):
                break
            if line:
                cleaned_lines.append(line)

        translation = '\n'.join(cleaned_lines)
        # ➀➁➂➃➄를 ①②③④⑤로 변환
        translation = re.sub(r'➀', '①', translation)
        translation = re.sub(r'➁', '②', translation)
        translation = re.sub(r'➂', '③', translation)
        translation = re.sub(r'➃', '④', translation)
        translation = re.sub(r'➄', '⑤', translation)
        # 공백 정규화 (줄바꿈은 유지하되, 연속된 공백은 하나로)
        translation = re.sub(r'[ \t]+', ' ', translation)
        translation = translation.strip()
        if translation:
            question_data['translation'] = translation

    # 어휘 추출 - 15페이지에서 가져오기
    vocab_current = extract_vocabulary_from_text(q8_9_text)
    vocab_next = ""
    if next_page_text:
        vocab_next = extract_vocabulary_from_text(next_page_text)

    # 다음 페이지에 어휘가 있으면 그것을 사용
    if vocab_next:
        question_data['vocabulary'] = vocab_next
    elif vocab_current:
        question_data['vocabulary'] = vocab_current

    return question_data

def format_question_markdown(question_data: dict) -> str:
    """문항을 마크다운 형식으로 변환합니다."""
    lines = []

    # 문항 번호 표시
    lines.append(f"## {question_data['question_no']}번")
    lines.append("")

    # 정답 표시
    if 'answers' in question_data and question_data['answers']:
        answer_lines = []
        for num, ans in sorted(question_data['answers'].items()):
            answer_lines.append(f"{num}번: {ans}")
        lines.append(f"**정답:** {', '.join(answer_lines)}")
        lines.append("")
    elif question_data.get('answer'):
        lines.append(f"**정답:** {question_data['answer']}")
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
    existing_md_path = 'data/gongmuwon/intermediate/markdown/commentary_md/page9_test.md'
    output_path = 'data/gongmuwon/intermediate/markdown/commentary_md/page9_test.md'

    print(f"[1/5] 기존 md 파일에서 중복 문항 제거 중...")
    # 기존 md 파일 읽기
    with open(existing_md_path, 'r', encoding='utf-8') as f:
        existing_content = f.read()

    # 8번 이후의 모든 중복 문항 제거
    existing_content = re.sub(r'\n## (?:8|9).*?번[\s\S]+$', '', existing_content)

    print(f"[2/5] PDF에서 14페이지 텍스트 추출 중...")
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 14:
            print(f"오류: PDF에는 {len(pdf.pages)}페이지만 있습니다.")
            return

        page14 = pdf.pages[13]  # 0-based index, so 13 = page 14
        page14_text = page14.extract_text()

        print(f"[3/5] PDF에서 15페이지 텍스트 추출 중 (어휘 확인용)...")
        page15_text = ""
        if len(pdf.pages) > 14:
            page15 = pdf.pages[14]  # 0-based index, so 14 = page 15
            page15_text = page15.extract_text()

    if not page14_text:
        print("오류: 텍스트를 추출할 수 없습니다.")
        return

    print(f"[4/5] 8번과 9번 문항 파싱 중...")
    question_data = parse_questions_8_9(page14_text, page15_text, page14_text)
    print(f"  → 8-9번 문항 해설을 파싱했습니다.")

    print(f"[5/5] 기존 md 파일에 추가 중...")

    # 8-9번 문항 마크다운 생성
    q8_9_markdown = format_question_markdown(question_data)

    # 기존 파일 끝에 추가
    new_content = existing_content.rstrip() + "\n\n" + q8_9_markdown

    # 파일 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"[완료] 저장 완료: {output_path}")

if __name__ == "__main__":
    main()

