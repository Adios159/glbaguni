#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rate Limiting 미들웨어
IP 기반 요청 속도 제한 기능을 제공합니다.
"""

import time
import asyncio
from typing import Dict, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta

import redis
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
    exempt_paths: list = None
    
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
        
    async def is_allowed(self, ip: str) -> tuple[bool, dict]:
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
        self.redis_client = None
        self._connect_to_redis()
        
    def _connect_to_redis(self):
        """Redis 연결"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                health_check_interval=30
            )
            # 연결 테스트
            self.redis_client.ping()
            logger.info("✅ Redis 연결 성공")
        except Exception as e:
            logger.warning(f"⚠️ Redis 연결 실패, 메모리 모드로 전환: {e}")
            self.redis_client = None
    
    async def is_allowed(self, ip: str) -> tuple[bool, dict]:
        """요청이 허용되는지 확인"""
        if not self.redis_client:
            # Redis 연결 실패시 메모리 모드로 대체
            return True, {"allowed": True, "fallback": "memory"}
        
        try:
            now = int(time.time())
            window_start = now - self.config.window_size
            key = f"rate_limit:{ip}"
            
            # Redis 파이프라인 사용으로 성능 최적화
            pipe = self.redis_client.pipeline()
            
            # 윈도우 밖의 오래된 요청들 제거
            pipe.zremrangebyscore(key, 0, window_start)
            
            # 현재 요청 수 확인
            pipe.zcard(key)
            
            # 새 요청 추가
            pipe.zadd(key, {str(now): now})
            
            # TTL 설정 (윈도우 크기 + 여유시간)
            pipe.expire(key, self.config.window_size + 60)
            
            results = pipe.execute()
            current_requests = results[1]  # zcard 결과
            
            if current_requests >= self.config.requests_per_minute:
                # 제한 초과시 방금 추가한 요청 제거
                self.redis_client.zrem(key, str(now))
                
                # 가장 오래된 요청 시간 조회
                oldest_requests = self.redis_client.zrange(key, 0, 0, withscores=True)
                oldest_time = oldest_requests[0][1] if oldest_requests else now
                reset_time = oldest_time + self.config.window_size
                
                return False, {
                    "allowed": False,
                    "limit": self.config.requests_per_minute,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "current_requests": current_requests
                }
            
            remaining = self.config.requests_per_minute - (current_requests + 1)
            
            return True, {
                "allowed": True,
                "limit": self.config.requests_per_minute,
                "remaining": remaining,
                "reset_time": now + self.config.window_size,
                "current_requests": current_requests + 1
            }
            
        except Exception as e:
            logger.error(f"Redis rate limit 확인 중 오류: {e}")
            # Redis 오류시 요청 허용 (안전한 실패)
            return True, {"allowed": True, "error": str(e)}


class RateLimitMiddleware:
    """Rate Limiting 미들웨어"""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        
        # Redis 우선 시도, 실패시 메모리 사용
        self.redis_limiter = RedisRateLimiter(self.config)
        self.memory_limiter = MemoryRateLimiter(self.config)
        
        # 실제 사용할 limiter 결정
        if self.redis_limiter.redis_client:
            self.limiter = self.redis_limiter
            logger.info("🚀 Redis 기반 Rate Limiter 활성화")
        else:
            self.limiter = self.memory_limiter
            logger.info("🚀 메모리 기반 Rate Limiter 활성화")
            # 메모리 정리 백그라운드 태스크 시작
            asyncio.create_task(self.memory_limiter.cleanup_old_records())
    
    def get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출"""
        # X-Forwarded-For 헤더 확인 (프록시/로드밸런서 환경)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 첫 번째 IP가 실제 클라이언트 IP
            return forwarded_for.split(",")[0].strip()
        
        # X-Real-IP 헤더 확인
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # 직접 연결인 경우
        return request.client.host if request.client else "unknown"
    
    async def __call__(self, request: Request, call_next):
        """미들웨어 실행"""
        # 제외할 경로인지 확인
        if request.url.path in self.config.exempt_paths:
            return await call_next(request)
        
        # 정적 파일 요청 제외
        if request.url.path.startswith(("/static", "/assets", "/favicon")):
            return await call_next(request)
        
        # 클라이언트 IP 추출
        client_ip = self.get_client_ip(request)
        
        try:
            # Rate limit 확인
            allowed, info = await self.limiter.is_allowed(client_ip)
            
            if not allowed:
                # 429 Too Many Requests 응답
                reset_time = datetime.fromtimestamp(info.get("reset_time", time.time()))
                
                logger.warning(
                    f"🚫 Rate limit 초과: IP={client_ip}, "
                    f"경로={request.url.path}, "
                    f"요청수={info.get('current_requests', 0)}/{info.get('limit', 0)}"
                )
                
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "message": f"요청 한도를 초과했습니다. {info.get('limit', 60)}회/분 제한",
                        "limit": info.get("limit"),
                        "reset_time": reset_time.isoformat(),
                        "retry_after": int(info.get("reset_time", time.time()) - time.time())
                    },
                    headers={
                        "X-RateLimit-Limit": str(info.get("limit", 60)),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(info.get("reset_time", time.time()))),
                        "Retry-After": str(max(1, int(info.get("reset_time", time.time()) - time.time())))
                    }
                )
            
            # 요청 처리
            response = await call_next(request)
            
            # Rate limit 정보를 응답 헤더에 추가
            response.headers["X-RateLimit-Limit"] = str(info.get("limit", 60))
            response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(int(info.get("reset_time", time.time())))
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limit 미들웨어 오류: {e}")
            # 오류 발생시 요청 허용 (안전한 실패)
            return await call_next(request)


# Slowapi 설정 (대안)
def get_limiter() -> Limiter:
    """Slowapi Limiter 인스턴스 생성"""
    return Limiter(key_func=get_remote_address)


def create_rate_limit_error_handler():
    """Rate limit 에러 핸들러"""
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        response = JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests", 
                "message": f"요청 한도 초과: {exc.detail}"
            }
        )
        response = _rate_limit_exceeded_handler(request, exc)
        return response
    
    return rate_limit_handler


# 전역 인스턴스
rate_limit_config = RateLimitConfig()
rate_limit_middleware = RateLimitMiddleware(rate_limit_config)
limiter = get_limiter()

# 설정 조정 함수
def configure_rate_limits(
    requests_per_minute: int = 60,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_password: str = None
):
    """Rate limit 설정 조정"""
    global rate_limit_config, rate_limit_middleware
    
    rate_limit_config.requests_per_minute = requests_per_minute
    rate_limit_config.redis_host = redis_host
    rate_limit_config.redis_port = redis_port
    rate_limit_config.redis_password = redis_password
    
    # 미들웨어 재생성
    rate_limit_middleware = RateLimitMiddleware(rate_limit_config)
    
    logger.info(f"✅ Rate limit 설정 업데이트: {requests_per_minute}회/분") 