#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSS 서비스 모듈
RSS 피드 수집 및 관리를 담당
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup

from ..config import get_settings
from ..utils import get_logger, ContextLogger, log_external_call
from ..utils.exception_handler import ExternalServiceError
from ..utils.validator import validate_url, sanitize_text
from ..models.response_schema import Article, RSSSource

logger = get_logger("services.rss")


class RSSService:
    """
    RSS 피드 수집 및 관리 서비스
    비동기적으로 여러 RSS 소스에서 뉴스를 수집
    """
    
    def __init__(self):
        """RSS 서비스 초기화"""
        self.settings = get_settings()
        self.client = None
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_articles": 0
        }
        
        logger.info("✅ RSS 서비스 초기화 완료")
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.rss_timeout),
            headers={
                'User-Agent': 'Glbaguni-NewsBot/3.0 (+https://glbaguni.com/bot)',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache'
            },
            follow_redirects=True,
            max_redirects=3
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.client:
            await self.client.aclose()
    
    async def fetch_rss_feeds(
        self,
        rss_urls: List[str],
        max_articles_per_source: Optional[int] = None,
        filter_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None
    ) -> Tuple[List[Article], List[Dict[str, Any]]]:
        """
        여러 RSS 피드에서 뉴스 수집
        
        Args:
            rss_urls: RSS URL 목록
            max_articles_per_source: 소스당 최대 기사 수
            filter_keywords: 포함할 키워드
            exclude_keywords: 제외할 키워드
        
        Returns:
            (수집된 기사 목록, 소스별 통계)
        """
        
        if max_articles_per_source is None:
            max_articles_per_source = self.settings.max_articles_per_source
        
        with ContextLogger(f"RSS 피드 수집 ({len(rss_urls)}개 소스)", "rss.fetch_feeds"):
            async with self:  # 컨텍스트 매니저 사용
                # 동시 요청 수 제한
                semaphore = asyncio.Semaphore(self.settings.max_concurrent_requests)
                
                # 각 RSS 소스에 대한 태스크 생성
                tasks = []
                for url in rss_urls:
                    task = self._fetch_single_rss_feed(
                        semaphore, url, max_articles_per_source,
                        filter_keywords, exclude_keywords
                    )
                    tasks.append(task)
                
                # 병렬 실행
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 결과 처리
                all_articles = []
                source_stats = []
                
                for i, result in enumerate(results):
                    url = rss_urls[i]
                    
                    if isinstance(result, Exception):
                        logger.error(f"❌ RSS 수집 실패 [{url}]: {result}")
                        source_stats.append({
                            "url": url,
                            "name": self._extract_domain_name(url),
                            "success": False,
                            "error": str(result),
                            "articles_count": 0,
                            "processing_time": 0
                        })
                        self._stats["failed_requests"] += 1
                    else:
                        articles, stats = result
                        all_articles.extend(articles)
                        source_stats.append(stats)
                        self._stats["successful_requests"] += 1
                        self._stats["total_articles"] += len(articles)
                
                self._stats["total_requests"] += len(rss_urls)
                
                logger.info(
                    f"✅ RSS 수집 완료 - 총 {len(all_articles)}개 기사 "
                    f"(성공: {len([s for s in source_stats if s['success']])}/{len(rss_urls)})"
                )
                
                return all_articles, source_stats
    
    async def _fetch_single_rss_feed(
        self,
        semaphore: asyncio.Semaphore,
        url: str,
        max_articles: int,
        filter_keywords: Optional[List[str]],
        exclude_keywords: Optional[List[str]]
    ) -> Tuple[List[Article], Dict[str, Any]]:
        """
        단일 RSS 피드 수집
        
        Args:
            semaphore: 동시 실행 제한
            url: RSS URL
            max_articles: 최대 기사 수
            filter_keywords: 포함할 키워드
            exclude_keywords: 제외할 키워드
        
        Returns:
            (기사 목록, 통계 정보)
        """
        
        async with semaphore:
            start_time = time.time()
            
            try:
                # URL 검증
                validated_url = validate_url(url)
                
                # RSS 피드 다운로드
                logger.debug(f"📡 RSS 요청 시작: {url}")
                
                response = await self.client.get(validated_url)
                response.raise_for_status()
                
                processing_time = time.time() - start_time
                
                log_external_call(
                    "RSS", urlparse(url).netloc, processing_time, True
                )
                
                # RSS 파싱
                articles = await self._parse_rss_content(
                    response.text, url, max_articles, filter_keywords, exclude_keywords
                )
                
                total_time = time.time() - start_time
                
                # 통계 정보 생성
                stats = {
                    "url": url,
                    "name": self._extract_feed_title(response.text) or self._extract_domain_name(url),
                    "success": True,
                    "articles_count": len(articles),
                    "processing_time": total_time,
                    "response_size": len(response.text),
                    "status_code": response.status_code
                }
                
                logger.debug(f"✅ RSS 수집 성공 [{url}]: {len(articles)}개 기사 ({total_time:.2f}초)")
                
                return articles, stats
                
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                logger.warning(f"⚠️ RSS HTTP 오류 [{url}]: {error_msg}")
                
                log_external_call(
                    "RSS", urlparse(url).netloc, time.time() - start_time, False
                )
                
                raise ExternalServiceError("RSS", error_msg)
                
            except httpx.TimeoutException:
                error_msg = f"요청 시간 초과 ({self.settings.rss_timeout}초)"
                logger.warning(f"⏰ RSS 타임아웃 [{url}]: {error_msg}")
                
                log_external_call(
                    "RSS", urlparse(url).netloc, time.time() - start_time, False
                )
                
                raise ExternalServiceError("RSS", error_msg)
                
            except Exception as e:
                error_msg = f"예상치 못한 오류: {str(e)}"
                logger.error(f"❌ RSS 오류 [{url}]: {error_msg}")
                
                log_external_call(
                    "RSS", urlparse(url).netloc, time.time() - start_time, False
                )
                
                raise ExternalServiceError("RSS", error_msg)
    
    async def _parse_rss_content(
        self,
        xml_content: str,
        source_url: str,
        max_articles: int,
        filter_keywords: Optional[List[str]],
        exclude_keywords: Optional[List[str]]
    ) -> List[Article]:
        """
        RSS XML 콘텐츠 파싱
        
        Args:
            xml_content: RSS XML 문자열
            source_url: RSS 소스 URL
            max_articles: 최대 기사 수
            filter_keywords: 포함할 키워드
            exclude_keywords: 제외할 키워드
        
        Returns:
            파싱된 기사 목록
        """
        
        try:
            # XML 파싱
            root = ET.fromstring(xml_content)
            
            # RSS 2.0 또는 Atom 피드 감지
            if root.tag == 'rss':
                articles = self._parse_rss_20(root, source_url)
            elif root.tag.endswith('feed'):  # Atom
                articles = self._parse_atom_feed(root, source_url)
            else:
                logger.warning(f"⚠️ 지원되지 않는 피드 형식: {root.tag}")
                return []
            
            # 키워드 필터링
            if filter_keywords or exclude_keywords:
                articles = self._filter_articles_by_keywords(
                    articles, filter_keywords, exclude_keywords
                )
            
            # 기사 수 제한
            articles = articles[:max_articles]
            
            logger.debug(f"📄 RSS 파싱 완료: {len(articles)}개 기사")
            
            return articles
            
        except ET.ParseError as e:
            logger.error(f"❌ XML 파싱 오류: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"❌ RSS 파싱 오류: {str(e)}")
            return []
    
    def _parse_rss_20(self, root: ET.Element, source_url: str) -> List[Article]:
        """RSS 2.0 형식 파싱"""
        
        articles = []
        
        # 채널 정보 추출
        channel = root.find('channel')
        if channel is None:
            return articles
        
        source_name = self._get_text_content(channel.find('title')) or self._extract_domain_name(source_url)
        
        # 각 아이템(기사) 파싱
        for item in channel.findall('item'):
            try:
                title = self._get_text_content(item.find('title'))
                link = self._get_text_content(item.find('link'))
                description = self._get_text_content(item.find('description'))
                pub_date = self._get_text_content(item.find('pubDate'))
                category = self._get_text_content(item.find('category'))
                
                if not title or not link:
                    continue  # 필수 필드가 없으면 스킵
                
                # 날짜 파싱
                published_at = self._parse_date(pub_date) if pub_date else None
                
                # HTML 태그 제거 및 텍스트 정리
                clean_description = self._clean_html_content(description) if description else None
                
                # Article 객체 생성
                article = Article(
                    title=sanitize_text(title, 200),
                    content=sanitize_text(clean_description, 2000) if clean_description else None,
                    url=link,
                    source=source_name,
                    published_at=published_at,
                    category=sanitize_text(category, 50) if category else None,
                    language="ko"  # 기본값, 실제로는 감지 로직 필요
                )
                
                articles.append(article)
                
            except Exception as e:
                logger.warning(f"⚠️ 기사 파싱 스킵: {str(e)}")
                continue
        
        return articles
    
    def _parse_atom_feed(self, root: ET.Element, source_url: str) -> List[Article]:
        """Atom 피드 파싱"""
        
        articles = []
        
        # 네임스페이스 처리
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        # 피드 제목 추출
        feed_title_elem = root.find('atom:title', ns)
        source_name = feed_title_elem.text if feed_title_elem is not None else self._extract_domain_name(source_url)
        
        # 각 엔트리(기사) 파싱
        for entry in root.findall('atom:entry', ns):
            try:
                title_elem = entry.find('atom:title', ns)
                link_elem = entry.find('atom:link', ns)
                summary_elem = entry.find('atom:summary', ns)
                content_elem = entry.find('atom:content', ns)
                updated_elem = entry.find('atom:updated', ns)
                category_elem = entry.find('atom:category', ns)
                
                title = title_elem.text if title_elem is not None else None
                link = link_elem.get('href') if link_elem is not None else None
                
                # 내용 우선순위: content > summary
                content = None
                if content_elem is not None:
                    content = content_elem.text
                elif summary_elem is not None:
                    content = summary_elem.text
                
                updated = updated_elem.text if updated_elem is not None else None
                category = category_elem.get('term') if category_elem is not None else None
                
                if not title or not link:
                    continue
                
                # 날짜 파싱
                published_at = self._parse_iso_date(updated) if updated else None
                
                # HTML 정리
                clean_content = self._clean_html_content(content) if content else None
                
                # Article 객체 생성
                article = Article(
                    title=sanitize_text(title, 200),
                    content=sanitize_text(clean_content, 2000) if clean_content else None,
                    url=link,
                    source=source_name,
                    published_at=published_at,
                    category=sanitize_text(category, 50) if category else None,
                    language="ko"
                )
                
                articles.append(article)
                
            except Exception as e:
                logger.warning(f"⚠️ Atom 엔트리 파싱 스킵: {str(e)}")
                continue
        
        return articles
    
    def _filter_articles_by_keywords(
        self,
        articles: List[Article],
        filter_keywords: Optional[List[str]],
        exclude_keywords: Optional[List[str]]
    ) -> List[Article]:
        """키워드 기반 기사 필터링"""
        
        filtered_articles = []
        
        for article in articles:
            # 검색 대상 텍스트 (제목 + 내용)
            search_text = (article.title + " " + (article.content or "")).lower()
            
            # 제외 키워드 확인
            if exclude_keywords:
                should_exclude = any(
                    keyword.lower() in search_text 
                    for keyword in exclude_keywords
                )
                if should_exclude:
                    continue
            
            # 포함 키워드 확인
            if filter_keywords:
                should_include = any(
                    keyword.lower() in search_text 
                    for keyword in filter_keywords
                )
                if not should_include:
                    continue
            
            filtered_articles.append(article)
        
        if filter_keywords or exclude_keywords:
            logger.debug(
                f"🔍 키워드 필터링: {len(articles)} → {len(filtered_articles)}개 기사"
            )
        
        return filtered_articles
    
    def _get_text_content(self, element: Optional[ET.Element]) -> Optional[str]:
        """XML 엘리먼트에서 텍스트 추출"""
        if element is None:
            return None
        
        # CDATA 섹션 처리
        text = element.text or ""
        
        # 자식 요소들의 텍스트도 포함
        for child in element:
            if child.text:
                text += child.text
            if child.tail:
                text += child.tail
        
        return text.strip() if text else None
    
    def _clean_html_content(self, html_content: str) -> str:
        """HTML 태그 제거 및 텍스트 정리"""
        if not html_content:
            return ""
        
        try:
            # BeautifulSoup로 HTML 파싱
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 스크립트, 스타일 태그 제거
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 텍스트만 추출
            text = soup.get_text()
            
            # 공백 정리
            import re
            text = re.sub(r'\s+', ' ', text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ HTML 정리 실패: {str(e)}")
            # 기본 태그 제거만 수행
            import re
            return re.sub(r'<[^>]+>', '', html_content).strip()
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """RSS 날짜 문자열 파싱 (RFC 2822 형식)"""
        if not date_str:
            return None
        
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"⚠️ 날짜 파싱 실패: {date_str} - {str(e)}")
            return None
    
    def _parse_iso_date(self, date_str: str) -> Optional[datetime]:
        """ISO 8601 날짜 문자열 파싱"""
        if not date_str:
            return None
        
        try:
            # 다양한 ISO 형식 지원
            from dateutil.parser import parse
            return parse(date_str)
        except Exception as e:
            logger.warning(f"⚠️ ISO 날짜 파싱 실패: {date_str} - {str(e)}")
            return None
    
    def _extract_feed_title(self, xml_content: str) -> Optional[str]:
        """RSS 피드에서 제목 추출"""
        try:
            root = ET.fromstring(xml_content)
            
            if root.tag == 'rss':
                channel = root.find('channel')
                if channel is not None:
                    title_elem = channel.find('title')
                    if title_elem is not None:
                        return title_elem.text
            elif root.tag.endswith('feed'):
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                title_elem = root.find('atom:title', ns)
                if title_elem is not None:
                    return title_elem.text
        except Exception:
            pass
        
        return None
    
    def _extract_domain_name(self, url: str) -> str:
        """URL에서 도메인명 추출"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # www. 제거
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain
        except Exception:
            return "Unknown Source"
    
    async def validate_rss_feed(self, url: str) -> Dict[str, Any]:
        """
        RSS 피드 유효성 검증
        
        Args:
            url: 검증할 RSS URL
        
        Returns:
            검증 결과 딕셔너리
        """
        
        result = {
            "is_valid": False,
            "url": url,
            "title": None,
            "article_count": 0,
            "last_updated": None,
            "error": None,
            "response_time": 0
        }
        
        start_time = time.time()
        
        try:
            async with self:
                response = await self.client.get(url)
                response.raise_for_status()
                
                result["response_time"] = time.time() - start_time
                
                # 기본 파싱 시도
                articles = await self._parse_rss_content(response.text, url, 5, None, None)
                
                result["is_valid"] = True
                result["title"] = self._extract_feed_title(response.text)
                result["article_count"] = len(articles)
                
                if articles:
                    # 가장 최근 기사의 날짜
                    latest_date = max(
                        (article.published_at for article in articles if article.published_at),
                        default=None
                    )
                    result["last_updated"] = latest_date
                
                logger.info(f"✅ RSS 검증 성공: {url}")
                
        except Exception as e:
            result["error"] = str(e)
            result["response_time"] = time.time() - start_time
            logger.warning(f"⚠️ RSS 검증 실패: {url} - {str(e)}")
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """RSS 서비스 통계 반환"""
        success_rate = (
            self._stats["successful_requests"] / max(1, self._stats["total_requests"])
        )
        
        return {
            **self._stats,
            "success_rate": success_rate,
            "avg_articles_per_request": (
                self._stats["total_articles"] / max(1, self._stats["successful_requests"])
            )
        }
    
    def reset_stats(self):
        """통계 초기화"""
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_articles": 0
        }
        logger.info("📊 RSS 서비스 통계 초기화")


if __name__ == "__main__":
    # 테스트 코드
    import asyncio
    
    async def test_rss_service():
        print("RSS 서비스 테스트:")
        
        try:
            service = RSSService()
            
            # 테스트 RSS URL들
            test_urls = [
                "https://feeds.bbci.co.uk/news/rss.xml",
                "https://rss.cnn.com/rss/edition.rss"
            ]
            
            # RSS 피드 수집 테스트
            articles, stats = await service.fetch_rss_feeds(test_urls, max_articles_per_source=3)
            
            print(f"✅ 수집된 기사: {len(articles)}개")
            for stat in stats:
                print(f"  - {stat['name']}: {stat['articles_count']}개 ({'성공' if stat['success'] else '실패'})")
            
            # 통계 출력
            service_stats = service.get_stats()
            print(f"✅ 서비스 통계: {service_stats}")
            
            # RSS 검증 테스트
            if test_urls:
                validation = await service.validate_rss_feed(test_urls[0])
                print(f"✅ RSS 검증: {'유효' if validation['is_valid'] else '무효'}")
            
        except Exception as e:
            print(f"❌ RSS 서비스 테스트 실패: {e}")
    
    # 실제 테스트 실행
    # asyncio.run(test_rss_service())
    print("RSS 서비스 모듈 로드 완료")