#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
해설 JSONL 파일을 Neon DB의 commentaries 테이블 형식 CSV로 변환합니다.

사용 예:
  python -m backend.tools.convert_commentary_jsonl_to_csv \
    --jsonl "data/gongmuwon/dataset/commentary_korean_history.jsonl" \
    --out "data/gongmuwon/dataset/commentary_korean_history.csv" \
    --user-id 1
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from typing import Dict, List, Optional


def convert_jsonl_to_csv(
    jsonl_path: str,
    output_path: str,
    user_id: int = 1,
    year: Optional[int] = None,
    exam_type: Optional[str] = None
) -> int:
    """해설 JSONL 파일을 commentaries 테이블 형식 CSV로 변환합니다.

    Args:
        jsonl_path: 입력 JSONL 파일 경로
        output_path: 출력 CSV 파일 경로
        user_id: 해설을 작성한 사용자 ID (기본값: 1, 시스템 사용자)
        year: 시험 연도 (파일명에서 추론 시도)
        exam_type: 시험 유형 (파일명에서 추론 시도)

    Returns:
        생성된 항목 수
    """
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"JSONL 파일을 찾을 수 없습니다: {jsonl_path}")

    # 파일명에서 연도 추론 (예: "250621" -> 2025)
    if year is None:
        basename = os.path.basename(jsonl_path)
        if "250621" in basename or "2025" in basename:
            year = 2025
        elif "2024" in basename:
            year = 2024
        else:
            year = 2025  # 기본값

    # 파일명에서 시험 유형 추론
    if exam_type is None:
        basename = os.path.basename(jsonl_path)
        if "지방직" in basename:
            exam_type = "지방직"
        elif "국가직" in basename:
            exam_type = "국가직"
        else:
            exam_type = "지방직"  # 기본값

    # JSONL 파일 읽기
    items: List[Dict[str, any]] = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    # CSV 파일 작성
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # commentaries 테이블 컬럼 순서
    # id는 auto increment이므로 제외
    fieldnames = [
        'user_id',
        'exam_question_id',  # 나중에 exam_questions 테이블과 매칭 필요
        'body',  # 해설 본문
        'selected',  # 선택한 보기 (answer_key와 동일)
        'is_correct',  # 정답 여부 (항상 True로 가정)
        'attempt_count',
        'confidence',
        'bookmarked',
        'extra_json',  # JSON 문자열로 저장
        # created_at, updated_at는 DB에서 자동 생성
    ]

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        for item in items:
            # exam_question_id는 나중에 exam_questions 테이블과 매칭해야 하므로
            # 임시로 NULL 또는 0으로 설정 (또는 extra_json에 매칭 정보 포함)
            # 실제로는 exam_questions 테이블에서 (year, exam_type, subject, question_no)로 찾아야 함

            # extra_json에 매칭 정보 포함
            extra_json = {
                "source_md": item.get("source_md"),
                "source_pdf": item.get("source_pdf"),
                "subject": item.get("subject"),
                "question_no": int(item.get("id")),
                "year": year,
                "exam_type": exam_type,
                "answer_key": item.get("answer"),
                "topic": item.get("question", "").split("\n")[0].replace("주제: ", "") if item.get("question") else ""
            }

            row = {
                'user_id': user_id,
                'exam_question_id': '',  # 빈 값 (나중에 매칭 필요)
                'body': item.get("question", ""),  # 해설 본문
                'selected': item.get("answer"),  # 선택한 보기
                'is_correct': 'true',  # 해설이므로 정답으로 가정
                'attempt_count': '0',
                'confidence': '',
                'bookmarked': 'false',
                'extra_json': json.dumps(extra_json, ensure_ascii=False)
            }

            writer.writerow(row)

    print(f"[완료] {len(items)}개 항목 생성 → {output_path}")
    print(f"[참고] exam_question_id는 빈 값입니다. exam_questions 테이블과 매칭하여 업데이트해야 합니다.")
    return len(items)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="해설 JSONL 파일을 commentaries 테이블 형식 CSV로 변환합니다."
    )
    parser.add_argument(
        "--jsonl",
        type=str,
        required=True,
        help="입력 JSONL 파일 경로"
    )
    parser.add_argument(
        "--out",
        type=str,
        required=True,
        help="출력 CSV 파일 경로"
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=1,
        help="해설을 작성한 사용자 ID (기본값: 1)"
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="시험 연도 (지정하지 않으면 파일명에서 추론)"
    )
    parser.add_argument(
        "--exam-type",
        type=str,
        default=None,
        help="시험 유형 (지방직/국가직, 지정하지 않으면 파일명에서 추론)"
    )

    args = parser.parse_args()

    try:
        convert_jsonl_to_csv(
            jsonl_path=args.jsonl,
            output_path=args.out,
            user_id=args.user_id,
            year=args.year,
            exam_type=args.exam_type
        )
        return 0
    except Exception as e:
        print(f"❌ 오류 발생: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

