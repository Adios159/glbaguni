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
from fastapi import FastAPI, HTTPException
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

# ===== 컴포넌트 관리 =====
try:
    from backend.utils.components import cleanup_components, initialize_components
except ImportError:
    from utils.components import cleanup_components, initialize_components

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
        await initialize_components()

        startup_time = time.time() - startup_start
        logger.info(f"🎉 서버 초기화 완료! (소요시간: {startup_time:.2f}초)")

        yield

    except Exception as e:
        logger.error(f"❌ 서버 초기화 실패: {str(e)}")
        raise
    finally:
        logger.info("🔄 서버 종료 중...")
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

# ===== 서버 실행 =====
if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 FastAPI 서버를 직접 실행합니다...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # 프로덕션에서는 False
        log_level="info",
        access_log=True,
    )

