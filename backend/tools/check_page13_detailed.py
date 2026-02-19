#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    page13 = pdf.pages[12]
    text = page13.extract_text()

    # 6번 시작부터 8번 시작 전까지
    q6_start = text.find('6.')
    q8_start = text.find('8.')

    if q6_start != -1:
        if q8_start != -1:
            q6_7_text = text[q6_start:q8_start]
        else:
            q6_7_text = text[q6_start:]

        print("=== 6-7번 전체 텍스트 ===")
        print(q6_7_text[:5000])
        print("\n=== 정답해설 부분 ===")
        ans_start = q6_7_text.find('정답해설')
        if ans_start != -1:
            ans_end = q6_7_text.find('오답해설', ans_start)
            if ans_end != -1:
                print(q6_7_text[ans_start:ans_end])
        print("\n=== 오답해설 부분 ===")
        wrong_start = q6_7_text.find('오답해설')
        if wrong_start != -1:
            wrong_end = q6_7_text.find('해석', wrong_start)
            if wrong_end != -1:
                print(q6_7_text[wrong_start:wrong_end])

