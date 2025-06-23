#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
최적화된 글바구니 백엔드 서버
- 향상된 로깅 시스템
- 환경 변수 안정화
- 비동기 HTTP 처리
- 공통 예외 처리
- GPT API 안정화
- 입력 검증 강화
- 헬스 체크 개선
"""

import os
import sys
import logging
import asyncio
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
import json
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

try:
    # 상대 임포트 시도 (모듈로 실행될 때)
    from .models import (
        SummaryRequest, SummaryResponse, ArticleSummary, 
        HistoryResponse, RecommendationResponse, UserStatsResponse,
        HistoryItem, RecommendationItem, NewsSearchRequest, NewsSearchResponse,
        Article
    )
    from .fetcher import ArticleFetcher
    from .summarizer import ArticleSummarizer
    from .notifier import EmailNotifier
    from .config import settings
    from .database import get_db, init_database
    from .history_service import HistoryService
    from .news_aggregator import NewsAggregator
    from .security import validate_input, sanitize_response
    SECURITY_AVAILABLE = True
except ImportError:
    # 절대 임포트로 폴백 (직접 실행될 때)
    from models import (
        SummaryRequest, SummaryResponse, ArticleSummary, 
        HistoryResponse, RecommendationResponse, UserStatsResponse,
        HistoryItem, RecommendationItem, NewsSearchRequest, NewsSearchResponse,
        Article
    )
    from fetcher import ArticleFetcher
    from summarizer import ArticleSummarizer
    from notifier import EmailNotifier
    from config import settings
    from database import get_db, init_database
    from history_service import HistoryService
    from news_aggregator import NewsAggregator
    try:
        from security import validate_input, sanitize_response
        SECURITY_AVAILABLE = True
    except ImportError:
        SECURITY_AVAILABLE = False

# ✅ 1. 기본 로깅 시스템 설정
def setup_logging():
    """로깅 시스템 설정"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("glbaguni_backend.log", encoding="utf-8")
        ]
    )
    
    # uvicorn 로깅 조정
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)
    
    return logging.getLogger(__name__)

# 로깅 설정
logger = setup_logging()

