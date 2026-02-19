#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    page14 = pdf.pages[13]
    text = page14.extract_text()

    # 해석 부분 찾기
    translation_match = re.search(r'[❚■]?해석\s*([\s\S]+?)(?=[❚■]?어휘|성정혜|2025|해당|$)', text, re.DOTALL)
    if translation_match:
        translation = translation_match.group(1).strip()

        with open('debug_translation_raw.txt', 'w', encoding='utf-8') as f:
            f.write(translation)
        print(f"해석 부분 길이: {len(translation)}")
        print(f"해석 부분 처음 200자:")
        print(translation[:200])

        # "사람들을 위한 건강" 찾기
        health_start = translation.find('사람들을 위한 건강')
        print(f"\n'사람들을 위한 건강' 위치: {health_start}")

        if health_start != -1:
            translation_after = translation[health_start:]
            with open('debug_translation_after_health.txt', 'w', encoding='utf-8') as f:
                f.write(translation_after)
            print(f"'사람들을 위한 건강' 이후 텍스트 길이: {len(translation_after)}")
            print(f"처음 300자:")
            print(translation_after[:300])
    else:
        print("해석 부분을 찾을 수 없습니다.")

