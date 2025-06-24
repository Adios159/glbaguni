#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
뉴스 요약 시스템
사용자가 자연어로 뉴스 주제를 입력하면, 키워드를 추출하고 관련 뉴스를 찾아 요약하는 시스템
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union, cast
from urllib.parse import urljoin, urlparse

import feedparser
import requests

# 보안 모듈 임포트
try:
    from .security import create_safe_prompt, validate_api_key, validate_input

    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

try:
    from newspaper import Article

    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    # Create a dummy BeautifulSoup import to avoid errors
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        BeautifulSoup = None

try:
    from openai import OpenAI
    from openai.types.chat import ChatCompletionMessageParam

    OPENAI_AVAILABLE = True
    LEGACY_OPENAI = False
except ImportError:
    try:
        import openai  # type: ignore

        OPENAI_AVAILABLE = True
        LEGACY_OPENAI = True
        # For legacy OpenAI, we'll use Any for messages type
        ChatCompletionMessageParam = Any  # type: ignore
    except ImportError:
        OPENAI_AVAILABLE = False
        LEGACY_OPENAI = False
        # Create dummy openai module to avoid import errors
        openai = None  # type: ignore
        ChatCompletionMessageParam = Any  # type: ignore

# 로깅 설정
logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    title: str
    link: str
    summary: str
    content: str = ""
    published_date: Optional[str] = None
    source: str = ""


class NewsKeywordExtractor:
    """키워드 추출 클래스"""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self.openai_client = None  # type: ignore
        if openai_api_key and OPENAI_AVAILABLE:
            if LEGACY_OPENAI:
                # Legacy OpenAI 사용시에는 전역 설정
                if openai is not None:
                    openai.api_key = openai_api_key  # type: ignore
            else:
                self.openai_client = OpenAI(api_key=openai_api_key)  # type: ignore

    def extract_keywords_with_gpt(self, text: str) -> List[str]:
        """GPT를 사용한 키워드 추출 - 보안 강화"""
        if not self.openai_api_key or not OPENAI_AVAILABLE:
            logger.warning(
                "OpenAI API key not provided or openai package not installed. Using simple keyword extraction."
            )
            return self.extract_keywords_simple(text)

        # 보안 검증: 사용자 입력 정화
        if SECURITY_AVAILABLE:
            try:
                safe_text = validate_input(text, "query")
                logger.info(
                    f"🔒 사용자 입력 검증 완료: {len(text)} -> {len(safe_text)} 문자"
                )
            except ValueError as e:
                logger.error(f"🚨 위험한 입력 감지: {e}")
                return self.extract_keywords_simple(text)
        else:
            safe_text = text[:200]  # 기본 길이 제한

        try:
            # 안전한 프롬프트 구조 사용
            system_message = """당신은 뉴스 키워드 추출 전문가입니다. 
사용자가 제공한 텍스트에서 뉴스 검색에 유용한 핵심 키워드를 추출해주세요.
- 고유명사(회사명, 인물명, 지역명, 기술명 등)를 우선 추출
- 핵심 주제어를 포함
- 최대 10개까지
- 각 키워드는 따옴표 없이 콤마로 구분
- 키워드만 출력하고 다른 설명은 하지 마세요"""

            if SECURITY_AVAILABLE:
                prompt_data = create_safe_prompt(safe_text, system_message)
                messages = cast(Any, prompt_data["messages"])
                max_tokens = prompt_data["max_tokens"]
                temperature = prompt_data["temperature"]
            else:
                # 폴백: 기본 프롬프트 구조
                messages = cast(
                    Any,
                    [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": f"텍스트: {safe_text}"},
                    ],
                )
                max_tokens = 200
                temperature = 0.3

            if LEGACY_OPENAI and openai is not None:
                # Legacy OpenAI API 사용
                response = openai.ChatCompletion.create(  # type: ignore
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                keywords_text = response.choices[0].message.content or ""
                keywords_text = keywords_text.strip()
            elif self.openai_client is not None:
                # 새로운 OpenAI 클라이언트 사용
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                keywords_text = response.choices[0].message.content or ""
                keywords_text = keywords_text.strip()
            else:
                logger.error("OpenAI client not properly initialized")
                return self.extract_keywords_simple(text)

            if not keywords_text:
                logger.warning("Empty response from GPT, using simple extraction")
                return self.extract_keywords_simple(text)

            keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
            logger.info(f"GPT로 추출된 키워드: {keywords}")
            return keywords[:10]  # 최대 10개

        except Exception as e:
            logger.error(f"GPT 키워드 추출 실패: {e}")
            return self.extract_keywords_simple(text)

    def extract_keywords_simple(self, text: str) -> List[str]:
        """간단한 키워드 추출 (GPT 사용 불가시 대안)"""
        # 한국어 키워드 패턴 매칭
        keywords = []

        # 기본적인 키워드 패턴들
        patterns = {
            "회사명": r"(삼성|LG|SK|현대|기아|네이버|카카오|쿠팡|배달의민족|토스|TSMC|애플|구글|마이크로소프트|테슬라)",
            "기술": r"(반도체|AI|인공지능|5G|6G|블록체인|메타버스|NFT|클라우드|빅데이터)",
            "경제": r"(주가|증시|코스피|나스닥|달러|원화|금리|인플레이션|경기침체)",
            "정치": r"(대통령|국회|정부|여당|야당|선거|정책|법안)",
            "사회": r"(코로나|백신|기후|환경|교육|의료|복지)",
        }

        for category, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)

        # 중복 제거 및 정리
        keywords = list(set(keywords))
        logger.info(f"간단 추출된 키워드: {keywords}")
        return keywords[:10]


