#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
어휘 추출 로직을 개선하여 여러 줄에 걸친 어휘와 한 줄에 여러 어휘를 처리합니다.
"""
import re

def extract_vocabulary_improved(text: str) -> str:
    """개선된 어휘 추출 함수"""
    vocab_match = re.search(r'[❚■]?어휘\s*([\s\S]+?)(?=\d+\.|성정혜|2025|해당|$)', text, re.DOTALL)
    if not vocab_match:
        return ""

    vocab_text = vocab_match.group(1).strip()

    # 푸터 제거
    vocab_text = re.sub(r'성정혜\s*영어.*', '', vocab_text, flags=re.DOTALL)
    vocab_text = re.sub(r'2025\s*Sung\s*Jung\s*hye.*', '', vocab_text, flags=re.DOTALL)
    vocab_text = re.sub(r'해당\s*콘텐츠는.*', '', vocab_text, flags=re.DOTALL)

    # "þ", "✔" 기호를 "☑"로 변환
    vocab_text = re.sub(r'þ', '☑', vocab_text)
    vocab_text = re.sub(r'✔', '☑', vocab_text)

    # 줄 단위로 처리
    lines = vocab_text.split('\n')
    vocab_items = []
    seen_words = set()

    # 모든 "☑" 위치 찾기
    full_text = ' '.join(lines)

    # "☑"로 시작하는 모든 항목 찾기
    # 패턴: "☑ word 뜻" (다음 "☑" 전까지 또는 끝까지)
    pattern = r'☑\s*([^\s☑]+(?:\s+[^\s☑]+)*?)\s+([^☑]+?)(?=\s*☑|성정혜|2025|해당|$)'
    matches = list(re.finditer(pattern, full_text))

    for match in matches:
        word = match.group(1).strip()
        meaning = match.group(2).strip()

        # 푸터 관련 텍스트 제거
        if re.search(r'성정혜|2025|해당', meaning):
            continue

        # 중복 방지
        word_lower = word.lower()
        if word_lower and word_lower not in seen_words:
            seen_words.add(word_lower)
            vocab_items.append(f'☑ {word} {meaning}')

    if vocab_items:
        return '\n'.join(vocab_items)

    return ""

# 테스트
if __name__ == "__main__":
    with open('q4_vocab.txt', 'r', encoding='utf-8') as f:
        text = f.read()

    result = extract_vocabulary_improved(text)
    print("추출된 어휘:")
    print(result)

