#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
글바구니 백엔드 서버 v2.2.0 - 리팩토링 버전
- 모듈화된 구조로 개선
- 각 기능별로 파일 분리
- 200줄 이하의 간결한 메인 파일
"""

import sys
import time
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 분리된 모듈들 임포트
from .utils.startup import SafeImporter, LoggingSystem, EnvironmentChecker
from .utils.app_state import ApplicationState
from .utils.responses import ResponseBuilder
from .routers.main import create_main_router
from .routers.summarize import create_summarize_router 
from .routers.history_router import create_history_router


# === 초기화 ===
# 로깅 초기화
logger = LoggingSystem.setup_logging()

# 환경변수 검증
if not EnvironmentChecker.validate_environment():
    sys.exit(1)

# 안전 임포터 초기화
importer = SafeImporter()

# 전역 애플리케이션 상태
app_state = ApplicationState()


# === FastAPI 앱 라이프사이클 ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    try:
        # 시작 시 초기화
        await app_state.initialize(importer)
        yield
    except Exception as e:
        logger.error(f"❌ 애플리케이션 시작 실패: {e}")
        raise
    finally:
        # 종료 시 정리
        await app_state.cleanup()


# === FastAPI 앱 초기화 ===
app = FastAPI(
    title="글바구니 (Glbaguni) - AI RSS Summarizer",
    description="AI 기반 RSS 피드 요약 서비스 - 리팩토링 버전",
    version="2.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 구체적인 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === 미들웨어 ===
@app.middleware("http")
async def request_tracking_middleware(request: Request, call_next):
    """요청 추적 및 로깅 미들웨어"""
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    # 요청 카운트 증가
    app_state.increment_request_count()

    # 요청 정보 로깅
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        f"🔍 [{request_id}] {request.method} {request.url.path} from {client_ip}"
    )

    try:
        response = await call_next(request)

        # 응답 시간 계산 및 로깅
        elapsed = time.time() - start_time
        logger.info(f"✅ [{request_id}] {response.status_code} - {elapsed:.3f}s")

        # 응답 헤더에 메타데이터 추가
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed:.3f}s"

        return response

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ [{request_id}] 오류 - {elapsed:.3f}s: {str(e)}")
        raise


# === 예외 핸들러들 ===
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리 핸들러"""
    logger.error(f"HTTP 예외: {exc.status_code} - {exc.detail} - URL: {request.url}")

    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseBuilder.error(
            error_code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            status_code=exc.status_code,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 오류 처리 핸들러"""
    logger.error(f"요청 검증 오류: {exc.errors()} - URL: {request.url}")

    return JSONResponse(
        status_code=422,
        content=ResponseBuilder.error(
            error_code="VALIDATION_ERROR",
            message="요청 데이터 형식이 올바르지 않습니다",
            status_code=422,
            details=exc.errors(),
        ),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리 핸들러"""
    request_id = str(uuid.uuid4())[:8]
    logger.error(f"❌ [{request_id}] 예상치 못한 오류: {str(exc)}")
    logger.error(f"❌ [{request_id}] 트레이스백:\n{traceback.format_exc()}")

    return JSONResponse(
        status_code=500,
        content=ResponseBuilder.error(
            error_code="INTERNAL_SERVER_ERROR",
            message="내부 서버 오류가 발생했습니다",
            status_code=500,
            request_id=request_id,
        ),
    )


# === 라우터 등록 ===
# 메인 라우터 (루트, 헬스체크, 테스트)
main_router = create_main_router(app_state, importer)
app.include_router(main_router)

# 요약 라우터  
summarize_router = create_summarize_router(app_state, importer)
app.include_router(summarize_router)

# 히스토리 라우터
history_router = create_history_router(app_state, importer)
app.include_router(history_router)


# === 개발 서버 실행 ===
if __name__ == "__main__":
    print("⚠️  경고: 이 파일은 최적화 버전입니다. 직접 실행하지 마세요.")
    print("💡 대신 다음 명령어를 사용하세요:")
    print("   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload")
    import sys
    sys.exit(1)
