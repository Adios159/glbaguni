#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP 차단 및 비정상적인 요청 패턴 감지 시스템
의심스러운 IP를 자동으로 탐지하고 차단하는 기능을 제공합니다.
"""

import asyncio
import hashlib
import json
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Union
import ipaddress
import re

# Redis 선택적 import
try:
    import redis  # type: ignore
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore
    Redis = None  # type: ignore

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

try:
    from utils.logging_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("ip_blocker")


class ThreatLevel(Enum):
    """위협 레벨 정의"""
    LOW = "low"           # 의심스러운 활동
    MEDIUM = "medium"     # 비정상적인 패턴
    HIGH = "high"         # 명백한 공격
    CRITICAL = "critical" # 즉시 차단 필요


class BlockReason(Enum):
    """차단 이유"""
    RATE_LIMIT_ABUSE = "rate_limit_abuse"           # Rate limit 남용
    FAILED_AUTH_ATTEMPTS = "failed_auth_attempts"   # 연속 로그인 실패
    CAPTCHA_FAILURES = "captcha_failures"           # CAPTCHA 반복 실패
    ENDPOINT_SCANNING = "endpoint_scanning"         # 엔드포인트 스캔
    USER_AGENT_VIOLATIONS = "user_agent_violations" # User-Agent 위반
    SUSPICIOUS_PATTERNS = "suspicious_patterns"     # 의심스러운 패턴
    MANUAL_BLOCK = "manual_block"                   # 수동 차단
    HONEYPOT_TRIGGERED = "honeypot_triggered"       # 허니팟 트리거


@dataclass
class RequestPattern:
    """요청 패턴 정보"""
    ip: str
    timestamp: float
    endpoint: str
    method: str
    user_agent: str
    status_code: int
    response_time: float
    threat_score: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "timestamp": self.timestamp,
            "endpoint": self.endpoint,
            "method": self.method,
            "user_agent": self.user_agent,
            "status_code": self.status_code,
            "response_time": self.response_time,
            "threat_score": self.threat_score
        }


@dataclass
class BlockedIP:
    """차단된 IP 정보"""
    ip: str
    reason: BlockReason
    threat_level: ThreatLevel
    blocked_at: float
    blocked_until: float
    block_count: int = 1
    request_count: int = 0
    last_violation: Optional[str] = None
    user_agents: Set[str] = field(default_factory=set)
    endpoints_accessed: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ip": self.ip,
            "reason": self.reason.value,
            "threat_level": self.threat_level.value,
            "blocked_at": self.blocked_at,
            "blocked_until": self.blocked_until,
            "block_count": self.block_count,
            "request_count": self.request_count,
            "last_violation": self.last_violation,
            "user_agents": list(self.user_agents),
            "endpoints_accessed": list(self.endpoints_accessed),
            "remaining_time": max(0, self.blocked_until - time.time())
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlockedIP':
        return cls(
            ip=data["ip"],
            reason=BlockReason(data["reason"]),
            threat_level=ThreatLevel(data["threat_level"]),
            blocked_at=data["blocked_at"],
            blocked_until=data["blocked_until"],
            block_count=data.get("block_count", 1),
            request_count=data.get("request_count", 0),
            last_violation=data.get("last_violation"),
            user_agents=set(data.get("user_agents", [])),
            endpoints_accessed=set(data.get("endpoints_accessed", []))
        )


@dataclass
class IPBlockerConfig:
    """IP 차단 설정"""
    enabled: bool = True
    
    # 패턴 감지 설정
    analysis_window_minutes: int = 15      # 분석 윈도우 (분)
    suspicious_request_count: int = 100    # 의심스러운 요청 수
    rapid_request_threshold: int = 20      # 빠른 요청 임계값 (초당)
    
    # 차단 임계값
    failed_auth_threshold: int = 10        # 인증 실패 임계값
    captcha_failure_threshold: int = 5     # CAPTCHA 실패 임계값
    endpoint_scan_threshold: int = 20      # 엔드포인트 스캔 임계값
    different_ua_threshold: int = 10       # 다른 User-Agent 임계값
    
    # 차단 시간 (초)
    low_threat_block_time: int = 900       # 15분
    medium_threat_block_time: int = 3600   # 1시간
    high_threat_block_time: int = 7200     # 2시간
    critical_threat_block_time: int = 86400 # 24시간
    
    # Redis 설정
    redis_enabled: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 1
    redis_password: Optional[str] = None
    redis_key_prefix: str = "ip_blocker:"
    
    # 화이트리스트
    whitelist_ips: Set[str] = field(default_factory=lambda: {
        "127.0.0.1", "::1", "localhost"
    })
    
    # 보호할 엔드포인트 패턴
    protected_endpoints: List[str] = field(default_factory=lambda: [
        r"/auth/.*",
        r"/admin/.*",
        r"/api/.*",
        r"/captcha/.*"
    ])


class RequestAnalyzer:
    """요청 패턴 분석기"""
    
    def __init__(self, config: IPBlockerConfig):
        self.config = config
        
        # 메모리 저장소
        self.request_history: Dict[str, deque] = defaultdict(deque)
        self.ip_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_requests": 0,
            "failed_auths": 0,
            "captcha_failures": 0,
            "user_agents": set(),
            "endpoints": set(),
            "last_request": 0,
            "first_request": 0,
            "rapid_requests": 0
        })
        
    def analyze_request(self, pattern: RequestPattern) -> Tuple[bool, BlockReason, ThreatLevel]:
        """요청 패턴 분석"""
        ip = pattern.ip
        now = time.time()
        
        # 요청 기록 추가
        self.request_history[ip].append(pattern)
        
        # 윈도우 밖의 오래된 요청 제거
        window_start = now - (self.config.analysis_window_minutes * 60)
        while (self.request_history[ip] and 
               self.request_history[ip][0].timestamp < window_start):
            self.request_history[ip].popleft()
        
        # 통계 업데이트
        stats = self.ip_stats[ip]
        stats["total_requests"] += 1
        stats["last_request"] = now
        stats["user_agents"].add(pattern.user_agent)
        stats["endpoints"].add(pattern.endpoint)
        
        if stats["first_request"] == 0:
            stats["first_request"] = now
        
        # 상태 코드별 처리
        if pattern.status_code == 401:
            stats["failed_auths"] += 1
        elif pattern.status_code == 429:  # Rate limit
            stats["rapid_requests"] += 1
        
        # 위협 분석
        return self._analyze_threats(ip, pattern, stats)
    
    def _analyze_threats(self, ip: str, pattern: RequestPattern, stats: Dict[str, Any]) -> Tuple[bool, BlockReason, ThreatLevel]:
        """위협 분석"""
        recent_requests = len(self.request_history[ip])
        
        # 1. 연속 인증 실패
        if stats["failed_auths"] >= self.config.failed_auth_threshold:
            return True, BlockReason.FAILED_AUTH_ATTEMPTS, ThreatLevel.HIGH
        
        # 2. 빠른 요청 (Rate limiting)
        if recent_requests >= self.config.rapid_request_threshold:
            return True, BlockReason.RATE_LIMIT_ABUSE, ThreatLevel.MEDIUM
        
        # 3. 다양한 User-Agent 사용 (봇 의심)
        if len(stats["user_agents"]) >= self.config.different_ua_threshold:
            return True, BlockReason.USER_AGENT_VIOLATIONS, ThreatLevel.MEDIUM
        
        # 4. CAPTCHA 반복 실패
        if stats["captcha_failures"] >= self.config.captcha_failure_threshold:
            return True, BlockReason.CAPTCHA_FAILURES, ThreatLevel.HIGH
        
        # 5. 다양한 엔드포인트 접근 (스캔 의심)
        if len(stats["endpoints"]) >= self.config.endpoint_scan_threshold:
            return True, BlockReason.ENDPOINT_SCANNING, ThreatLevel.MEDIUM
        
        # 6. 404 에러 패턴 (엔드포인트 탐색)
        recent_404s = sum(1 for req in self.request_history[ip] if req.status_code == 404)
        if recent_404s >= 15:
            return True, BlockReason.ENDPOINT_SCANNING, ThreatLevel.MEDIUM
        
        # 7. 의심스러운 총 요청 수
        if recent_requests >= self.config.suspicious_request_count:
            return True, BlockReason.SUSPICIOUS_PATTERNS, ThreatLevel.LOW
        
        return False, BlockReason.SUSPICIOUS_PATTERNS, ThreatLevel.LOW


class IPBlockerStorage:
    """IP 차단 저장소 (Redis + 메모리)"""
    
    def __init__(self, config: IPBlockerConfig):
        self.config = config
        self.memory_storage: Dict[str, BlockedIP] = {}
        self.redis_client: Optional[Union[Any, None]] = None  # Redis client 타입
        
        if config.redis_enabled and REDIS_AVAILABLE:
            self._connect_redis()
        elif config.redis_enabled and not REDIS_AVAILABLE:
            logger.warning("⚠️ Redis가 설치되지 않았습니다. 메모리 모드로 실행합니다.")
    
    def _connect_redis(self):
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
                socket_connect_timeout=5
            )
            self.redis_client.ping()  # type: ignore
            logger.info("✅ IP Blocker Redis 연결 성공")
        except Exception as e:
            logger.warning(f"⚠️ IP Blocker Redis 연결 실패, 메모리 모드 사용: {e}")
            self.redis_client = None
    
    async def is_blocked(self, ip: str) -> Tuple[bool, Optional[BlockedIP]]:
        """IP 차단 여부 확인"""
        try:
            # Redis에서 확인
            if self.redis_client:
                key = f"{self.config.redis_key_prefix}blocked:{ip}"
                data = self.redis_client.get(key)
                if data:
                    blocked_ip = BlockedIP.from_dict(json.loads(data))
                    if time.time() < blocked_ip.blocked_until:
                        return True, blocked_ip
                    else:
                        # 만료된 차단 해제
                        await self.unblock_ip(ip)
                        return False, None
            
            # 메모리에서 확인
            if ip in self.memory_storage:
                blocked_ip = self.memory_storage[ip]
                if time.time() < blocked_ip.blocked_until:
                    return True, blocked_ip
                else:
                    # 만료된 차단 해제
                    del self.memory_storage[ip]
                    return False, None
            
            return False, None
            
        except Exception as e:
            logger.error(f"IP 차단 확인 중 오류: {e}")
            return False, None
    
    async def block_ip(self, blocked_ip: BlockedIP):
        """IP 차단"""
        try:
            ip = blocked_ip.ip
            
            # Redis에 저장
            if self.redis_client:
                key = f"{self.config.redis_key_prefix}blocked:{ip}"
                ttl = int(blocked_ip.blocked_until - time.time())
                if ttl > 0:
                    self.redis_client.setex(
                        key, 
                        ttl, 
                        json.dumps(blocked_ip.to_dict())
                    )
            
            # 메모리에 저장
            self.memory_storage[ip] = blocked_ip
            
            logger.warning(
                f"🚫 IP 차단: {ip} | 이유: {blocked_ip.reason.value} | "
                f"레벨: {blocked_ip.threat_level.value} | "
                f"해제 시간: {datetime.fromtimestamp(blocked_ip.blocked_until)}"
            )
            
        except Exception as e:
            logger.error(f"IP 차단 처리 중 오류: {e}")
    
    async def unblock_ip(self, ip: str):
        """IP 차단 해제"""
        try:
            # Redis에서 제거
            if self.redis_client:
                key = f"{self.config.redis_key_prefix}blocked:{ip}"
                self.redis_client.delete(key)
            
            # 메모리에서 제거
            if ip in self.memory_storage:
                del self.memory_storage[ip]
            
            logger.info(f"✅ IP 차단 해제: {ip}")
            
        except Exception as e:
            logger.error(f"IP 차단 해제 중 오류: {e}")
    
    async def get_blocked_ips(self) -> List[BlockedIP]:
        """차단된 IP 목록 조회"""
        try:
            blocked_ips = []
            
            # Redis에서 조회
            if self.redis_client:
                pattern = f"{self.config.redis_key_prefix}blocked:*"
                keys = self.redis_client.keys(pattern)
                for key in keys:
                    data = self.redis_client.get(key)
                    if data:
                        blocked_ip = BlockedIP.from_dict(json.loads(data))
                        blocked_ips.append(blocked_ip)
            
            # 메모리에서 조회
            for blocked_ip in self.memory_storage.values():
                # Redis에서 이미 가져온 것과 중복 제거
                if not any(bi.ip == blocked_ip.ip for bi in blocked_ips):
                    blocked_ips.append(blocked_ip)
            
            # 만료된 것들 제거
            current_time = time.time()
            valid_blocked_ips = []
            for blocked_ip in blocked_ips:
                if current_time < blocked_ip.blocked_until:
                    valid_blocked_ips.append(blocked_ip)
                else:
                    await self.unblock_ip(blocked_ip.ip)
            
            return valid_blocked_ips
            
        except Exception as e:
            logger.error(f"차단된 IP 목록 조회 중 오류: {e}")
            return []


class IPBlockerMiddleware:
    """IP 차단 미들웨어"""
    
    def __init__(self, config: Optional[IPBlockerConfig] = None):
        self.config = config or IPBlockerConfig()
        self.analyzer = RequestAnalyzer(self.config)
        self.storage = IPBlockerStorage(self.config)
        
        # 통계
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "analyzed_requests": 0,
            "auto_blocks": 0,
            "manual_blocks": 0,
            "start_time": time.time()
        }
        
        # 정리 작업 플래그 (안전하게 처리)
        self._cleanup_task_started = False
        
        logger.info(f"🛡️ IP 차단 미들웨어 활성화 (Redis: {'사용' if self.config.redis_enabled and REDIS_AVAILABLE else '미사용'})")
    
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
    
    def is_whitelisted(self, ip: str) -> bool:
        """화이트리스트 확인"""
        if ip in self.config.whitelist_ips:
            return True
        
        # CIDR 범위 확인
        try:
            for whitelist_ip in self.config.whitelist_ips:
                if "/" in whitelist_ip:  # CIDR 표기법
                    network = ipaddress.ip_network(whitelist_ip, strict=False)
                    if ipaddress.ip_address(ip) in network:
                        return True
        except ValueError:
            # IP 주소 파싱 실패 시 화이트리스트 통과하지 않음
            pass
        
        return False
    
    def is_protected_endpoint(self, path: str) -> bool:
        """보호된 엔드포인트 확인"""
        for pattern in self.config.protected_endpoints:
            if re.search(pattern, path):
                return True
        return False
    
    async def __call__(self, request: Request, call_next):
        """미들웨어 메인 처리"""
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        try:
            if not self.config.enabled:
                return await call_next(request)
            
            ip = self.get_client_ip(request)
            
            # 화이트리스트 확인
            if self.is_whitelisted(ip):
                return await call_next(request)
            
            # 이미 차단된 IP 확인
            is_blocked, blocked_info = await self.storage.is_blocked(ip)
            if is_blocked and blocked_info:
                self.stats["blocked_requests"] += 1
                
                remaining_time = int(blocked_info.blocked_until - time.time())
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "IP Blocked",
                        "message": f"귀하의 IP가 차단되었습니다. 이유: {blocked_info.reason.value}",
                        "blocked_until": datetime.fromtimestamp(blocked_info.blocked_until).isoformat(),
                        "remaining_seconds": remaining_time,
                        "threat_level": blocked_info.threat_level.value,
                        "block_count": blocked_info.block_count
                    }
                )
            
            # 요청 처리
            response = await call_next(request)
            response_time = time.time() - start_time
            
            # 보호된 엔드포인트만 분석
            if self.is_protected_endpoint(str(request.url.path)):
                self.stats["analyzed_requests"] += 1
                
                # 요청 패턴 생성
                pattern = RequestPattern(
                    ip=ip,
                    timestamp=start_time,
                    endpoint=str(request.url.path),
                    method=request.method,
                    user_agent=request.headers.get("user-agent", ""),
                    status_code=response.status_code,
                    response_time=response_time
                )
                
                # 패턴 분석
                should_block, reason, threat_level = self.analyzer.analyze_request(pattern)
                
                if should_block:
                    await self._block_ip_automatically(ip, reason, threat_level, pattern)
                    self.stats["auto_blocks"] += 1
            
            return response
            
        except Exception as e:
            logger.error(f"IP 차단 미들웨어 오류: {e}")
            # 오류 발생 시에도 요청은 계속 처리
            return await call_next(request)
        
        finally:
            # 정리 작업 시작 (한 번만)
            self._start_cleanup_task_if_needed()
    
    async def _block_ip_automatically(self, ip: str, reason: BlockReason, threat_level: ThreatLevel, pattern: RequestPattern):
        """IP 자동 차단"""
        try:
            # 차단 시간 결정
            block_duration = {
                ThreatLevel.LOW: self.config.low_threat_block_time,
                ThreatLevel.MEDIUM: self.config.medium_threat_block_time,
                ThreatLevel.HIGH: self.config.high_threat_block_time,
                ThreatLevel.CRITICAL: self.config.critical_threat_block_time,
            }.get(threat_level, self.config.medium_threat_block_time)
            
            now = time.time()
            
            # 기존 차단 정보 확인
            _, existing_block = await self.storage.is_blocked(ip)
            
            if existing_block is not None:
                # 기존 차단이 있으면 카운트 증가
                blocked_ip = BlockedIP(
                    ip=ip,
                    reason=reason,
                    threat_level=threat_level,
                    blocked_at=now,
                    blocked_until=now + block_duration,
                    block_count=existing_block.block_count + 1,
                    request_count=existing_block.request_count + 1,
                    last_violation=f"{pattern.method} {pattern.endpoint}",
                    user_agents=existing_block.user_agents | {pattern.user_agent},
                    endpoints_accessed=existing_block.endpoints_accessed | {pattern.endpoint}
                )
            else:
                # 새로운 차단
                blocked_ip = BlockedIP(
                    ip=ip,
                    reason=reason,
                    threat_level=threat_level,
                    blocked_at=now,
                    blocked_until=now + block_duration,
                    block_count=1,
                    request_count=1,
                    last_violation=f"{pattern.method} {pattern.endpoint}",
                    user_agents={pattern.user_agent},
                    endpoints_accessed={pattern.endpoint}
                )
            
            await self.storage.block_ip(blocked_ip)
            
        except Exception as e:
            logger.error(f"IP 자동 차단 처리 중 오류: {e}")
    
    async def block_ip_manually(self, ip: str, reason: str = "Manual block", duration_hours: int = 24) -> bool:
        """IP 수동 차단"""
        try:
            now = time.time()
            blocked_ip = BlockedIP(
                ip=ip,
                reason=BlockReason.MANUAL_BLOCK,
                threat_level=ThreatLevel.HIGH,
                blocked_at=now,
                blocked_until=now + (duration_hours * 3600),
                last_violation=reason
            )
            
            await self.storage.block_ip(blocked_ip)
            self.stats["manual_blocks"] += 1
            return True
            
        except Exception as e:
            logger.error(f"IP 수동 차단 중 오류: {e}")
            return False
    
    async def unblock_ip_manually(self, ip: str) -> bool:
        """IP 수동 차단 해제"""
        try:
            await self.storage.unblock_ip(ip)
            return True
        except Exception as e:
            logger.error(f"IP 수동 차단 해제 중 오류: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        blocked_ips = await self.storage.get_blocked_ips()
        return {
            **self.stats,
            "blocked_ips_count": len(blocked_ips),
            "uptime_seconds": int(time.time() - self.stats["start_time"]),
            "redis_enabled": self.config.redis_enabled and REDIS_AVAILABLE and self.storage.redis_client is not None
        }
    
    async def _cleanup_task(self):
        """만료된 차단 정리 작업"""
        while True:
            try:
                await asyncio.sleep(300)  # 5분마다 실행
                await self.storage.get_blocked_ips()  # 이 메서드에서 만료된 것들을 자동 정리
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"정리 작업 중 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 후 재시도
    
    def _start_cleanup_task_if_needed(self):
        """정리 작업 시작 (필요한 경우)"""
        if not self._cleanup_task_started:
            self._cleanup_task_started = True
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 백그라운드 태스크로 시작
                    asyncio.create_task(self._cleanup_task())
            except Exception as e:
                logger.warning(f"정리 작업 시작 실패: {e}")
                self._cleanup_task_started = False


# 전역 미들웨어 인스턴스
_global_ip_blocker: Optional[IPBlockerMiddleware] = None


def get_ip_blocker_middleware():
    """전역 IP 차단 미들웨어 인스턴스 반환"""
    global _global_ip_blocker
    if _global_ip_blocker is None:
        _global_ip_blocker = IPBlockerMiddleware()
    return _global_ip_blocker


def configure_ip_blocker(
    redis_enabled: bool = False,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    suspicious_request_count: int = 100,
    failed_auth_threshold: int = 10,
    medium_threat_block_time: int = 3600
):
    """IP 차단 시스템 설정"""
    global _global_ip_blocker
    
    config = IPBlockerConfig(
        redis_enabled=redis_enabled and REDIS_AVAILABLE,
        redis_host=redis_host,
        redis_port=redis_port,
        suspicious_request_count=suspicious_request_count,
        failed_auth_threshold=failed_auth_threshold,
        medium_threat_block_time=medium_threat_block_time
    )
    
    _global_ip_blocker = IPBlockerMiddleware(config)
    
    if redis_enabled and not REDIS_AVAILABLE:
        logger.warning("⚠️ Redis를 활성화하려고 했지만 redis 패키지가 설치되지 않았습니다. 메모리 모드로 실행합니다.")
    
    logger.info(f"🛡️ IP 차단 시스템 설정 완료 (Redis: {'사용' if config.redis_enabled else '미사용'})") 