import asyncio
import json
import logging
import os
import re
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Load environment variables first
load_dotenv()

try:
    # 상대 임포트 시도 (모듈로 실행될 때)
    from .config import settings
    from .database import get_db, init_database
    from .fetcher import ArticleFetcher
    from .history_service import HistoryService
    from .models import (
        ArticleSummary,
        HistoryItem,
        HistoryResponse,
        NewsSearchRequest,
        NewsSearchResponse,
        RecommendationItem,
        RecommendationResponse,
        SummaryRequest,
        SummaryResponse,
        UserStatsResponse,
    )
    from .news_aggregator import NewsAggregator
    from .notifier import EmailNotifier
    from .security import sanitize_response, validate_input
    from .summarizer import ArticleSummarizer

    SECURITY_AVAILABLE = True
except ImportError:
    # 절대 임포트로 폴백 (직접 실행될 때)
    from config import settings
    from database import get_db, init_database
    from fetcher import ArticleFetcher
    from history_service import HistoryService
    from models import (
        ArticleSummary,
        HistoryItem,
        HistoryResponse,
        NewsSearchRequest,
        NewsSearchResponse,
        RecommendationItem,
        RecommendationResponse,
        SummaryRequest,
        SummaryResponse,
        UserStatsResponse,
    )
    from news_aggregator import NewsAggregator
    from notifier import EmailNotifier
    from summarizer import ArticleSummarizer

    try:
        from security import sanitize_response, validate_input

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
            logging.FileHandler("glbaguni_backend.log", encoding="utf-8"),
        ],
    )

    # HTTP 요청 로깅을 위한 별도 로거
    access_logger = logging.getLogger("access")
    access_logger.setLevel(logging.INFO)

    return logging.getLogger(__name__)


# 로깅 설정
logger = setup_logging()


# ✅ 2. 환경 변수 안정화
def validate_environment():
    """환경 변수 검증"""
    required_vars = ["OPENAI_API_KEY"]
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


# ✅ 3. 비동기 HTTP 클라이언트 설정
class AsyncHTTPClient:
    """비동기 HTTP 클라이언트 매니저"""

    def __init__(self):
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()


# 전역 HTTP 클라이언트
http_client = None


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
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
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
    lifespan=lifespan,
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
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail} - URL: {request.url}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
        },
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
            "timestamp": datetime.now().isoformat(),
        },
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
            "timestamp": datetime.now().isoformat(),
        },
    )


# ✅ 요청/응답 로깅 미들웨어
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """요청/응답 로깅"""
    start_time = time.time()

    # 요청 로깅
    logger.info(
        f"📥 {request.method} {request.url} - 클라이언트: {request.client.host}"
    )

    # 요청 처리
    response = await call_next(request)

    # 응답 로깅
    process_time = time.time() - start_time
    logger.info(
        f"📤 {request.method} {request.url} - 상태: {response.status_code} - 처리시간: {process_time:.2f}초"
    )

    return response


# ✅ 6. 입력 검증 유틸리티
def validate_and_sanitize_input(text: str, max_length: int = 1000) -> str:
    """입력 텍스트 검증 및 정화"""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="입력 텍스트가 비어있습니다.")

    # 길이 제한
    if len(text) > max_length:
        raise HTTPException(
            status_code=400, detail=f"입력 텍스트가 너무 깁니다. (최대 {max_length}자)"
        )

    # 금지된 특수문자 필터링
    dangerous_patterns = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe.*?>.*?</iframe>",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise HTTPException(
                status_code=400, detail="허용되지 않는 문자가 포함되어 있습니다."
            )

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

            # 여기에 실제 GPT API 호출 로직이 들어갑니다
            # 예시로 summarizer를 사용
            result = await asyncio.to_thread(summarizer.summarize_text, prompt)

            logger.info("✅ GPT API 호출 성공")
            return result

        except Exception as e:
            logger.error(f"❌ GPT API 호출 실패 (시도 {attempt + 1}): {str(e)}")

            if attempt == max_retries - 1:
                logger.error("❌ 모든 GPT API 호출 시도 실패")
                return "죄송합니다. 현재 AI 서비스에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요."

            # 재시도 전 대기
            await asyncio.sleep(2**attempt)  # 지수 백오프


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
            "향상된 오류 처리",
        ],
        "status": "running",
    }


# ✅ 7. 향상된 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    """향상된 헬스 체크"""
    try:
        # 기본 상태
        health_status = {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "version": "2.1.0",
        }

        # 외부 서비스 상태 확인
        checks = {}

        # OpenAI API 키 확인
        checks["openai_api"] = (
            "configured" if os.getenv("OPENAI_API_KEY") else "not_configured"
        )

        # 데이터베이스 연결 확인
        try:
            with get_db() as db:
                db.execute("SELECT 1")
            checks["database"] = "healthy"
        except Exception as e:
            checks["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"

        # HTTP 클라이언트 상태 확인
        checks["http_client"] = (
            "healthy" if http_client and not http_client.is_closed else "error"
        )

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
            "error": str(e),
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
            "logging": True,
        },
    }


