#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content Extractor Service
HTML 및 RSS 콘텐츠 추출 전용 서비스
"""

import logging
from typing import Any, Optional
from urllib.parse import urlparse

import chardet
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ContentExtractor:
    """HTML 및 RSS 콘텐츠 추출 서비스"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Glbaguni RSS Bot)"})

    def detect_encoding(self, response: requests.Response) -> str:
        """응답의 인코딩을 감지합니다."""
        # Content-Type 헤더에서 charset 확인
        content_type = response.headers.get("content-type", "").lower()
        if "charset=" in content_type:
            charset = content_type.split("charset=")[1].split(";")[0].strip()
            logger.info(f"🔍 [ENCODING] Header charset: {charset}")
            return charset

        # chardet으로 감지
        detected = chardet.detect(response.content)
        encoding = detected.get("encoding", "utf-8") if detected else "utf-8"
        confidence = detected.get("confidence", 0) if detected else 0

        logger.info(
            f"🔍 [ENCODING] Detected: {encoding} (confidence: {confidence:.2f})"
        )

        # 한국어 사이트를 위한 encoding 우선순위
        if confidence < 0.7 and any(
            korean_domain in response.url.lower()
            for korean_domain in [".co.kr", "naver", "daum", "joins", "chosun", "jtbc"]
        ):
            return "utf-8"  # 한국 사이트는 보통 utf-8

        return encoding

    def extract_content_korean(self, soup: BeautifulSoup) -> str:
        """한국 뉴스 사이트에 특화된 콘텐츠 추출"""
        content_parts = []

        # 한국 뉴스 사이트별 셀렉터 정의
        korean_selectors = [
            # SBS
            ".article-text-area",
            ".text_area",
            ".article_txt",
            # JTBC
            ".article_content",
            ".news_content",
            ".content_text",
            # 연합뉴스
            ".story-news-article",
            ".article-txt",
            ".content",
            # 조선일보
            ".par",
            ".article_body",
            ".news_article_body",
            # 중앙일보
            ".article_body",
            ".news_text",
            ".article_content",
            # 한겨레
            ".text",
            ".article-text",
            ".content-text",
            # MBC
            ".news_txt",
            ".article_area",
            ".content_area",
            # 일반적인 셀렉터
            "article",
            ".article",
            "#article",
            ".post-content",
            ".entry-content",
            ".content",
            ".main-content",
        ]

        for selector in korean_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        text = element.get_text(strip=True)
                        if text and len(text) > 100:  # 의미있는 길이의 텍스트만
                            content_parts.append(text)
                            logger.info(
                                f"✅ [EXTRACT] Found content with selector: {selector}"
                            )
                            break
                if content_parts:
                    break
            except Exception as e:
                logger.debug(f"⚠️ [EXTRACT] Selector {selector} failed: {e}")
                continue

        return " ".join(content_parts)

    def clean_korean_text(self, text: str) -> str:
        """한국어 텍스트 정리"""
        if not text:
            return ""

        # 불필요한 문구 제거
        unwanted_phrases = [
            "저작권자 ⓒ",
            "무단전재 및 재배포 금지",
            "기자 =",
            "특파원 =",
            "= 기자",
            "본 기사는",
            "이 기사는",
            "▲",
            "▼",
            "◆",
            "◇",
            "Copyright",
            "All rights reserved",
            "뉴스1",
            "연합뉴스",
            "더보기",
            "관련기사",
            "ⓒ 한경닷컴",
            "한국경제",
            "매일경제",
            "페이스북",
            "트위터",
            "카카오톡",
            "네이버",
            "URL복사",
        ]

        for phrase in unwanted_phrases:
            text = text.replace(phrase, "")

        # 연속된 공백 정리
        import re

        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n+", "\n", text)

        return text.strip()

    def extract_content_fallback(self, soup: BeautifulSoup) -> str:
        """일반적인 콘텐츠 추출 방법"""
        content_tags = ["article", "main", ".content", ".post", ".entry"]

        for tag in content_tags:
            try:
                if tag.startswith("."):
                    elements = soup.select(tag)
                else:
                    elements = soup.find_all(tag)

                if elements:
                    content = elements[0].get_text(strip=True)
                    if len(content) > 100:
                        return content
            except Exception:
                continue

        # 마지막 수단: body 태그에서 텍스트 추출
        body = soup.find("body")
        if body:
            return body.get_text(strip=True)

        return soup.get_text(strip=True)

    def extract_content_from_rss_entry(self, entry: Any) -> str:
        """RSS 엔트리에서 콘텐츠 추출"""
        content = ""

        # RSS 필드 우선순위 순서로 확인
        content_fields = [
            "content",  # Atom 표준
            "summary",  # RSS 표준
            "description",  # RSS 표준
            "summary_detail",  # feedparser 확장
            "content_detail",  # feedparser 확장
        ]

        for field in content_fields:
            if hasattr(entry, field):
                field_content = getattr(entry, field)

                if isinstance(field_content, list) and field_content:
                    # content, summary_detail 등은 리스트
                    field_content = field_content[0]

                if isinstance(field_content, dict):
                    # detail 객체에서 value 추출
                    field_content = field_content.get("value", "") or field_content.get(
                        "content", ""
                    )

                if isinstance(field_content, str) and field_content.strip():
                    content = field_content
                    break

        if not content:
            return ""

        return self.clean_rss_content(content)

    def clean_rss_content(self, content: str) -> str:
        """RSS 콘텐츠 정리"""
        if not content:
            return ""

        # HTML 태그 제거
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")
            content = soup.get_text()
        except:
            pass

        # 불필요한 문구 제거
        unwanted = [
            "The post",
            "appeared first on",
            "Continue reading",
            "[Read more...]",
            "Read more",
            "더보기",
            "전체보기",
            "&nbsp;",
            "&amp;",
            "&lt;",
            "&gt;",
            "&quot;",
        ]

        for phrase in unwanted:
            content = content.replace(phrase, "")

        return content.strip()

    def extract_title(self, soup: BeautifulSoup) -> str:
        """페이지 제목 추출"""
        # 제목 태그 우선순위
        title_selectors = [
            "h1.title",
            "h1.headline",
            ".article-title h1",
            ".news-title",
            ".post-title",
            "h1",
            "title",
        ]

        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text(strip=True)
                    if title and len(title) > 5:
                        return title
            except Exception:
                continue

        # 기본값: HTML title 태그
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)

        return "제목 없음"

    def extract_content(self, soup: BeautifulSoup) -> str:
        """통합 콘텐츠 추출"""
        # 1단계: 한국 뉴스 사이트 특화 추출
        content = self.extract_content_korean(soup)

        if content and len(content.strip()) > 100:
            return self.clean_korean_text(content)

        # 2단계: 일반적인 방법으로 추출
        content = self.extract_content_fallback(soup)

        if content:
            return self.clean_korean_text(content)

        return "본문 추출 실패"
