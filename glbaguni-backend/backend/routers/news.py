#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
News Router
뉴스 검색 및 자연어 처리 관련 엔드포인트
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

# 의존성 임포트
try:
    from database import get_db
    from models import NewsSearchRequest, NewsSearchResponse
    from services.gpt_service import GPTService
    from services.news_service import NewsService
    from utils.validator import validate_user_input
except ImportError:
    try:
        from backend.database import get_db
        from backend.models import NewsSearchRequest, NewsSearchResponse
        from backend.services.gpt_service import GPTService
        from backend.services.news_service import NewsService
        from backend.utils.validator import validate_user_input
    except ImportError:
        # 기본값으로 None 또는 Mock 객체 사용
        get_db = None
        NewsSearchRequest = None
        NewsSearchResponse = None
        GPTService = None
        NewsService = None
        def validate_user_input(text: str, max_length: int = 5000) -> str:
            return text

import logging

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/news", tags=["news"])


# 요청/응답 모델
class SearchQueryRequest(BaseModel):
    """뉴스 검색 쿼리 요청"""

    query: str
    max_articles: int = 10
    language: str = "ko"
    user_id: Optional[str] = None


class KeywordExtractionRequest(BaseModel):
    """키워드 추출 요청"""

    text: str
    max_keywords: int = 10


# 서비스 인스턴스 (안전한 초기화)
try:
    news_service = NewsService() if NewsService else None
except Exception:
    news_service = None


@router.post("/search")
async def search_news(
    request: SearchQueryRequest,
    background_tasks: BackgroundTasks,
):
    """
    자연어 쿼리로 뉴스를 검색합니다.

    - **query**: 검색할 뉴스 주제 (예: "요즘 반도체 뉴스 알려줘")
    - **max_articles**: 최대 기사 수 (기본값: 10)
    - **language**: 요약 언어 (ko/en)
    - **user_id**: 사용자 ID (선택사항)
    """
    request_id = str(uuid.uuid4())[:8]

    try:
        # 1. 요청 수신
        logger.info(f"📥 [뉴스검색] 사용자 입력 수신 완료 - ID: {request_id}")
        logger.info(f"🔍 [{request_id}] 뉴스 검색 요청: '{request.query}'")

        # 2. 입력 검증 시작
        logger.info(f"🔎 [검증] 검색 쿼리 검증 시작 - ID: {request_id}")

        # 입력 검증 (매개변수 순서 수정)
        validated_query = validate_user_input(request.query, 1000)

        if len(validated_query.strip()) < 2:
            raise HTTPException(status_code=400, detail="검색 쿼리가 너무 짧습니다.")

        # 2. 입력 검증 완료
        logger.info(f"🔎 [검증] 검색 쿼리 검증 완료 - ID: {request_id}")

        # 3. 처리 시작
        logger.info(f"⚙️ [처리] 뉴스 검색 실행 시작 - ID: {request_id}")

        # 뉴스 검색 실행 (실제 메서드 사용)
        if news_service:
            search_result = await news_service.search_news(
                query=validated_query,
                max_results=request.max_articles,
                sources=None
            )
        else:
            search_result = []

        # 4. 처리 완료
        logger.info(f"✅ [완료] 뉴스 검색 완료 - ID: {request_id}: {len(search_result)}개 기사")

        # 5. 응답 전송
        logger.info(f"📤 [응답] 클라이언트에 응답 전송 - ID: {request_id}")

        return {
            "success": True,
            "message": f"{len(search_result)}개의 관련 뉴스를 찾았습니다.",
            "articles": [
                {
                    "title": article.title,
                    "url": str(article.url),
                    "content": article.content[:500] + "..." if len(article.content) > 500 else article.content,
                    "source": article.source,
                    "published_date": article.published_at.isoformat() if article.published_at else None,
                }
                for article in search_result
            ],
            "extracted_keywords": [],  # 키워드 추출은 별도 구현 필요
            "total_articles": len(search_result),
            "request_id": request_id,
            "processed_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [오류] 뉴스 검색 중 오류 발생 - ID: {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"뉴스 검색 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/extract-keywords")
async def extract_keywords(request: KeywordExtractionRequest):
    """
    텍스트에서 키워드를 추출합니다.

    - **text**: 키워드를 추출할 텍스트
    - **max_keywords**: 최대 키워드 수
    """
    request_id = str(uuid.uuid4())[:8]

    try:
        # 1. 요청 수신
        logger.info(f"📥 [키워드추출] 사용자 입력 수신 완료 - ID: {request_id}")
        logger.info(f"🏷️ [{request_id}] 키워드 추출 요청")

        # 2. 입력 검증 시작
        logger.info(f"🔎 [검증] 텍스트 검증 시작 - ID: {request_id}")

        # 입력 검증 (매개변수 순서 수정)
        validated_text = validate_user_input(request.text, 10000)

        # 2. 입력 검증 완료
        logger.info(f"🔎 [검증] 텍스트 검증 완료 - ID: {request_id}")

        # 3. 처리 시작
        logger.info(f"⚙️ [처리] 키워드 추출 실행 시작 - ID: {request_id}")

        # 간단한 키워드 추출 구현 (실제로는 NLP 라이브러리 사용)
        import re
        words = re.findall(r'\b\w+\b', validated_text)
        keywords = list(set(word for word in words if len(word) > 2))[:request.max_keywords]

        # 4. 처리 완료
        logger.info(f"✅ [완료] 키워드 추출 완료 - ID: {request_id}: {len(keywords)}개")

        # 5. 응답 전송
        logger.info(f"📤 [응답] 클라이언트에 응답 전송 - ID: {request_id}")

        return {
            "success": True,
            "keywords": keywords,
            "count": len(keywords),
            "request_id": request_id,
            "processed_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [오류] 키워드 추출 중 오류 발생 - ID: {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"키워드 추출 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/trending")
async def get_trending_news(category: Optional[str] = None, limit: int = 20):
    """
    트렌딩 뉴스를 가져옵니다.

    - **category**: 카테고리 필터 (선택사항)
    - **limit**: 최대 기사 수
    """
    try:
        # 임시 구현 - 실제로는 트렌딩 뉴스 API 사용
        trending_news = []

        return {
            "success": True,
            "trending_news": trending_news,
            "count": len(trending_news),
            "category": category or "all",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"트렌딩 뉴스 조회 실패: {e}")
        raise HTTPException(
            status_code=500, detail=f"트렌딩 뉴스 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/sources")
async def get_news_sources():
    """사용 가능한 뉴스 소스 목록을 반환합니다."""
    try:
        # 기본 뉴스 소스 목록
        sources = [
            {"name": "네이버 뉴스", "type": "portal", "language": "ko"},
            {"name": "다음 뉴스", "type": "portal", "language": "ko"},
            {"name": "연합뉴스", "type": "agency", "language": "ko"},
            {"name": "KBS", "type": "broadcast", "language": "ko"},
            {"name": "MBC", "type": "broadcast", "language": "ko"},
        ]

        return {
            "success": True,
            "sources": sources,
            "count": len(sources),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"뉴스 소스 조회 실패: {e}")
        raise HTTPException(
            status_code=500, detail="뉴스 소스 목록을 가져올 수 없습니다."
        )


@router.get("/health")
async def news_health_check():
    """뉴스 라우터 헬스 체크"""
    return {
        "status": "healthy",
        "router": "news",
        "timestamp": datetime.now().isoformat(),
        "news_service_available": news_service is not None,
    }
