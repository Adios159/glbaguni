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
from typing import Dict, List, Optional, Set, Tuple, Any
import ipaddress
import re

import redis
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
        stats["user_agents"].add(pattern.user_agent)
        stats["endpoints"].add(pattern.endpoint)
        stats["last_request"] = now
        
        if stats["first_request"] == 0:
            stats["first_request"] = now
        
        # 인증 실패 추적
        if pattern.endpoint.startswith("/auth/") and pattern.status_code == 401:
            stats["failed_auths"] += 1
        
        # CAPTCHA 실패 추적
        if pattern.endpoint.startswith("/captcha/") and pattern.status_code == 403:
            stats["captcha_failures"] += 1
        
        # 위협 분석
        return self._analyze_threats(ip, pattern, stats)
    
    def _analyze_threats(self, ip: str, pattern: RequestPattern, stats: Dict[str, Any]) -> Tuple[bool, BlockReason, ThreatLevel]:
        """위협 수준 분석"""
        recent_requests = len(self.request_history[ip])
        
        # 1. 인증 실패 과다
        if stats["failed_auths"] >= self.config.failed_auth_threshold:
            return True, BlockReason.FAILED_AUTH_ATTEMPTS, ThreatLevel.HIGH
        
        # 2. CAPTCHA 실패 과다
        if stats["captcha_failures"] >= self.config.captcha_failure_threshold:
            return True, BlockReason.CAPTCHA_FAILURES, ThreatLevel.MEDIUM
        
        # 3. 빠른 연속 요청
        if recent_requests >= self.config.rapid_request_threshold:
            time_span = time.time() - self.request_history[ip][0].timestamp
            if time_span < 60:  # 1분 내에 너무 많은 요청
                return True, BlockReason.RATE_LIMIT_ABUSE, ThreatLevel.HIGH
        
        # 4. 엔드포인트 스캔
        if len(stats["endpoints"]) >= self.config.endpoint_scan_threshold:
            return True, BlockReason.ENDPOINT_SCANNING, ThreatLevel.MEDIUM
        
        # 5. 다양한 User-Agent 사용 (봇 의심)
        if len(stats["user_agents"]) >= self.config.different_ua_threshold:
            return True, BlockReason.SUSPICIOUS_PATTERNS, ThreatLevel.MEDIUM
        
        # 6. 404 에러 과다 (스캔 의심)
        recent_404s = sum(1 for req in self.request_history[ip] if req.status_code == 404)
        if recent_404s >= 15:
            return True, BlockReason.ENDPOINT_SCANNING, ThreatLevel.MEDIUM
        
        # 7. 의심스러운 총 요청 수
        if recent_requests >= self.config.suspicious_request_count:
            return True, BlockReason.SUSPICIOUS_PATTERNS, ThreatLevel.LOW
        
        return False, None, ThreatLevel.LOW


