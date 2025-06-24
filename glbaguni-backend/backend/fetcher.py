import logging
import time
from datetime import datetime
from typing import Any, List, Optional, Union
from urllib.parse import urlparse

import chardet
import feedparser
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

# Handle relative imports for both module and script execution
try:
    # Try absolute imports first
    import sys
    import os
    
    # Add the backend directory to the path
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    from config import settings
    from models import Article
    from services.content_extractor import ContentExtractor
    from services.rss_service import RSSService
except ImportError:
    try:
        # Fallback for package import
        from .config import settings
        from .models import Article
        from .services.content_extractor import ContentExtractor
        from .services.rss_service import RSSService
    except ImportError:
        # Basic imports for testing
        try:
            from .models import Article
        except ImportError:
            from models import Article
        # Mock settings for testing
        class MockSettings:
            def __init__(self):
                self.rss_timeout = 30
                self.crawling_timeout = 15
        settings = MockSettings()

logger = logging.getLogger(__name__)


class ArticleFetcher:
    """Fetches articles from RSS feeds and direct URLs - Legacy wrapper."""

    def __init__(self):
        # 새로운 서비스들로 위임
        try:
            self.rss_service = RSSService()
            self.content_extractor = ContentExtractor()
            # 기존 호환성을 위한 속성들
            self.session = self.rss_service.session
        except (ImportError, NameError):
            # For testing purposes
            import requests
            self.rss_service = None
            self.content_extractor = None
            self.session = requests.Session()

    def fetch_rss_articles(self, rss_url: str, max_articles: int = 10) -> List[Article]:
        """Fetch articles from RSS feed - delegates to RSSService."""
        if self.rss_service:
            return self.rss_service.fetch_rss_articles(rss_url, max_articles)
        else:
            # Fallback for testing
            return []

    def fetch_html_article(self, url: str) -> Optional[Article]:
        """Fetch article content from direct URL using BeautifulSoup with Korean support."""
        try:
            logger.info(f"Fetching HTML article: {url}")

            # Validate URL
            if not url.startswith(("http://", "https://")):
                logger.error(f"Invalid URL: {url}")
                return None

            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                logger.warning(f"Content is not HTML: {content_type}")
                return None

            # Handle Korean encoding detection
            encoding = self._detect_encoding(response)
            logger.info(f"Using encoding: {encoding}")

            # Parse with detected encoding
            soup = BeautifulSoup(
                response.content, "html.parser", from_encoding=encoding
            )

            # Extract title
            title = self._extract_title(soup)

            # Extract content with Korean site support
            content = self._extract_content_korean(soup)

            if not title or not content:
                logger.warning(f"Could not extract title or content from {url}")
                return None

            # Clean and validate content
            title = title.strip()
            content = content.strip()

            if len(content) < 30:  # Reduced minimum content length for Korean articles
                logger.warning(
                    f"Content too short from {url}: {len(content)} characters"
                )
                return None

            try:
                article = Article(
                    title=title,
                    url=url,  # type: ignore # Pydantic will validate this
                    content=content,
                    source=urlparse(url).netloc or "unknown",
                )

                logger.info(
                    f"Successfully fetched article: {title} ({len(content)} characters)"
                )
                return article
            except Exception as e:
                logger.error(f"Error creating Article object: {e}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching HTML article {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching HTML article {url}: {e}")
            return None

    def _detect_encoding(self, response: requests.Response) -> str:
        """Detect and return appropriate encoding for Korean content."""
        # Try apparent encoding first (good for Korean sites)
        if hasattr(response, "apparent_encoding") and response.apparent_encoding:
            apparent = response.apparent_encoding.lower()
            # Common Korean encodings
            if any(
                enc in apparent for enc in ["euc-kr", "cp949", "ks_c_5601", "korean"]
            ):
                logger.info(f"Detected Korean encoding: {response.apparent_encoding}")
                return response.apparent_encoding

        # Check encoding from headers
        if response.encoding and response.encoding.lower() != "iso-8859-1":
            return response.encoding

        # Check apparent encoding for other cases
        if hasattr(response, "apparent_encoding") and response.apparent_encoding:
            return response.apparent_encoding

        # Default fallback
        return "utf-8"

    def _extract_content_korean(self, soup: BeautifulSoup) -> str:
        """Extract article content with Korean news site support."""
        # Remove unwanted elements
        for unwanted in soup(
            [
                "script",
                "style",
                "nav",
                "header",
                "footer",
                "aside",
                "form",
                "iframe",
                "noscript",
                "button",
                "input",
                "select",
                "textarea",
            ]
        ):
            unwanted.decompose()

        # Remove common unwanted elements
        unwanted_selectors = [
            ".ad",
            ".advertisement",
            ".banner",
            ".social",
            ".share",
            ".related",
            ".comment",
            ".sidebar",
            ".menu",
            ".navigation",
            ".breadcrumb",
        ]
        for selector in unwanted_selectors:
            for elem in soup.select(selector):
                elem.decompose()

        # Enhanced Korean news site content selectors (ordered by priority)
        korean_selectors = [
            # Hani (한겨레)
            {"tag": "div", "id": "article-view-content-div"},
            {"tag": "div", "class_": "article-text"},
            {"tag": "div", "id": "articleBodyContents"},
            {"tag": "div", "class_": "article-text-area"},
            # Chosun (조선일보)
            {"tag": "div", "class_": "par"},
            {"tag": "div", "id": "news_body_id"},
            {"tag": "div", "class_": "news_body"},
            # JoongAng (중앙일보)
            {"tag": "div", "class_": "article_body"},
            {"tag": "div", "id": "article_body"},
            {"tag": "div", "class_": "article"},
            # Yonhap (연합뉴스)
            {"tag": "div", "class_": "story-news-article"},
            {"tag": "div", "id": "articleWrap"},
            {"tag": "div", "class_": "story"},
            {"tag": "div", "id": "articleText"},
            # SBS
            {"tag": "div", "class_": "text_area"},
            {"tag": "div", "id": "container"},
            {"tag": "div", "class_": "article_area"},
            # KBS
            {"tag": "div", "class_": "detail-body"},
            {"tag": "div", "id": "content"},
            {"tag": "div", "class_": "detail_content"},
            # MBC
            {"tag": "div", "class_": "news_txt"},
            {"tag": "div", "id": "content"},
            # JTBC
            {"tag": "div", "class_": "article_content"},
            {"tag": "div", "id": "articlebody"},
            # Generic Korean patterns
            {"tag": "div", "id": "newsEndContents"},
            {"tag": "div", "class_": "view-content"},
            {"tag": "div", "class_": "article-content"},
            {"tag": "div", "class_": "news-content"},
            {"tag": "div", "class_": "post-content"},
            {"tag": "div", "class_": "entry-content"},
            # Generic selectors (lowest priority)
            {"tag": "article"},
            {"tag": "div", "class_": "article-body"},
            {"tag": "main"},
        ]

        # Try each selector
        for selector in korean_selectors:
            try:
                if "class_" in selector:
                    content_elem = soup.find(selector["tag"], class_=selector["class_"])
                elif "id" in selector:
                    content_elem = soup.find(selector["tag"], id=selector["id"])
                else:
                    content_elem = soup.find(selector["tag"])

                if content_elem:
                    # Remove nested unwanted elements (only if it's a Tag, not NavigableString)
                    from bs4 import Tag

                    if isinstance(content_elem, Tag) and hasattr(
                        content_elem, "find_all"
                    ):
                        for unwanted in content_elem.find_all(
                            ["script", "style", "iframe", "noscript"]
                        ):
                            unwanted.decompose()

                    text = content_elem.get_text(separator=" ", strip=True)
                    if len(text) > 100:  # Minimum content length
                        logger.info(f"Content extracted using selector: {selector}")
                        return self._clean_korean_text(text)
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        # Fallback to generic content extraction
        logger.info("Using fallback content extraction")
        return self._extract_content_fallback(soup)

    def _clean_korean_text(self, text: str) -> str:
        """Clean extracted Korean text."""
        import re

        # Remove extra whitespace
        text = " ".join(text.split())

        # Remove common Korean site artifacts
        artifacts = [
            r"기자\s*=?\s*\w+@\w+\.\w+",  # Remove reporter email
            r"Copyright\s*©.*",
            r"저작권자\s*©.*",
            r"무단전재.*금지",
            r"배포.*금지",
            r"\[.*?기자\]",
            r"\[.*?특파원\]",
            r"▶.*?◀",
            r"※.*",
            r"☞.*",
            r"■.*",
            r"▲.*",
            r"●.*",
        ]

        for pattern in artifacts:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove multiple spaces
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def _extract_content_fallback(self, soup: BeautifulSoup) -> str:
        """Fallback content extraction method."""
        try:
            # Try to find content in paragraphs
            paragraphs = soup.find_all("p")
            if paragraphs:
                content_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 20:  # Filter out short paragraphs
                        content_parts.append(text)

                if content_parts:
                    combined_text = " ".join(content_parts)
                    if len(combined_text) > 100:
                        return self._clean_korean_text(combined_text)

            # Last resort: body text
            body = soup.find("body")
            if body:
                text = body.get_text(separator=" ", strip=True)
                if len(text) > 100:
                    return self._clean_korean_text(text)

            return "본문 추출 실패"

        except Exception as e:
            logger.error(f"Fallback content extraction failed: {e}")
            return "본문 추출 실패"

    def _extract_content_from_rss_entry(self, entry: Any) -> str:
        """Extract content from RSS entry, trying different fields with Korean support."""
        # Try different content fields (order matters for Korean RSS feeds)
        content_fields = ["content", "description", "summary", "subtitle"]

        for field in content_fields:
            if hasattr(entry, field):
                content = getattr(entry, field)

                # Handle different content types
                if isinstance(content, list) and content:
                    try:
                        # Try to get the value from the first content item
                        if hasattr(content[0], "value"):
                            extracted = content[0].value
                        elif isinstance(content[0], dict) and "value" in content[0]:
                            extracted = content[0]["value"]
                        else:
                            extracted = str(content[0])

                        if extracted and len(extracted.strip()) > 10:
                            logger.debug(
                                f"Extracted content from {field}: {len(extracted)} characters"
                            )
                            return self._clean_rss_content(extracted.strip())
                    except (AttributeError, IndexError, KeyError) as e:
                        logger.debug(f"Failed to extract from {field}: {e}")
                        continue

                elif isinstance(content, str) and content.strip():
                    if len(content.strip()) > 10:
                        logger.debug(
                            f"Extracted content from {field}: {len(content)} characters"
                        )
                        return self._clean_rss_content(content.strip())

                elif hasattr(content, "value"):
                    try:
                        value = getattr(content, "value")
                        if value:
                            logger.debug(
                                f"Extracted content from {field}.value: {len(str(value))} characters"
                            )
                            return self._clean_rss_content(str(value).strip())
                    except AttributeError:
                        continue

        return ""

    def _clean_rss_content(self, content: str) -> str:
        """Clean RSS content by removing HTML tags and extra whitespace."""
        import re
        from html import unescape

        # Remove HTML tags
        content = re.sub(r"<[^>]+>", "", content)

        # Unescape HTML entities
        content = unescape(content)

        # Remove extra whitespace
        content = " ".join(content.split())

        # Remove common RSS artifacts
        content = re.sub(r"\[CDATA\[|\]\]", "", content)
        content = re.sub(r"^\s*\.\.\.\s*", "", content)

        return content.strip()

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title from HTML."""
        # Try different title selectors
        title_selectors = [
            "h1",
            "title",
            '[class*="title"]',
            '[class*="headline"]',
            "h2",
            "h3",
        ]

        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                return title_elem.get_text().strip()

        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract article content from HTML."""
        # Remove unwanted elements
        for unwanted in soup(
            ["script", "style", "nav", "header", "footer", "aside", "form"]
        ):
            unwanted.decompose()

        # Try different content selectors
        content_selectors = [
            "article",
            '[class*="content"]',
            '[class*="article"]',
            '[class*="post"]',
            "main",
            ".entry-content",
            ".post-content",
            ".story-content",
            ".article-content",
        ]

        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                text = content_elem.get_text(separator=" ", strip=True)
                if len(text) > 100:  # Minimum content length
                    return text

        # Fallback to body text
        body = soup.find("body")
        if body:
            return body.get_text(separator=" ", strip=True)

        return ""

    def fetch_multiple_sources(
        self,
        rss_urls: Optional[List[str]] = None,
        article_urls: Optional[List[str]] = None,
        max_articles: int = 10,
    ) -> List[Article]:
        """Fetch articles from multiple sources with timeout protection."""
        import time

        start_time = time.time()
        max_processing_time = 60  # 최대 60초 처리 시간 제한

        articles = []

        # Fetch from RSS feeds
        if rss_urls:
            processed_feeds = 0
            max_feeds = 5  # 최대 5개 RSS 피드만 처리

            for rss_url in rss_urls:
                # 시간 초과 체크
                if time.time() - start_time > max_processing_time:
                    logger.warning(
                        f"Processing timeout reached, stopping RSS fetch at {processed_feeds} feeds"
                    )
                    break

                if processed_feeds >= max_feeds:
                    logger.info(f"Maximum RSS feeds reached: {max_feeds}")
                    break

                try:
                    rss_articles = self.fetch_rss_articles(
                        rss_url, min(max_articles, 10)
                    )
                    articles.extend(rss_articles)
                    processed_feeds += 1
                    # Add small delay between requests
                    time.sleep(0.3)  # 0.5에서 0.3으로 단축
                except Exception as e:
                    logger.error(f"Error fetching RSS feed {rss_url}: {e}")
                    continue

        # Fetch from direct URLs
        if article_urls:
            processed_urls = 0
            max_urls = 10  # 최대 10개 직접 URL만 처리

            for url in article_urls:
                # 시간 초과 체크
                if time.time() - start_time > max_processing_time:
                    logger.warning(
                        f"Processing timeout reached, stopping URL fetch at {processed_urls} URLs"
                    )
                    break

                if processed_urls >= max_urls:
                    logger.info(f"Maximum URLs reached: {max_urls}")
                    break

                try:
                    article = self.fetch_html_article(url)
                    if article:
                        articles.append(article)
                    processed_urls += 1
                    # Add small delay between requests
                    time.sleep(0.3)  # 0.5에서 0.3으로 단축
                except Exception as e:
                    logger.error(f"Error fetching article {url}: {e}")
                    continue

        # Sort by published date (newest first) and limit total
        try:
            articles.sort(key=lambda x: x.published_date or datetime.min, reverse=True)
        except Exception as e:
            logger.warning(f"Error sorting articles: {e}")

        # 최종 결과 제한
        final_articles = articles[:max_articles]
        processing_time = time.time() - start_time
        logger.info(
            f"Fetch completed: {len(final_articles)} articles in {processing_time:.2f}s"
        )

        return final_articles
