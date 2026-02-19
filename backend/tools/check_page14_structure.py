#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    # 14페이지 확인
    page14 = pdf.pages[13]
    text = page14.extract_text()

    print("=== 14페이지 첫 2000자 ===")
    print(text[:2000])

    # 문항 번호 패턴 찾기
    print("\n=== 문항 번호 패턴 ===")
    matches = re.finditer(r'(?:^|\n)\s*(\d+)(?:\s*-\s*(\d+))?\.', text, re.MULTILINE)
    for match in matches:
        start_q = match.group(1)
        end_q = match.group(2) if match.group(2) else start_q
        print(f"찾은 문항: {start_q} - {end_q} (위치: {match.start()})")

