#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
영어 항목의 source_pdf 필드를 올바른 경로로 수정합니다.
"""
import json

jsonl_path = 'data/gongmuwon/dataset/commentary_korean_history.jsonl'
pdf_path = '250621 지방직 9급 영어 해설 성정혜.pdf'

# JSONL 파일 읽기
items = []
with open(jsonl_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            items.append(json.loads(line))

# 영어 항목의 source_pdf 수정
updated_count = 0
for item in items:
    if item.get("subject") == "영어":
        item["source_pdf"] = pdf_path
        updated_count += 1

# 파일 저장
with open(jsonl_path, 'w', encoding='utf-8') as f:
    for item in items:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"[완료] {updated_count}개 영어 항목의 source_pdf 수정 완료")
print(f"  → {pdf_path}")

