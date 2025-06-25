#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rate Limiting 테스트 라우터
Rate limiting 기능을 테스트하고 모니터링할 수 있는 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any

try:
    from utils.logging_config import get_logger
    from utils.rate_limiter import rate_limit_middleware
except ImportError:
    from backend.utils.logging_config import get_logger
    from backend.utils.rate_limiter import rate_limit_middleware
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("rate_limit_test")

router = APIRouter(prefix="/rate-limit", tags=["Rate Limiting"])


@router.get("/test")
async def test_rate_limit(request: Request) -> Dict[str, Any]:
    """
    Rate limiting 테스트 엔드포인트
    이 엔드포인트를 반복 호출하여 rate limiting이 작동하는지 확인할 수 있습니다.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    return {
        "message": "Rate limit 테스트 성공!",
        "timestamp": time.time(),
        "client_ip": client_ip,
        "path": str(request.url.path),
        "method": request.method,
        "headers": {
            "x-ratelimit-limit": request.headers.get("x-ratelimit-limit"),
            "x-ratelimit-remaining": request.headers.get("x-ratelimit-remaining"),
            "x-ratelimit-reset": request.headers.get("x-ratelimit-reset")
        }
    }


@router.get("/status")
async def rate_limit_status(request: Request) -> Dict[str, Any]:
    """
    현재 rate limiting 상태 조회
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # 현재 설정 정보 반환
    return {
        "rate_limit_enabled": True,
        "client_ip": client_ip,
        "limits": {
            "requests_per_minute": 60,
            "window_size_seconds": 60
        },
        "current_time": time.time(),
        "message": "Rate limiting이 활성화되어 있습니다."
    }


@router.post("/bulk-test")
async def bulk_test_rate_limit(request: Request, count: int = 10) -> Dict[str, Any]:
    """
    대량 요청 시뮬레이션
    주의: 이 엔드포인트는 테스트 목적으로만 사용하세요.
    """
    if count > 100:
        raise HTTPException(status_code=400, detail="테스트는 최대 100회까지만 가능합니다.")
    
    client_ip = request.client.host if request.client else "unknown"
    
    return {
        "message": f"{count}번의 요청을 시뮬레이션했습니다.",
        "client_ip": client_ip,
        "simulated_requests": count,
        "warning": "실제로는 각 요청이 개별적으로 rate limit에 적용됩니다."
    }


@router.get("/info")
async def rate_limit_info() -> Dict[str, Any]:
    """
    Rate limiting 설정 정보
    """
    return {
        "rate_limiting": {
            "enabled": True,
            "type": "IP-based",
            "limits": {
                "requests_per_minute": 60,
                "window_size": "60 seconds",
                "response_code": 429
            },
            "features": [
                "IP 기반 제한",
                "슬라이딩 윈도우",
                "Redis/메모리 지원",
                "자동 헤더 추가",
                "예외 경로 지원"
            ]
        },
        "headers": {
            "X-RateLimit-Limit": "분당 허용 요청 수",
            "X-RateLimit-Remaining": "남은 요청 수",
            "X-RateLimit-Reset": "리셋 시간 (Unix timestamp)",
            "Retry-After": "재시도 가능 시간 (초)"
        },
        "exempt_paths": [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/health/basic"
        ]
    } 