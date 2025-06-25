#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
글바구니 백엔드 서버 v3.1.0 - 안정화 리팩토링 버전
- 개선된 예외 처리
- 의존성 주입 최적화
- 코드 모듈화 및 가독성 향상
- 보안 강화
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from typing import Any as HttpUrl
from typing import Dict, List, Optional, Union

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

# 환경변수 우선 로드
load_dotenv()


# === 모듈 임포트 및 안전성 검증 ===
class ModuleImporter:
    """안전한 모듈 임포트를 위한 클래스"""

    def __init__(self):
        self.modules = {}
        self.security_available = False
        self.model_classes = {}
        self._import_modules()

    def _import_modules(self):
        """모듈들을 안전하게 임포트"""
        try:
            # 절대 임포트 시도
            from config import settings
            from database import get_db, init_database
            from fetcher import ArticleFetcher
            from history_service import HistoryService
            from models import (
                Article,
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

            self.modules.update(
                {
                    "fetcher_class": ArticleFetcher,
                    "summarizer_class": ArticleSummarizer,
                    "notifier_class": EmailNotifier,
                    "settings": settings,
                    "get_db": get_db,
                    "init_database": init_database,
                    "history_service_class": HistoryService,
                    "news_aggregator_class": NewsAggregator,
                }
            )

            self.model_classes.update(
                {
                    "SummaryRequest": SummaryRequest,
                    "SummaryResponse": SummaryResponse,
                    "ArticleSummary": ArticleSummary,
                    "Article": Article,
                    "HistoryResponse": HistoryResponse,
                    "RecommendationResponse": RecommendationResponse,
                    "UserStatsResponse": UserStatsResponse,
                    "HistoryItem": HistoryItem,
                    "RecommendationItem": RecommendationItem,
                    "NewsSearchRequest": NewsSearchRequest,
                    "NewsSearchResponse": NewsSearchResponse,
                }
            )

            try:
                from security import sanitize_response, validate_input

                self.modules.update(
                    {
                        "validate_input": validate_input,
                        "sanitize_response": sanitize_response,
                    }
                )
                self.security_available = True
            except ImportError:
                logging.warning("보안 모듈을 찾을 수 없습니다")

        except ImportError:
            # 절대 임포트로 폴백
            try:
                from config import settings
                from database import get_db, init_database
                from fetcher import ArticleFetcher
                from history_service import HistoryService
                from models import (
                    Article,
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

                self.modules.update(
                    {
                        "fetcher_class": ArticleFetcher,
                        "summarizer_class": ArticleSummarizer,
                        "notifier_class": EmailNotifier,
                        "settings": settings,
                        "get_db": get_db,
                        "init_database": init_database,
                        "history_service_class": HistoryService,
                        "news_aggregator_class": NewsAggregator,
                    }
                )

                self.model_classes.update(
                    {
                        "SummaryRequest": SummaryRequest,
                        "SummaryResponse": SummaryResponse,
                        "ArticleSummary": ArticleSummary,
                        "Article": Article,
                        "HistoryResponse": HistoryResponse,
                        "RecommendationResponse": RecommendationResponse,
                        "UserStatsResponse": UserStatsResponse,
                        "HistoryItem": HistoryItem,
                        "RecommendationItem": RecommendationItem,
                        "NewsSearchRequest": NewsSearchRequest,
                        "NewsSearchResponse": NewsSearchResponse,
                    }
                )

                try:
                    from security import sanitize_response, validate_input

                    self.modules.update(
                        {
                            "validate_input": validate_input,
                            "sanitize_response": sanitize_response,
                        }
                    )
                    self.security_available = True
                except ImportError:
                    pass

            except ImportError as e:
                logging.error(f"필수 모듈 임포트 실패: {e}")
                sys.exit(1)


# 모듈 임포터 초기화
importer = ModuleImporter()

# 전역에서 사용할 모델 클래스들 정의
SummaryRequest = importer.model_classes.get("SummaryRequest")
SummaryResponse = importer.model_classes.get("SummaryResponse")
ArticleSummary = importer.model_classes.get("ArticleSummary")
Article = importer.model_classes.get("Article")
HistoryResponse = importer.model_classes.get("HistoryResponse")
RecommendationResponse = importer.model_classes.get("RecommendationResponse")
UserStatsResponse = importer.model_classes.get("UserStatsResponse")
HistoryItem = importer.model_classes.get("HistoryItem")
RecommendationItem = importer.model_classes.get("RecommendationItem")
NewsSearchRequest = importer.model_classes.get("NewsSearchRequest")
NewsSearchResponse = importer.model_classes.get("NewsSearchResponse")


# === 로깅 시스템 ===
class LoggingManager:
    """로깅 관리 클래스"""

    @staticmethod
    def setup_logging() -> logging.Logger:
        """로깅 시스템 초기화"""
        try:
            os.makedirs("logs", exist_ok=True)

            # 로그 포맷 설정
            log_format = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

            # 핸들러 설정
            handlers = [
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("logs/server.log", encoding="utf-8"),
            ]

            # 기본 로깅 설정
            logging.basicConfig(
                level=logging.INFO, format=log_format, handlers=handlers, force=True
            )

            # 외부 라이브러리 로그 레벨 조정
            for logger_name in ["httpx", "httpcore", "urllib3", "asyncio"]:
                logging.getLogger(logger_name).setLevel(logging.WARNING)

            logger = logging.getLogger("glbaguni")
            logger.info("🚀 글바구니 서버 v3.1.0 로깅 시스템 초기화 완료")
            return logger

        except Exception as e:
            print(f"로깅 시스템 초기화 실패: {e}")
            sys.exit(1)


logger = LoggingManager.setup_logging()


# === 환경변수 검증 ===
class EnvironmentValidator:
    """환경변수 검증 클래스"""

    REQUIRED_VARS = ["OPENAI_API_KEY"]
    OPTIONAL_VARS = ["SMTP_SERVER", "SMTP_USERNAME", "SMTP_PASSWORD"]

    @classmethod
    def validate_environment(cls) -> bool:
        """환경변수 검증"""
        try:
            missing_vars = []

            for var in cls.REQUIRED_VARS:
                value = os.getenv(var)
                if not value:
                    missing_vars.append(var)
                elif var == "OPENAI_API_KEY" and not value.startswith("sk-"):
                    logger.error(f"❌ {var} 형식이 올바르지 않습니다")
                    return False

            if missing_vars:
                logger.error(f"❌ 필수 환경변수 누락: {', '.join(missing_vars)}")
                return False

            # 선택적 환경변수 확인
            missing_optional = []
            for var in cls.OPTIONAL_VARS:
                if not os.getenv(var):
                    missing_optional.append(var)

            if missing_optional:
                logger.warning(f"⚠️ 선택적 환경변수 누락: {', '.join(missing_optional)}")

            logger.info("✅ 환경변수 검증 완료")
            return True

        except Exception as e:
            logger.error(f"환경변수 검증 중 오류: {e}")
            return False


# 환경변수 검증 실행
if not EnvironmentValidator.validate_environment():
    sys.exit(1)


# === 전역 컴포넌트 관리 ===
class ComponentManager:
    """애플리케이션 컴포넌트 관리 클래스"""

    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None
        self.fetcher: Optional[Any] = None
        self.summarizer: Optional[Any] = None
        self.notifier: Optional[Any] = None
        self.history_service: Optional[Any] = None
        self.news_aggregator: Optional[Any] = None
        self.initialized = False

    async def initialize(self) -> None:
        """컴포넌트 초기화"""
        try:
            logger.info("🔧 컴포넌트 초기화 시작...")
            start_time = time.time()

            # HTTP 클라이언트 초기화
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            )
            logger.info("✅ HTTP 클라이언트 초기화 완료")

            # 데이터베이스 초기화
            await self._safe_call(importer.modules["init_database"])
            logger.info("✅ 데이터베이스 초기화 완료")

            # 서비스 컴포넌트 초기화
            await self._initialize_services()

            elapsed = time.time() - start_time
            self.initialized = True
            logger.info(f"🎉 전체 컴포넌트 초기화 완료! ({elapsed:.2f}초)")

        except Exception as e:
            logger.error(f"❌ 컴포넌트 초기화 실패: {e}")
            logger.error(traceback.format_exc())
            raise

    async def _initialize_services(self) -> None:
        """서비스 컴포넌트들 초기화"""
        try:
            # 기본 서비스들
            self.fetcher = importer.modules["fetcher_class"]()
            self.summarizer = importer.modules["summarizer_class"]()
            self.history_service = importer.modules["history_service_class"]()

            # 뉴스 애그리게이터 (OpenAI API 키 필요)
            self.news_aggregator = importer.modules["news_aggregator_class"](
                openai_api_key=importer.modules["settings"].OPENAI_API_KEY
            )

            # 이메일 노티파이어 (선택적)
            try:
                self.notifier = importer.modules["notifier_class"]()
                logger.info("✅ 이메일 서비스 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ 이메일 서비스 초기화 실패: {e}")
                self.notifier = None

            logger.info("✅ 서비스 컴포넌트 초기화 완료")

        except Exception as e:
            logger.error(f"서비스 초기화 중 오류: {e}")
            raise

    async def cleanup(self) -> None:
        """컴포넌트 정리"""
        try:
            logger.info("🔄 컴포넌트 정리 중...")

            if self.http_client:
                await self.http_client.aclose()
                logger.info("✅ HTTP 클라이언트 종료 완료")

            self.initialized = False
            logger.info("✅ 컴포넌트 정리 완료")

        except Exception as e:
            logger.error(f"컴포넌트 정리 중 오류: {e}")

    async def _safe_call(self, func, *args, **kwargs):
        """안전한 함수 호출"""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            logger.error(f"함수 호출 실패: {func.__name__} - {str(e)}")
            raise


# 전역 컴포넌트 매니저
comp = ComponentManager()


# === 유틸리티 함수들 ===
class InputValidator:
    """입력 검증 유틸리티"""

    @staticmethod
    def validate_text_input(
        text: str, max_len: int = 5000, field_name: str = "텍스트"
    ) -> str:
        """텍스트 입력 검증"""
        try:
            if not text or not isinstance(text, str):
                raise HTTPException(400, f"{field_name}가 비어있습니다")

            text = text.strip()
            if not text:
                raise HTTPException(400, f"{field_name}가 비어있습니다")

            if len(text) > max_len:
                raise HTTPException(
                    400, f"{field_name}가 너무 깁니다 (최대 {max_len}자)"
                )

            # 기본 XSS 방지
            dangerous_patterns = [
                r"<script[^>]*>.*?</script>",
                r"javascript\s*:",
                r"on\w+\s*=",
                r"<iframe[^>]*>.*?</iframe>",
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                    raise HTTPException(
                        400, f"{field_name}에 위험한 패턴이 감지되었습니다"
                    )

            # 보안 모듈이 있으면 추가 검증
            if importer.security_available:
                try:
                    text = importer.modules["validate_input"](text)
                except Exception as e:
                    logger.warning(f"보안 검증 실패: {e}")

            return text

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"입력 검증 중 오류: {e}")
            raise HTTPException(500, "입력 검증 중 내부 오류가 발생했습니다")


class ResponseFormatter:
    """응답 형식 통일"""

    @staticmethod
    def success_response(data: Any, message: str = "성공", **kwargs) -> Dict[str, Any]:
        """성공 응답 형식"""
        response = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())[:8],
        }
        response.update(kwargs)
        return response

    @staticmethod
    def error_response(
        error_code: str, message: str, status_code: int = 500, **kwargs
    ) -> Dict[str, Any]:
        """오류 응답 형식"""
        response = {
            "success": False,
            "error_code": error_code,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())[:8],
        }
        response.update(kwargs)
        return response


