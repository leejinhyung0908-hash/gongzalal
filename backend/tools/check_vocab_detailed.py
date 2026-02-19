#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import re

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'

with pdfplumber.open(pdf_path) as pdf:
    # 11페이지
    page11 = pdf.pages[10]
    page11_text = page11.extract_text()

    # 12페이지
    page12 = pdf.pages[11]
    page12_text = page12.extract_text()

    # 11페이지에서 4번 어휘 찾기
    print("=== 11페이지 4번 어휘 (원본) ===")
    q4_start = page11_text.find('4.')
    if q4_start != -1:
        q4_text = page11_text[q4_start:]
        vocab_start = q4_text.find('어휘')
        if vocab_start != -1:
            # 5번 시작 전까지
            q5_start = q4_text.find('5.')
            if q5_start != -1:
                vocab_text = q4_text[vocab_start:q5_start]
            else:
                vocab_text = q4_text[vocab_start:vocab_start+3000]
            # 어휘 부분만 출력
            vocab_text = re.sub(r'[❚■]?어휘\s*', '', vocab_text, count=1)
            print(vocab_text)
            print("\n--- 어휘 라인별 분리 ---")
            for i, line in enumerate(vocab_text.split('\n')):
                if '☑' in line or '✔' in line or 'þ' in line:
                    print(f"{i}: {line}")

    print("\n\n=== 12페이지 5번 어휘 (원본) ===")
    q5_start = page12_text.find('5.')
    if q5_start != -1:
        q5_text = page12_text[q5_start:]
        vocab_start = q5_text.find('어휘')
        if vocab_start != -1:
            # 6번 시작 전까지
            q6_start = q5_text.find('6.')
            if q6_start != -1:
                vocab_text = q5_text[vocab_start:q6_start]
            else:
                vocab_text = q5_text[vocab_start:vocab_start+3000]
            # 어휘 부분만 출력
            vocab_text = re.sub(r'[❚■]?어휘\s*', '', vocab_text, count=1)
            print(vocab_text)
            print("\n--- 어휘 라인별 분리 ---")
            for i, line in enumerate(vocab_text.split('\n')):
                if '☑' in line or '✔' in line or 'þ' in line:
                    print(f"{i}: {line}")

