#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보안 기능 테스트 라우터
Rate limiting, User-Agent 검증 등 보안 기능을 테스트하고 모니터링할 수 있는 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any, Optional

try:
    from utils.logging_config import get_logger
    from utils.rate_limiter import rate_limit_middleware
    from utils.user_agent_validator import user_agent_middleware, SecurityLevel
except ImportError:
    from backend.utils.logging_config import get_logger
    from backend.utils.rate_limiter import rate_limit_middleware
    from backend.utils.user_agent_validator import user_agent_middleware, SecurityLevel
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("security_test")

router = APIRouter(prefix="/security", tags=["Security"])


@router.get("/test/user-agent")
async def test_user_agent_validation(request: Request) -> Dict[str, Any]:
    """
    User-Agent 검증 테스트 엔드포인트
    현재 요청의 User-Agent를 분석하고 검증 결과를 반환합니다.
    """
    user_agent = request.headers.get("user-agent", "")
    client_ip = request.client.host if request.client else "unknown"
    
    # 헤더 분석
    security_headers = {}
    for header in ["x-security-check", "x-security-warning", "x-block-reason"]:
        value = request.headers.get(header)
        if value:
            security_headers[header] = value
    
    return {
        "message": "User-Agent 검증 테스트 성공!",
        "timestamp": time.time(),
        "client_info": {
            "ip": client_ip,
            "user_agent": user_agent,
            "method": request.method,
            "path": str(request.url.path),
            "referer": request.headers.get("referer", ""),
            "x_forwarded_for": request.headers.get("x-forwarded-for", ""),
        },
        "security_headers": security_headers,
        "validation_result": "통과" if user_agent else "User-Agent 헤더 없음"
    }


@router.get("/test/blocked-user-agents")
async def test_blocked_user_agents() -> Dict[str, Any]:
    """
    차단될 User-Agent 패턴들을 보여줍니다.
    """
    blocked_examples = [
        "curl/7.68.0",
        "python-requests/2.25.1",
        "wget/1.20.3",
        "PostmanRuntime/7.28.0",
        "HTTPie/2.4.0",
        "Scrapy/2.5.0",
        "python-urllib3/1.26.5",
        "Go-http-client/1.1",
        "axios/0.21.1",
        "node-fetch/2.6.1"
    ]
    
    return {
        "message": "차단될 User-Agent 패턴 예시",
        "blocked_patterns": blocked_examples,
        "note": "이런 User-Agent들은 보안 정책에 따라 차단될 수 있습니다.",
        "test_instruction": "위 User-Agent 중 하나로 요청을 보내면 차단됩니다."
    }


@router.get("/test/allowed-user-agents")
async def test_allowed_user_agents() -> Dict[str, Any]:
    """
    허용되는 User-Agent 패턴들을 보여줍니다.
    """
    allowed_examples = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
    ]
    
    return {
        "message": "허용되는 User-Agent 패턴 예시",
        "allowed_patterns": allowed_examples,
        "note": "일반적인 웹 브라우저 User-Agent들은 허용됩니다.",
        "categories": {
            "Chrome": "Chrome 기반 브라우저",
            "Firefox": "Firefox 브라우저",
            "Safari": "Safari 브라우저",
            "Edge": "Microsoft Edge 브라우저"
        }
    }


@router.get("/stats")
async def get_security_stats() -> Dict[str, Any]:
    """
    보안 미들웨어 통계 정보
    """
    try:
        # User-Agent 검증 통계
        ua_stats = user_agent_middleware.get_stats() if hasattr(user_agent_middleware, 'get_stats') else {}
        
        # Rate limiting 통계 (가능한 경우)
        rl_stats = {}
        
        return {
            "timestamp": time.time(),
            "user_agent_validation": ua_stats,
            "rate_limiting": rl_stats,
            "security_status": "활성화됨"
        }
    except Exception as e:
        logger.error(f"보안 통계 조회 중 오류: {e}")
        return {
            "error": "통계 조회 실패",
            "message": str(e),
            "timestamp": time.time()
        }


