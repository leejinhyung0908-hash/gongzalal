#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdfplumber
import sys

pdf_path = 'data/gongmuwon/raw/commentary/250621 지방직 9급 영어 해설 성정혜.pdf'
output_path = 'page9_text.txt'

try:
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 9:
            print(f"PDF에는 {len(pdf.pages)}페이지만 있습니다.")
            sys.exit(1)

        page = pdf.pages[8]  # 0-based index, so 8 = page 9
        text = page.extract_text()

        if text:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"9페이지 텍스트를 {output_path}에 저장했습니다.")
            print(f"총 {len(text)}자 추출되었습니다.")
        else:
            print("텍스트를 추출할 수 없습니다.")
except Exception as e:
    print(f"오류 발생: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
