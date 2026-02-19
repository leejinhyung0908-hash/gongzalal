#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
15페이지에서 8-9번 문항의 어휘를 추출하여 기존 md 파일에 추가합니다.
"""
import pdfplumber
import re
import os

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

def main():
    pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'
    md_path = 'data/gongmuwon/intermediate/markdown/commentary_md/page9_test.md'

    print(f"[1/3] PDF에서 15페이지 텍스트 추출 중...")
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 15:
            print(f"오류: PDF에는 {len(pdf.pages)}페이지만 있습니다.")
            return

        page15 = pdf.pages[14]  # 0-based index, so 14 = page 15
        page15_text = page15.extract_text()

    if not page15_text:
        print("오류: 텍스트를 추출할 수 없습니다.")
        return

    print(f"[2/3] 8-9번 어휘 추출 중...")
    vocabulary = extract_vocabulary_from_text(page15_text)

    if not vocabulary:
        print("경고: 어휘를 찾을 수 없습니다.")
        return

    print(f"  → 어휘 추출 완료 ({len(vocabulary.split(chr(10)))}개 항목)")

    print(f"[3/3] 마크다운 파일에 어휘 추가 중...")

    # 기존 md 파일 읽기
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 8-9번 문항의 어휘 섹션 찾기
    pattern = r'(## 8\s*-\s*9번[\s\S]+?)(### 어휘\s*\n\s*\n|### 어휘\s*\n---|$)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        # 어휘 섹션이 이미 있는지 확인
        q8_9_section = match.group(1)

        if '### 어휘' in q8_9_section:
            # 기존 어휘 섹션 교체
            content = re.sub(
                r'(## 8\s*-\s*9번[\s\S]+?)(### 어휘\s*[\s\S]+?)(\n---|\n## \d+번|$)',
                r'\1### 어휘\n\n' + vocabulary + '\n\n\3',
                content,
                flags=re.DOTALL
            )
        else:
            # 어휘 섹션이 없으면 추가 (해석 다음에)
            if '### 해석' in q8_9_section:
                content = re.sub(
                    r'(## 8\s*-\s*9번[\s\S]+?### 해석[\s\S]+?)(\n---|\n## \d+번|$)',
                    r'\1\n\n### 어휘\n\n' + vocabulary + '\n\n\2',
                    content,
                    flags=re.DOTALL
                )
            else:
                # 해석도 없으면 오답해설 다음에 추가
                content = re.sub(
                    r'(## 8\s*-\s*9번[\s\S]+?### 오답해설[\s\S]+?)(\n---|\n## \d+번|$)',
                    r'\1\n\n### 어휘\n\n' + vocabulary + '\n\n\2',
                    content,
                    flags=re.DOTALL
                )
    else:
        print("오류: 8-9번 문항을 찾을 수 없습니다.")
        return

    # 파일 저장
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[완료] 저장 완료: {md_path}")

if __name__ == "__main__":
    main()

