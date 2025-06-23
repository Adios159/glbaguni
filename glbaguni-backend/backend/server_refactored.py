#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
글바구니 백엔드 서버 v3.0.0 - 완전 리팩토링 버전
"""

import os
import sys
import logging
import asyncio
import time
import traceback
from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid
import json
import re
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
from pydantic import HttpUrl

# 환경변수 로드
load_dotenv()

# 모듈 임포트
try:
    from .models import *
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
    from models import *
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

# 로깅 설정
def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/server.log", encoding="utf-8")
        ]
    )
    for logger_name in ["httpx", "httpcore", "urllib3"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    logger = logging.getLogger("glbaguni")
    logger.info("🚀 글바구니 서버 v3.0.0 시작")
    return logger

logger = setup_logging()

# 환경변수 검증
def validate_env():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or not api_key.startswith('sk-'):
        logger.error("❌ OPENAI_API_KEY 누락 또는 잘못된 형식")
        return False
    logger.info("✅ 환경변수 검증 완료")
    return True

if not validate_env():
    sys.exit(1)

# 전역 컴포넌트
class Components:
    http_client: Optional[httpx.AsyncClient] = None
    fetcher: Optional[ArticleFetcher] = None
    summarizer: Optional[ArticleSummarizer] = None
    notifier: Optional[EmailNotifier] = None
    history_service: Optional[HistoryService] = None
    news_aggregator: Optional[NewsAggregator] = None

comp = Components()

# 유틸리티 함수들
async def safe_call(func, *args, **kwargs):
    """안전한 함수 호출"""
    try:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return await asyncio.to_thread(func, *args, **kwargs)
    except Exception as e:
        logger.error(f"함수 호출 실패: {func.__name__} - {str(e)}")
        raise

def validate_input_text(text: str, max_len: int = 5000) -> str:
    """입력 텍스트 검증"""
    if not text or not text.strip():
        raise HTTPException(400, "텍스트가 비어있습니다")
    
    text = text.strip()
    if len(text) > max_len:
        raise HTTPException(400, f"텍스트가 너무 깁니다 (최대 {max_len}자)")
    
    # XSS 방지
    dangerous = [r'<script', r'javascript:', r'on\w+\s*=']
    for pattern in dangerous:
        if re.search(pattern, text, re.IGNORECASE):
            raise HTTPException(400, "위험한 문자 패턴 감지")
    
    return text

def error_response(code: str, msg: str, status: int = 500) -> Dict:
    """표준 에러 응답"""
    return {
        "success": False,
        "error_code": code,
        "message": msg,
        "timestamp": datetime.now().isoformat(),
        "request_id": str(uuid.uuid4())[:8]
    }

# 앱 라이프사이클
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_time = time.time()
    
    try:
        logger.info("🔧 컴포넌트 초기화...")
        
        # HTTP 클라이언트
        comp.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=20)
        )
        
        # 데이터베이스
        await safe_call(init_database)
        
        # 컴포넌트들
        comp.fetcher = ArticleFetcher()
        comp.summarizer = ArticleSummarizer()
        comp.history_service = HistoryService()
        comp.news_aggregator = NewsAggregator(openai_api_key=settings.OPENAI_API_KEY)
        
        try:
            comp.notifier = EmailNotifier()
            logger.info("✅ 이메일 서비스 초기화")
        except Exception as e:
            logger.warning(f"⚠️ 이메일 서비스 실패: {e}")
            comp.notifier = None
        
        elapsed = time.time() - start_time
        logger.info(f"🎉 초기화 완료! ({elapsed:.2f}초)")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 초기화 실패: {e}")
        raise
    finally:
        logger.info("🔄 서버 종료...")
        if comp.http_client:
            await comp.http_client.aclose()

# FastAPI 앱
app = FastAPI(
    title="글바구니 RSS 요약 서비스",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    req_id = str(uuid.uuid4())[:8]
    
    client = request.client.host if request.client else "unknown"
    logger.info(f"📥 [{req_id}] {request.method} {request.url.path} from {client}")
    
    try:
        response = await call_next(request)
        elapsed = time.time() - start
        logger.info(f"📤 [{req_id}] {response.status_code} in {elapsed:.3f}s")
        return response
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"💥 [{req_id}] Error in {elapsed:.3f}s: {e}")
        raise

# 예외 핸들러
@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(f"HTTP_{exc.status_code}", exc.detail, exc.status_code)
    )

@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    error_id = str(uuid.uuid4())[:8]
    logger.error(f"💥 Unexpected error [{error_id}]: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content=error_response(
            "INTERNAL_ERROR",
            "서버 오류가 발생했습니다",
            500
        )
    )

# API 엔드포인트들
@app.get("/")
async def root():
    return {
        "service": "글바구니 RSS 요약 서비스",
        "version": "3.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    start = time.time()
    status = {"status": "healthy", "timestamp": datetime.now().isoformat()}
    checks = {}
    
    try:
        # 환경변수
        checks["env"] = {
            "openai": "✅" if os.getenv("OPENAI_API_KEY") else "❌",
            "smtp": "✅" if os.getenv("SMTP_USERNAME") else "⚠️"
        }
        
        # 데이터베이스
        try:
            db = next(get_db())
            await asyncio.to_thread(db.execute, text("SELECT 1"))
            db.close()
            checks["database"] = "✅"
        except Exception:
            checks["database"] = "❌"
            status["status"] = "degraded"
        
        # 컴포넌트
        checks["components"] = {
            "fetcher": "✅" if comp.fetcher else "❌",
            "summarizer": "✅" if comp.summarizer else "❌",
            "notifier": "✅" if comp.notifier else "⚠️"
        }
        
        status["checks"] = checks
        status["response_time_ms"] = round((time.time() - start) * 1000, 2)
        
        return status
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/debug")
async def debug():
    return {
        "env": {
            "OPENAI_API_KEY": "SET" if os.getenv("OPENAI_API_KEY") else "NOT_SET",
            "SMTP_USERNAME": "SET" if os.getenv("SMTP_USERNAME") else "NOT_SET"
        },
        "components": {
            "http_client": bool(comp.http_client),
            "fetcher": bool(comp.fetcher),
            "summarizer": bool(comp.summarizer),
            "notifier": bool(comp.notifier)
        },
        "security": SECURITY_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/summarize")
async def summarize_articles(request: SummaryRequest, bg: BackgroundTasks, db: Session = Depends(get_db)):
    req_id = str(uuid.uuid4())[:8]
    logger.info(f"🚀 [{req_id}] 요약 요청 시작")
    
    try:
        if not request.rss_urls and not request.article_urls:
            raise HTTPException(400, "RSS URL 또는 기사 URL이 필요합니다")
        
        user_id = request.user_id or str(uuid.uuid4())
        max_articles = min(request.max_articles or 10, 20)
        
        rss_urls = [str(url) for url in (request.rss_urls or [])[:10]]
        article_urls = [str(url) for url in (request.article_urls or [])[:15]]
        
        logger.info(f"📊 [{req_id}] RSS: {len(rss_urls)}, 기사: {len(article_urls)}")
        
        # 기사 수집
        if not comp.fetcher:
            raise HTTPException(500, "기사 수집 서비스 없음")
        
        articles = await safe_call(
            comp.fetcher.fetch_multiple_sources,
            rss_urls=rss_urls or None,
            article_urls=article_urls or None,
            max_articles=max_articles
        )
        
        if not articles:
            return SummaryResponse(
                success=False,
                message="기사를 가져올 수 없습니다",
                total_articles=0,
                processed_at=datetime.now(),
                user_id=user_id
            )
        
        logger.info(f"✅ [{req_id}] {len(articles)}개 기사 수집")
        
        # 요약 처리
        summaries = []
        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"📝 [{req_id}] 요약 {i}/{len(articles)}")
                
                summary_result = await safe_call(
                    comp.summarizer.summarize,
                    f"제목: {article.title}\n내용: {article.content}",
                    request.language or "ko"
                )
                
                if isinstance(summary_result, dict):
                    summary_text = summary_result.get("summary", "요약 실패")
                else:
                    summary_text = str(summary_result)
                
                summaries.append(ArticleSummary(
                    title=article.title,
                    url=str(article.url),
                    summary=summary_text,
                    source=getattr(article, 'source', 'unknown'),
                    original_length=len(article.content),
                    summary_length=len(summary_text)
                ))
                
            except Exception as e:
                logger.error(f"❌ [{req_id}] 요약 실패: {e}")
                continue
        
        # 백그라운드 작업
        if request.recipient_email and summaries and comp.notifier:
            bg.add_task(send_email_bg, request.recipient_email, summaries, req_id)
        
        if summaries and comp.history_service:
            bg.add_task(save_history_bg, user_id, summaries, db, req_id)
        
        logger.info(f"🎉 [{req_id}] 요약 완료: {len(summaries)}개")
        
        return SummaryResponse(
            success=True,
            message=f"{len(summaries)}개 기사 요약 완료",
            summaries=summaries,
            total_articles=len(summaries),
            processed_at=datetime.now(),
            user_id=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 [{req_id}] 요약 오류: {e}")
        raise HTTPException(500, f"요약 처리 실패: {e}")

@app.post("/summarize-text")
async def summarize_text(request: Request):
    req_id = str(uuid.uuid4())[:8]
    
    try:
        body = await request.json()
        text = body.get("text", "")
        language = body.get("language", "ko")
        
        validated_text = validate_input_text(text, 10000)
        logger.info(f"📝 [{req_id}] 텍스트 요약: {len(validated_text)}자")
        
        if not comp.summarizer:
            raise HTTPException(500, "요약 서비스 없음")
        
        result = await safe_call(comp.summarizer.summarize, validated_text, language)
        
        if isinstance(result, dict):
            summary = result.get("summary", "요약 실패")
        else:
            summary = str(result)
        
        return {
            "success": True,
            "summary": summary,
            "original_length": len(validated_text),
            "summary_length": len(summary),
            "language": language,
            "processed_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 [{req_id}] 텍스트 요약 실패: {e}")
        raise HTTPException(500, f"텍스트 요약 실패: {e}")

# 백그라운드 작업들
async def send_email_bg(email: str, summaries: List[ArticleSummary], req_id: str):
    try:
        logger.info(f"📧 [{req_id}] 이메일 발송: {email}")
        if comp.notifier:
            await safe_call(comp.notifier.send_summary_email, email, summaries)
            logger.info(f"✅ [{req_id}] 이메일 발송 완료")
    except Exception as e:
        logger.error(f"❌ [{req_id}] 이메일 발송 실패: {e}")

async def save_history_bg(user_id: str, summaries: List[ArticleSummary], db: Session, req_id: str):
    try:
        logger.info(f"💾 [{req_id}] 히스토리 저장: {len(summaries)}개")
        
        if comp.history_service:
            for summary in summaries:
                try:
                    url = HttpUrl(summary.url) if isinstance(summary.url, str) else summary.url
                except:
                    url = HttpUrl("https://example.com")
                
                article = Article(
                    title=summary.title,
                    url=url,
                    content=f"요약: {summary.summary}",
                    source=summary.source
                )
                
                await safe_call(
                    comp.history_service.save_summary_history,
                    db, user_id, article, summary.summary, "ko",
                    summary.original_length, summary.summary_length
                )
            
            logger.info(f"✅ [{req_id}] 히스토리 저장 완료")
    except Exception as e:
        logger.error(f"❌ [{req_id}] 히스토리 저장 실패: {e}")

@app.get("/history")
async def get_history(
    user_id: str = Query(..., description="사용자 ID"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    per_page: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    language: Optional[str] = Query(None, description="언어 필터"),
    db: Session = Depends(get_db)
):
    """사용자 히스토리 조회"""
    req_id = str(uuid.uuid4())[:8]
    
    try:
        logger.info(f"📚 [{req_id}] 히스토리 조회: {user_id}, 페이지 {page}")
        
        if not comp.history_service:
            raise HTTPException(500, "히스토리 서비스 없음")
        
        # 히스토리 조회
        result = await safe_call(
            comp.history_service.get_user_history,
            db, user_id, page, per_page, language
        )
        
        if not isinstance(result, tuple) or len(result) != 2:
            raise Exception("히스토리 데이터 형식 오류")
        
        items, total = result
        
        # HistoryItem 변환
        history_items = []
        for item in items:
            try:
                keywords = json.loads(item.keywords) if item.keywords else []
            except:
                keywords = []
            
            history_items.append({
                "id": item.id,
                "article_title": item.article_title,
                "article_url": item.article_url,
                "article_source": item.article_source,
                "content_excerpt": item.content_excerpt,
                "summary_text": item.summary_text,
                "summary_language": item.summary_language,
                "original_length": item.original_length,
                "summary_length": item.summary_length,
                "keywords": keywords,
                "created_at": item.created_at.isoformat() if item.created_at else None
            })
        
        logger.info(f"✅ [{req_id}] 히스토리 조회 완료: {len(history_items)}개")
        
        return {
            "success": True,
            "history": history_items,
            "total_items": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 [{req_id}] 히스토리 조회 실패: {e}")
        raise HTTPException(500, f"히스토리 조회 실패: {e}")

@app.post("/news-search")
async def news_search(request: Request, bg: BackgroundTasks):
    """뉴스 검색"""
    req_id = str(uuid.uuid4())[:8]
    
    try:
        body = await request.json()
        query = body.get("query", "")
        max_articles = body.get("max_articles", 10)
        recipient_email = body.get("recipient_email")
        
        query = validate_input_text(query, 500)
        logger.info(f"🔎 [{req_id}] 뉴스 검색: {query}")
        
        if not comp.news_aggregator:
            raise HTTPException(500, "뉴스 검색 서비스 없음")
        
        # 뉴스 검색 실행
        result = await safe_call(
            comp.news_aggregator.process_news_query,
            query,
            min(max_articles, 20)
        )
        
        # 결과 처리
        if isinstance(result, tuple) and len(result) == 2:
            articles, keywords = result
        else:
            articles = result if isinstance(result, list) else []
            keywords = []
        
        logger.info(f"✅ [{req_id}] 뉴스 검색 완료: {len(articles)}개")
        
        # 백그라운드 이메일 발송
        if recipient_email and articles and comp.notifier:
            bg.add_task(send_news_email_bg, recipient_email, query, articles, req_id)
        
        return {
            "success": True,
            "message": f"{len(articles)}개 뉴스를 찾았습니다",
            "articles": [
                {
                    "title": article.title,
                    "url": str(article.url),
                    "summary": getattr(article, 'summary', ''),
                    "source": getattr(article, 'source', 'unknown'),
                    "published_date": article.published_date.isoformat() if getattr(article, 'published_date', None) else None
                }
                for article in articles
            ],
            "total_articles": len(articles),
            "keywords": keywords,
            "processed_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 [{req_id}] 뉴스 검색 실패: {e}")
        raise HTTPException(500, f"뉴스 검색 실패: {e}")

@app.get("/recommendations")
async def get_recommendations(
    user_id: str = Query(..., description="사용자 ID"),
    limit: int = Query(5, ge=1, le=20, description="추천 개수"),
    db: Session = Depends(get_db)
):
    """개인화 추천"""
    req_id = str(uuid.uuid4())[:8]
    
    try:
        logger.info(f"💡 [{req_id}] 추천 요청: {user_id}")
        
        if not comp.history_service:
            raise HTTPException(500, "추천 서비스 없음")
        
        # 사용자 히스토리 기반 추천
        recommendations = await safe_call(
            comp.history_service.generate_recommendations,
            db, user_id, limit
        )
        
        if not recommendations:
            recommendations = []
        
        logger.info(f"✅ [{req_id}] 추천 완료: {len(recommendations)}개")
        
        return {
            "success": True,
            "recommendations": [
                {
                    "title": rec.title,
                    "description": rec.description,
                    "url": str(rec.url),
                    "category": rec.category,
                    "confidence_score": rec.confidence_score
                }
                for rec in recommendations
            ],
            "total_recommendations": len(recommendations),
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 [{req_id}] 추천 실패: {e}")
        raise HTTPException(500, f"추천 실패: {e}")

# 백그라운드 작업 추가
async def send_news_email_bg(email: str, query: str, articles: List, req_id: str):
    try:
        logger.info(f"📧 [{req_id}] 뉴스 검색 결과 이메일: {email}")
        
        if comp.notifier:
            # 뉴스 검색 결과를 ArticleSummary 형태로 변환
            summaries = []
            for article in articles[:5]:  # 최대 5개만
                summaries.append(ArticleSummary(
                    title=article.title,
                    url=str(article.url),
                    summary=f"'{query}' 검색 결과",
                    source=getattr(article, 'source', 'unknown'),
                    original_length=0,
                    summary_length=0
                ))
            
            await safe_call(comp.notifier.send_summary_email, email, summaries)
            logger.info(f"✅ [{req_id}] 뉴스 이메일 발송 완료")
    except Exception as e:
        logger.error(f"❌ [{req_id}] 뉴스 이메일 발송 실패: {e}")

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 서버 직접 실행")
    uvicorn.run("server_refactored:app", host="0.0.0.0", port=8001, reload=False) 