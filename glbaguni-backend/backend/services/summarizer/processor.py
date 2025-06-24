#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarizer Processor Module
요약 후처리 및 결과 처리
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from backend.models import Article, ArticleSummary
    from backend.services.summarizer.client import SummarizerClient
    from backend.services.summarizer.prompts import SummarizerPrompts
except ImportError:
    from client import SummarizerClient
    from prompts import SummarizerPrompts

    from models import Article, ArticleSummary

logger = logging.getLogger(__name__)


class SummarizerProcessor:
    """요약 후처리 및 결과 관리 클래스"""

    def __init__(self):
        """프로세서 초기화"""
        self.client = SummarizerClient()
        self.processed_count = 0
        self.failed_count = 0

    def process_single_article(
        self,
        article: Article,
        custom_prompt: Optional[str] = None,
        language: str = "ko",
    ) -> Optional[ArticleSummary]:
        """
        단일 기사를 처리하여 요약을 생성합니다.

        Args:
            article: 요약할 기사 객체
            custom_prompt: 사용자 정의 프롬프트
            language: 대상 언어

        Returns:
            요약된 기사 객체 또는 None
        """
        try:
            logger.info(f"📄 기사 요약 처리 시작: {article.title}")

            # 프롬프트 생성
            messages = SummarizerPrompts.build_article_prompt(
                article.title, article.content, language
            )

            # API 호출
            result = self.client.call_openai_api(messages)

            if not result.get("success"):
                logger.error(f"기사 요약 실패: {result.get('error', 'Unknown error')}")
                self.failed_count += 1
                return None

            # ArticleSummary 객체 생성
            summary_text = result["summary"]
            article_summary = ArticleSummary(
                title=article.title,
                url=article.url,
                summary=summary_text,
                source=article.source,
                original_length=len(article.content),
                summary_length=len(summary_text),
            )

            # 후처리 적용
            article_summary = self.post_process_summary(article_summary, language)

            self.processed_count += 1
            logger.info(f"✅ 기사 요약 완료: {article.title}")

            return article_summary

        except Exception as e:
            logger.error(f"기사 처리 중 오류 ({article.title}): {e}")
            self.failed_count += 1
            return None

    def process_multiple_articles(
        self,
        articles: List[Article],
        custom_prompt: Optional[str] = None,
        language: str = "ko",
        max_articles: Optional[int] = None,
    ) -> List[ArticleSummary]:
        """
        여러 기사를 일괄 처리합니다.

        Args:
            articles: 요약할 기사 리스트
            custom_prompt: 사용자 정의 프롬프트
            language: 대상 언어
            max_articles: 최대 처리할 기사 수

        Returns:
            요약된 기사 리스트
        """
        if max_articles:
            articles = articles[:max_articles]

        logger.info(f"📚 일괄 요약 처리 시작: {len(articles)}개 기사")

        summaries = []
        start_time = datetime.now()

        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"📄 [{i}/{len(articles)}] 처리 중: {article.title}")

                summary = self.process_single_article(article, custom_prompt, language)
                if summary:
                    summaries.append(summary)

            except Exception as e:
                logger.error(f"기사 {i} 처리 실패: {e}")
                continue

        elapsed_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"✅ 일괄 요약 완료 - 성공: {len(summaries)}, 실패: {self.failed_count}, "
            f"소요시간: {elapsed_time:.2f}초"
        )

        return summaries

    def post_process_summary(
        self, summary: ArticleSummary, language: str
    ) -> ArticleSummary:
        """
        요약 결과를 후처리합니다.

        Args:
            summary: 요약 객체
            language: 언어 설정

        Returns:
            후처리된 요약 객체
        """
        # 텍스트 정리
        cleaned_text = self.clean_summary_text(summary.summary, language)

        # 품질 검증
        quality_score = self.calculate_quality_score(summary)

        # 새로운 요약 객체 생성 (기존 객체 업데이트)
        summary.summary = cleaned_text

        # 추가 메타데이터 설정 (필요시)
        if hasattr(summary, "quality_score"):
            summary.quality_score = quality_score

        return summary

    def clean_summary_text(self, text: str, language: str) -> str:
        """
        요약 텍스트를 정리합니다.

        Args:
            text: 원본 텍스트
            language: 언어 설정

        Returns:
            정리된 텍스트
        """
        if not text:
            return ""

        # 기본 정리
        cleaned = text.strip()

        # 연속된 공백 제거
        cleaned = re.sub(r"\s+", " ", cleaned)

        # 불필요한 접두사/접미사 제거
        prefixes_to_remove = [
            "요약:",
            "Summary:",
            "요약 결과:",
            "결과:",
            "Here is a summary:",
            "다음은 요약입니다:",
        ]

        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()

        # 언어별 특수 정리
        if language == "ko":
            cleaned = self.clean_korean_text(cleaned)
        else:
            cleaned = self.clean_english_text(cleaned)

        # 마침표로 끝나도록 보장
        if cleaned and not cleaned.endswith((".", "!", "?")):
            cleaned += "."

        return cleaned

    def clean_korean_text(self, text: str) -> str:
        """한국어 텍스트 특수 정리"""
        # 불필요한 한국어 표현 제거
        unwanted_phrases = [
            "이 기사는",
            "기사에서는",
            "보도에 따르면",
            "해당 내용은",
            "관련하여",
        ]

        for phrase in unwanted_phrases:
            text = text.replace(phrase, "")

        return text.strip()

    def clean_english_text(self, text: str) -> str:
        """영어 텍스트 특수 정리"""
        # 불필요한 영어 표현 제거
        unwanted_phrases = [
            "According to the article",
            "The article states",
            "In this article",
            "The report mentions",
        ]

        for phrase in unwanted_phrases:
            text = text.replace(phrase, "")

        return text.strip()

    def calculate_quality_score(self, summary: ArticleSummary) -> float:
        """
        요약 품질 점수를 계산합니다.

        Args:
            summary: 요약 객체

        Returns:
            품질 점수 (0.0 ~ 1.0)
        """
        score = 0.0

        # 길이 적절성 (0.3)
        ideal_length = 150  # 적정 요약 길이
        length_ratio = min(summary.summary_length / ideal_length, 1.0)
        score += length_ratio * 0.3

        # 압축률 (0.3)
        compression_ratio = summary.summary_length / summary.original_length
        if 0.1 <= compression_ratio <= 0.3:  # 적정 압축률
            score += 0.3
        elif compression_ratio < 0.1:
            score += compression_ratio * 3  # 너무 짧은 경우 감점
        else:
            score += (1 - compression_ratio) * 0.6  # 너무 긴 경우 감점

        # 문장 구조 (0.2)
        sentence_count = len([s for s in summary.summary.split(".") if s.strip()])
        if 3 <= sentence_count <= 5:  # 적정 문장 수
            score += 0.2
        else:
            score += max(0, 0.2 - abs(sentence_count - 4) * 0.05)

        # 특수문자 및 형식 (0.2)
        if summary.summary.endswith((".", "!", "?")):
            score += 0.1
        if not re.search(r"[^\w\s가-힣.,!?()-]", summary.summary):
            score += 0.1

        return min(score, 1.0)

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        처리 통계를 반환합니다.

        Returns:
            처리 통계 딕셔너리
        """
        total_processed = self.processed_count + self.failed_count
        success_rate = (
            self.processed_count / total_processed if total_processed > 0 else 0
        )

        return {
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "total_count": total_processed,
            "success_rate": round(success_rate * 100, 2),
            "client_stats": self.client.get_usage_stats(),
        }

    def reset_stats(self):
        """통계를 초기화합니다."""
        self.processed_count = 0
        self.failed_count = 0
        self.client.reset_stats()
        logger.info("📊 처리 통계 초기화 완료")
