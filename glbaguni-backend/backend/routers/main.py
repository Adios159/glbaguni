#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메인 엔드포인트들 (루트, 헬스체크, 테스트)
"""

import logging
import os
import time
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import text

from ..utils.responses import ResponseBuilder


def create_main_router(app_state, importer):
    """메인 라우터 생성"""
    router = APIRouter()

    @router.get("/")
    async def root():
        """루트 엔드포인트"""
        return ResponseBuilder.success(
            data={
                "service": "글바구니 (Glbaguni)",
                "description": "AI 기반 RSS 피드 요약 서비스",
                "version": "2.2.0",
                "status": "운영중",
                "features": [
                    "RSS 피드 요약",
                    "자연어 뉴스 검색",
                    "사용자 히스토리",
                    "개인화 추천",
                    "이메일 알림",
                ],
                "stats": app_state.get_stats(),
            },
            message="글바구니 서비스에 오신 것을 환영합니다!",
        )

    @router.get("/health")
    async def health_check():
        """상세한 헬스 체크 엔드포인트"""
        try:
            logger = logging.getLogger("glbaguni")
            
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "2.2.0",
                "uptime_seconds": (
                    time.time() - app_state.start_time if app_state.start_time else 0
                ),
                "components": {},
                "environment": {},
                "database": {},
            }

            # 컴포넌트 상태 확인
            if app_state.initialized:
                health_data["components"] = {
                    "core": "healthy",
                    "http_client": "healthy" if app_state.http_client else "unavailable",
                    "fetcher": "healthy" if app_state.fetcher else "unavailable",
                    "summarizer": "healthy" if app_state.summarizer else "unavailable",
                    "notifier": "healthy" if app_state.notifier else "unavailable",
                    "history_service": (
                        "healthy" if app_state.history_service else "unavailable"
                    ),
                    "news_aggregator": (
                        "healthy" if app_state.news_aggregator else "unavailable"
                    ),
                }
            else:
                health_data["status"] = "initializing"
                health_data["components"]["core"] = "initializing"

            # 환경변수 상태
            health_data["environment"] = {
                "openai_api_key": (
                    "configured" if os.getenv("OPENAI_API_KEY") else "missing"
                ),
                "smtp_configured": "yes" if os.getenv("SMTP_USERNAME") else "no",
                "security_module": (
                    "available" if importer.security_available else "unavailable"
                ),
            }

            # 데이터베이스 연결 테스트
            try:
                db_session = next(importer.services["get_db"]())
                db_session.execute(text("SELECT 1"))
                health_data["database"] = {"status": "healthy", "connection": "active"}
                db_session.close()
            except Exception as e:
                logger.error(f"데이터베이스 헬스 체크 실패: {e}")
                health_data["database"] = {"status": "unhealthy", "error": str(e)}
                health_data["status"] = "degraded"

            # 전체 상태 결정
            component_statuses = list(health_data["components"].values())
            if "unavailable" in component_statuses or "unhealthy" in component_statuses:
                health_data["status"] = "degraded"

            return ResponseBuilder.success(data=health_data, message="헬스 체크 완료")

        except Exception as e:
            logger = logging.getLogger("glbaguni")
            logger.error(f"헬스 체크 중 오류: {e}")
            return ResponseBuilder.error(
                error_code="HEALTH_CHECK_ERROR",
                message="헬스 체크 중 오류가 발생했습니다",
                status_code=500,
            )

    @router.get("/test")
    async def test_endpoint():
        """테스트 엔드포인트"""
        return ResponseBuilder.success(
            data={
                "test_status": "OK",
                "environment_vars": {
                    var: "SET" if os.getenv(var) else "NOT_SET"
                    for var in ["OPENAI_API_KEY", "SMTP_USERNAME", "SMTP_PASSWORD"]
                },
                "modules": {
                    "security_available": importer.security_available,
                    "models_loaded": len(importer.models),
                    "services_loaded": len(importer.services),
                },
            },
            message="테스트 완료",
        )

    return router 