@router.get("/info")
async def security_info() -> Dict[str, Any]:
    """
    보안 설정 정보
    """
    return {
        "security_features": {
            "user_agent_validation": {
                "enabled": True,
                "description": "비정상적인 User-Agent 차단",
                "security_levels": ["permissive", "moderate", "strict", "lockdown"],
                "current_level": "moderate"
            },
            "rate_limiting": {
                "enabled": True,
                "description": "IP 기반 요청 속도 제한",
                "limits": {
                    "requests_per_minute": 60,
                    "window_size": "60 seconds"
                }
            }
        },
        "blocked_user_agents": [
            "자동화 도구 (curl, wget, python-requests)",
            "스크래핑 도구 (Scrapy, BeautifulSoup)",
            "테스팅 도구 (PostmanRuntime, HTTPie)",
            "프로그래밍 언어 HTTP 클라이언트",
            "빈 User-Agent 또는 의심스러운 패턴"
        ],
        "allowed_user_agents": [
            "Chrome, Firefox, Safari, Edge 등 주요 브라우저",
            "모바일 브라우저",
            "정상적인 웹 애플리케이션"
        ],
        "exempt_paths": [
            "/docs", "/redoc", "/openapi.json",
            "/health", "/health/basic",
            "/static/*", "/assets/*", "/favicon.ico"
        ]
    }


@router.post("/test/simulate-attack")
async def simulate_attack(
    request: Request,
    attack_type: str = "user_agent",
    count: int = 5
) -> Dict[str, Any]:
    """
    보안 공격 시뮬레이션 (테스트용)
    실제 공격이 아닌 보안 테스트 목적입니다.
    """
    if count > 20:
        raise HTTPException(status_code=400, detail="시뮬레이션은 최대 20회까지만 가능합니다.")
    
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")
    
    simulation_result = {
        "attack_type": attack_type,
        "simulation_count": count,
        "client_ip": client_ip,
        "current_user_agent": user_agent,
        "timestamp": time.time()
    }
    
    if attack_type == "user_agent":
        simulation_result.update({
            "description": "비정상적인 User-Agent로 요청 시뮬레이션",
            "note": "실제로는 이런 User-Agent들이 차단됩니다",
            "simulated_agents": [
                "curl/7.68.0",
                "python-requests/2.25.1", 
                "Scrapy/2.5.0",
                "bot/1.0",
                "wget/1.20.3"
            ]
        })
    elif attack_type == "rate_limit":
        simulation_result.update({
            "description": "대량 요청으로 Rate Limit 테스트",
            "note": "실제 환경에서는 429 오류가 발생합니다"
        })
    else:
        raise HTTPException(status_code=400, detail="지원되지 않는 공격 타입입니다.")
    
    return simulation_result


@router.get("/test/endpoint-security/{level}")
async def test_endpoint_security(level: str, request: Request) -> Dict[str, Any]:
    """
    엔드포인트별 보안 레벨 테스트
    """
    valid_levels = ["permissive", "moderate", "strict", "lockdown"]
    if level not in valid_levels:
        raise HTTPException(
            status_code=400, 
            detail=f"유효하지 않은 보안 레벨입니다. 사용 가능: {valid_levels}"
        )
    
    user_agent = request.headers.get("user-agent", "")
    
    return {
        "message": f"{level} 보안 레벨 테스트 성공!",
        "security_level": level,
        "user_agent": user_agent,
        "timestamp": time.time(),
        "description": {
            "permissive": "관대한 정책 - 명시적 차단 패턴만 차단",
            "moderate": "중간 정책 - 화이트리스트 우선, 알려진 패턴 확인",
            "strict": "엄격한 정책 - 화이트리스트에만 의존",
            "lockdown": "매우 엄격한 정책 - 주요 브라우저만 허용"
        }.get(level, "알 수 없는 레벨")
    } 