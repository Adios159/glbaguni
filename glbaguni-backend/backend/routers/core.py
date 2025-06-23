#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
핵심 라우터 모듈
기본 엔드포인트들 (/, /health, /debug) 관리
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger("glbaguni.core")

router = APIRouter()


@router.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": "글바구니 (Glbaguni)",
        "description": "AI 기반 RSS 요약 서비스",
        "version": "3.0.0",
        "status": "running",
        "features": [
            "RSS 피드 요약",
            "사용자 히스토리 관리",
            "개인화 추천",
            "다국어 지원 (한국어/영어)",
            "완전 비동기 처리",
            "포괄적 오류 처리",
            "실시간 로깅"
        ],
        "endpoints": {
            "health": "/health",
            "debug": "/debug", 
            "docs": "/docs",
            "summarize": "/summarize",
            "summarize_text": "/summarize/text",
            "history": "/history",
            "news_search": "/news-search"
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health")
async def health_check():
    """포괄적인 헬스 체크"""
    start_time = time.time()
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "uptime_seconds": time.time()
    }
    
    checks = {}
    
    try:
        # 환경변수 체크
        checks["environment"] = {
            "openai_api_key": "✅" if os.getenv("OPENAI_API_KEY") else "❌",
            "smtp_configured": "✅" if (os.getenv("SMTP_USERNAME") and os.getenv("SMTP_PASSWORD")) else "⚠️"
        }
        
        # 데이터베이스 체크
        try:
            from ..database import get_db
            db = next(get_db())
            await asyncio.to_thread(db.execute, text("SELECT 1"))
            db.close()
            checks["database"] = "✅ healthy"
        except Exception as e:
            checks["database"] = f"❌ {str(e)}"
            health_status["status"] = "degraded"
        
        # 컴포넌트 체크
        try:
            from ..utils.components import components
            component_status = {}
            for name, component in [
                ("fetcher", components.fetcher),
                ("summarizer", components.summarizer),
                ("history_service", components.history_service),
                ("news_aggregator", components.news_aggregator),
                ("notifier", components.notifier)
            ]:
                component_status[name] = "✅" if component else "❌"
            
            checks["components"] = component_status
        except ImportError:
            checks["components"] = "⚠️ not available"
        
        # 전체 상태 결정
        if any("❌" in str(v) for v in checks.values()):
            health_status["status"] = "unhealthy"
        elif any("⚠️" in str(v) for v in checks.values()):
            health_status["status"] = "degraded"
        
        health_status["checks"] = checks
        health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        return health_status
        
    except Exception as e:
        logger.error(f"헬스 체크 실패: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }


@router.get("/debug")
async def debug_info():
    """디버깅 정보 엔드포인트"""
    try:
        from ..utils.components import components
        
        components_status = {
            "http_client": bool(components.http_client),
            "fetcher": bool(components.fetcher),
            "summarizer": bool(components.summarizer),
            "notifier": bool(components.notifier),
            "history_service": bool(components.history_service),
            "news_aggregator": bool(components.news_aggregator)
        }
    except ImportError:
        components_status = {"status": "not available"}
    
    # 보안 모듈 확인
    try:
        from ..security import validate_input
        security_available = True
    except ImportError:
        security_available = False
    
    return {
        "environment_variables": {
            "OPENAI_API_KEY": "SET" if os.getenv("OPENAI_API_KEY") else "NOT_SET",
            "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "default"),
            "SMTP_HOST": os.getenv("SMTP_HOST", "default"),
            "SMTP_USERNAME": "SET" if os.getenv("SMTP_USERNAME") else "NOT_SET"
        },
        "components_status": components_status,
        "security_module": security_available,
        "python_version": sys.version,
        "current_working_directory": os.getcwd(),
        "timestamp": datetime.now().isoformat()
    } 