#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
합격수기 데이터 크롤링 스크립트

합격수기 웹사이트에서 데이터를 크롤링하여 구조화된 형태로 저장합니다.
"""

import json
import re
import csv
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SuccessStoryCrawler:
    """합격수기 크롤러"""

    def __init__(self, output_dir: str = "data/success_stories"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _parse_table(self, table) -> Dict[str, str]:
        """HTML 테이블을 딕셔너리로 파싱"""
        result = {}
        if not table:
            return result

        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key and value:
                    result[key] = value
        return result

    def parse_story_content(self, html_content: str) -> Dict[str, Any]:
        """합격수기 HTML을 파싱하여 구조화된 데이터로 변환

        Args:
            html_content: HTML 콘텐츠

        Returns:
            구조화된 합격수기 데이터
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        story_data = {
            "exam_info": {},
            "study_style": {},
            "daily_plan": "",
            "subject_methods": {},
            "interview_prep": "",
            "difficulties": "",
            "key_points": "",
            "raw_text": ""
        }

        # 테이블 기반 파싱 시도 (공단기 페이지 구조)
        tables = soup.find_all('table')

        # 첫 번째 테이블: 합격 선배의 시험 정보
        if len(tables) > 0:
            exam_info_table = self._parse_table(tables[0])
            if exam_info_table:
                # 최종합격에서 정보 추출
                final_pass = exam_info_table.get("최종합격", "")
                if final_pass:
                    # "2025 국가직 9급 보호" 형식에서 추출
                    year_match = re.search(r"(\d{4})", final_pass)
                    if year_match:
                        story_data["exam_info"]["year"] = year_match.group(1)

                    exam_type_match = re.search(r"(국가직|지방직|서울시|경기도|인천시|부산시|대구시|광주시|대전시|울산시|세종시)", final_pass)
                    if exam_type_match:
                        story_data["exam_info"]["exam_type"] = exam_type_match.group(1)

                    grade_match = re.search(r"(\d)\s*급", final_pass)
                    if grade_match:
                        story_data["exam_info"]["grade"] = grade_match.group(1)

                    job_series_match = re.search(r"(보호|일반행정|교육행정|소방|경찰|세무|회계|관세|통계|기계|전기|화학|농업|임업|수산|환경|건축|토목|도시계획|조경|정보보호|정보통신|전산|방송통신)", final_pass)
                    if job_series_match:
                        job = job_series_match.group(1)
                        if job == "보호":
                            story_data["exam_info"]["job_series"] = "보호직"
                        elif job == "일반행정":
                            story_data["exam_info"]["job_series"] = "일반행정직"
                        elif job == "교육행정":
                            story_data["exam_info"]["job_series"] = "교육행정직"
                        else:
                            story_data["exam_info"]["job_series"] = job + "직"

                # 응시과목 추출
                subjects_text = exam_info_table.get("응시과목", "")
                if subjects_text:
                    subjects = [s.strip() for s in subjects_text.split(',')]
                    story_data["exam_info"]["subjects"] = subjects

                # 총 수험기간
                study_period = exam_info_table.get("총 수험기간", "")
                if study_period:
                    story_data["exam_info"]["총 수험기간"] = study_period

                # 시험 응시 횟수
                exam_count = exam_info_table.get("시험 응시 횟수", "")
                if exam_count:
                    story_data["exam_info"]["시험 응시 횟수"] = exam_count

        # 두 번째 테이블: 합격 선배의 공부 스타일 및 합격수기
        if len(tables) > 1:
            study_style_table = self._parse_table(tables[1])
            if study_style_table:
                # 하루 학습 계획은 별도 필드로 분리
                daily_plan_key = None
                for key in study_style_table.keys():
                    if "하루 학습 계획" in key or "생활 패턴" in key:
                        daily_plan_key = key
                        break

                if daily_plan_key:
                    story_data["daily_plan"] = study_style_table.pop(daily_plan_key, "")

                # 과목별 학습법은 별도 필드로 분리
                subject_method_key = None
                for key in study_style_table.keys():
                    if "과목별 학습법" in key or "수강 강사" in key:
                        subject_method_key = key
                        break

                if subject_method_key:
                    subject_method_text = study_style_table.pop(subject_method_key, "")
                    # 과목별로 분리 시도
                    subjects = story_data["exam_info"].get("subjects", [])
                    if isinstance(subjects, list) and subjects and subject_method_text:
                        subject_methods_dict = {}
                        # 각 과목별로 텍스트 분리
                        remaining_text = subject_method_text
                        for i, subject in enumerate(subjects):
                            if subject in remaining_text:
                                # 해당 과목 부분 찾기
                                idx = remaining_text.find(subject)
                                if idx >= 0:
                                    # 과목명부터 시작하는 부분 추출
                                    subject_part = remaining_text[idx:]

                                    # 다음 과목명이나 섹션 끝까지
                                    next_subject_idx = len(subject_part)
                                    for other_subject in subjects:
                                        if other_subject != subject:
                                            other_idx = subject_part.find(other_subject, len(subject))
                                            if other_idx > 0 and other_idx < next_subject_idx:
                                                next_subject_idx = other_idx

                                    # 면접, 어려웠던 점 등의 키워드로도 구분
                                    stop_keywords = ["면접", "수험생활중", "어려웠던 점", "합격으로 이끈"]
                                    for keyword in stop_keywords:
                                        keyword_idx = subject_part.find(keyword, len(subject))
                                        if keyword_idx > 0 and keyword_idx < next_subject_idx:
                                            next_subject_idx = keyword_idx

                                    subject_text = subject_part[:next_subject_idx].strip()
                                    if subject_text:
                                        subject_methods_dict[subject] = subject_text

                                    # 다음 과목을 위해 남은 텍스트 업데이트
                                    remaining_text = remaining_text[idx + next_subject_idx:]

                        if subject_methods_dict:
                            story_data["subject_methods"] = subject_methods_dict
                        else:
                            # 분리 실패 시 전체 텍스트 저장
                            story_data["subject_methods"] = {"전체": subject_method_text}
                    else:
                        story_data["subject_methods"] = {"전체": subject_method_text} if subject_method_text else {}

                # 면접 준비과정 분리
                interview_key = None
                for key in study_style_table.keys():
                    if "면접" in key:
                        interview_key = key
                        break

                if interview_key:
                    interview_text = study_style_table.pop(interview_key, "")
                    # 면접 텍스트에서 다른 섹션 내용 제거
                    # "수험생활중", "어려웠던 점", "합격으로 이끈" 등이 포함되면 그 앞까지만
                    stop_keywords = ["수험생활중", "어려웠던 점", "합격으로 이끈", "학습 전략", "KEY POINT"]
                    for keyword in stop_keywords:
                        if keyword in interview_text:
                            interview_text = interview_text.split(keyword)[0].strip()
                            break
                    story_data["interview_prep"] = interview_text

                # 어려웠던 점 분리
                difficulties_key = None
                for key in study_style_table.keys():
                    if "어려웠던 점" in key or "극복방법" in key:
                        difficulties_key = key
                        break

                if difficulties_key:
                    story_data["difficulties"] = study_style_table.pop(difficulties_key, "")

                # 핵심 포인트 분리
                key_points_key = None
                for key in study_style_table.keys():
                    if "학습 전략" in key or "KEY POINT" in key or "핵심" in key:
                        key_points_key = key
                        break

                if key_points_key:
                    story_data["key_points"] = study_style_table.pop(key_points_key, "")

                # 나머지는 study_style에 저장
                story_data["study_style"] = study_style_table

        # 시험 정보 추출 (패턴 기반, 테이블에서 못 찾은 경우)
        exam_info_patterns = {
            "year": r"(\d{4})\s*년",
            "exam_type": r"(국가직|지방직|서울시|경기도|인천시|부산시|대구시|광주시|대전시|울산시|세종시)",
            "grade": r"(\d)\s*급",
            "job_series": r"([가-힣]+행정직|일반행정직|교육행정직|보호직|소방직|경찰직|세무직|회계직|관세직|통계직|기계직|전기직|화학직|농업직|임업직|수산직|환경직|건축직|토목직|도시계획직|조경직|정보보호직|정보통신직|전산직|방송통신직)",
            "subjects": r"(국어|영어|한국사|행정법총론|행정학개론|회계학|경제학|세법|관세법|통계학|기계일반|전기일반|화학일반|농업일반|임업일반|수산일반|환경일반|건축일반|토목일반|도시계획|조경|정보보호|정보통신|전산일반|방송통신|교육학개론|사회복지학개론|형사정책개론|형법|형사소송법|민법|상법|노동법|지방세법|국제법|국제경제법|국제관계법|국제정치학|국제경제학|국제통상학|국제개발학|국제협력학)"
        }

        text = soup.get_text(separator='\n', strip=True)
        story_data["raw_text"] = text

        # 테이블에서 못 찾은 정보는 패턴으로 추출
        for key, pattern in exam_info_patterns.items():
            if key not in story_data["exam_info"] or not story_data["exam_info"].get(key):
                match = re.search(pattern, text)
                if match:
                    if key == "subjects":
                        subjects = re.findall(pattern, text)
                        story_data["exam_info"][key] = list(set(subjects))
                    else:
                        story_data["exam_info"][key] = match.group(1) if match.groups() else match.group(0)

        # 시험 정보 추출
        for key, pattern in exam_info_patterns.items():
            match = re.search(pattern, text)
            if match:
                if key == "subjects":
                    # 과목은 여러 개일 수 있음
                    subjects = re.findall(pattern, text)
                    story_data["exam_info"][key] = list(set(subjects))
                else:
                    story_data["exam_info"][key] = match.group(1) if match.groups() else match.group(0)

        # 텍스트 기반 섹션 추출 (테이블에서 못 찾은 경우)
        # 이미 테이블에서 추출한 섹션은 건너뛰기
        if not story_data.get("daily_plan") or not story_data.get("subject_methods") or not story_data.get("interview_prep") or not story_data.get("difficulties") or not story_data.get("key_points"):
            sections = {
                "하루 학습 계획 및생활 패턴": "daily_plan",
                "하루 학습 계획 및 생활 패턴": "daily_plan",
                "과목별 학습법 &수강 강사 및 활용 교재": "subject_methods",
                "과목별 학습법": "subject_methods",
                "면접 준비과정": "interview_prep",
                "수험생활중 어려웠던 점과극복방법": "difficulties",
                "수험생활중 어려웠던 점과 극복방법": "difficulties",
                "합격으로 이끈 나만의 학습 전략 KEY POINT": "key_points",
                "합격으로 이끈 나만의 학습 전략": "key_points"
            }

            lines = text.split('\n')
            current_section = None
            current_content = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 섹션 헤더 확인
                section_found = False
                for section_name, section_key in sections.items():
                    if section_name in line:
                        # 이미 해당 섹션이 채워져 있으면 건너뛰기
                        if story_data.get(section_key):
                            continue

                        # 이전 섹션 저장
                        if current_section and current_content:
                            content_text = '\n'.join(current_content)
                            # 섹션 구분자 제거
                            for stop_keyword in ["면접", "수험생활중", "어려웠던 점", "합격으로 이끈", "학습 전략"]:
                                if stop_keyword in content_text and current_section != section_key:
                                    content_text = content_text.split(stop_keyword)[0].strip()
                                    break

                            if current_section == "subject_methods":
                                story_data[current_section] = self._parse_section_dict(content_text)
                            else:
                                story_data[current_section] = content_text

                        current_section = section_key
                        current_content = []
                        section_found = True
                        break

                if not section_found:
                    if current_section:
                        # 섹션 종료 키워드 확인
                        stop_keywords = {
                            "interview_prep": ["수험생활중", "어려웠던 점", "합격으로 이끈"],
                            "difficulties": ["합격으로 이끈", "학습 전략"],
                            "key_points": ["목록", "TOP", "프리패스"]
                        }
                        should_stop = False
                        if current_section in stop_keywords:
                            for keyword in stop_keywords[current_section]:
                                if keyword in line:
                                    should_stop = True
                                    break

                        if not should_stop:
                            current_content.append(line)
                        else:
                            # 현재 섹션 저장하고 종료
                            content_text = '\n'.join(current_content)
                            if current_section == "subject_methods":
                                story_data[current_section] = self._parse_section_dict(content_text)
                            else:
                                story_data[current_section] = content_text
                            current_section = None
                            current_content = []

            # 마지막 섹션 저장
            if current_section and current_content:
                content_text = '\n'.join(current_content)
                # 섹션 구분자 제거
                for stop_keyword in ["목록", "TOP", "프리패스"]:
                    if stop_keyword in content_text:
                        content_text = content_text.split(stop_keyword)[0].strip()
                        break

                if current_section == "subject_methods":
                    story_data[current_section] = self._parse_section_dict(content_text)
                else:
                    story_data[current_section] = content_text

        # 과목별 학습법에서 과목명 추출
        if story_data.get("subject_methods") and isinstance(story_data["subject_methods"], str):
            # 과목명으로 분리 시도
            subject_text = story_data["subject_methods"]
            subjects = story_data["exam_info"].get("subjects", [])
            if isinstance(subjects, list) and subjects:
                subject_methods_dict = {}
                for subject in subjects:
                    # 과목명이 포함된 문단 찾기
                    pattern = rf"{subject}[^가-힣]*?([가-힣\s]+(?:선생님|강의|교재|수강|학습)[^가-힣]*?)(?={subjects[0] if subjects else ''}|$)"
                    match = re.search(pattern, subject_text, re.DOTALL)
                    if match:
                        subject_methods_dict[subject] = match.group(1).strip()
                    else:
                        # 간단하게 과목명 다음 문장 찾기
                        parts = subject_text.split(subject)
                        if len(parts) > 1:
                            next_part = parts[1].strip()
                            # 다음 과목명이나 섹션 끝까지
                            for other_subject in subjects:
                                if other_subject != subject and other_subject in next_part:
                                    next_part = next_part.split(other_subject)[0]
                                    break
                            if next_part:
                                subject_methods_dict[subject] = next_part[:500]  # 최대 500자

                if subject_methods_dict:
                    story_data["subject_methods"] = subject_methods_dict

        return story_data

    def _parse_section_dict(self, text: str) -> Dict[str, Any]:
        """섹션 텍스트를 딕셔너리로 파싱"""
        result = {}
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if ':' in line or '：' in line:
                parts = re.split(r'[:：]', line, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    result[key] = value

        return result

    def crawl_from_url(self, url: str) -> Optional[Dict[str, Any]]:
        """URL에서 합격수기 데이터 크롤링

        Args:
            url: 크롤링할 URL

        Returns:
            구조화된 합격수기 데이터 또는 None
        """
        try:
            logger.info(f"크롤링 시작: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            story_data = self.parse_story_content(response.text)
            story_data["source_url"] = url
            story_data["crawled_at"] = datetime.now().isoformat()

            return story_data

        except Exception as e:
            logger.error(f"크롤링 실패 ({url}): {e}")
            return None

    def crawl_from_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """파일에서 합격수기 데이터 크롤링 (로컬 HTML 파일)

        Args:
            file_path: HTML 파일 경로

        Returns:
            구조화된 합격수기 데이터 또는 None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            story_data = self.parse_story_content(html_content)
            story_data["source_file"] = file_path
            story_data["crawled_at"] = datetime.now().isoformat()

            return story_data

        except Exception as e:
            logger.error(f"파일 파싱 실패 ({file_path}): {e}")
            return None

    def save_to_json(self, stories: List[Dict[str, Any]], filename: str = "success_stories.json"):
        """JSON 파일로 저장"""
        output_path = self.output_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stories, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 저장 완료: {output_path} ({len(stories)}개)")

    def save_to_csv(self, stories: List[Dict[str, Any]], filename: str = "success_stories.csv"):
        """CSV 파일로 저장"""
        output_path = self.output_dir / filename

        if not stories:
            logger.warning("저장할 데이터가 없습니다.")
            return

        # CSV 헤더 생성
        fieldnames = [
            "id", "year", "exam_type", "grade", "job_series", "subjects",
            "study_period", "study_hours", "review_count", "book_count",
            "daily_plan", "subject_methods", "interview_prep", "difficulties",
            "key_points", "raw_text", "source_url", "crawled_at"
        ]

        rows = []
        for idx, story in enumerate(stories, 1):
            exam_info = story.get("exam_info", {})
            study_style = story.get("study_style", {})

            row = {
                "id": idx,
                "year": exam_info.get("year", ""),
                "exam_type": exam_info.get("exam_type", ""),
                "grade": exam_info.get("grade", ""),
                "job_series": exam_info.get("job_series", ""),
                "subjects": ", ".join(exam_info.get("subjects", [])) if isinstance(exam_info.get("subjects"), list) else exam_info.get("subjects", ""),
                "study_period": study_style.get("총 수험기간", ""),
                "study_hours": study_style.get("평균 학습 시간", ""),
                "review_count": study_style.get("평균 회독수", ""),
                "book_count": study_style.get("평균 문제집 권수", ""),
                "daily_plan": story.get("daily_plan", ""),
                "subject_methods": json.dumps(story.get("subject_methods", {}), ensure_ascii=False),
                "interview_prep": story.get("interview_prep", ""),
                "difficulties": story.get("difficulties", ""),
                "key_points": story.get("key_points", ""),
                "raw_text": story.get("raw_text", "")[:1000],  # 처음 1000자만
                "source_url": story.get("source_url", ""),
                "crawled_at": story.get("crawled_at", "")
            }
            rows.append(row)

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logger.info(f"CSV 저장 완료: {output_path} ({len(rows)}개)")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="합격수기 데이터 크롤링")
    parser.add_argument("--url", type=str, help="크롤링할 URL")
    parser.add_argument("--file", type=str, help="크롤링할 HTML 파일 경로")
    parser.add_argument("--urls-file", type=str, help="URL 목록이 담긴 파일 (한 줄에 하나씩)")
    parser.add_argument("--output-dir", type=str, default="data/success_stories", help="출력 디렉토리")
    parser.add_argument("--format", type=str, choices=["json", "csv", "both"], default="both", help="저장 형식")

    args = parser.parse_args()

    crawler = SuccessStoryCrawler(output_dir=args.output_dir)
    stories = []

    # 단일 URL 크롤링
    if args.url:
        story = crawler.crawl_from_url(args.url)
        if story:
            stories.append(story)

    # 단일 파일 크롤링
    if args.file:
        story = crawler.crawl_from_file(args.file)
        if story:
            stories.append(story)

    # URL 목록 파일에서 크롤링
    if args.urls_file:
        with open(args.urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        for url in urls:
            story = crawler.crawl_from_url(url)
            if story:
                stories.append(story)
            time.sleep(1)  # 서버 부하 방지

    if not stories:
        logger.warning("크롤링된 데이터가 없습니다.")
        return

    # 저장
    if args.format in ["json", "both"]:
        crawler.save_to_json(stories)

    if args.format in ["csv", "both"]:
        crawler.save_to_csv(stories)

    logger.info(f"총 {len(stories)}개의 합격수기 데이터를 크롤링했습니다.")


if __name__ == "__main__":
    main()

