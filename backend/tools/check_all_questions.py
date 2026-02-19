#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

with open('data/gongmuwon/intermediate/markdown/commentary_md/page9_test.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 모든 문항 번호 찾기
pattern = r'^## (\d+(?:\s*-\s*\d+)?)번'
matches = re.findall(pattern, content, re.MULTILINE)

print(f"총 {len(matches)}개 문항:")
for match in matches:
    print(f"  - {match}번")

# 빠른 정답 Check 확인
if '빠른 정답 Check' in content:
    print("\n빠른 정답 Check 포함됨")

