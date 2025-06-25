#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rate Limiting 미들웨어
IP 기반 요청 속도 제한 기능을 제공합니다.
"""

import time
import asyncio
from typing import Dict, Optional, List, Tuple, Any, Union
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta

# Redis 선택적 import
try:
    import redis  # type: ignore
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

# SlowAPI 선택적 import
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler  # type: ignore
    from slowapi.util import get_remote_address  # type: ignore
    from slowapi.errors import RateLimitExceeded  # type: ignore
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    Limiter = None  # type: ignore
    _rate_limit_exceeded_handler = None  # type: ignore
    get_remote_address = None  # type: ignore
    RateLimitExceeded = Exception  # type: ignore

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

try:
    from utils.logging_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("rate_limiter")


@dataclass
class RateLimitConfig:
    """Rate Limit 설정 클래스"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000  
    requests_per_day: int = 10000
    window_size: int = 60  # 윈도우 크기 (초)
    
    # Redis 설정
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # 제외할 엔드포인트들
    exempt_paths: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.exempt_paths is None:
            self.exempt_paths = [
                "/docs", 
                "/redoc", 
                "/openapi.json",
                "/health",
                "/health/basic"
            ]


class MemoryRateLimiter:
    """메모리 기반 Rate Limiter"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()
        
        # 메모리 관리 시스템에 캐시 등록
        try:
            from utils.memory_manager import get_memory_manager
            memory_manager = get_memory_manager()
            memory_manager.register_cache("rate_limiter_requests", self.requests)
            logger.debug("Rate Limiter 캐시를 메모리 관리 시스템에 등록했습니다.")
        except Exception as e:
            logger.debug(f"Rate Limiter 캐시 등록 실패 (무시됨): {e}")
        
    async def is_allowed(self, ip: str) -> Tuple[bool, Dict[str, Any]]:
        """요청이 허용되는지 확인"""
        async with self.lock:
            now = time.time()
            window_start = now - self.config.window_size
            
            # 현재 IP의 요청 기록
            ip_requests = self.requests[ip]
            
            # 윈도우 밖의 오래된 요청들 제거
            while ip_requests and ip_requests[0] < window_start:
                ip_requests.popleft()
            
            # 현재 요청 수 확인
            current_requests = len(ip_requests)
            
            # 제한 초과 확인
            if current_requests >= self.config.requests_per_minute:
                oldest_request = ip_requests[0] if ip_requests else now
                reset_time = oldest_request + self.config.window_size
                
                return False, {
                    "allowed": False,
                    "limit": self.config.requests_per_minute,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "current_requests": current_requests
                }
            
            # 새 요청 기록
            ip_requests.append(now)
            remaining = self.config.requests_per_minute - (current_requests + 1)
            
            return True, {
                "allowed": True,
                "limit": self.config.requests_per_minute,
                "remaining": remaining,
                "reset_time": window_start + self.config.window_size,
                "current_requests": current_requests + 1
            }
    
    async def cleanup_old_records(self):
        """오래된 요청 기록 정리 (백그라운드 태스크)"""
        while True:
            try:
                async with self.lock:
                    now = time.time()
                    window_start = now - self.config.window_size
                    
                    # 각 IP별로 오래된 기록 정리
                    ips_to_remove = []
                    for ip, ip_requests in self.requests.items():
                        while ip_requests and ip_requests[0] < window_start:
                            ip_requests.popleft()
                        
                        # 요청 기록이 없는 IP 제거
                        if not ip_requests:
                            ips_to_remove.append(ip)
                    
                    for ip in ips_to_remove:
                        del self.requests[ip]
                
                # 30초마다 정리
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"메모리 정리 중 오류: {e}")
                await asyncio.sleep(60)


class RedisRateLimiter:
    """Redis 기반 Rate Limiter"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.redis_client: Optional[Any] = None
        if REDIS_AVAILABLE:
            self._connect_to_redis()
        else:
            logger.warning("⚠️ Redis가 설치되지 않았습니다. 메모리 모드로 실행합니다.")
        
    def _connect_to_redis(self):
        """Redis 연결"""
        if not REDIS_AVAILABLE or not redis:
            logger.warning("⚠️ Redis 모듈을 사용할 수 없습니다.")
            return
            
        try:
            self.redis_client = redis.Redis(  # type: ignore
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                health_check_interval=30
            )
            # 연결 테스트
            self.redis_client.ping()  # type: ignore
            logger.info("✅ Redis 연결 성공")
        except Exception as e:
            logger.warning(f"⚠️ Redis 연결 실패, 메모리 모드로 전환: {e}")
            self.redis_client = None
    
    async def is_allowed(self, ip: str) -> Tuple[bool, Dict[str, Any]]:
        """요청이 허용되는지 확인"""
        if not self.redis_client:
            # Redis 연결 실패시 메모리 모드로 대체
            return True, {"allowed": True, "fallback": "memory"}
        
        try:
            now = int(time.time())
            window_start = now - self.config.window_size
            key = f"rate_limit:{ip}"
            
            # Redis 파이프라인 사용으로 성능 최적화
            pipe = self.redis_client.pipeline()  # type: ignore
            
            # 윈도우 밖의 오래된 요청들 제거
            pipe.zremrangebyscore(key, 0, window_start)  # type: ignore
            
            # 현재 요청 수 확인
            pipe.zcard(key)  # type: ignore
            
            # 새 요청 추가
            pipe.zadd(key, {str(now): now})  # type: ignore
            
            # TTL 설정 (윈도우 크기 + 여유시간)
            pipe.expire(key, self.config.window_size + 60)  # type: ignore
            
            results = pipe.execute()  # type: ignore
            current_requests = results[1]  # zcard 결과
            
            if current_requests >= self.config.requests_per_minute:
                # 제한 초과시 방금 추가한 요청 제거
                self.redis_client.zrem(key, str(now))  # type: ignore
                
                # 가장 오래된 요청 시간 조회
                oldest_requests = self.redis_client.zrange(key, 0, 0, withscores=True)  # type: ignore
                oldest_time = oldest_requests[0][1] if oldest_requests else now
                reset_time = oldest_time + self.config.window_size
                
                return False, {
                    "allowed": False,
                    "limit": self.config.requests_per_minute,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "current_requests": current_requests
                }
            
            remaining = self.config.requests_per_minute - current_requests
            
            return True, {
                "allowed": True,
                "limit": self.config.requests_per_minute,
                "remaining": remaining,
                "reset_time": window_start + self.config.window_size,
                "current_requests": current_requests
            }
            
        except Exception as e:
            logger.error(f"Redis rate limiting 오류: {e}")
            # Redis 오류시 요청 허용 (fail-open)
            return True, {"allowed": True, "error": str(e)}