class NewsContentParser:
    """뉴스 본문 파싱 클래스"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def parse_article_content(self, url: str) -> str:
        """기사 본문 파싱"""
        try:
            if NEWSPAPER_AVAILABLE:
                return self._parse_with_newspaper(url)
            else:
                return self._parse_with_beautifulsoup(url)
        except Exception as e:
            logger.error(f"기사 파싱 실패 ({url}): {e}")
            return ""

    def _parse_with_newspaper(self, url: str) -> str:
        """newspaper3k를 사용한 파싱"""
        try:
            article = Article(url, language="ko")
            article.download()
            article.parse()
            return article.text
        except Exception as e:
            logger.error(f"Newspaper 파싱 실패: {e}")
            return self._parse_with_beautifulsoup(url)

    def _parse_with_beautifulsoup(self, url: str) -> str:
        """BeautifulSoup을 사용한 파싱"""
        if not BeautifulSoup:
            logger.error("BeautifulSoup not available. Please install beautifulsoup4.")
            return ""

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # 일반적인 기사 본문 선택자들
            selectors = [
                "article",
                ".article-content",
                ".news-content",
                ".post-content",
                "#articleText",
                ".article_view",
                ".read_body",
            ]

            content = ""
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    content = elements[0].get_text(strip=True)
                    break

            if not content:
                # 폴백: 모든 p 태그에서 텍스트 추출
                paragraphs = soup.find_all("p")
                content = "\n".join([p.get_text(strip=True) for p in paragraphs])

            return content

        except Exception as e:
            logger.error(f"BeautifulSoup 파싱 실패: {e}")
            return ""


class NewsSummarizer:
    """뉴스 요약 클래스"""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self.openai_client = None  # type: ignore
        if openai_api_key and OPENAI_AVAILABLE:
            if LEGACY_OPENAI:
                # Legacy OpenAI 사용시에는 전역 설정
                if openai is not None:
                    openai.api_key = openai_api_key  # type: ignore
            else:
                self.openai_client = OpenAI(api_key=openai_api_key)  # type: ignore

    def summarize_article(self, content: str, title: str = "") -> str:
        """기사 요약"""
        if not content:
            return "본문 내용이 없습니다."

        if not self.openai_api_key or not OPENAI_AVAILABLE:
            logger.warning(
                "OpenAI API key not provided or openai package not installed. Using simple summarization."
            )
            return self._simple_summarize(content)

        try:
            # 본문이 너무 길면 자르기 (2000자 이내)
            if len(content) > 2000:
                content = content[:2000] + "..."

            prompt = f"""
다음 뉴스 기사를 3-4줄로 간결하게 요약해주세요.
- 핵심 내용만 포함
- 객관적이고 중립적인 톤
- 한국어로 작성

