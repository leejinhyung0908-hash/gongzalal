#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1-5번 문항의 해석 부분을 올바른 순서로 재배치합니다.
올바른 순서: 정답해설 → 오답해설 → 해석 → 어휘
"""
import re

def fix_question_translation_order(content: str, question_no: int) -> str:
    """특정 문항의 해석 순서를 수정합니다."""
    # 문항 패턴 찾기
    if question_no == 1:
        pattern = r'(## 1번[\s\S]+?)(### 어휘[\s\S]+?)(### 해석[\s\S]+?)(?=## 2번|$)'
    else:
        pattern = rf'(## {question_no}번[\s\S]+?)(?=## \d+번|$)'

    def replace_func(match):
        if question_no == 1:
            question_content = match.group(1)
            vocab_section = match.group(2)
            translation_section = match.group(3)

            # 해석을 어휘 전으로 이동
            # 정답해설과 오답해설 사이에 해석이 있는지 확인
            if '### 해석' in question_content:
                # 이미 해석이 있으면 제거
                question_content = re.sub(r'\n### 해석[\s\S]+?(?=\n### 어휘|\n---|$)', '', question_content)

            # 오답해설 다음에 해석 추가
            question_content = re.sub(
                r'(### 오답해설[\s\S]+?)(\n### 어휘|\n---|$)',
                r'\1\n\n' + translation_section.strip() + r'\n\n\2',
                question_content,
                flags=re.DOTALL
            )

            return question_content + vocab_section
        else:
            question_content = match.group(1)

            # 오답해설에서 해석 부분 제거
            wrong_explanation_match = re.search(r'(### 오답해설[\s\S]+?)(?=### 어휘|### 해석|$)', question_content, re.DOTALL)
            if wrong_explanation_match:
                wrong_explanation = wrong_explanation_match.group(1)
                # 해석 내용이 섞여있는지 확인하고 제거
                # 해석은 보통 선택지(①②③④)가 포함되어 있음
                lines = wrong_explanation.split('\n')
                cleaned_lines = []
                translation_lines = []
                in_translation = False

                for line in lines:
                    line_stripped = line.strip()
                    # 해석 시작 패턴 (대화나 본문 내용)
                    if (line_stripped and
                        not line_stripped.startswith('①') and
                        not line_stripped.startswith('②') and
                        not line_stripped.startswith('③') and
                        not line_stripped.startswith('④') and
                        not line_stripped.startswith('➀') and
                        not line_stripped.startswith('➁') and
                        not line_stripped.startswith('➂') and
                        not line_stripped.startswith('➃') and
                        ('안녕' in line_stripped or '발표 자료' in line_stripped or
                         '예비 조사' in line_stripped or '비즈니스 세계' in line_stripped or
                         'Yuna:' in line_stripped or 'Jenny:' in line_stripped or
                         'A:' in line_stripped or 'B:' in line_stripped)):
                        in_translation = True
                        translation_lines.append(line)
                    elif in_translation:
                        if (line_stripped.startswith('①') or line_stripped.startswith('②') or
                            line_stripped.startswith('③') or line_stripped.startswith('④') or
                            line_stripped.startswith('➀') or line_stripped.startswith('➁') or
                            line_stripped.startswith('➂') or line_stripped.startswith('➃')):
                            translation_lines.append(line)
                        else:
                            in_translation = False
                            if line_stripped and not line_stripped.startswith('###'):
                                cleaned_lines.append(line)
                    else:
                        cleaned_lines.append(line)

                # 오답해설 정리
                cleaned_wrong = '\n'.join(cleaned_lines).strip()

                # 해석 부분 추출
                translation_text = '\n'.join(translation_lines).strip() if translation_lines else ''

                # 기존 해석 섹션 확인
                existing_translation_match = re.search(r'### 해석\s*([\s\S]+?)(?=### 어휘|\n---|$)', question_content, re.DOTALL)
                if existing_translation_match:
                    existing_translation = existing_translation_match.group(1).strip()
                    if translation_text and translation_text not in existing_translation:
                        translation_text = existing_translation + '\n' + translation_text
                    else:
                        translation_text = existing_translation

                # 오답해설 교체
                question_content = question_content.replace(wrong_explanation, cleaned_wrong)

                # 해석 섹션이 없으면 추가
                if translation_text and '### 해석' not in question_content:
                    # 어휘 전에 해석 추가
                    question_content = re.sub(
                        r'(### 오답해설[\s\S]+?)(\n### 어휘|\n---|$)',
                        r'\1\n\n### 해석\n\n' + translation_text + r'\n\n\2',
                        question_content,
                        flags=re.DOTALL
                    )
                elif translation_text and '### 해석' in question_content:
                    # 기존 해석 섹션 교체
                    question_content = re.sub(
                        r'### 해석\s*[\s\S]+?(?=### 어휘|\n---|$)',
                        '### 해석\n\n' + translation_text + '\n\n',
                        question_content,
                        flags=re.DOTALL
                    )

            return question_content

    content = re.sub(pattern, replace_func, content, flags=re.DOTALL)
    return content

def main():
    md_path = 'data/gongmuwon/intermediate/markdown/commentary_md/page9_test.md'

    print("[1/2] 마크다운 파일 읽기 중...")
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("[2/2] 각 문항의 해석 순서 수정 중...")

    # 1번부터 5번까지 순서대로 수정
    for q_no in range(1, 6):
        print(f"  → {q_no}번 문항 수정 중...")
        content = fix_question_translation_order(content, q_no)

    # 파일 저장
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[완료] 저장 완료: {md_path}")

if __name__ == "__main__":
    main()

