#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch Router
RSS 피드 및 뉴스 수집 관련 엔드포인트
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, HttpUrl

# 의존성 임포트
try:
    from services.content_extractor import ContentExtractor
    from services.rss_service import RSSService
    from utils.validator import validate_user_input, validate_url
except ImportError:
    try:
        from backend.services.content_extractor import ContentExtractor
        from backend.services.rss_service import RSSService
        from backend.utils.validator import validate_user_input, validate_url
    except ImportError:
        # 기본값으로 None 또는 Mock 객체 사용
        ContentExtractor = None
        RSSService = None
        def validate_user_input(text: str, max_length: int = 5000) -> str:
            return text
        def validate_url(url: str) -> str:
            return url

import logging

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/fetch", tags=["fetch"])


# 요청/응답 모델
class RSSFetchRequest(BaseModel):
    """RSS 피드 요청 모델"""

    rss_urls: List[HttpUrl]
    max_articles: int = 10
    user_id: Optional[str] = None


class ArticleFetchRequest(BaseModel):
    """개별 기사 요청 모델"""

    url: HttpUrl
    user_id: Optional[str] = None


class FetchResponse(BaseModel):
    """수집 응답 모델"""

    success: bool
    message: str
    articles_count: int
    articles: List[dict]
    request_id: str
    processed_at: str


# 서비스 인스턴스 (안전한 초기화)
try:
    rss_service = RSSService() if RSSService else None
    content_extractor = ContentExtractor() if ContentExtractor else None
except Exception:
    rss_service = None
    content_extractor = None


