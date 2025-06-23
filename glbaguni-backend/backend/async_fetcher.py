#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
비동기 기사 수집 모듈 v3.0.0
완전한 async/await 패턴으로 리팩토링
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
import uuid

import httpx
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

try:
    from .models import Article
    from .config import settings
except ImportError:
    from models import Article
    from config import settings

logger = logging.getLogger("glbaguni.fetcher")

class AsyncArticleFetcher:
    """완전 비동기 기사 수집기"""
    
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.timeout = httpx.Timeout(connect=10.0, read=30.0)
        self.limits = httpx.Limits(max_connections=10, max_keepalive_connections=5)
        
        # 헤더 설정
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Glbaguni RSS Bot v3.0)',
            'Accept': 'application/rss+xml, application/xml, text/xml, text/html, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate'
        }
    
    async def __aenter__(self):
        """async context manager 진입"""
        self.session = httpx.AsyncClient(
            timeout=self.timeout,
            limits=self.limits,
            headers=self.headers,
            follow_redirects=True
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """async context manager 종료"""
        if self.session:
            await self.session.aclose()
    
    async def fetch_rss_articles(self, rss_url: str, max_articles: int = 10) -> List[Article]:
        """RSS 피드에서 기사 수집 (완전 비동기)"""
        req_id = str(uuid.uuid4())[:8]
        logger.info(f"📡 [{req_id}] RSS 수집 시작: {rss_url}")
        
        try:
            if not self.session:
                raise Exception("HTTP 세션이 초기화되지 않았습니다")
            
            # RSS 콘텐츠 다운로드
            response = await self.session.get(rss_url, timeout=30.0)
            response.raise_for_status()
            
            # 인코딩 감지 및 처리
            content = response.content
            if response.encoding:
                try:
                    decoded_content = content.decode(response.encoding, errors='ignore')
                except:
                    decoded_content = content.decode('utf-8', errors='ignore')
            else:
                decoded_content = content.decode('utf-8', errors='ignore')
            
            logger.info(f"📥 [{req_id}] RSS 다운로드 완료: {len(decoded_content)}자")
            
            # feedparser로 파싱 (동기 함수를 별도 스레드에서 실행)
            feed = await asyncio.to_thread(feedparser.parse, decoded_content)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                logger.warning(f"⚠️ [{req_id}] RSS 엔트리가 없습니다")
                return []
            
            logger.info(f"📋 [{req_id}] {len(feed.entries)}개 엔트리 발견")
            
            # 병렬로 기사 처리
            tasks = []
            for entry in feed.entries[:max_articles]:
                task = self._process_rss_entry(entry, rss_url, req_id)
                tasks.append(task)
            
            # 모든 작업을 병렬로 실행
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 성공한 결과만 수집
            articles = []
            for result in results:
                if isinstance(result, Article):
                    articles.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"❌ [{req_id}] 기사 처리 실패: {result}")
            
            logger.info(f"✅ [{req_id}] RSS 수집 완료: {len(articles)}개 기사")
            return articles
            
        except Exception as e:
            logger.error(f"💥 [{req_id}] RSS 수집 실패: {str(e)}")
            return []
    
    async def _process_rss_entry(self, entry: Any, source_url: str, req_id: str) -> Optional[Article]:
        """RSS 엔트리 처리 (비동기)"""
        try:
            # 필수 필드 확인
            if not hasattr(entry, 'title') or not hasattr(entry, 'link'):
                return None
            
            title = str(entry.title).strip()
            url = str(entry.link).strip()
            
            if not title or not url:
                return None
            
            # URL 유효성 검사
            if not url.startswith(('http://', 'https://')):
                return None
            
            # RSS에서 콘텐츠 추출
            content = self._extract_rss_content(entry)
            
            # 콘텐츠가 부족하면 전문 기사 가져오기 시도
            if len(content.strip()) < 100:
                try:
                    full_content = await self._fetch_full_article_content(url)
                    if full_content and len(full_content) > len(content):
                        content = full_content
                except Exception as e:
                    logger.warning(f"⚠️ [{req_id}] 전문 기사 가져오기 실패: {e}")
            
            # 최소 콘텐츠 길이 확인
            if len(content.strip()) < 50:
                return None
            
            # 게시일 파싱
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    time_struct = entry.published_parsed[:6]
                    published_date = datetime(*time_struct)
                except:
                    pass
            
            # Article 객체 생성
            return Article(
                title=title,
                url=url,
                content=content,
                published_date=published_date,
                author=getattr(entry, 'author', None),
                source=urlparse(source_url).netloc or 'unknown'
            )
            
        except Exception as e:
            logger.error(f"❌ [{req_id}] RSS 엔트리 처리 실패: {e}")
            return None
    
    def _extract_rss_content(self, entry: Any) -> str:
        """RSS 엔트리에서 콘텐츠 추출"""
        content_candidates = []
        
        # 다양한 콘텐츠 필드 시도
        for field in ['content', 'summary', 'description']:
            if hasattr(entry, field):
                field_value = getattr(entry, field)
                if isinstance(field_value, list) and field_value:
                    field_value = field_value[0]
                if hasattr(field_value, 'value'):
                    content_candidates.append(field_value.value)
                elif isinstance(field_value, str):
                    content_candidates.append(field_value)
        
        # 가장 긴 콘텐츠 선택
        if content_candidates:
            content = max(content_candidates, key=len)
            return self._clean_html_content(content)
        
        return ""
    
    def _clean_html_content(self, content: str) -> str:
        """HTML 콘텐츠 정화"""
        if not content:
            return ""
        
        try:
            # BeautifulSoup으로 HTML 파싱
            soup = BeautifulSoup(content, 'html.parser')
            
            # 불필요한 태그 제거
            for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            # 텍스트 추출
            text = soup.get_text(separator=' ', strip=True)
            
            # 연속된 공백 정리
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n', text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"HTML 정화 실패: {e}")
            # 기본적인 HTML 태그만 제거
            content = re.sub(r'<[^>]+>', '', content)
            content = re.sub(r'\s+', ' ', content)
            return content.strip()
    
    async def _fetch_full_article_content(self, url: str) -> Optional[str]:
        """전문 기사 콘텐츠 가져오기 (비동기)"""
        if not self.session:
            return None
        
        try:
            response = await self.session.get(url, timeout=20.0)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 기사 본문 추출 시도
            content_selectors = [
                'article',
                '.article-content',
                '.content',
                '.post-content',
                '#content',
                '.entry-content',
                'main'
            ]
            
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = elements[0].get_text(separator=' ', strip=True)
                    if len(content) > 200:  # 충분한 길이의 콘텐츠만
                        return self._clean_html_content(content)
            
            return None
            
        except Exception as e:
            logger.warning(f"전문 기사 가져오기 실패 ({url}): {e}")
            return None
    
    async def fetch_single_article(self, url: str) -> Optional[Article]:
        """단일 기사 URL에서 기사 수집 (비동기)"""
        req_id = str(uuid.uuid4())[:8]
        logger.info(f"📰 [{req_id}] 단일 기사 수집: {url}")
        
        try:
            if not self.session:
                raise Exception("HTTP 세션이 초기화되지 않았습니다")
            
            response = await self.session.get(url, timeout=30.0)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 제목 추출
            title = self._extract_title(soup)
            if not title:
                return None
            
            # 본문 추출
            content = await self._extract_article_content(soup)
            if not content or len(content) < 100:
                return None
            
            logger.info(f"✅ [{req_id}] 단일 기사 수집 완료: {title[:50]}...")
            
            return Article(
                title=title,
                url=url,
                content=content,
                published_date=None,
                author=None,
                source=urlparse(url).netloc or 'unknown'
            )
            
        except Exception as e:
            logger.error(f"💥 [{req_id}] 단일 기사 수집 실패: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """기사 제목 추출"""
        title_selectors = [
            'h1.title',
            'h1.article-title',
            'h1#title',
            '.article-header h1',
            'h1',
            'title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 10:
                    return title
        
        return None
    
    async def _extract_article_content(self, soup: BeautifulSoup) -> Optional[str]:
        """기사 본문 추출"""
        # 불필요한 태그 제거
        for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'ads']):
            tag.decompose()
        
        # 본문 추출 시도
        content_selectors = [
            'article',
            '.article-content',
            '.content',
            '.post-content',
            '#content',
            '.entry-content',
            '.article-body',
            'main'
        ]
        
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                content = elements[0].get_text(separator=' ', strip=True)
                if len(content) > 200:
                    return self._clean_html_content(content)
        
        # 기본 본문 추출
        paragraphs = soup.find_all('p')
        if paragraphs:
            content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            if len(content) > 200:
                return content
        
        return None
    
    async def fetch_multiple_sources(
        self,
        rss_urls: Optional[List[str]] = None,
        article_urls: Optional[List[str]] = None,
        max_articles: int = 10
    ) -> List[Article]:
        """여러 소스에서 기사 수집 (완전 비동기)"""
        req_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        logger.info(f"🎯 [{req_id}] 다중 소스 수집 시작")
        logger.info(f"📊 [{req_id}] RSS: {len(rss_urls or [])}, 기사: {len(article_urls or [])}")
        
        all_articles = []
        tasks = []
        
        try:
            async with self:  # context manager 사용
                # RSS URL들 처리
                if rss_urls:
                    for rss_url in rss_urls:
                        task = self.fetch_rss_articles(rss_url, max_articles // len(rss_urls) + 1)
                        tasks.append(task)
                
                # 개별 기사 URL들 처리
                if article_urls:
                    for article_url in article_urls:
                        task = self.fetch_single_article(article_url)
                        tasks.append(task)
                
                # 모든 작업을 병렬로 실행
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, list):
                            all_articles.extend(result)
                        elif isinstance(result, Article):
                            all_articles.append(result)
                        elif isinstance(result, Exception):
                            logger.error(f"❌ [{req_id}] 작업 실패: {result}")
            
            # 중복 제거 (URL 기준)
            seen_urls = set()
            unique_articles = []
            for article in all_articles:
                if str(article.url) not in seen_urls:
                    seen_urls.add(str(article.url))
                    unique_articles.append(article)
            
            # 최대 기사 수 제한
            final_articles = unique_articles[:max_articles]
            
            elapsed = time.time() - start_time
            logger.info(f"🎉 [{req_id}] 다중 소스 수집 완료: {len(final_articles)}개 기사 ({elapsed:.2f}초)")
            
            return final_articles
            
        except Exception as e:
            logger.error(f"💥 [{req_id}] 다중 소스 수집 실패: {e}")
            return []

# 편의 함수들
async def fetch_rss_async(rss_url: str, max_articles: int = 10) -> List[Article]:
    """RSS 피드 비동기 수집 (편의 함수)"""
    async with AsyncArticleFetcher() as fetcher:
        return await fetcher.fetch_rss_articles(rss_url, max_articles)

async def fetch_article_async(url: str) -> Optional[Article]:
    """단일 기사 비동기 수집 (편의 함수)"""
    async with AsyncArticleFetcher() as fetcher:
        return await fetcher.fetch_single_article(url)