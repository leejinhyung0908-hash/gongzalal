#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    page13 = pdf.pages[12]
    text = page13.extract_text()

    with open('page13_full_text.txt', 'w', encoding='utf-8') as f:
        f.write(text)

    print("13페이지 전체 텍스트를 page13_full_text.txt에 저장했습니다.")