# === FastAPI 앱 라이프사이클 ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    try:
        # 시작 시 초기화
        await comp.initialize()
        yield
    except Exception as e:
        logger.error(f"❌ 애플리케이션 시작 실패: {e}")
        raise
    finally:
        # 종료 시 정리
        await comp.cleanup()


# === FastAPI 앱 초기화 ===
app = FastAPI(
    title="글바구니 RSS 요약 서비스",
    description="AI 기반 RSS 피드 요약 서비스 - 안정화 버전",
    version="3.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인 설정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === 미들웨어 ===
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """요청 로깅 미들웨어"""
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    # 요청 로깅
    logger.info(f"🔍 [{request_id}] {request.method} {request.url}")

    try:
        response = await call_next(request)

        # 응답 로깅
        elapsed = time.time() - start_time
        logger.info(f"✅ [{request_id}] {response.status_code} - {elapsed:.3f}s")

        # 응답 헤더에 요청 ID 추가
        response.headers["X-Request-ID"] = request_id
        return response

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ [{request_id}] 오류 - {elapsed:.3f}s: {str(e)}")
        raise


# === 예외 핸들러 ===
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    logger.error(f"HTTP 예외: {exc.status_code} - {exc.detail} - URL: {request.url}")

    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseFormatter.error_response(
            error_code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            status_code=exc.status_code,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 예외 처리"""
    logger.error(f"요청 검증 오류: {exc.errors()} - URL: {request.url}")

    return JSONResponse(
        status_code=422,
        content=ResponseFormatter.error_response(
            error_code="VALIDATION_ERROR",
            message="요청 데이터가 올바르지 않습니다",
            status_code=422,
            details=exc.errors(),
        ),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    request_id = str(uuid.uuid4())[:8]
    logger.error(f"❌ [{request_id}] 예상치 못한 오류: {str(exc)}")
    logger.error(f"❌ [{request_id}] Traceback: {traceback.format_exc()}")

    return JSONResponse(
        status_code=500,
        content=ResponseFormatter.error_response(
            error_code="INTERNAL_ERROR",
            message="내부 서버 오류가 발생했습니다",
            status_code=500,
            request_id=request_id,
        ),
    )


# === API 엔드포인트들 ===


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return ResponseFormatter.success_response(
        data={
            "service": "글바구니 RSS 요약 서비스",
            "version": "3.1.0",
            "status": "운영중",
            "features": [
                "RSS 피드 요약",
                "자연어 뉴스 검색",
                "사용자 히스토리",
                "개인화 추천",
            ],
        },
        message="글바구니 서비스에 오신 것을 환영합니다!",
    )


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "3.1.0",
            "components": {},
        }

        # 컴포넌트 상태 확인
        if comp.initialized:
            health_status["components"]["core"] = "healthy"
            health_status["components"]["http_client"] = (
                "healthy" if comp.http_client else "unavailable"
            )
            health_status["components"]["database"] = "healthy"
            health_status["components"]["fetcher"] = (
                "healthy" if comp.fetcher else "unavailable"
            )
            health_status["components"]["summarizer"] = (
                "healthy" if comp.summarizer else "unavailable"
            )
            health_status["components"]["notifier"] = (
                "healthy" if comp.notifier else "unavailable"
            )
        else:
            health_status["status"] = "initializing"
            health_status["components"]["core"] = "initializing"

        # 데이터베이스 연결 테스트
        try:
            db = next(importer.modules["get_db"]())
            db.execute(text("SELECT 1"))
            health_status["components"]["database"] = "healthy"
            db.close()
        except Exception as e:
            logger.error(f"데이터베이스 헬스 체크 실패: {e}")
            health_status["components"]["database"] = "unhealthy"
            health_status["status"] = "degraded"

        # OpenAI API 키 확인
        api_key = os.getenv("OPENAI_API_KEY")
        health_status["components"]["openai"] = (
            "configured" if api_key and api_key.startswith("sk-") else "unconfigured"
        )

        return ResponseFormatter.success_response(
            data=health_status, message="헬스 체크 완료"
        )

    except Exception as e:
        logger.error(f"헬스 체크 중 오류: {e}")
        return ResponseFormatter.error_response(
            error_code="HEALTH_CHECK_ERROR",
            message="헬스 체크 중 오류가 발생했습니다",
            status_code=500,
        )


@app.post("/summarize")
async def summarize_articles(
    request: Any,
    bg: BackgroundTasks,
    db: Session = Depends(importer.modules.get("get_db")),
):
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

        articles = await comp._safe_call(
            comp.fetcher.fetch_multiple_sources,
            rss_urls=rss_urls or None,
            article_urls=article_urls or None,
            max_articles=max_articles,
        )

        if not articles:
            if not SummaryResponse:
                raise HTTPException(500, "응답 모델이 초기화되지 않았습니다")
            return SummaryResponse(
                success=False,
                message="기사를 가져올 수 없습니다",
                total_articles=0,
                processed_at=datetime.now(),
                user_id=user_id,
            )

        logger.info(f"✅ [{req_id}] {len(articles)}개 기사 수집")

        # 요약 처리
        summaries = []
        for i, article in enumerate(articles, 1):
            try:
                logger.info(f"📝 [{req_id}] 요약 {i}/{len(articles)}")

                if not comp.summarizer:
                    logger.error(f"❌ [{req_id}] 요약 서비스가 없습니다")
                    continue

                summary_result = await comp._safe_call(
                    comp.summarizer.summarize,
                    f"제목: {article.title}\n내용: {article.content}",
                    request.language or "ko",
                )

                if isinstance(summary_result, dict):
                    summary_text = summary_result.get("summary", "요약 실패")
                else:
                    summary_text = str(summary_result)

                if not ArticleSummary:
                    logger.error(f"❌ [{req_id}] ArticleSummary 모델이 없습니다")
                    continue

                summaries.append(
                    ArticleSummary(
                        title=article.title,
                        url=str(article.url),
                        summary=summary_text,
                        source=getattr(article, "source", "unknown"),
                        original_length=len(article.content),
                        summary_length=len(summary_text),
                    )
                )

            except Exception as e:
                logger.error(f"❌ [{req_id}] 요약 실패: {e}")
                continue

        # 백그라운드 작업
        if request.recipient_email and summaries and comp.notifier:
            bg.add_task(send_email_bg, request.recipient_email, summaries, req_id)

        if summaries and comp.history_service:
            bg.add_task(save_history_bg, user_id, summaries, db, req_id)

        logger.info(f"🎉 [{req_id}] 요약 완료: {len(summaries)}개")

        if not SummaryResponse:
            raise HTTPException(500, "응답 모델이 초기화되지 않았습니다")

        return SummaryResponse(
            success=True,
            message=f"{len(summaries)}개 기사 요약 완료",
            summaries=summaries,
            total_articles=len(summaries),
            processed_at=datetime.now(),
            user_id=user_id,
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

        validated_text = InputValidator.validate_text_input(text, 10000)
        logger.info(f"📝 [{req_id}] 텍스트 요약: {len(validated_text)}자")

        if not comp.summarizer:
            raise HTTPException(500, "요약 서비스 없음")

        result = await comp._safe_call(
            comp.summarizer.summarize, validated_text, language
        )

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
            "processed_at": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 [{req_id}] 텍스트 요약 실패: {e}")
        raise HTTPException(500, f"텍스트 요약 실패: {e}")


# 백그라운드 작업들
async def send_email_bg(email: str, summaries: List, req_id: str):
    try:
        logger.info(f"📧 [{req_id}] 이메일 발송: {email}")
        if comp.notifier:
            await comp._safe_call(comp.notifier.send_summary_email, email, summaries)
            logger.info(f"✅ [{req_id}] 이메일 발송 완료")
    except Exception as e:
        logger.error(f"❌ [{req_id}] 이메일 발송 실패: {e}")


async def save_history_bg(user_id: str, summaries: List, db: Session, req_id: str):
    try:
        logger.info(f"💾 [{req_id}] 히스토리 저장: {len(summaries)}개")

        if comp.history_service:
            for summary in summaries:
                try:
                    # URL 문자열을 그대로 사용
                    url = (
                        summary.url
                        if isinstance(summary.url, str)
                        else str(summary.url)
                    )
                except:
                    url = "https://example.com"

                if not Article:
                    logger.error(f"❌ [{req_id}] Article 모델이 없습니다")
                    continue

                article = Article(
                    title=summary.title,
                    url=url,
                    content=f"요약: {summary.summary}",
                    source=summary.source,
                )

                await comp._safe_call(
                    comp.history_service.save_summary_history,
                    db,
                    user_id,
                    article,
                    summary.summary,
                    "ko",
                    summary.original_length,
                    summary.summary_length,
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
    db: Session = Depends(importer.modules.get("get_db")),
):
    """사용자 히스토리 조회"""
    req_id = str(uuid.uuid4())[:8]

    try:
        logger.info(f"📚 [{req_id}] 히스토리 조회: {user_id}, 페이지 {page}")

        if not comp.history_service:
            raise HTTPException(500, "히스토리 서비스 없음")

        # 히스토리 조회
        result = await comp._safe_call(
            comp.history_service.get_user_history, db, user_id, page, per_page, language
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

            history_items.append(
                {
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
                    "created_at": (
                        item.created_at.isoformat() if item.created_at else None
                    ),
                }
            )

        logger.info(f"✅ [{req_id}] 히스토리 조회 완료: {len(history_items)}개")

        return {
            "success": True,
            "history": history_items,
            "total_items": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
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

        query = InputValidator.validate_text_input(query, 500)
        logger.info(f"🔎 [{req_id}] 뉴스 검색: {query}")

        if not comp.news_aggregator:
            raise HTTPException(500, "뉴스 검색 서비스 없음")

        # 뉴스 검색 실행
        result = await comp._safe_call(
            comp.news_aggregator.process_news_query, query, min(max_articles, 20)
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
                    "summary": getattr(article, "summary", ""),
                    "source": getattr(article, "source", "unknown"),
                    "published_date": (
                        article.published_date.isoformat()
                        if getattr(article, "published_date", None)
                        else None
                    ),
                }
                for article in articles
            ],
            "total_articles": len(articles),
            "keywords": keywords,
            "processed_at": datetime.now().isoformat(),
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
    db: Session = Depends(importer.modules.get("get_db")),
):
    """개인화 추천"""
    req_id = str(uuid.uuid4())[:8]

    try:
        logger.info(f"💡 [{req_id}] 추천 요청: {user_id}")

        if not comp.history_service:
            raise HTTPException(500, "추천 서비스 없음")

        # 사용자 히스토리 기반 추천
        recommendations = await comp._safe_call(
            comp.history_service.generate_recommendations, db, user_id, limit
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
                    "confidence_score": rec.confidence_score,
                }
                for rec in recommendations
            ],
            "total_recommendations": len(recommendations),
            "user_id": user_id,
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
                if not ArticleSummary:
                    logger.error(f"❌ [{req_id}] ArticleSummary 모델이 없습니다")
                    continue

                summaries.append(
                    ArticleSummary(
                        title=article.title,
                        url=str(article.url),
                        summary=f"'{query}' 검색 결과",
                        source=getattr(article, "source", "unknown"),
                        original_length=0,
                        summary_length=0,
                    )
                )

            await comp._safe_call(comp.notifier.send_summary_email, email, summaries)
            logger.info(f"✅ [{req_id}] 뉴스 이메일 발송 완료")
    except Exception as e:
        logger.error(f"❌ [{req_id}] 뉴스 이메일 발송 실패: {e}")


if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 서버 직접 실행")
    uvicorn.run("server_refactored:app", host="0.0.0.0", port=8000, reload=False)
