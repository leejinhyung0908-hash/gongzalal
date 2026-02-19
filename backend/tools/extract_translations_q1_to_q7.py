#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1번부터 7번까지의 해석 부분을 추출하여 기존 md 파일에 추가합니다.
8-9번의 해석 추출 로직을 참고합니다.
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

def extract_translation_for_question(text: str, question_no: int) -> Optional[str]:
    """특정 문항의 해석 부분을 추출합니다."""
    # 문항 번호 패턴 찾기 (예: "1.", "2.", "3." 등)
    # "1."로 시작하되, 앞에 다른 숫자가 없는 경우
    q_pattern = rf'(?:^|\n){question_no}\.'

    # 문항 시작 위치 찾기
    q_match = re.search(q_pattern, text)
    if not q_match:
        return None

    q_start = q_match.start()

    # 다음 문항 시작 위치 찾기
    next_q_pattern = rf'(?:^|\n){question_no + 1}\.'
    next_q_match = re.search(next_q_pattern, text[q_start + 1:])
    if next_q_match:
        q_text = text[q_start:q_start + 1 + next_q_match.start()]
    else:
        # 마지막 문항인 경우
        q_text = text[q_start:]

    # 해석 부분 찾기
    translation_match = re.search(r'[❚■]?해석\s*([\s\S]+?)(?=[❚■]?어휘|❚정답해설|❚오답해설|\d+\.|성정혜|2025|해당|$)', q_text, re.DOTALL)
    if translation_match:
        translation = translation_match.group(1).strip()

        # 푸터 제거
        translation = remove_footer_header(translation)

        # 줄 단위로 정리
        lines = translation.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # 정답해설이나 오답해설이 섞여있는 경우 제거
            if re.match(r'[❚■]?정답해설', line) or re.match(r'[❚■]?오답해설', line):
                break
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
        # 공백 정규화
        translation = re.sub(r'[ \t]+', ' ', translation)
        translation = translation.strip()

        if translation:
            return translation

    return None

def extract_translation_for_questions_6_7(text: str) -> Optional[str]:
    """6-7번 문항의 해석 부분을 추출합니다."""
    # "6. - 7." 또는 "6." 패턴 찾기
    q6_match = re.search(r'6\.\s*(?:-\s*7\.)?\s*([\s\S]+?)(?=8\.|$)', text)
    if not q6_match:
        return None

    q6_7_text = q6_match.group(1)

    # 해석 부분 찾기
    translation_match = re.search(r'[❚■]?해석\s*([\s\S]+?)(?=[❚■]?어휘|성정혜|2025|해당|$)', q6_7_text, re.DOTALL)
    if translation_match:
        translation = translation_match.group(1).strip()

        # 푸터 제거
        translation = remove_footer_header(translation)

        # 줄 단위로 정리
        lines = translation.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            # 정답해설이나 오답해설이 섞여있는 경우 제거
            if re.match(r'[❚■]?정답해설', line) or re.match(r'[❚■]?오답해설', line):
                break
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
        # 공백 정규화
        translation = re.sub(r'[ \t]+', ' ', translation)
        translation = translation.strip()

        if translation:
            return translation

    return None

def add_translation_to_md(md_path: str, question_no: int, translation: str):
    """마크다운 파일의 특정 문항에 해석 부분을 추가합니다."""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 문항 번호 패턴 (예: "## 1번", "## 6 - 7번")
    if question_no == 6:
        pattern = r'(## 6\s*-\s*7번[\s\S]+?)(### 오답해설[\s\S]+?)(\n---|\n## \d+번|$)'
    else:
        pattern = rf'(## {question_no}번[\s\S]+?)(### 오답해설[\s\S]+?)(\n---|\n## \d+번|$)'

    def replace_func(match):
        before = match.group(1)
        wrong_explanation = match.group(2)
        after = match.group(3)

        # 이미 해석 부분이 있는지 확인
        if '### 해석' in wrong_explanation:
            return match.group(0)

        # 오답해설 다음에 해석 추가
        return before + wrong_explanation + "\n\n### 해석\n\n" + translation + "\n\n" + after

    new_content = re.sub(pattern, replace_func, content, flags=re.DOTALL)

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'
    md_path = 'data/gongmuwon/intermediate/markdown/commentary_md/page9_test.md'

    print(f"[1/3] PDF에서 텍스트 추출 중...")

    # 각 페이지에서 텍스트 추출 (1-7번은 10-13페이지에 있을 것으로 예상)
    page_texts = {}
    with pdfplumber.open(pdf_path) as pdf:
        # 10페이지부터 13페이지까지 추출
        for page_idx in range(9, 13):  # 0-based, so 9 = page 10
            if page_idx < len(pdf.pages):
                page = pdf.pages[page_idx]
                page_text = page.extract_text()
                if page_text:
                    page_texts[page_idx + 1] = page_text  # 1-based page number

    if not page_texts:
        print("오류: 텍스트를 추출할 수 없습니다.")
        return

    print(f"[2/3] 각 문항의 해석 추출 중...")

    translations = {}

    # 각 문항별로 해당 페이지에서 추출
    # 1번: 9페이지
    with pdfplumber.open(pdf_path) as pdf:
        if 8 < len(pdf.pages):  # 0-based, so 8 = page 9
            page9 = pdf.pages[8]
            page9_text = page9.extract_text()
            if page9_text:
                translation = extract_translation_for_question(page9_text, 1)
                if translation:
                    translations[1] = translation
                    print(f"  → 1번 해석 추출 완료")
                else:
                    print(f"  → 1번 해석을 찾을 수 없습니다.")

    # 2번: 10페이지
    if 10 in page_texts:
        translation = extract_translation_for_question(page_texts[10], 2)
        if translation:
            translations[2] = translation
            print(f"  → 2번 해석 추출 완료")
        else:
            print(f"  → 2번 해석을 찾을 수 없습니다.")

    # 3번: 10페이지
    if 10 in page_texts:
        translation = extract_translation_for_question(page_texts[10], 3)
        if translation:
            translations[3] = translation
            print(f"  → 3번 해석 추출 완료")
        else:
            print(f"  → 3번 해석을 찾을 수 없습니다.")

    # 4번: 11페이지
    if 11 in page_texts:
        translation = extract_translation_for_question(page_texts[11], 4)
        if translation:
            translations[4] = translation
            print(f"  → 4번 해석 추출 완료")
        else:
            print(f"  → 4번 해석을 찾을 수 없습니다.")

    # 5번: 12페이지
    if 12 in page_texts:
        translation = extract_translation_for_question(page_texts[12], 5)
        if translation:
            translations[5] = translation
            print(f"  → 5번 해석 추출 완료")
        else:
            print(f"  → 5번 해석을 찾을 수 없습니다.")

    # 6-7번: 13페이지
    if 13 in page_texts:
        translation_6_7 = extract_translation_for_questions_6_7(page_texts[13])
        if translation_6_7:
            translations[6] = translation_6_7
            print(f"  → 6-7번 해석 추출 완료")
        else:
            print(f"  → 6-7번 해석을 찾을 수 없습니다.")

    print(f"[3/3] 마크다운 파일에 해석 추가 중...")

    # 각 문항에 해석 추가
    for q_no, translation in translations.items():
        add_translation_to_md(md_path, q_no, translation)
        print(f"  → {q_no}번 해석 추가 완료")

    print(f"[완료] 저장 완료: {md_path}")

if __name__ == "__main__":
    main()