class RateLimitMiddleware:
    """Rate Limiting 미들웨어"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        
        # Redis 우선, 실패시 메모리 사용
        if REDIS_AVAILABLE:
            self.limiter = RedisRateLimiter(self.config)
        else:
            self.limiter = MemoryRateLimiter(self.config)
            logger.info("📝 메모리 기반 Rate Limiter 사용")
            
        # 메모리 정리 태스크 시작
        if isinstance(self.limiter, MemoryRateLimiter):
            asyncio.create_task(self.limiter.cleanup_old_records())
    
    def get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 추출"""
        # X-Forwarded-For 헤더 확인
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # X-Real-IP 헤더 확인
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # 직접 연결
        return request.client.host if request.client else "unknown"
    
    async def __call__(self, request: Request, call_next):
        """미들웨어 메인 처리"""
        try:
            # 제외 경로 확인
            path = str(request.url.path)
            if self.config.exempt_paths and any(exempt in path for exempt in self.config.exempt_paths):
                return await call_next(request)
            
            # 클라이언트 IP 추출
            client_ip = self.get_client_ip(request)
            
            # Rate limit 확인
            allowed, info = await self.limiter.is_allowed(client_ip)
            
            if not allowed:
                # Rate limit 초과
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"요청 한도를 초과했습니다. {info.get('remaining', 0)}초 후 다시 시도해주세요.",
                        "limit": info.get("limit", 0),
                        "remaining": info.get("remaining", 0),
                        "reset_time": info.get("reset_time", 0),
                        "current_requests": info.get("current_requests", 0)
                    },
                    headers={
                        "X-RateLimit-Limit": str(info.get("limit", 0)),
                        "X-RateLimit-Remaining": str(info.get("remaining", 0)),
                        "X-RateLimit-Reset": str(int(info.get("reset_time", 0))),
                        "Retry-After": str(int(info.get("reset_time", 0) - time.time()))
                    }
                )
            
            # 요청 처리
            response = await call_next(request)
            
            # Rate limit 헤더 추가
            if "error" not in info:  # Redis 오류가 없는 경우만
                response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
                response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
                response.headers["X-RateLimit-Reset"] = str(int(info.get("reset_time", 0)))
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting 미들웨어 오류: {e}")
            # 오류 발생시 요청 계속 처리 (fail-open)
            return await call_next(request)


def get_limiter() -> Optional[Any]:
    """SlowAPI Limiter 인스턴스 반환"""
    if not SLOWAPI_AVAILABLE:
        logger.warning("⚠️ SlowAPI가 설치되지 않았습니다.")
        return None
        
    if REDIS_AVAILABLE:
        return Limiter(key_func=get_remote_address)  # type: ignore
    else:
        logger.warning("⚠️ Redis 없이 SlowAPI 사용, 메모리 기반으로 동작")
        return Limiter(key_func=get_remote_address)  # type: ignore


def create_rate_limit_error_handler():
    """Rate limit 오류 핸들러 생성"""
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        response = JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "요청이 너무 빈번합니다. 잠시 후 다시 시도해주세요.",
                "detail": str(exc.detail) if hasattr(exc, 'detail') else "Rate limit exceeded"
            }
        )
        return response
    return rate_limit_handler


def configure_rate_limits(
    requests_per_minute: int = 60,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_password: Optional[str] = None
) -> RateLimitConfig:
    """Rate limit 설정 구성"""
    config = RateLimitConfig(
        requests_per_minute=requests_per_minute,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_password=redis_password
    )
    
    if not REDIS_AVAILABLE:
        logger.warning("⚠️ Redis가 설치되지 않아 메모리 기반 rate limiting을 사용합니다.")
    
    if not SLOWAPI_AVAILABLE:
        logger.warning("⚠️ SlowAPI가 설치되지 않아 커스텀 rate limiting을 사용합니다.")
        
    return config


# 전역 미들웨어 인스턴스
_global_rate_limiter: Optional[RateLimitMiddleware] = None


def get_rate_limit_middleware():
    """전역 Rate Limit 미들웨어 인스턴스 반환"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimitMiddleware()
    return _global_rate_limiter


def rate_limit_middleware(request: Request, call_next):
    """Rate Limit 미들웨어 함수"""
    middleware_instance = get_rate_limit_middleware()
    return middleware_instance(request, call_next) 