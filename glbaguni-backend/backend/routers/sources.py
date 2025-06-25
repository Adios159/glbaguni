#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sources Router
언론사 목록 관련 엔드포인트
"""

import logging
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/sources", tags=["sources"])


class NewsSource(BaseModel):
    """뉴스 소스 모델"""
    name: str
    category: str
    rss_url: str


class SourcesResponse(BaseModel):
    """언론사 목록 응답 모델"""
    success: bool
    message: str
    sources: List[NewsSource]
    total_count: int


# 언론사 목록 데이터
NEWS_SOURCES = [
    # 종합지
    {
        "name": "한겨레",
        "category": "종합",
        "rss_url": "http://www.hani.co.kr/rss/"
    },
    {
        "name": "조선일보",
        "category": "종합",
        "rss_url": "https://www.chosun.com/arc/outboundfeeds/rss/"
    },
    {
        "name": "중앙일보",
        "category": "종합",
        "rss_url": "https://rss.joins.com/joins_news_list.xml"
    },
    {
        "name": "동아일보",
        "category": "종합",
        "rss_url": "https://rss.donga.com/total.xml"
    },
    {
        "name": "경향신문",
        "category": "종합",
        "rss_url": "http://www.khan.co.kr/rss/rssdata/total_news.xml"
    },
    
    # IT/테크
    {
        "name": "ZDNet Korea",
        "category": "IT",
        "rss_url": "https://www.zdnet.co.kr/news/news_list_rss.asp"
    },
    {
        "name": "전자신문",
        "category": "IT",
        "rss_url": "https://www.etnews.com/rss/news.xml"
    },
    {
        "name": "디지털타임스",
        "category": "IT",
        "rss_url": "https://www.dt.co.kr/rss/news.xml"
    },
    {
        "name": "아이뉴스24",
        "category": "IT",
        "rss_url": "https://www.inews24.com/rss/allnews.xml"
    },
    {
        "name": "블로터",
        "category": "IT",
        "rss_url": "https://www.bloter.net/feed/"
    },
    
    # 통신사
    {
        "name": "연합뉴스",
        "category": "통신",
        "rss_url": "https://www.yna.co.kr/rss/news.xml"
    },
    {
        "name": "뉴스1",
        "category": "통신",
        "rss_url": "https://www.news1.kr/rss/news.xml"
    },
    
    # 경제지
    {
        "name": "한국경제",
        "category": "경제",
        "rss_url": "https://www.hankyung.com/feed/all-news"
    },
    {
        "name": "매일경제",
        "category": "경제",
        "rss_url": "https://www.mk.co.kr/rss/30000001/"
    },
    {
        "name": "서울경제",
        "category": "경제",
        "rss_url": "https://www.sedaily.com/RSS/S1N1.xml"
    },
    
    # 방송사
    {
        "name": "SBS",
        "category": "방송",
        "rss_url": "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01"
    },
    {
        "name": "MBC",
        "category": "방송",
        "rss_url": "https://imnews.imbc.com/rss/news.xml"
    },
    {
        "name": "KBS",
        "category": "방송",
        "rss_url": "http://world.kbs.co.kr/rss/rss_news.htm?lang=k"
    },
    {
        "name": "YTN",
        "category": "방송",
        "rss_url": "https://www.ytn.co.kr/_comm/rss_list.php"
    },
    {
        "name": "JTBC",
        "category": "방송",
        "rss_url": "https://news.jtbc.joins.com/rss/news.xml"
    }
]


@router.get("/", response_model=SourcesResponse)
async def get_news_sources(category: Optional[str] = None):
    """
    언론사 목록을 조회합니다.
    
    Args:
        category: 카테고리 필터 (선택사항)
        
    Returns:
        SourcesResponse: 언론사 목록
        
    Example:
        GET /sources
        GET /sources?category=IT
    """
    try:
        # 카테고리 필터링
        if category:
            filtered_sources = [
                source for source in NEWS_SOURCES 
                if source["category"].lower() == category.lower()
            ]
            logger.info(f"언론사 목록 조회 완료 (카테고리: {category}): {len(filtered_sources)}개")
        else:
            filtered_sources = NEWS_SOURCES
            logger.info(f"전체 언론사 목록 조회 완료: {len(filtered_sources)}개")
        
        # NewsSource 객체로 변환
        sources = [NewsSource(**source) for source in filtered_sources]
        
        return SourcesResponse(
            success=True,
            message="언론사 목록을 성공적으로 조회했습니다.",
            sources=sources,
            total_count=len(sources)
        )
        
    except Exception as e:
        logger.error(f"언론사 목록 조회 중 오류: {e}")
        return SourcesResponse(
            success=False,
            message=f"언론사 목록 조회에 실패했습니다: {str(e)}",
            sources=[],
            total_count=0
        )


@router.get("/categories")
async def get_categories():
    """
    사용 가능한 카테고리 목록을 조회합니다.
    
    Returns:
        dict: 카테고리 목록
        
    Example:
        GET /sources/categories
    """
    try:
        # 중복 제거된 카테고리 목록 생성
        categories = list(set(source["category"] for source in NEWS_SOURCES))
        categories.sort()  # 알파벳 순 정렬
        
        logger.info(f"카테고리 목록 조회 완료: {len(categories)}개")
        
        return {
            "success": True,
            "message": "카테고리 목록을 성공적으로 조회했습니다.",
            "categories": categories,
            "total_count": len(categories)
        }
        
    except Exception as e:
        logger.error(f"카테고리 목록 조회 중 오류: {e}")
        return {
            "success": False,
            "message": f"카테고리 목록 조회에 실패했습니다: {str(e)}",
            "categories": [],
            "total_count": 0
        }


@router.get("/health")
async def sources_health_check():
    """
    Sources 라우터 헬스체크 엔드포인트
    
    Returns:
        dict: 상태 정보
    """
    return {
        "status": "healthy",
        "service": "news sources",
        "endpoints": {
            "sources": "GET /sources",
            "categories": "GET /sources/categories"
        },
        "total_sources": len(NEWS_SOURCES),
        "available_categories": list(set(source["category"] for source in NEWS_SOURCES))
    }
