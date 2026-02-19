#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    page14 = pdf.pages[13]
    text = page14.extract_text()

    # 8번 문항 부분 찾기
    q8_match = re.search(r'8\.\s*(?:-\s*9\.)?\s*([\s\S]+?)(?=10\.|$)', text)
    if q8_match:
        q8_9_text = q8_match.group(1)

        # 해석 부분 찾기
        translation_match = re.search(r'[❚■]?해석\s*([\s\S]+?)(?=[❚■]?어휘|성정혜|2025|해당|$)', q8_9_text, re.DOTALL)
        if translation_match:
            translation = translation_match.group(1).strip()

            # 파일로 저장
            with open('translation_raw.txt', 'w', encoding='utf-8') as f:
                f.write(translation)
            print("해석 부분을 translation_raw.txt에 저장했습니다.")
            print(f"해석 부분 길이: {len(translation)}")

            # "사람들을 위한 건강" 찾기
            health_start = translation.find('사람들을 위한 건강')
            print(f"'사람들을 위한 건강' 위치: {health_start}")

            if health_start != -1:
                with open('translation_after_health.txt', 'w', encoding='utf-8') as f:
                    f.write(translation[health_start:])
                print("'사람들을 위한 건강' 이후 텍스트를 translation_after_health.txt에 저장했습니다.")
        else:
            print("해석 부분을 찾을 수 없습니다.")
    else:
        print("8번 문항을 찾을 수 없습니다.")