# ✅ 2. 환경 변수 안정화
def validate_environment():
    """환경 변수 검증"""
    required_vars = ['OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ 필수 환경 변수가 누락되었습니다: {', '.join(missing_vars)}")
        logger.error("서버를 종료합니다. .env 파일을 확인해주세요.")
        sys.exit(1)
    
    logger.info("✅ 환경 변수 검증 완료")

# 환경 변수 검증 실행
validate_environment()

# 전역 변수들
http_client: Optional[httpx.AsyncClient] = None
news_aggregator: Optional[NewsAggregator] = None
fetcher: Optional[ArticleFetcher] = None
summarizer: Optional[ArticleSummarizer] = None
notifier: Optional[EmailNotifier] = None
history_service: Optional[HistoryService] = None

# ✅ 라이프사이클 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    global http_client, news_aggregator, fetcher, summarizer, notifier, history_service
    
    try:
        # 시작 시 초기화
        logger.info("🚀 서버 시작 중...")
        
        # HTTP 클라이언트 초기화
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        # 데이터베이스 초기화
        init_database()
        logger.info("✅ 데이터베이스 초기화 완료")
        
        # 컴포넌트 초기화
        fetcher = ArticleFetcher()
        summarizer = ArticleSummarizer()
        notifier = EmailNotifier()
        history_service = HistoryService()
        news_aggregator = NewsAggregator(openai_api_key=settings.OPENAI_API_KEY)
        
        logger.info("✅ 모든 컴포넌트 초기화 완료")
        logger.info("🎉 서버 시작 완료!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 서버 시작 실패: {e}")
        raise
    finally:
        # 종료 시 정리
        logger.info("🔄 서버 종료 중...")
        if http_client:
            await http_client.aclose()
        logger.info("✅ 서버 종료 완료")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="글바구니 (Glbaguni) - AI RSS Summarizer",
    description="AI-powered RSS feed summarization service with enhanced stability and performance",
    version="2.1.0",
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 4. 공통 예외 처리 핸들러
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail} - URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 오류 처리"""
    logger.error(f"Validation Error: {exc.errors()} - URL: {request.url}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": "입력 데이터 검증 실패",
            "details": exc.errors(),
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    logger.error(f"Unexpected Error: {str(exc)} - URL: {request.url}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "timestamp": datetime.now().isoformat()
        }
    )

# ✅ 요청/응답 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """요청/응답 로깅"""
    start_time = time.time()
    
    # 요청 로깅
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"📥 {request.method} {request.url} - 클라이언트: {client_host}")
    
    # 요청 처리
    response = await call_next(request)
    
    # 응답 로깅
    process_time = time.time() - start_time
    logger.info(f"📤 {request.method} {request.url} - 상태: {response.status_code} - 처리시간: {process_time:.2f}초")
    
    return response

# ✅ 6. 입력 검증 유틸리티
def validate_and_sanitize_input(text: str, max_length: int = 1000) -> str:
    """입력 텍스트 검증 및 정화"""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="입력 텍스트가 비어있습니다.")
    
    # 길이 제한
    if len(text) > max_length:
        raise HTTPException(status_code=400, detail=f"입력 텍스트가 너무 깁니다. (최대 {max_length}자)")
    
    # 금지된 특수문자 필터링
    dangerous_patterns = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe.*?>.*?</iframe>'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise HTTPException(status_code=400, detail="허용되지 않는 문자가 포함되어 있습니다.")
    
    # 보안 검증 적용 (있는 경우)
    if SECURITY_AVAILABLE:
        try:
            return validate_input(text, "text")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"입력 검증 실패: {str(e)}")
    
    return text.strip()

# ✅ 5. GPT API 호출 안정화
async def safe_gpt_call(prompt: str, max_retries: int = 3) -> str:
    """안전한 GPT API 호출"""
    for attempt in range(max_retries):
        try:
            logger.info(f"🤖 GPT API 호출 시도 {attempt + 1}/{max_retries}")
            
            # summarizer가 초기화되었는지 확인
            if summarizer and hasattr(summarizer, 'summarize'):
                result = await asyncio.to_thread(summarizer.summarize, prompt)
                # 결과가 문자열인지 확인
                if isinstance(result, str):
                    logger.info("✅ GPT API 호출 성공")
                    return result
                else:
                    # dict 또는 다른 타입인 경우
                    logger.warning(f"⚠️ 예상과 다른 응답 타입: {type(result)}")
                    if isinstance(result, dict) and 'summary' in result:
                        return str(result['summary'])
                    else:
                        return str(result)
            else:
                # 대안으로 간단한 요약 반환
                sentences = prompt.split('.')[:3]
                result = '. '.join(sentences) + '.'
                logger.info("✅ 간단 요약 완료")
                return result
            
        except Exception as e:
            logger.error(f"❌ GPT API 호출 실패 (시도 {attempt + 1}): {str(e)}")
            
            if attempt == max_retries - 1:
                logger.error("❌ 모든 GPT API 호출 시도 실패")
                return "죄송합니다. 현재 AI 서비스에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
            
            # 재시도 전 대기
            await asyncio.sleep(2 ** attempt)  # 지수 백오프
    
    return "요약을 생성할 수 없습니다."

# API 엔드포인트들

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "글바구니 (Glbaguni)",
        "description": "안정성과 성능이 향상된 AI 기반 RSS 요약 서비스",
        "version": "2.1.0",
        "features": [
            "RSS 요약", 
            "사용자 히스토리", 
            "개인화 추천", 
            "다국어 지원",
            "비동기 처리",
            "향상된 오류 처리"
        ],
        "status": "running"
    }

# ✅ 7. 향상된 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    """향상된 헬스 체크"""
    try:
        # 기본 상태
        health_status: Dict[str, Any] = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "version": "2.1.0"
        }
        
        # 외부 서비스 상태 확인
        checks: Dict[str, str] = {}
        
        # OpenAI API 키 확인
        checks["openai_api"] = "configured" if os.getenv("OPENAI_API_KEY") else "not_configured"
        
        # 데이터베이스 연결 확인
        try:
            db = next(get_db())
            db.execute(text("SELECT 1"))
            db.close()
            checks["database"] = "healthy"
        except Exception as e:
            checks["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        # HTTP 클라이언트 상태 확인
        if http_client and not http_client.is_closed:
            checks["http_client"] = "healthy"
        else:
            checks["http_client"] = "error"
        
        health_status["checks"] = checks
        
        # 전체 상태 결정
        if any("error" in str(v) for v in checks.values()):
            health_status["status"] = "unhealthy"
        
        return health_status
        
    except Exception as e:
        logger.error(f"❌ 헬스 체크 실패: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/test")
async def test_endpoint():
    """개선된 테스트 엔드포인트"""
    return {
        "message": "백엔드 서버가 정상 작동 중입니다!",
        "port": 8001,
        "timestamp": datetime.now().isoformat(),
        "features_enabled": {
            "security": SECURITY_AVAILABLE,
            "async_http": http_client is not None,
            "logging": True
        }
    }

# ✅ 향상된 요약 엔드포인트
@app.post("/summarize", response_model=SummaryResponse)
async def summarize_articles(
    request: SummaryRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """향상된 기사 요약 엔드포인트"""
    start_time = time.time()
    max_processing_time = 120  # 최대 2분
    
    try:
        logger.info(f"🚀 요약 요청 시작 - 사용자: {request.user_id}")
        
        # 입력 검증
        if not request.rss_urls and not request.article_urls:
            raise HTTPException(
                status_code=400, 
                detail="최소 하나의 RSS URL 또는 기사 URL이 필요합니다."
            )
        
        # 사용자 ID 생성
        if history_service:
            user_id = request.user_id or history_service.generate_user_id()
        else:
            user_id = request.user_id or str(uuid.uuid4())
        
        # 처리 제한
        max_articles = min(request.max_articles or 10, 15)
        
        # RSS URL 검증 및 제한
        rss_urls = None
        if request.rss_urls:
            rss_urls = [str(url) for url in request.rss_urls[:5]]  # 최대 5개
        
        # 기사 URL 검증 및 제한
        article_urls = None
        if request.article_urls:
            article_urls = [str(url) for url in request.article_urls[:10]]  # 최대 10개
        
        logger.info(f"📊 처리 대상: RSS {len(rss_urls) if rss_urls else 0}개, 기사 {len(article_urls) if article_urls else 0}개")
        
        # 시간 초과 체크
        if time.time() - start_time > max_processing_time:
            raise HTTPException(status_code=408, detail="요청 시간 초과")
        
        # 비동기로 기사 가져오기
        if fetcher:
            articles = await asyncio.to_thread(
                fetcher.fetch_multiple_sources,
                rss_urls=rss_urls,
                article_urls=article_urls,
                max_articles=max_articles
            )
        else:
            articles = []
        
        if not articles:
            logger.warning("❌ 가져온 기사가 없습니다")
            return SummaryResponse(
                success=False,
                message="제공된 소스에서 기사를 가져올 수 없습니다.",
                total_articles=0,
                processed_at=datetime.now(),
                user_id=user_id
            )
        
        logger.info(f"📝 {len(articles)}개 기사 가져오기 완료")
        
        # 기사 요약 (안전한 GPT 호출)
        summaries = []
        for article in articles:
            try:
                # Article 객체가 아닌 경우 건너뛰기
                if not hasattr(article, 'title') or not hasattr(article, 'content'):
                    continue
                
                summary = await safe_gpt_call(f"제목: {article.title}\n내용: {article.content}")
                summaries.append(ArticleSummary(
                    title=article.title,
                    url=str(article.url),
                    summary=summary,
                    source=getattr(article, 'source', 'unknown'),
                    original_length=len(article.content),
                    summary_length=len(summary)
                ))
            except Exception as e:
                logger.error(f"❌ 기사 요약 실패: {str(e)}")
                continue
        
        # 이메일 발송 (백그라운드)
        if request.recipient_email and summaries:
            background_tasks.add_task(
                send_summary_email,
                request.recipient_email,
                summaries
            )
        
        # 히스토리 저장 (백그라운드)
        if summaries:
            background_tasks.add_task(
                save_to_history,
                user_id,
                summaries,
                db
            )
        
        processing_time = time.time() - start_time
        logger.info(f"✅ 요약 완료 - 처리시간: {processing_time:.2f}초, 요약 {len(summaries)}개")
        
        return SummaryResponse(
            success=True,
            message=f"{len(summaries)}개 기사가 성공적으로 요약되었습니다.",
            summaries=summaries,
            total_articles=len(summaries),
            processed_at=datetime.now(),
            user_id=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 요약 처리 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="요약 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )

# ✅ 향상된 텍스트 요약 엔드포인트
@app.post("/summarize-text")
async def summarize_text_endpoint(request: Request):
    """향상된 텍스트 요약 엔드포인트"""
    try:
        body = await request.json()
        text = body.get("text", "")
        user_id = body.get("user_id", "")
        
        # 입력 검증 및 정화
        validated_text = validate_and_sanitize_input(text, max_length=5000)
        
        logger.info(f"📝 텍스트 요약 요청 - 길이: {len(validated_text)}자")
        
        # 안전한 GPT 호출
        summary = await safe_gpt_call(validated_text)
        
        # 보안 응답 정화 (있는 경우)
        if SECURITY_AVAILABLE:
            try:
                # sanitize_response가 Dict를 받는 경우를 위한 래퍼
                response_data = {"summary": summary}
                sanitized_data = sanitize_response(response_data)
                summary = sanitized_data.get("summary", summary)
            except Exception as e:
                logger.warning(f"응답 정화 실패: {str(e)}")
        
        logger.info("✅ 텍스트 요약 완료")
        
        return {
            "success": True,
            "summary": summary,
            "original_length": len(validated_text),
            "summary_length": len(summary),
            "processed_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 텍스트 요약 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="텍스트 요약 중 오류가 발생했습니다."
        )

# 기존 엔드포인트들 (개선된 에러 처리 포함)
@app.get("/history", response_model=HistoryResponse)
async def get_user_history(
    user_id: str = Query(..., description="User ID for history retrieval"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    language: Optional[str] = Query(None, description="Filter by language (ko/en)"),
    db: Session = Depends(get_db)
):
    """사용자 히스토리 조회 (향상된 에러 처리)"""
    try:
        logger.info(f"📚 히스토리 조회 요청 - 사용자: {user_id}, 페이지: {page}")
        
        if history_service:
            history_data = await asyncio.to_thread(
                history_service.get_user_history,
                db, user_id, page, per_page, language
            )
        else:
            history_data = ([], 0)
        
        # history_data가 tuple인 경우 처리
        if isinstance(history_data, tuple) and len(history_data) == 2:
            history_items, total_count = history_data
            
            # HistoryItem으로 변환
            formatted_items = []
            for item in history_items:
                try:
                    keywords = json.loads(item.keywords if item.keywords else "[]")
                except:
                    keywords = []
                
                formatted_items.append(HistoryItem(
                    id=item.id,
                    article_title=item.article_title,
                    article_url=item.article_url,
                    article_source=item.article_source,
                    content_excerpt=item.content_excerpt,
                    summary_text=item.summary_text,
                    summary_language=item.summary_language,
                    original_length=item.original_length,
                    summary_length=item.summary_length,
                    keywords=keywords,
                    created_at=item.created_at
                ))
            
            logger.info(f"✅ 히스토리 조회 완료 - {len(formatted_items)}개 항목")
            return HistoryResponse(
                success=True,
                history=formatted_items,
                total_items=total_count,
                page=page,
                per_page=per_page
            )
        else:
            raise ValueError("Invalid history data format")
        
    except Exception as e:
        logger.error(f"❌ 히스토리 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="히스토리 조회 중 오류가 발생했습니다."
        )

# 백그라운드 작업 함수들
async def send_summary_email(recipient_email: str, summaries: List[ArticleSummary]):
    """이메일 발송 (백그라운드 작업)"""
    try:
        logger.info(f"📧 이메일 발송 시작: {recipient_email}")
        if notifier:
            await asyncio.to_thread(notifier.send_summary_email, recipient_email, summaries)
        logger.info("✅ 이메일 발송 완료")
    except Exception as e:
        logger.error(f"❌ 이메일 발송 실패: {str(e)}")

async def save_to_history(user_id: str, summaries: List[ArticleSummary], db: Session):
    """히스토리 저장 (백그라운드 작업)"""
    try:
        logger.info(f"💾 히스토리 저장 시작: {user_id}")
        if history_service:
            # 각 요약을 개별적으로 저장
            for summary in summaries:
                # Article 객체로 변환
                from pydantic import HttpUrl
                try:
                    url = HttpUrl(summary.url) if isinstance(summary.url, str) else summary.url
                except Exception:
                    url = HttpUrl("https://example.com")
                
                article = Article(
                    title=summary.title,
                    url=url,
                    content=f"요약: {summary.summary}",
                    source=summary.source
                )
                await asyncio.to_thread(
                    history_service.save_summary_history,
                    db, user_id, article, summary.summary, "ko",
                    summary.original_length, summary.summary_length
                )
        logger.info("✅ 히스토리 저장 완료")
    except Exception as e:
        logger.error(f"❌ 히스토리 저장 실패: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 FastAPI 서버를 직접 실행합니다...")
    uvicorn.run(
        "main_optimized:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    ) 