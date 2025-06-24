#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
News Collector Module
뉴스 수집 로직 (200줄 이하)
"""

import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

import chardet
import feedparser
import requests
from requests.adapters import HTTPAdapter

try:
    from ...models import Article
except ImportError:
    from models import Article

logger = logging.getLogger(__name__)


class NewsCollector:
    """뉴스 수집 전담 클래스"""

    def __init__(self):
        """수집기 초기화"""
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

        logger.info("NewsCollector 초기화 완료")

    def fetch_rss_feed(
        self, rss_url: str, timeout: int = 10
    ) -> Optional[feedparser.FeedParserDict]:
        """
        RSS 피드를 가져옵니다.

        Args:
            rss_url: RSS 피드 URL
            timeout: 타임아웃 (초)

        Returns:
            파싱된 RSS 피드 또는 None
        """
        try:
            logger.info(f"📡 RSS 피드 요청: {rss_url}")

            # HTTP 요청으로 RSS 가져오기
            response = self.session.get(rss_url, timeout=timeout)
            response.raise_for_status()

            # 인코딩 감지 및 디코딩
            encoding = self._detect_encoding(response)
            decoded_content = self._decode_content(response.content, encoding)

            # RSS 파싱
            feed = feedparser.parse(decoded_content)

            # 파싱 결과 검증
            if not hasattr(feed, "entries") or not feed.entries:
                logger.warning(f"⚠️ RSS 피드에 엔트리가 없습니다: {rss_url}")
                return None

            logger.info(f"✅ RSS 피드 파싱 완료: {len(feed.entries)}개 엔트리")
            return feed

        except requests.RequestException as e:
            logger.error(f"❌ RSS 피드 요청 실패 ({rss_url}): {e}")
            return None
        except Exception as e:
            logger.error(f"❌ RSS 피드 처리 실패 ({rss_url}): {e}")
            return None

    def fetch_multiple_feeds(
        self, rss_urls: List[str], max_articles_per_feed: int = 10
    ) -> List[Article]:
        """
        여러 RSS 피드에서 기사를 수집합니다.

        Args:
            rss_urls: RSS URL 리스트
            max_articles_per_feed: 피드당 최대 기사 수

        Returns:
            수집된 기사 리스트
        """
        all_articles = []

        logger.info(f"📚 다중 RSS 피드 수집 시작: {len(rss_urls)}개 피드")

        for i, rss_url in enumerate(rss_urls, 1):
            try:
                logger.info(f"📄 [{i}/{len(rss_urls)}] 처리 중: {rss_url}")

                # RSS 피드 가져오기
                feed = self.fetch_rss_feed(rss_url)
                if not feed:
                    continue

                # 기사 변환
                articles = self._convert_feed_to_articles(
                    feed, rss_url, max_articles_per_feed
                )
                all_articles.extend(articles)

                logger.info(
                    f"✅ [{i}/{len(rss_urls)}] 완료: {len(articles)}개 기사 수집"
                )

            except Exception as e:
                logger.error(f"❌ RSS 피드 처리 실패 ({rss_url}): {e}")
                continue

        logger.info(f"🎉 다중 RSS 수집 완료: 총 {len(all_articles)}개 기사")
        return all_articles

    def _detect_encoding(self, response: requests.Response) -> str:
        """응답의 문자 인코딩을 감지합니다."""
        # Content-Type 헤더에서 charset 확인
        content_type = response.headers.get("content-type", "").lower()
        if "charset=" in content_type:
            charset = content_type.split("charset=")[1].split(";")[0].strip()
            logger.debug(f"🔍 헤더 인코딩: {charset}")
            return charset

        # chardet으로 감지
        detected = chardet.detect(response.content)
        encoding = detected.get("encoding", "utf-8") if detected else "utf-8"
        confidence = detected.get("confidence", 0) if detected else 0

        logger.debug(f"🔍 감지된 인코딩: {encoding} (신뢰도: {confidence:.2f})")

        # 한국어 사이트를 위한 기본값
        if confidence < 0.7:
            return "utf-8"

        return encoding

    def _decode_content(self, content: bytes, encoding: str) -> str:
        """바이트 콘텐츠를 문자열로 디코딩합니다."""
        try:
            return content.decode(encoding, errors="ignore")
        except (UnicodeDecodeError, LookupError):
            logger.warning(f"⚠️ {encoding} 디코딩 실패, UTF-8로 대체")
            return content.decode("utf-8", errors="ignore")

    def _convert_feed_to_articles(
        self, feed: feedparser.FeedParserDict, source_url: str, max_articles: int
    ) -> List[Article]:
        """RSS 피드 엔트리를 Article 객체로 변환합니다."""
        articles = []
        source = urlparse(source_url).netloc or "unknown"

        for entry in feed.entries[:max_articles]:
            try:
                article = self._create_article_from_entry(entry, source)
                if article:
                    articles.append(article)
            except Exception as e:
                logger.debug(f"엔트리 변환 실패: {e}")
                continue

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
        content = self._extract_content_from_entry(entry)
        if not content or len(content.strip()) < 50:
            return None

        # 발행일 파싱
        published_date = self._parse_published_date(entry)

        return Article(
            title=title,
            url=url,
            content=content,
            published_date=published_date,
            author=getattr(entry, "author", None),
            source=source,
        )

    def _extract_content_from_entry(self, entry) -> str:
        """RSS 엔트리에서 콘텐츠를 추출합니다."""
        # RSS 필드 우선순위 순서로 확인
        content_fields = ["content", "summary", "description"]

        for field in content_fields:
            if hasattr(entry, field):
                field_content = getattr(entry, field)

                if isinstance(field_content, list) and field_content:
                    field_content = field_content[0]

                if isinstance(field_content, dict):
                    field_content = field_content.get("value", "") or field_content.get(
                        "content", ""
                    )

                if isinstance(field_content, str) and field_content.strip():
                    return self._clean_html_content(field_content)

        return ""

    def _clean_html_content(self, content: str) -> str:
        """HTML 콘텐츠를 정리합니다."""
        if not content:
            return ""

        # HTML 태그 제거 (간단한 방식)
        import re

        clean_content = re.sub(r"<[^>]+>", "", content)

        # HTML 엔티티 정리
        clean_content = clean_content.replace("&nbsp;", " ")
        clean_content = clean_content.replace("&amp;", "&")
        clean_content = clean_content.replace("&lt;", "<")
        clean_content = clean_content.replace("&gt;", ">")
        clean_content = clean_content.replace("&quot;", '"')

        # 연속된 공백 정리
        clean_content = re.sub(r"\s+", " ", clean_content)

        return clean_content.strip()

    def _parse_published_date(self, entry) -> Optional[datetime]:
        """RSS 엔트리에서 발행일을 파싱합니다."""
        if not hasattr(entry, "published_parsed") or not entry.published_parsed:
            return None

        try:
            parsed_date = entry.published_parsed
            if isinstance(parsed_date, (list, tuple)) and len(parsed_date) >= 6:
                # 안전한 날짜 변환
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
