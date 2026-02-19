#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    page15 = pdf.pages[14]  # 0-based index, so 14 = page 15
    text = page15.extract_text()

    # 파일로 저장
    with open('page15_text.txt', 'w', encoding='utf-8') as f:
        f.write(text)

    print("15페이지 텍스트를 page15_text.txt에 저장했습니다.")

    # 어휘 부분 찾기
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

        with open('page15_vocab.txt', 'w', encoding='utf-8') as f:
            f.write(vocab_text)
        print(f"어휘 부분을 page15_vocab.txt에 저장했습니다.")
        print(f"어휘 부분 길이: {len(vocab_text)}")
    else:
        print("어휘 부분을 찾을 수 없습니다.")

