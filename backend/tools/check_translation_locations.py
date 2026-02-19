#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    # 10페이지부터 13페이지까지 확인
    for page_idx in range(9, 13):  # 0-based, so 9 = page 10
        if page_idx < len(pdf.pages):
            page = pdf.pages[page_idx]
            text = page.extract_text()

            if text:
                # 해석 부분 찾기
                translation_matches = list(re.finditer(r'[❚■]?해석', text))
                if translation_matches:
                    with open(f'page{page_idx+1}_text.txt', 'w', encoding='utf-8') as f:
                        f.write(text)
                    print(f"\n=== 페이지 {page_idx + 1} ===")
                    print(f"텍스트를 page{page_idx+1}_text.txt에 저장했습니다.")
                    for match in translation_matches:
                        start = match.start()
                        print(f"해석 위치: {start}")

                # 각 문항 번호 찾기
                q_matches = list(re.finditer(r'(\d+)\.', text))
                if q_matches:
                    print(f"\n페이지 {page_idx + 1}의 문항 번호들:")
                    for match in q_matches:
                        q_no = match.group(1)
                        print(f"  {q_no}번 (위치: {match.start()})")

