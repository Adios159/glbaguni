#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS Service
RSS 피드 처리 전용 서비스
"""

import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

import chardet
import feedparser
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

try:
    from ..models import Article
    from .content_extractor import ContentExtractor
except ImportError:
    from content_extractor import ContentExtractor

    from models import Article

logger = logging.getLogger(__name__)


class RSSService:
    """RSS 피드 처리 서비스"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Glbaguni RSS Bot)",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            }
        )
        self.session.mount("http://", HTTPAdapter(max_retries=3))
        self.session.mount("https://", HTTPAdapter(max_retries=3))
        self.content_extractor = ContentExtractor()

    def fetch_rss_articles(self, rss_url: str, max_articles: int = 10) -> List[Article]:
        """RSS 피드에서 기사 목록을 가져옵니다."""
        try:
            logger.info(f"📡 RSS 피드 가져오기: {rss_url}")

            # RSS 피드 요청 및 인코딩 처리
            response = self.session.get(rss_url, timeout=10)
            response.raise_for_status()

            # 인코딩 감지 및 디코딩
            detected_encoding = chardet.detect(response.content)
            encoding = (
                detected_encoding.get("encoding", "utf-8")
                if detected_encoding
                else "utf-8"
            )
            logger.info(f"🔍 RSS 인코딩: {encoding}")

            try:
                decoded_content = response.content.decode(encoding, errors="ignore")
            except Exception:
                decoded_content = response.content.decode("utf-8", errors="ignore")

            # RSS 파싱
            feed = feedparser.parse(decoded_content)

            return self._process_feed_entries(feed, rss_url, max_articles)

        except Exception as e:
            logger.error(f"❌ RSS 피드 처리 실패 ({rss_url}): {e}")
            return []

    def _process_feed_entries(
        self, feed, rss_url: str, max_articles: int
    ) -> List[Article]:
        """RSS 피드 엔트리들을 처리합니다."""
        if not hasattr(feed, "entries") or not feed.entries:
            logger.warning(f"⚠️ RSS 피드에 엔트리가 없습니다: {rss_url}")
            return []

        articles = []
        source = urlparse(rss_url).netloc or "unknown"

        for entry in feed.entries[:max_articles]:
            try:
                article = self._create_article_from_entry(entry, source)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"엔트리 처리 실패: {e}")
                continue

        logger.info(f"✅ RSS에서 {len(articles)}개 기사 처리 완료")
        return articles

    def _create_article_from_entry(self, entry, source: str) -> Optional[Article]:
        """RSS 엔트리에서 Article 객체를 생성합니다."""
        # 필수 필드 검증
        if not hasattr(entry, "title") or not hasattr(entry, "link"):
            return None

        title = str(entry.title).strip()
        url = str(entry.link)

        if not title or not url.startswith(("http://", "https://")):
            return None

        # 콘텐츠 추출
        content = self.content_extractor.extract_content_from_rss_entry(entry)
        if not content or len(content.strip()) < 50:
            return None

        # 발행일 파싱
        published_date = self._parse_published_date(entry)

        # Article 객체 생성
        return Article(
            title=title,
            url=url,
            content=content,
            published_date=published_date,
            author=getattr(entry, "author", None),
            source=source,
        )

    def _parse_published_date(self, entry) -> Optional[datetime]:
        """RSS 엔트리에서 발행일을 파싱합니다."""
        if not hasattr(entry, "published_parsed") or not entry.published_parsed:
            return None

        try:
            parsed_date = entry.published_parsed
            if isinstance(parsed_date, (list, tuple)) and len(parsed_date) >= 6:
                # time.struct_time을 datetime으로 변환
                date_parts = []
                for i in range(6):
                    if i < len(parsed_date) and parsed_date[i] is not None:
                        try:
                            date_parts.append(int(parsed_date[i]))
                        except (ValueError, TypeError):
                            date_parts.append(0)
                    else:
                        date_parts.append(0)

                return datetime(*date_parts)
        except Exception as e:
            logger.debug(f"발행일 파싱 실패: {e}")
            return None

        return None

    def get_default_rss_feeds(self) -> List[str]:
        """기본 RSS 피드 목록을 반환합니다."""
        return [
            # 주요 뉴스 사이트
            "https://feeds.feedburner.com/yonhapnews_top",  # 연합뉴스
            "https://rss.sbs.co.kr/news/SectionRssFeed.jsp?sectionId=01",  # SBS
            "http://fs.jtbc.joins.com/RSS/newsflash.xml",  # JTBC
            "https://rss.mk.co.kr/rss/30000001.xml",  # 매일경제
            # 기술/IT 뉴스
            "https://feeds.feedburner.com/yonhapnews_it",
            "https://rss.mk.co.kr/rss/50400007.xml",  # 매경 IT
        ]

    def fetch_multiple_rss_feeds(
        self, rss_urls: Optional[List[str]] = None, max_articles_per_feed: int = 5
    ) -> List[Article]:
        """여러 RSS 피드에서 기사를 가져옵니다."""
        if not rss_urls:
            rss_urls = self.get_default_rss_feeds()

        all_articles = []

        for rss_url in rss_urls:
            try:
                articles = self.fetch_rss_articles(rss_url, max_articles_per_feed)
                all_articles.extend(articles)
            except Exception as e:
                logger.warning(f"RSS 피드 처리 실패 ({rss_url}): {e}")
                continue

        logger.info(f"📊 총 {len(all_articles)}개 기사 수집 완료")
        return all_articles
