#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
14페이지에서 어휘 헤더를 확인하고, 15페이지에서 어휘 내용을 추출하여 8-9번에 추가합니다.
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

def extract_vocabulary_from_page15(text: str) -> str:
    """15페이지에서 어휘 내용을 추출합니다."""
    # 10번 문항 시작 지점 찾기
    next_q_match = re.search(r'10\.', text)
    if next_q_match:
        vocab_text = text[:next_q_match.start()]
    else:
        vocab_text = text

    # 푸터 제거
    vocab_text = remove_footer_header(vocab_text)

    # 줄 단위로 분리
    lines = vocab_text.split('\n')
    vocab_items = []
    seen_words = set()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # "þ" 기호로 시작하는 줄만 처리
        if line.startswith('þ') or 'þ' in line:
            # "þ"를 "☑"로 변환
            line = line.replace('þ', '☑')

            # 한 줄에 여러 어휘가 있을 수 있음 (예: "☑ word1 뜻1 ☑ word2 뜻2")
            # "☑"로 분리
            parts = re.split(r'☑\s*', line)
            for part in parts:
                part = part.strip()
                if not part:
                    continue

                # 푸터 관련 텍스트 제거
                if re.search(r'성정혜|2025|해당|10\.', part):
                    continue

                # 단어 추출 (중복 방지)
                # 형식: "word 뜻" 또는 "word 뜻1, 뜻2"
                word_match = re.match(r'^([^\s]+(?:\s+[^\s]+)*?)\s+(.+)$', part)
                if word_match:
                    word = word_match.group(1).strip().lower()
                    meaning = word_match.group(2).strip()
                    if word and word not in seen_words:
                        seen_words.add(word)
                        vocab_items.append(f'☑ {word_match.group(1).strip()} {meaning}')
                else:
                    # 단어만 있는 경우
                    if part and part not in seen_words:
                        seen_words.add(part.lower())
                        vocab_items.append(f'☑ {part}')

    if vocab_items:
        return '\n'.join(vocab_items)

    return ""

def main():
    pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'
    md_path = 'data/gongmuwon/intermediate/markdown/commentary_md/page9_test.md'

    print(f"[1/4] PDF에서 14페이지 텍스트 추출 중...")
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 15:
            print(f"오류: PDF에는 {len(pdf.pages)}페이지만 있습니다.")
            return

        page14 = pdf.pages[13]  # 0-based index, so 13 = page 14
        page14_text = page14.extract_text()

        print(f"[2/4] PDF에서 15페이지 텍스트 추출 중...")
        page15 = pdf.pages[14]  # 0-based index, so 14 = page 15
        page15_text = page15.extract_text()

    if not page14_text or not page15_text:
        print("오류: 텍스트를 추출할 수 없습니다.")
        return

    # 14페이지에서 어휘 헤더 확인
    vocab_header_found = False
    if '❚어휘' in page14_text or '■어휘' in page14_text or '어휘' in page14_text:
        vocab_header_found = True
        print(f"[3/4] 14페이지에서 어휘 헤더 확인 완료")

    print(f"[3/4] 15페이지에서 8-9번 어휘 내용 추출 중...")
    vocabulary = extract_vocabulary_from_page15(page15_text)

    if not vocabulary:
        print("경고: 어휘를 찾을 수 없습니다.")
        # 디버깅을 위해 15페이지 텍스트 저장
        with open('page15_debug.txt', 'w', encoding='utf-8') as f:
            f.write(page15_text)
        print("15페이지 텍스트를 page15_debug.txt에 저장했습니다.")
        return

    print(f"  → 어휘 추출 완료 ({len(vocabulary.split(chr(10)))}개 항목)")

    print(f"[4/4] 마크다운 파일에 어휘 추가 중...")

    # 기존 md 파일 읽기
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 8-9번 문항의 해석 다음에 어휘 추가
    pattern = r'(## 8\s*-\s*9번[\s\S]+?### 해석[\s\S]+?)(\n---|\n## \d+번|$)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        before = match.group(1)
        after = match.group(2)

        # 이미 어휘 섹션이 있는지 확인
        if '### 어휘' in before:
            # 기존 어휘 섹션 교체
            before = re.sub(
                r'### 어휘\s*[\s\S]+?(?=\n---|\n## \d+번|$)',
                '### 어휘\n\n' + vocabulary + '\n\n',
                before,
                flags=re.DOTALL
            )
            new_content = before + after
        else:
            # 어휘 섹션 추가
            new_content = before + "\n\n### 어휘\n\n" + vocabulary + "\n\n" + after
    else:
        print("오류: 8-9번 문항의 해석 부분을 찾을 수 없습니다.")
        return

    # 파일 저장
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"[완료] 저장 완료: {md_path}")

if __name__ == "__main__":
    main()

