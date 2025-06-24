#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
글바구니 (Glbaguni) - AI RSS Summarizer Backend v3.0.0
간결한 FastAPI 앱 정의 - 모든 기능 로직은 외부 모듈로 분리
"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

# ===== 환경변수 최우선 로드 =====
load_dotenv()

# ===== 로깅 시스템 설정 =====
try:
    from backend.utils.logging_config import setup_comprehensive_logging
except ImportError:
    from utils.logging_config import setup_comprehensive_logging

os.makedirs("logs", exist_ok=True)
logger = setup_comprehensive_logging()

# ===== 환경변수 검증 =====
try:
    from backend.utils.environment import validate_environment_comprehensive
except ImportError:
    from utils.environment import validate_environment_comprehensive

if not validate_environment_comprehensive():
    sys.exit(1)

# ===== 미들웨어 및 예외 핸들러 =====
try:
    from backend.utils.exception_handlers import (
        global_exception_handler,
        http_exception_handler,
        validation_exception_handler,
    )
    from backend.utils.middleware import logging_middleware
except ImportError:
    from utils.exception_handlers import (
        global_exception_handler,
        http_exception_handler,
        validation_exception_handler,
    )
    from utils.middleware import logging_middleware


# ===== 애플리케이션 라이프사이클 =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    startup_start = time.time()

    try:
        logger.info("🔧 서버 초기화 시작...")
        # 새로운 안전한 컴포넌트 관리자 사용
        from backend.utils.component_manager import initialize_all_components
        await initialize_all_components()

        startup_time = time.time() - startup_start
        logger.info(f"🎉 서버 초기화 완료! (소요시간: {startup_time:.2f}초)")

        yield

    except Exception as e:
        logger.error(f"❌ 서버 초기화 실패: {str(e)}")
        raise
    finally:
        logger.info("🔄 서버 종료 중...")
        # 새로운 안전한 컴포넌트 관리자 사용
        from backend.utils.component_manager import cleanup_components
        await cleanup_components()
        logger.info("✅ 서버 종료 완료")


# ===== FastAPI 앱 생성 =====
app = FastAPI(
    title="글바구니 (Glbaguni) - AI RSS Summarizer",
    description="AI 기반 RSS 요약 서비스 - 모듈화 구조",
    version="3.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ===== CORS 설정 =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 미들웨어 등록 =====
app.middleware("http")(logging_middleware)

# ===== 예외 핸들러 등록 =====
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)


# ===== 라우터 등록 =====
def register_routers():
    """모든 라우터를 앱에 등록"""
    import importlib.util
    
    routers_to_register = [
        ("core", "핵심 기능"),
        ("summarize", "요약 서비스"),
        ("health", "헬스체크"),
        ("auth", "인증 및 보안"),
        ("news", "뉴스 검색"),
        ("fetch", "데이터 수집"),
        ("history_router", "히스토리"),
    ]

    current_dir = os.path.dirname(os.path.abspath(__file__))

    for router_name, description in routers_to_register:
        try:
            # 직접 파일 import만 사용 (가장 안정적)
            router_file = os.path.join(current_dir, "routers", f"{router_name}.py")
            
            if not os.path.exists(router_file):
                logger.warning(f"⚠️ {description} 라우터 파일이 존재하지 않습니다: {router_file}")
                continue
                
            spec = importlib.util.spec_from_file_location(f"routers.{router_name}", router_file)
            if not spec or not spec.loader:
                logger.warning(f"⚠️ {description} 라우터 spec 생성 실패")
                continue
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "router"):
                app.include_router(module.router)
                logger.info(f"✅ {description} 라우터 등록 완료 ({router_name})")
            else:
                logger.warning(f"⚠️ {router_name} 모듈에 router 속성이 없습니다")

        except Exception as e:
            logger.error(f"❌ {description} 라우터 등록 중 오류 ({router_name}): {e}")
            import traceback
            logger.debug(f"상세 오류: {traceback.format_exc()}")


# 라우터 등록 실행
register_routers()

# ===== 프론트엔드 호환을 위한 추가 엔드포인트 =====
from fastapi import Request, Query
from pydantic import BaseModel
from typing import Optional, List

