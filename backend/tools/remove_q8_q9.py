#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8-9번 문항과 비어있는 해석 부분을 삭제합니다.
"""
import re

def main():
    md_path = 'data/gongmuwon/intermediate/markdown/commentary_md/page9_test.md'

    print(f"[1/2] md 파일 읽기 중...")
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"[2/2] 8-9번 문항 삭제 중...")

    # 8-9번 문항 전체 삭제 (## 8 - 9번부터 다음 문항 또는 파일 끝까지)
    # 다음 문항이 있으면 그 전까지, 없으면 파일 끝까지
    pattern = r'\n## 8 - 9번[\s\S]+?(?=\n## \d+번|\Z)'
    content = re.sub(pattern, '', content)

    # 비어있는 해석 부분도 삭제 (혹시 남아있을 수 있음)
    content = re.sub(r'\n### 해석\s*\n\s*\n', '', content)

    # 파일 저장
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[완료] 8-9번 문항이 삭제되었습니다.")

if __name__ == "__main__":
    main()

