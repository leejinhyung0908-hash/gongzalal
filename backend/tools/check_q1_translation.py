#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    # 9페이지와 10페이지 확인
    for page_idx in [8, 9]:  # 0-based, so 8 = page 9, 9 = page 10
        if page_idx < len(pdf.pages):
            page = pdf.pages[page_idx]
            text = page.extract_text()

            if text:
                # 1번 문항 찾기
                q1_match = re.search(r'(?:^|\n)1\.', text)
                if q1_match:
                    print(f"\n=== 페이지 {page_idx + 1}에서 1번 문항 발견 ===")
                    start = q1_match.start()
                    # 1번부터 2번 전까지
                    q2_match = re.search(r'(?:^|\n)2\.', text[start:])
                    if q2_match:
                        q1_text = text[start:start + q2_match.start()]
                    else:
                        q1_text = text[start:]

                    # 해석 부분 찾기
                    translation_match = re.search(r'[❚■]?해석\s*([\s\S]+?)(?=[❚■]?어휘|❚정답해설|❚오답해설|2\.|성정혜|2025|해당|$)', q1_text, re.DOTALL)
                    if translation_match:
                        translation = translation_match.group(1).strip()
                        with open(f'q1_translation_page{page_idx+1}.txt', 'w', encoding='utf-8') as f:
                            f.write(translation)
                        print(f"1번 해석을 q1_translation_page{page_idx+1}.txt에 저장했습니다.")
                        print(f"해석 길이: {len(translation)}")
                        print(f"해석 처음 200자: {translation[:200]}")
                    else:
                        print(f"페이지 {page_idx + 1}에서 1번 해석을 찾을 수 없습니다.")