class NewsSearchRequest(BaseModel):
    """뉴스 검색 요청 모델"""
    query: str
    max_articles: int = 10
    language: str = "ko"
    recipient_email: Optional[str] = None
    user_id: Optional[str] = None

@app.post("/news-search")
async def news_search_compat(request: NewsSearchRequest, background_tasks: BackgroundTasks):
    """
    프론트엔드 호환용 뉴스 검색 엔드포인트
    NewsAggregator를 직접 사용하여 실제 뉴스 검색 수행
    """
    import uuid
    request_id = str(uuid.uuid4())[:8]
    
    try:
        logger.info(f"🔍 [{request_id}] 뉴스 검색 요청: '{request.query}'")
        
        # NewsAggregator를 직접 사용
        from backend.news_aggregator import NewsAggregator
        from backend.config import get_settings
        
        settings = get_settings()
        openai_api_key = getattr(settings, 'openai_api_key', None)
        
        # NewsAggregator 인스턴스 생성 및 검색 실행
        logger.info(f"🔄 [{request_id}] NewsAggregator 초기화 중...")
        news_aggregator = NewsAggregator(openai_api_key=openai_api_key)
        
        logger.info(f"🔄 [{request_id}] 뉴스 검색 실행 중...")
        news_articles, keywords = news_aggregator.process_news_query(
            query=request.query, 
            max_articles=min(request.max_articles, 20)
        )
        
        # 결과 변환
        articles = []
        for news_article in news_articles:
            articles.append({
                "title": news_article.title,
                "url": news_article.link,
                "content": news_article.content or news_article.summary,
                "source": news_article.source,
                "published_date": news_article.published_date,
                "summary": news_article.summary
            })
        
        logger.info(f"✅ [{request_id}] 뉴스 검색 완료: {len(articles)}개 기사")
        logger.info(f"🏷️ [{request_id}] 추출된 키워드: {keywords}")
        
        # 이메일 발송 (백그라운드 태스크)
        if request.recipient_email and articles:
            logger.info(f"📧 [{request_id}] 이메일 발송 예약: {request.recipient_email}")
            # 실제 이메일 발송 로직 구현
            background_tasks.add_task(send_news_email_background, request.recipient_email, request.query, articles, request_id)
        
        return {
            "success": True,
            "message": f"{len(articles)}개의 관련 뉴스를 찾았습니다.",
            "articles": articles,
            "extracted_keywords": keywords,
            "total_articles": len(articles),
            "request_id": request_id,
            "processed_at": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ [{request_id}] 뉴스 검색 오류: {e}")
        return {
            "success": False,
            "message": f"뉴스 검색 중 오류가 발생했습니다: {str(e)}",
            "articles": [],
            "extracted_keywords": [],
            "total_articles": 0,
            "request_id": request_id,
            "processed_at": time.time()
        }

# ===== 백그라운드 태스크 함수들 =====
async def send_news_email_background(recipient_email: str, query: str, articles: list, request_id: str):
    """뉴스 검색 결과 이메일 발송 (백그라운드 태스크)"""
    try:
        logger.info(f"📧 [{request_id}] 뉴스 이메일 발송 시작: {recipient_email}")
        
        # EmailNotifier와 ArticleSummary 임포트
        from backend.notifier import EmailNotifier
        from backend.models import ArticleSummary
        
        # EmailNotifier 인스턴스 생성
        email_notifier = EmailNotifier()
        
        # 기사들을 ArticleSummary 형태로 변환
        summaries = []
        for article in articles[:5]:  # 최대 5개만 이메일로 발송
            summary = ArticleSummary(
                title=article.get('title', '제목 없음'),
                url=article.get('url', ''),
                summary=article.get('summary', article.get('content', '')[:200] + '...'),
                source=article.get('source', '출처 불명'),
                original_length=len(article.get('content', '')),
                summary_length=len(article.get('summary', ''))
            )
            summaries.append(summary)
        
        if summaries:
            # 커스텀 제목으로 이메일 발송
            subject = f"🔍 '{query}' 뉴스 검색 결과 ({len(summaries)}개 기사)"
            success = email_notifier.send_summary_email(
                recipient=recipient_email,
                summaries=summaries,
                custom_subject=subject
            )
            
            if success:
                logger.info(f"✅ [{request_id}] 뉴스 이메일 발송 완료: {recipient_email}")
            else:
                logger.error(f"❌ [{request_id}] 뉴스 이메일 발송 실패: {recipient_email}")
        else:
            logger.warning(f"⚠️ [{request_id}] 발송할 기사가 없음")
            
    except Exception as e:
        logger.error(f"❌ [{request_id}] 뉴스 이메일 발송 중 오류: {e}")

# ===== 테스트용 이메일 엔드포인트 =====
@app.post("/test-email")
async def test_email_sending(request: dict):
    """이메일 발송 테스트 엔드포인트"""
    try:
        recipient = request.get("email", "")
        if not recipient:
            return {"success": False, "message": "이메일 주소가 필요합니다."}
        
        logger.info(f"📧 이메일 테스트 요청: {recipient}")
        
        # EmailNotifier 임포트 및 초기화
        from backend.notifier import EmailNotifier
        email_notifier = EmailNotifier()
        
        # 테스트 이메일 발송
        success = email_notifier.send_test_email(recipient)
        
        if success:
            return {"success": True, "message": f"테스트 이메일이 {recipient}로 발송되었습니다."}
        else:
            return {"success": False, "message": "이메일 발송에 실패했습니다. SMTP 설정을 확인해주세요."}
            
    except Exception as e:
        logger.error(f"❌ 이메일 테스트 오류: {e}")
        return {"success": False, "message": f"오류: {str(e)}"}

# ===== 히스토리 및 추천 엔드포인트 =====
@app.get("/history")
async def get_history(
    user_id: str = Query(..., description="사용자 ID"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    per_page: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    language: Optional[str] = Query(None, description="언어 필터 (ko/en)")
):
    """사용자 히스토리 조회"""
    try:
        logger.info(f"📚 히스토리 조회 요청: user_id={user_id}, page={page}")
        
        # 임시로 빈 데이터 반환 (나중에 실제 DB 조회로 교체)
        return {
            "success": True,
            "history": [],
            "total_items": 0,
            "current_page": page,
            "per_page": per_page,
            "total_pages": 0
        }
        
    except Exception as e:
        logger.error(f"❌ 히스토리 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="히스토리 조회 중 오류가 발생했습니다")

@app.get("/recommendations")
async def get_recommendations(
    user_id: str = Query(..., description="사용자 ID"),
    max_recommendations: int = Query(10, ge=1, le=20, description="최대 추천 개수")
):
    """사용자 맞춤 추천"""
    try:
        logger.info(f"🔥 추천 요청: user_id={user_id}, max={max_recommendations}")
        
        # 임시로 빈 데이터 반환 (나중에 실제 추천 로직으로 교체)
        return {
            "success": True,
            "recommendations": [],
            "total_recommendations": 0,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"❌ 추천 조회 오류: {e}")
        raise HTTPException(status_code=500, detail="추천 조회 중 오류가 발생했습니다")

@app.post("/recommendation-click")
async def log_recommendation_click(
    user_id: str = Query(..., description="사용자 ID"),
    article_url: str = Query(..., description="기사 URL")
):
    """추천 클릭 로깅"""
    try:
        logger.info(f"👆 추천 클릭 로그: user_id={user_id}, url={article_url}")
        
        return {
            "success": True,
            "message": "클릭이 기록되었습니다"
        }
        
    except Exception as e:
        logger.error(f"❌ 추천 클릭 로그 오류: {e}")
        raise HTTPException(status_code=500, detail="클릭 로그 기록 중 오류가 발생했습니다")

# ===== 애플리케이션 준비 완료 =====
logger.info("🎉 글바구니 백엔드 애플리케이션이 준비되었습니다!")
logger.info("💡 실행 방법: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload")

# 참고: 직접 실행은 uvicorn을 통해서만 지원됩니다.
# python -m backend.main 대신 다음 명령어를 사용하세요:
# uvicorn backend.main:app --reload