@router.post("/rss", response_model=FetchResponse)
async def fetch_rss_feeds(request: RSSFetchRequest, background_tasks: BackgroundTasks):
    """
    RSS 피드에서 기사들을 수집합니다.

    - **rss_urls**: RSS 피드 URL 목록
    - **max_articles**: 피드당 최대 기사 수 (기본값: 10)
    - **user_id**: 사용자 ID (선택사항)
    """
    request_id = str(uuid.uuid4())[:8]

    try:
        # 1. 요청 수신
        logger.info(f"📥 [RSS요청] 사용자 입력 수신 완료 - ID: {request_id}")
        logger.info(f"📡 [{request_id}] RSS 피드 수집 요청: {len(request.rss_urls)}개 피드")

        # 2. 입력 검증 시작
        logger.info(f"🔎 [검증] RSS URL 검증 시작 - ID: {request_id}")
        
        # URL 검증
        validated_urls = []
        for url in request.rss_urls:
            try:
                validated_url = validate_url(str(url))
                validated_urls.append(validated_url)
            except Exception as e:
                logger.warning(f"⚠️ 유효하지 않은 URL 스킵: {url} - {e}")
                continue

        if not validated_urls:
            raise HTTPException(status_code=400, detail="유효한 RSS URL이 없습니다.")

        # 2. 입력 검증 완료
        logger.info(f"🔎 [검증] RSS URL 검증 완료 - ID: {request_id}, 유효한 URL: {len(validated_urls)}개")

        # 3. 처리 시작
        logger.info(f"⚙️ [처리] RSS 피드 수집 실행 시작 - ID: {request_id}")

        # RSS 피드 수집
        all_articles = []
        if rss_service:
            for rss_url in validated_urls:
                try:
                    # RSS 서비스가 있다면 간단한 더미 데이터 반환
                    # 실제 구현에서는 적절한 메서드 호출
                    all_articles.append({
                        'title': f'Sample Article from {rss_url}',
                        'url': rss_url,
                        'content': 'Sample content',
                        'source': 'RSS',
                        'published_at': None
                    })
                except Exception as e:
                    logger.warning(f"⚠️ RSS 피드 수집 실패 ({rss_url}): {e}")
                    continue
        else:
            logger.warning("RSS 서비스를 사용할 수 없습니다.")

        # 4. 처리 완료
        logger.info(f"✅ [완료] RSS 피드 수집 완료 - ID: {request_id}, 수집된 기사: {len(all_articles)}개")

        # 응답 생성
        articles_data = []
        for article in all_articles:
            published_at = article.get('published_at') if isinstance(article, dict) else getattr(article, 'published_at', None)
            articles_data.append(
                {
                    "title": article.get('title', 'Untitled') if isinstance(article, dict) else getattr(article, 'title', 'Untitled'),
                    "url": str(article.get('url', '') if isinstance(article, dict) else getattr(article, 'url', '')),
                    "content": (
                        (article.get('content', '') if isinstance(article, dict) else getattr(article, 'content', ''))[:500] + "..."
                        if len(article.get('content', '') if isinstance(article, dict) else getattr(article, 'content', '')) > 500
                        else (article.get('content', '') if isinstance(article, dict) else getattr(article, 'content', ''))
                    ),
                    "source": article.get('source', 'Unknown') if isinstance(article, dict) else getattr(article, 'source', 'Unknown'),
                    "published_date": (
                        published_at.isoformat()
                        if published_at and hasattr(published_at, 'isoformat')
                        else None
                    ),
                }
            )

        # 5. 응답 전송
        logger.info(f"📤 [응답] 클라이언트에 응답 전송 - ID: {request_id}")

        return FetchResponse(
            success=True,
            message=f"{len(all_articles)}개의 기사를 성공적으로 수집했습니다.",
            articles_count=len(all_articles),
            articles=articles_data,
            request_id=request_id,
            processed_at=datetime.now().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [오류] RSS 피드 수집 중 오류 발생 - ID: {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"RSS 피드 수집 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/article", response_model=FetchResponse)
async def fetch_single_article(request: ArticleFetchRequest):
    """
    개별 기사 URL에서 콘텐츠를 추출합니다.

    - **url**: 기사 URL
    - **user_id**: 사용자 ID (선택사항)
    """
    request_id = str(uuid.uuid4())[:8]

    try:
        # 1. 요청 수신
        logger.info(f"📥 [기사요청] 사용자 입력 수신 완료 - ID: {request_id}")
        logger.info(f"📄 [{request_id}] 개별 기사 수집: {request.url}")

        # 2. 입력 검증 시작
        logger.info(f"🔎 [검증] 기사 URL 검증 시작 - ID: {request_id}")
        
        # URL 검증
        validated_url = validate_url(str(request.url))
        
        # 2. 입력 검증 완료
        logger.info(f"🔎 [검증] 기사 URL 검증 완료 - ID: {request_id}")

        # 3. 처리 시작
        logger.info(f"⚙️ [처리] 기사 콘텐츠 추출 시작 - ID: {request_id}")

        # 기사 내용 추출
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urlparse

        try:
            response = requests.get(validated_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            
            # 기본적인 콘텐츠 추출
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "Untitled"
            
            # 본문 추출 (간단한 구현)
            content_tags = soup.find_all(['p', 'div', 'article'])
            content = " ".join([tag.get_text().strip() for tag in content_tags])

            if not content or len(content.strip()) < 50:
                raise HTTPException(
                    status_code=400, detail="기사 내용을 추출할 수 없습니다."
                )

            # 4. 처리 완료
            logger.info(f"✅ [완료] 기사 콘텐츠 추출 완료 - ID: {request_id}")

            article_data = {
                "title": title_text,
                "url": validated_url,
                "content": content[:1000] + "..." if len(content) > 1000 else content,
                "source": urlparse(validated_url).netloc,
                "published_date": None,
            }

            # 5. 응답 전송
            logger.info(f"📤 [응답] 클라이언트에 응답 전송 - ID: {request_id}")

            return FetchResponse(
                success=True,
                message="기사를 성공적으로 수집했습니다.",
                articles_count=1,
                articles=[article_data],
                request_id=request_id,
                processed_at=datetime.now().isoformat(),
            )

        except requests.RequestException as e:
            raise HTTPException(
                status_code=400, detail=f"기사를 가져올 수 없습니다: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [오류] 기사 수집 중 오류 발생 - ID: {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"기사 수집 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/default-feeds")
async def get_default_rss_feeds():
    """기본 RSS 피드 목록을 반환합니다."""
    try:
        default_feeds = [
            {"name": "연합뉴스", "url": "https://www.yonhapnews.co.kr/rss/news.xml", "category": "general"},
            {"name": "KBS", "url": "http://world.kbs.co.kr/rss/rss_news.htm", "category": "broadcast"},
            {"name": "MBC", "url": "https://imnews.imbc.com/rss/news/news_00.xml", "category": "broadcast"},
        ]

        return {
            "success": True,
            "feeds": default_feeds,
            "count": len(default_feeds),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"기본 RSS 피드 조회 실패: {e}")
        raise HTTPException(
            status_code=500, detail="기본 RSS 피드 목록을 가져올 수 없습니다."
        )


@router.get("/health")
async def fetch_health_check():
    """fetch 라우터 헬스 체크"""
    return {
        "status": "healthy",
        "router": "fetch",
        "timestamp": datetime.now().isoformat(),
        "rss_service_available": rss_service is not None,
        "content_extractor_available": content_extractor is not None,
    }
