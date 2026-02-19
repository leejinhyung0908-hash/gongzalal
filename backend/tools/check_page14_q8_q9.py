#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    page14 = pdf.pages[13]
    text = page14.extract_text()

    # 파일로 저장
    with open('page14_text.txt', 'w', encoding='utf-8') as f:
        f.write(text)

    # 문항 번호 패턴 찾기
    print("=== 14페이지 문항 번호 패턴 ===")
    # "8. - 9." 또는 "8." 형식 찾기
    matches = re.finditer(r'(?:^|\n)\s*(\d+)(?:\s*-\s*(\d+))?\.', text, re.MULTILINE)
    for match in matches:
        start_q = match.group(1)
        end_q = match.group(2) if match.group(2) else start_q
        print(f"찾은 문항: {start_q} - {end_q} (위치: {match.start()})")

    print("\n=== 14페이지 첫 부분 ===")
    print(text[:500])