# ✅ 향상된 요약 엔드포인트
@app.post("/summarize", response_model=SummaryResponse)
async def summarize_articles(
    request: SummaryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
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
                detail="최소 하나의 RSS URL 또는 기사 URL이 필요합니다.",
            )

        # 사용자 ID 생성
        user_id = request.user_id or history_service.generate_user_id()

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

        logger.info(
            f"📊 처리 대상: RSS {len(rss_urls) if rss_urls else 0}개, 기사 {len(article_urls) if article_urls else 0}개"
        )

        # 시간 초과 체크
        if time.time() - start_time > max_processing_time:
            raise HTTPException(status_code=408, detail="요청 시간 초과")

        # 비동기로 기사 가져오기
        articles = await asyncio.to_thread(
            fetcher.fetch_multiple_sources,
            rss_urls=rss_urls,
            article_urls=article_urls,
            max_articles=max_articles,
        )

        if not articles:
            logger.warning("❌ 가져온 기사가 없습니다")
            return SummaryResponse(
                success=False,
                message="제공된 소스에서 기사를 가져올 수 없습니다.",
                total_articles=0,
                processed_at=datetime.now(),
                user_id=user_id,
            )

        logger.info(f"📝 {len(articles)}개 기사 가져오기 완료")

        # 기사 요약 (안전한 GPT 호출)
        summaries = []
        for article in articles:
            try:
                summary = await safe_gpt_call(
                    f"제목: {article.title}\n내용: {article.content}"
                )
                summaries.append(
                    ArticleSummary(
                        title=article.title,
                        url=article.url,
                        summary=summary,
                        original_length=len(article.content),
                        summary_length=len(summary),
                        created_at=datetime.now(),
                    )
                )
            except Exception as e:
                logger.error(f"❌ 기사 요약 실패: {str(e)}")
                continue

        # 이메일 발송 (백그라운드)
        if request.recipient_email and summaries:
            background_tasks.add_task(
                send_summary_email, request.recipient_email, summaries
            )

        # 히스토리 저장 (백그라운드)
        if summaries:
            background_tasks.add_task(save_to_history, user_id, summaries, db)

        processing_time = time.time() - start_time
        logger.info(
            f"✅ 요약 완료 - 처리시간: {processing_time:.2f}초, 요약 {len(summaries)}개"
        )

        return SummaryResponse(
            success=True,
            message=f"{len(summaries)}개 기사가 성공적으로 요약되었습니다.",
            summaries=summaries,
            total_articles=len(summaries),
            processed_at=datetime.now(),
            user_id=user_id,
            processing_time=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 요약 처리 중 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="요약 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        )


# ✅ 향상된 텍스트 요약 엔드포인트
@app.post("/summarize-text")
async def summarize_text(request: Request, db: Session = Depends(get_db)):
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
                summary = sanitize_response(summary)
            except Exception as e:
                logger.warning(f"응답 정화 실패: {str(e)}")

        logger.info("✅ 텍스트 요약 완료")

        return {
            "success": True,
            "summary": summary,
            "original_length": len(validated_text),
            "summary_length": len(summary),
            "processed_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 텍스트 요약 실패: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="텍스트 요약 중 오류가 발생했습니다."
        )


# 백그라운드 작업 함수들
async def send_summary_email(recipient_email: str, summaries: List[ArticleSummary]):
    """이메일 발송 (백그라운드 작업)"""
    try:
        logger.info(f"📧 이메일 발송 시작: {recipient_email}")
        await asyncio.to_thread(notifier.send_summary_email, recipient_email, summaries)
        logger.info("✅ 이메일 발송 완료")
    except Exception as e:
        logger.error(f"❌ 이메일 발송 실패: {str(e)}")


async def save_to_history(user_id: str, summaries: List[ArticleSummary], db: Session):
    """히스토리 저장 (백그라운드 작업)"""
    try:
        logger.info(f"💾 히스토리 저장 시작: {user_id}")
        await asyncio.to_thread(history_service.save_summaries, user_id, summaries, db)
        logger.info("✅ 히스토리 저장 완료")
    except Exception as e:
        logger.error(f"❌ 히스토리 저장 실패: {str(e)}")


# 기존 엔드포인트들도 동일한 패턴으로 개선...
# (히스토리, 추천, 통계 등의 엔드포인트들)

if __name__ == "__main__":
    print("⚠️  경고: 이 파일은 백업용입니다. 직접 실행하지 마세요.")
    print("💡 대신 다음 명령어를 사용하세요:")
    print("   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload")
    import sys
    sys.exit(1)
