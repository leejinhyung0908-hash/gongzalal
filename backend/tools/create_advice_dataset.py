#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
합격수기 데이터를 기반으로 학습 상담(ADVICE) 데이터셋 생성

합격수기 데이터에서 질문-답변 쌍을 생성하여 ExaOne 모델 학습용 데이터셋을 만듭니다.
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdviceDatasetGenerator:
    """학습 상담 데이터셋 생성기"""

    def __init__(self, input_file: str, output_dir: str = "data/success_stories"):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 질문 템플릿 (자연스러운 사용자 질문 패턴)
        self.question_templates = {
            "study_period": [
                "{job_series}을 준비하는 데 보통 얼마나 걸려?",
                "{job_series} 합격하는데 걸리는 시간은?",
                "{job_series} 준비 기간이 얼마나 걸리나요?",
                "평균적으로 {job_series} 합격하는데 걸리는 시간은?",
                "{job_series} 수험 기간은 보통 얼마나 걸려?",
                "{exam_type} {grade} {job_series} 준비하는데 얼마나 걸렸나요?",
                "수험 기간은 얼마나 걸렸나요?",
                "총 수험 기간이 얼마나 되나요?",
                "몇 개월 동안 공부했나요?",
                "합격까지 얼마나 걸렸나요?"
            ],
            "study_hours": [
                "하루에 몇 시간씩 공부해야 해?",
                "평균적으로 하루에 몇 시간 공부했나요?",
                "하루 학습 시간은 보통 얼마나 되나요?",
                "일일 공부 시간이 얼마나 되나요?",
                "하루에 몇 시간씩 공부했나요?",
                "평균 학습 시간이 얼마나 되나요?"
            ],
            "study_method": [
                "어떻게 공부해야 돼?",
                "공부 방법을 알려줘",
                "어떻게 공부하셨나요?",
                "공부 방법이 궁금해요",
                "학습 방법을 알려주세요",
                "어떤 방식으로 공부했나요?",
                "공부 스타일이 어떻게 되나요?"
            ],
            "subject_method": [
                "{job_series} 준비하는데 {subject}는 어떻게 공부해야 해?",
                "{subject} 과목 공부법 알려줘",
                "{subject}는 어떻게 공부했나요?",
                "{subject} 학습법이 궁금해요",
                "{subject}는 어떻게 준비했나요?",
                "{subject} 공부 방법을 알려주세요",
                "{subject}는 어떻게 접근했나요?",
                "{job_series} {subject} 공부법이 궁금해요"
            ],
            "subject_method_detail": [
                "{job_series} {grade} 공무원 시험을 준비하는데, {subject} 과목의 {detail_area} 공부법을 알려줘",
                "{subject} {detail_area} 영역은 어떻게 공부해야 해?",
                "{subject} {detail_area} 부분 공부법 알려줘"
            ],
            "daily_plan": [
                "하루 일과가 어떻게 되나요?",
                "하루 학습 계획을 알려주세요",
                "일일 스케줄이 궁금해요",
                "하루 생활 패턴이 어떻게 되나요?",
                "하루 계획을 공유해주세요",
                "하루 일과는 어떻게 구성했나요?"
            ],
            "difficulties": [
                "어려웠던 점이 뭐였나요?",
                "어떤 부분이 힘들었나요?",
                "어려움을 어떻게 극복했나요?",
                "수험 생활 중 어려웠던 점은?",
                "어떤 점이 가장 힘들었나요?",
                "공부하면서 어려웠던 부분은?"
            ],
            "key_points": [
                "합격의 핵심 포인트는 뭐였나요?",
                "가장 중요한 학습 전략이 뭐였나요?",
                "합격으로 이끈 전략을 알려주세요",
                "핵심 학습 포인트가 뭐였나요?",
                "가장 효과적이었던 공부법은?",
                "합격 노하우 알려줘"
            ],
            "interview_prep": [
                "면접 준비는 어떻게 했나요?",
                "면접 준비 과정이 궁금해요",
                "면접은 어떻게 준비했나요?",
                "면접 대비 방법을 알려주세요",
                "면접 준비 팁이 있나요?"
            ],
            "general_advice": [
                "합격 수기를 공유해주세요",
                "합격 노하우를 알려주세요",
                "공부 조언을 해주세요",
                "수험생에게 조언을 해주세요",
                "{job_series} 합격 선배의 조언이 필요해요",
                "{job_series} 준비하는 사람에게 조언해줘"
            ]
        }

        # 과목별 세부 영역 (예: 국어의 논리/추론, 영어의 독해 등)
        self.subject_detail_areas = {
            "국어": ["논리", "추론", "문법", "독해", "문학", "어휘"],
            "영어": ["독해", "문법", "어휘", "회화"],
            "한국사": ["고대사", "중세사", "근세사", "근현대사", "문화사"],
            "행정법총론": ["행정법일반", "행정작용법", "행정구제법"],
            "행정학개론": ["행정이론", "조직론", "인사행정", "재무행정", "정책학"],
            "회계학": ["재무회계", "원가회계", "관리회계"],
            "형사정책개론": ["형사정책", "범죄학", "형사법"],
            "사회복지학개론": ["사회복지이론", "사회복지실천", "사회복지정책"]
        }

    def load_stories(self) -> List[Dict[str, Any]]:
        """합격수기 데이터 로드"""
        if not self.input_file.exists():
            raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {self.input_file}")

        with open(self.input_file, 'r', encoding='utf-8') as f:
            if self.input_file.suffix == '.json':
                stories = json.load(f)
            elif self.input_file.suffix == '.jsonl':
                stories = [json.loads(line) for line in f if line.strip()]
            else:
                raise ValueError(f"지원하지 않는 파일 형식: {self.input_file.suffix}")

        logger.info(f"로드된 합격수기 데이터: {len(stories)}개")
        return stories

    def generate_qa_pairs(self, story: Dict[str, Any]) -> List[Dict[str, Any]]:
        """합격수기 데이터에서 질문-답변 쌍 생성"""
        qa_pairs = []

        exam_info = story.get("exam_info", {})
        study_style = story.get("study_style", {})
        daily_plan = story.get("daily_plan", "")
        subject_methods = story.get("subject_methods", {})
        interview_prep = story.get("interview_prep", "")
        difficulties = story.get("difficulties", "")
        key_points = story.get("key_points", "")

        # 시험 정보 추출
        job_series = exam_info.get("job_series", "")
        exam_type = exam_info.get("exam_type", "")
        grade = exam_info.get("grade", "")
        year = exam_info.get("year", "")

        # 시험 정보 기반 컨텍스트 생성
        exam_context = self._build_exam_context(exam_info)

        # 수험 기간 관련 질문
        if study_style.get("총 수험기간"):
            for template in self.question_templates["study_period"]:
                question = template.format(
                    job_series=job_series or "공무원",
                    exam_type=exam_type or "",
                    grade=grade or ""
                )
                qa_pairs.append({
                    "question": question,
                    "answer": f"{exam_context}\n\n총 수험 기간은 {study_style.get('총 수험기간', '')}입니다.",
                    "category": "study_period",
                    "exam_info": exam_info
                })

        # 학습 시간 관련 질문
        if study_style.get("평균 학습 시간"):
            for template in self.question_templates["study_hours"]:
                qa_pairs.append({
                    "question": template,
                    "answer": f"{exam_context}\n\n평균적으로 하루에 {study_style.get('평균 학습 시간', '')} 정도 공부했습니다.",
                    "category": "study_hours",
                    "exam_info": exam_info
                })

        # 하루 학습 계획 관련 질문
        if daily_plan:
            for template in self.question_templates["daily_plan"]:
                qa_pairs.append({
                    "question": template,
                    "answer": f"{exam_context}\n\n{daily_plan}",
                    "category": "daily_plan",
                    "exam_info": exam_info
                })

        # 과목별 학습법 관련 질문
        if subject_methods:
            subjects = exam_info.get("subjects", [])
            if isinstance(subjects, str):
                subjects = [subjects]

            for subject in subjects:
                if subject and subject in subject_methods:
                    # 기본 과목별 학습법 질문
                    for template in self.question_templates["subject_method"]:
                        question = template.format(
                            subject=subject,
                            job_series=job_series or "공무원",
                            exam_type=exam_type or "",
                            grade=grade or ""
                        )
                        qa_pairs.append({
                            "question": question,
                            "answer": f"{exam_context}\n\n{subject} 과목의 경우, {subject_methods[subject]}",
                            "category": "subject_method",
                            "exam_info": exam_info
                        })

                    # 세부 영역별 질문 (예: 국어의 논리/추론)
                    if subject in self.subject_detail_areas:
                        detail_areas = self.subject_detail_areas[subject]
                        for detail_area in detail_areas:
                            # subject_methods에서 해당 영역 관련 내용이 있는지 확인
                            method_text = subject_methods.get(subject, "")
                            if detail_area.lower() in method_text.lower() or "논리" in method_text or "추론" in method_text:
                                for template in self.question_templates["subject_method_detail"]:
                                    question = template.format(
                                        subject=subject,
                                        detail_area=detail_area,
                                        job_series=job_series or "공무원",
                                        exam_type=exam_type or "",
                                        grade=grade or ""
                                    )
                                    # 세부 영역에 맞는 답변 생성
                                    answer = f"{exam_context}\n\n{subject} 과목의 {detail_area} 영역은 다음과 같이 공부하시면 됩니다. {method_text}"
                                    qa_pairs.append({
                                        "question": question,
                                        "answer": answer,
                                        "category": "subject_method_detail",
                                        "exam_info": exam_info
                                    })

        # 어려웠던 점 관련 질문
        if difficulties:
            for template in self.question_templates["difficulties"]:
                qa_pairs.append({
                    "question": template,
                    "answer": f"{exam_context}\n\n{difficulties}",
                    "category": "difficulties",
                    "exam_info": exam_info
                })

        # 핵심 포인트 관련 질문
        if key_points:
            for template in self.question_templates["key_points"]:
                qa_pairs.append({
                    "question": template,
                    "answer": f"{exam_context}\n\n{key_points}",
                    "category": "key_points",
                    "exam_info": exam_info
                })

        # 면접 준비 관련 질문
        if interview_prep:
            for template in self.question_templates["interview_prep"]:
                qa_pairs.append({
                    "question": template,
                    "answer": f"{exam_context}\n\n{interview_prep}",
                    "category": "interview_prep",
                    "exam_info": exam_info
                })

        # 종합 조언 질문
        if any([daily_plan, difficulties, key_points]):
            for template in self.question_templates["general_advice"]:
                question = template.format(
                    job_series=job_series or "공무원",
                    exam_type=exam_type or "",
                    grade=grade or ""
                )
                answer_parts = []
                if daily_plan:
                    answer_parts.append(f"하루 학습 계획:\n{daily_plan}")
                if difficulties:
                    answer_parts.append(f"어려웠던 점과 극복 방법:\n{difficulties}")
                if key_points:
                    answer_parts.append(f"핵심 학습 전략:\n{key_points}")

                if answer_parts:
                    qa_pairs.append({
                        "question": question,
                        "answer": f"{exam_context}\n\n" + "\n\n".join(answer_parts),
                        "category": "general_advice",
                        "exam_info": exam_info
                    })

        return qa_pairs

    def _build_exam_context(self, exam_info: Dict[str, Any]) -> str:
        """시험 정보 기반 컨텍스트 생성"""
        parts = []

        if exam_info.get("year"):
            parts.append(f"{exam_info['year']}년")
        if exam_info.get("exam_type"):
            parts.append(exam_info["exam_type"])
        if exam_info.get("grade"):
            parts.append(f"{exam_info['grade']}")
        if exam_info.get("job_series"):
            parts.append(exam_info["job_series"])

        if parts:
            return f"[{', '.join(parts)} 합격 선배의 조언]"
        return "[합격 선배의 조언]"

    def convert_to_exaone_format(
        self,
        qa_pairs: List[Dict[str, Any]],
        format_type: str = "both"
    ) -> List[Dict[str, Any]]:
        """ExaOne 학습용 형식으로 변환

        Args:
            qa_pairs: 질문-답변 쌍 리스트
            format_type: "chat", "instruction", "both" 중 하나

        Returns:
            ExaOne 학습용 데이터 리스트
        """
        exaone_data = []

        for qa in qa_pairs:
            question = qa["question"]
            answer = qa["answer"]
            exam_info = qa.get("exam_info", {})
            category = qa.get("category", "general")

            # Chat 형식 (ExaOne Instruct 모델용)
            if format_type in ["chat", "both"]:
                exaone_data.append({
                    "messages": [
                        {
                            "role": "user",
                            "content": question
                        },
                        {
                            "role": "assistant",
                            "content": answer
                        }
                    ],
                    "category": category,
                    "exam_info": exam_info
                })

            # Instruction 형식 (SFT 학습용)
            if format_type in ["instruction", "both"]:
                # instruction 형식으로 변환
                # 질문이 이미 instruction 형태인 경우 그대로 사용
                instruction = question
                input_text = ""

                # 과목별 세부 질문인 경우 instruction 형식으로 변환
                if category == "subject_method_detail":
                    # 예: "보호직 9급 공무원 시험을 준비하는데, 국어 과목의 논리/추론 영역 공부법을 알려줘."
                    job_series = exam_info.get("job_series", "")
                    grade = exam_info.get("grade", "")
                    subjects = exam_info.get("subjects", [])
                    if isinstance(subjects, str):
                        subjects = [subjects]

                    # 질문에서 과목과 영역 추출 시도
                    for subject in subjects:
                        if subject in question:
                            # 이미 instruction 형식이면 그대로 사용
                            instruction = question
                            break

                exaone_data.append({
                    "instruction": instruction,
                    "input": input_text,
                    "output": answer,
                    "category": category,
                    "exam_info": exam_info
                })

        return exaone_data

    def save_to_csv(self, qa_pairs: List[Dict[str, Any]], filename: str = "advice_dataset.csv"):
        """CSV 파일로 저장"""
        output_path = self.output_dir / filename

        fieldnames = [
            "id", "question", "answer", "category",
            "year", "exam_type", "grade", "job_series", "subjects"
        ]

        rows = []
        for idx, qa in enumerate(qa_pairs, 1):
            exam_info = qa.get("exam_info", {})
            subjects = exam_info.get("subjects", [])
            if isinstance(subjects, list):
                subjects = ", ".join(subjects)

            row = {
                "id": idx,
                "question": qa["question"],
                "answer": qa["answer"],
                "category": qa.get("category", ""),
                "year": exam_info.get("year", ""),
                "exam_type": exam_info.get("exam_type", ""),
                "grade": exam_info.get("grade", ""),
                "job_series": exam_info.get("job_series", ""),
                "subjects": subjects
            }
            rows.append(row)

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"CSV 저장 완료: {output_path} ({len(rows)}개)")

    def save_to_jsonl(
        self,
        exaone_data: List[Dict[str, Any]],
        filename: str = "advice_dataset.jsonl",
        format_type: str = "both"
    ):
        """JSONL 파일로 저장 (ExaOne 학습용)

        Args:
            exaone_data: ExaOne 형식 데이터
            filename: 저장할 파일명
            format_type: "chat", "instruction", "both"
        """
        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            for item in exaone_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        logger.info(f"JSONL 저장 완료: {output_path} ({len(exaone_data)}개)")

        # 형식별로 분리 저장
        if format_type == "both":
            chat_data = [item for item in exaone_data if "messages" in item]
            instruction_data = [item for item in exaone_data if "instruction" in item]

            if chat_data:
                chat_path = self.output_dir / "advice_dataset_chat.jsonl"
                with open(chat_path, 'w', encoding='utf-8') as f:
                    for item in chat_data:
                        f.write(json.dumps(item, ensure_ascii=False) + '\n')
                logger.info(f"Chat 형식 JSONL 저장 완료: {chat_path} ({len(chat_data)}개)")

            if instruction_data:
                instruction_path = self.output_dir / "advice_dataset_instruction.jsonl"
                with open(instruction_path, 'w', encoding='utf-8') as f:
                    for item in instruction_data:
                        f.write(json.dumps(item, ensure_ascii=False) + '\n')
                logger.info(f"Instruction 형식 JSONL 저장 완료: {instruction_path} ({len(instruction_data)}개)")

    def generate(self, format_type: str = "both"):
        """데이터셋 생성 메인 함수

        Args:
            format_type: "chat", "instruction", "both" 중 하나
        """
        stories = self.load_stories()

        all_qa_pairs = []
        for story in stories:
            qa_pairs = self.generate_qa_pairs(story)
            all_qa_pairs.extend(qa_pairs)

        logger.info(f"생성된 질문-답변 쌍: {len(all_qa_pairs)}개")

        # 카테고리별 통계
        category_counts = {}
        for qa in all_qa_pairs:
            category = qa.get("category", "unknown")
            category_counts[category] = category_counts.get(category, 0) + 1

        logger.info("카테고리별 분포:")
        for category, count in category_counts.items():
            logger.info(f"  {category}: {count}개")

        # CSV 저장
        self.save_to_csv(all_qa_pairs)

        # ExaOne 형식으로 변환 및 JSONL 저장
        exaone_data = self.convert_to_exaone_format(all_qa_pairs, format_type=format_type)
        self.save_to_jsonl(exaone_data, format_type=format_type)

        return all_qa_pairs, exaone_data


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="합격수기 기반 학습 상담 데이터셋 생성")
    parser.add_argument("--input", type=str, required=True, help="합격수기 JSON/JSONL 파일 경로")
    parser.add_argument("--output-dir", type=str, default="data/success_stories", help="출력 디렉토리")
    parser.add_argument("--format", type=str, choices=["chat", "instruction", "both"], default="both",
                       help="출력 형식: chat (messages), instruction (instruction/input/output), both (둘 다)")

    args = parser.parse_args()

    generator = AdviceDatasetGenerator(args.input, args.output_dir)
    generator.generate(format_type=args.format)

    logger.info("데이터셋 생성 완료!")


if __name__ == "__main__":
    main()