제목: {title}
본문: {content}

요약:"""

            if LEGACY_OPENAI and openai is not None:
                # Legacy OpenAI API 사용
                response = openai.ChatCompletion.create(  # type: ignore
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "당신은 뉴스 요약 전문가입니다."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=300,
                    temperature=0.3,
                )
                summary = response.choices[0].message.content or ""
                if summary:
                    summary = summary.strip()
                else:
                    summary = self._simple_summarize(content)
            elif self.openai_client is not None:
                # 새로운 OpenAI 클라이언트 사용
                summarizer_messages = cast(
                    Any,
                    [
                        {"role": "system", "content": "당신은 뉴스 요약 전문가입니다."},
                        {"role": "user", "content": prompt},
                    ],
                )
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=summarizer_messages,
                    max_tokens=300,
                    temperature=0.3,
                )
                summary = response.choices[0].message.content or ""
                if summary:
                    summary = summary.strip()
                else:
                    summary = self._simple_summarize(content)
            else:
                logger.error("OpenAI client not properly initialized")
                return self._simple_summarize(content)

            return summary

        except Exception as e:
            logger.error(f"GPT 요약 실패: {e}")
            return self._simple_summarize(content)

    def _simple_summarize(self, content: str) -> str:
        """간단한 요약 (GPT 사용 불가시 대안)"""
        sentences = content.split(".")
        if len(sentences) > 3:
            return ". ".join(sentences[:3]) + "."
        return content


class NewsAggregator:
    """뉴스 수집 및 요약 메인 클래스"""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.keyword_extractor = NewsKeywordExtractor(openai_api_key)
        self.content_parser = NewsContentParser()
        self.summarizer = NewsSummarizer(openai_api_key)
        self.rss_feeds = self._get_rss_feeds()

    def _get_rss_feeds(self) -> Dict[str, List[str]]:
        """RSS 피드 목록 반환 - 무한로딩 방지를 위해 제한된 피드만 사용"""
        # 무한로딩 방지를 위해 가장 안정적인 주요 피드만 선택
        rss_feeds = {
            "SBS": [
                "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01",  # 헤드라인
                "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=02",  # 정치
                "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=03",  # 경제
            ],
            "JTBC": [
                "https://fs.jtbc.co.kr/RSS/newsflash.xml",  # 뉴스플래시
                "https://fs.jtbc.co.kr/RSS/politics.xml",  # 정치
                "https://fs.jtbc.co.kr/RSS/economy.xml",  # 경제
            ],
            "연합뉴스": [
                "https://www.yonhapnews.co.kr/rss/allheadlines.xml",  # 전체
                "https://www.yonhapnews.co.kr/rss/politics.xml",  # 정치
                "https://www.yonhapnews.co.kr/rss/economy.xml",  # 경제
            ],
            # 정부RSS 제거 - 무한로딩의 주요 원인
        }
        return rss_feeds

    def fetch_rss_articles(self, rss_url: str, source: str) -> List[Dict[str, Any]]:
        """RSS에서 기사 목록 가져오기 - 타임아웃 추가"""
        try:
            # 타임아웃 추가하여 무한 대기 방지
            import signal

            def timeout_handler(signum: int, frame: Any) -> None:
                raise TimeoutError("RSS fetch timeout")

            # Windows에서는 signal.SIGALRM이 지원되지 않으므로 requests timeout 사용
            feed = feedparser.parse(rss_url)
            articles: List[Dict[str, Any]] = []

            # 최대 기사 수 제한 (무한루프 방지)
            max_entries = min(len(feed.entries), 20)  # 최대 20개로 제한

            for entry in feed.entries[:max_entries]:
                article = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "published": entry.get("published", ""),
                    "source": source,
                }
                articles.append(article)

            logger.info(f"RSS에서 {len(articles)}개 기사 수집: {source}")
            return articles

        except Exception as e:
            logger.error(f"RSS 수집 실패 ({rss_url}): {e}")
            return []

    def filter_articles_by_keywords(
        self, articles: List[Dict[str, Any]], keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """키워드로 기사 필터링"""
        if not keywords:
            return articles

        filtered_articles = []

        for article in articles:
            title = article.get("title", "").lower()
            summary = article.get("summary", "").lower()

            # 키워드 중 하나라도 제목이나 요약에 포함되면 선택
            for keyword in keywords:
                if keyword.lower() in title or keyword.lower() in summary:
                    filtered_articles.append(article)
                    break

        logger.info(f"키워드 필터링 결과: {len(filtered_articles)}개 기사")
        return filtered_articles

    def process_news_query(
        self, query: str, max_articles: int = 10
    ) -> Tuple[List[NewsArticle], List[str]]:
        """뉴스 쿼리 처리 (메인 함수) - 키워드도 함께 반환 - 무한로딩 방지"""
        logger.info(f"뉴스 검색 시작: '{query}'")

        # 1. 키워드 추출
        keywords = self.keyword_extractor.extract_keywords_with_gpt(query)
        if not keywords:
            logger.warning("키워드를 추출할 수 없습니다.")
            return [], []

        # 2. RSS 피드에서 기사 수집 - 제한된 수의 피드만 처리
        all_articles: List[Dict[str, Any]] = []
        processed_feeds = 0
        max_feeds_per_source = 2  # 소스당 최대 2개 피드만 처리

        for source, feeds in self.rss_feeds.items():
            feed_count = 0
            if isinstance(feeds, list):  # 일반 언론사 RSS의 경우
                for feed_url in feeds:
                    if feed_count >= max_feeds_per_source:
                        break
                    try:
                        articles = self.fetch_rss_articles(feed_url, source)
                        all_articles.extend(articles)
                        feed_count += 1
                        processed_feeds += 1

                        # 무한로딩 방지: 너무 많은 피드 처리하지 않기
                        if processed_feeds >= 6:  # 최대 6개 피드만 처리
                            logger.info(
                                f"최대 피드 수 도달, 처리 중단: {processed_feeds}"
                            )
                            break

                        time.sleep(0.2)  # API 호출 제한 고려 (0.5에서 0.2로 단축)
                    except Exception as e:
                        logger.error(f"RSS 처리 오류: {e}")
                        continue

            if processed_feeds >= 6:
                break

        logger.info(f"총 {processed_feeds}개 피드에서 {len(all_articles)}개 기사 수집")

        # 3. 키워드로 필터링
        filtered_articles = self.filter_articles_by_keywords(all_articles, keywords)

        # 4. 중복 제거 (URL 기준)
        unique_articles: Dict[str, Dict[str, Any]] = {}
        for article in filtered_articles:
            url = article["link"]
            if url not in unique_articles:
                unique_articles[url] = article

        filtered_articles = list(unique_articles.values())[:max_articles]

        # 5. 본문 크롤링 및 요약 - 처리 시간 제한
        result_articles: List[NewsArticle] = []
        max_process_time = 30  # 최대 30초만 처리
        start_time = time.time()

        for i, article in enumerate(filtered_articles):
            # 시간 초과 체크
            if time.time() - start_time > max_process_time:
                logger.warning(f"처리 시간 초과, {i}개 기사만 처리됨")
                break

            logger.info(
                f"기사 처리 중 ({i+1}/{len(filtered_articles)}): {article['title']}"
            )

            try:
                # 본문 크롤링 - 타임아웃 추가
                content = self.content_parser.parse_article_content(article["link"])

                # 내용이 너무 짧으면 스킵
                if len(content.strip()) < 100:
                    logger.warning(f"내용이 너무 짧아 스킵: {article['title']}")
                    continue

                # 요약 생성
                summary = self.summarizer.summarize_article(content, article["title"])

                news_article = NewsArticle(
                    title=article["title"],
                    link=article["link"],
                    summary=summary,
                    content=content[:500] + "..." if len(content) > 500 else content,
                    published_date=article.get("published"),
                    source=article["source"],
                )

                result_articles.append(news_article)
                time.sleep(0.5)  # API 호출 제한 고려

            except Exception as e:
                logger.error(f"기사 처리 오류: {e}")
                continue

        logger.info(f"뉴스 검색 완료: {len(result_articles)}개 기사 처리")
        return result_articles, keywords