class IPBlockerStorage:
    """IP 차단 저장소 (Redis + 메모리)"""
    
    def __init__(self, config: IPBlockerConfig):
        self.config = config
        self.memory_storage: Dict[str, BlockedIP] = {}
        self.redis_client = None
        
        if config.redis_enabled:
            self._connect_redis()
    
    def _connect_redis(self):
        """Redis 연결"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
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
    
    def __init__(self, config: IPBlockerConfig = None):
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
        
        logger.info(f"🛡️ IP 차단 미들웨어 활성화 (Redis: {'사용' if self.config.redis_enabled else '미사용'})")
    
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
        except Exception:
            pass
        
        return False
    
    def is_protected_endpoint(self, path: str) -> bool:
        """보호 대상 엔드포인트 확인"""
        for pattern in self.config.protected_endpoints:
            if re.match(pattern, path):
                return True
        return False
    
    async def __call__(self, request: Request, call_next):
        """미들웨어 실행"""
        if not self.config.enabled:
            return await call_next(request)
        
        start_time = time.time()
        client_ip = self.get_client_ip(request)
        self.stats["total_requests"] += 1
        
        try:
            # 화이트리스트 확인
            if self.is_whitelisted(client_ip):
                return await call_next(request)
            
            # 차단 여부 확인
            is_blocked, blocked_info = await self.storage.is_blocked(client_ip)
            if is_blocked:
                self.stats["blocked_requests"] += 1
                
                logger.warning(
                    f"🚫 차단된 IP 접근 시도: {client_ip} | "
                    f"경로: {request.url.path} | "
                    f"이유: {blocked_info.reason.value}"
                )
                
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Forbidden",
                        "message": "귀하의 IP가 임시 차단되었습니다.",
                        "reason": "비정상적인 요청 패턴이 감지되었습니다.",
                        "blocked_until": datetime.fromtimestamp(blocked_info.blocked_until).isoformat(),
                        "contact": "문제가 지속되면 관리자에게 문의하세요.",
                        "ip": client_ip
                    },
                    headers={
                        "X-Blocked-IP": client_ip,
                        "X-Block-Reason": blocked_info.reason.value,
                        "X-Block-Level": blocked_info.threat_level.value,
                        "Retry-After": str(max(1, int(blocked_info.blocked_until - time.time())))
                    }
                )
            
            # 요청 처리
            response = await call_next(request)
            response_time = time.time() - start_time
            
            # 보호 대상 엔드포인트인 경우 패턴 분석
            if self.is_protected_endpoint(request.url.path):
                self.stats["analyzed_requests"] += 1
                
                pattern = RequestPattern(
                    ip=client_ip,
                    timestamp=start_time,
                    endpoint=request.url.path,
                    method=request.method,
                    user_agent=request.headers.get("user-agent", ""),
                    status_code=response.status_code,
                    response_time=response_time
                )
                
                # 비정상 패턴 분석
                should_block, reason, threat_level = self.analyzer.analyze_request(pattern)
                
                if should_block:
                    # 차단 처리
                    await self._block_ip_automatically(client_ip, reason, threat_level, pattern)
            
            return response
            
        except Exception as e:
            logger.error(f"IP 차단 미들웨어 오류: {e}")
            # 오류 발생시 요청 허용
            return await call_next(request)
    
    async def _block_ip_automatically(self, ip: str, reason: BlockReason, threat_level: ThreatLevel, pattern: RequestPattern):
        """자동 IP 차단"""
        now = time.time()
        
        # 차단 시간 결정
        block_duration = {
            ThreatLevel.LOW: self.config.low_threat_block_time,
            ThreatLevel.MEDIUM: self.config.medium_threat_block_time,
            ThreatLevel.HIGH: self.config.high_threat_block_time,
            ThreatLevel.CRITICAL: self.config.critical_threat_block_time
        }[threat_level]
        
        # 기존 차단 정보 확인
        is_blocked, existing_block = await self.storage.is_blocked(ip)
        
        if is_blocked:
            # 기존 차단 연장 및 카운트 증가
            existing_block.block_count += 1
            existing_block.blocked_until = now + (block_duration * existing_block.block_count)  # 반복 시 더 오래 차단
            existing_block.last_violation = f"{reason.value} at {pattern.endpoint}"
            existing_block.user_agents.add(pattern.user_agent)
            existing_block.endpoints_accessed.add(pattern.endpoint)
            blocked_ip = existing_block
        else:
            # 새로운 차단
            blocked_ip = BlockedIP(
                ip=ip,
                reason=reason,
                threat_level=threat_level,
                blocked_at=now,
                blocked_until=now + block_duration,
                last_violation=f"{reason.value} at {pattern.endpoint}",
                user_agents={pattern.user_agent},
                endpoints_accessed={pattern.endpoint}
            )
        
        await self.storage.block_ip(blocked_ip)
        self.stats["auto_blocks"] += 1
    
    async def block_ip_manually(self, ip: str, reason: str = "Manual block", duration_hours: int = 24) -> bool:
        """수동 IP 차단"""
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
            logger.error(f"수동 IP 차단 실패: {e}")
            return False
    
    async def unblock_ip_manually(self, ip: str) -> bool:
        """수동 IP 차단 해제"""
        try:
            await self.storage.unblock_ip(ip)
            return True
        except Exception as e:
            logger.error(f"수동 IP 차단 해제 실패: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        blocked_ips = await self.storage.get_blocked_ips()
        runtime = time.time() - self.stats["start_time"]
        
        return {
            **self.stats,
            "runtime_seconds": runtime,
            "currently_blocked_ips": len(blocked_ips),
            "requests_per_minute": (self.stats["total_requests"] / max(runtime / 60, 1)),
            "block_rate": (self.stats["blocked_requests"] / max(self.stats["total_requests"], 1)) * 100,
            "blocked_ips_info": [ip.to_dict() for ip in blocked_ips[:10]]  # 최근 10개만
        }
    
    async def _cleanup_task(self):
        """만료된 데이터 정리 작업"""
        while True:
            try:
                # 만료된 차단 정리
                await self.storage.get_blocked_ips()  # 내부적으로 만료된 것들 정리
                
                # 요청 히스토리 정리
                now = time.time()
                window_start = now - (self.config.analysis_window_minutes * 60)
                
                for ip in list(self.analyzer.request_history.keys()):
                    history = self.analyzer.request_history[ip]
                    while history and history[0].timestamp < window_start:
                        history.popleft()
                    
                    # 빈 히스토리 제거
                    if not history:
                        del self.analyzer.request_history[ip]
                        if ip in self.analyzer.ip_stats:
                            del self.analyzer.ip_stats[ip]
                
                await asyncio.sleep(300)  # 5분마다 정리
                
            except Exception as e:
                logger.error(f"IP 차단 정리 작업 오류: {e}")
                await asyncio.sleep(60)

    def _start_cleanup_task_if_needed(self):
        """필요시 정리 작업 시작"""
        if not self._cleanup_task_started:
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._cleanup_task())
                self._cleanup_task_started = True
                logger.info("🔄 IP 차단 정리 작업 시작")
            except RuntimeError:
                # 이벤트 루프가 없는 경우 나중에 시작
                pass


# 전역 인스턴스 (지연 생성)
default_ip_blocker_config = IPBlockerConfig()
ip_blocker_middleware = None

def get_ip_blocker_middleware():
    """IP 차단 미들웨어 인스턴스를 안전하게 가져오기"""
    global ip_blocker_middleware
    if ip_blocker_middleware is None:
        ip_blocker_middleware = IPBlockerMiddleware(default_ip_blocker_config)
    return ip_blocker_middleware

# 설정 함수
def configure_ip_blocker(
    redis_enabled: bool = False,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    suspicious_request_count: int = 100,
    failed_auth_threshold: int = 10,
    medium_threat_block_time: int = 3600
):
    """IP 차단 설정 업데이트"""
    global default_ip_blocker_config, ip_blocker_middleware
    
    default_ip_blocker_config.redis_enabled = redis_enabled
    default_ip_blocker_config.redis_host = redis_host
    default_ip_blocker_config.redis_port = redis_port
    default_ip_blocker_config.suspicious_request_count = suspicious_request_count
    default_ip_blocker_config.failed_auth_threshold = failed_auth_threshold
    default_ip_blocker_config.medium_threat_block_time = medium_threat_block_time
    
    # 미들웨어 재생성
    ip_blocker_middleware = IPBlockerMiddleware(default_ip_blocker_config)
    
    logger.info(f"✅ IP 차단 설정 업데이트 완료 (Redis: {'사용' if redis_enabled else '미사용'})") 