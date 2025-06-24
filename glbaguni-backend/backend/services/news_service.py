#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
뉴스 서비스 모듈
RSS 수집과 GPT 요약을 통합하는 메인 서비스
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..models.request_schema import SummarizeRequest, TextSummarizeRequest
from ..models.response_schema import Article, Summary
from ..utils import ContextLogger, get_logger
from .gpt_service import GPTService
from .rss_service import RSSService

logger = get_logger("services.news")


class NewsService:
    """
    뉴스 종합 서비스
    RSS 수집과 GPT 요약을 통합
    """

    def __init__(self):
        """뉴스 서비스 초기화"""
        self.settings = get_settings()
        self.rss_service = RSSService()
        self.gpt_service = GPTService()

        logger.info("✅ 뉴스 서비스 초기화 완료")

    async def process_summarize_request(
        self, request: SummarizeRequest
    ) -> Dict[str, Any]:
        """
        뉴스 요약 요청 처리

        Args:
            request: 요약 요청 데이터

        Returns:
            처리 결과 딕셔너리
        """

        with ContextLogger("뉴스 요약 요청 처리", "news.summarize"):
            try:
                # 1. RSS 피드 수집
                articles, source_stats = await self.rss_service.fetch_rss_feeds(
                    rss_urls=request.rss_urls,
                    max_articles_per_source=request.max_articles,
                    filter_keywords=request.filter_keywords,
                    exclude_keywords=request.exclude_keywords,
                )

                if not articles:
                    return {
                        "success": False,
                        "message": "수집된 기사가 없습니다",
                        "total_articles": 0,
                        "processed_articles": 0,
                        "failed_articles": 0,
                        "sources": source_stats,
                    }

                # 2. GPT 요약 생성
                summary = await self.gpt_service.summarize_articles(
                    articles=[article.dict() for article in articles],
                    style=request.summary_style,
                    max_length=self.settings.summary_max_length,
                    language=request.language,
                )

                # 3. 결과 구성
                result = {
                    "success": True,
                    "message": "뉴스 요약이 완료되었습니다",
                    "total_articles": len(articles),
                    "processed_articles": len(articles),
                    "failed_articles": 0,
                    "summary": summary.dict(),
                    "articles": [
                        {
                            "title": article.title,
                            "url": article.url,
                            "source": article.source,
                            "published_at": (
                                article.published_at.isoformat()
                                if article.published_at
                                else None
                            ),
                        }
                        for article in articles[:10]  # 최대 10개만 반환
                    ],
                    "sources": source_stats,
                    "generated_at": datetime.now().isoformat(),
                }

                logger.info(
                    f"✅ 뉴스 요약 완료 - {len(articles)}개 기사 → {summary.summary_length}자 요약"
                )

                return result

            except Exception as e:
                logger.error(f"❌ 뉴스 요약 실패: {str(e)}")
                raise

    async def process_text_summarize_request(
        self, request: TextSummarizeRequest
    ) -> Summary:
        """
        텍스트 직접 요약 요청 처리

        Args:
            request: 텍스트 요약 요청

        Returns:
            요약 결과
        """

        with ContextLogger("텍스트 요약 처리", "news.text_summarize"):
            return await self.gpt_service.summarize_text(
                text=request.text,
                style=request.summary_style,
                max_length=request.summary_length,
                language=request.language,
                focus_keywords=request.focus_keywords,
            )

    async def search_news(
        self, query: str, max_results: int = 20, sources: Optional[List[str]] = None
    ) -> List[Article]:
        """
        뉴스 검색
        NewsAggregator를 사용하여 실제 뉴스 검색 수행

        Args:
            query: 검색 쿼리
            max_results: 최대 결과 수
            sources: 검색할 소스 목록

        Returns:
            검색된 기사 목록
        """

        logger.info(f"🔍 뉴스 검색: {query}")

        try:
            # NewsAggregator 임포트 및 사용
            from ..news_aggregator import NewsAggregator
            from ..config import get_settings
            
            settings = get_settings()
            openai_api_key = getattr(settings, 'openai_api_key', None)
            
            # NewsAggregator 인스턴스 생성
            news_aggregator = NewsAggregator(openai_api_key=openai_api_key)
            
            # 뉴스 검색 실행
            logger.info(f"🔄 NewsAggregator를 사용하여 뉴스 검색 중...")
            news_articles, keywords = news_aggregator.process_news_query(
                query=query, 
                max_articles=min(max_results, 20)
            )
            
            # NewsArticle을 Article 형태로 변환
            result_articles = []
            for news_article in news_articles:
                article = Article(
                    title=news_article.title,
                    url=news_article.link,
                    content=news_article.content or news_article.summary,
                    source=news_article.source,
                    published_at=datetime.now()  # published_date 파싱은 별도 구현 필요
                )
                result_articles.append(article)
            
            logger.info(f"✅ 뉴스 검색 완료: {len(result_articles)}개 기사 발견")
            logger.info(f"🏷️ 추출된 키워드: {keywords}")
            
            return result_articles
            
        except Exception as e:
            logger.error(f"❌ 뉴스 검색 실패: {str(e)}")
            # 오류 발생시 빈 리스트 반환 (서비스 중단 방지)
            return []

    async def get_recommendations(
        self, user_interests: List[str], max_recommendations: int = 15
    ) -> List[Article]:
        """
        개인화된 뉴스 추천

        Args:
            user_interests: 사용자 관심사
            max_recommendations: 최대 추천 수

        Returns:
            추천 기사 목록
        """

        logger.info(f"💡 뉴스 추천: {user_interests}")

        # 임시 구현 - 실제로는 추천 알고리즘 적용
        return []

    def get_service_stats(self) -> Dict[str, Any]:
        """통합 서비스 통계"""
        return {
            "rss_stats": self.rss_service.get_stats(),
            "gpt_stats": self.gpt_service.get_usage_stats(),
        }
