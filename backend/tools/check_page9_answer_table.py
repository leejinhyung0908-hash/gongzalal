#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[8]  # 0-based, so 8 = page 9
    text = page.extract_text()

    with open('page9_full_text.txt', 'w', encoding='utf-8') as f:
        f.write(text)

    print("9페이지 텍스트를 page9_full_text.txt에 저장했습니다.")
    print("\n처음 2000자:")
    print(text[:2000])

