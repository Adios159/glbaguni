#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
User-Agent 검증 미들웨어
비정상적인 User-Agent를 감지하고 차단하는 기능을 제공합니다.
"""

import re
import time
from typing import Dict, List, Optional, Pattern, Set
from dataclasses import dataclass
from enum import Enum

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

try:
    from utils.logging_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("user_agent_validator")


class SecurityLevel(Enum):
    """보안 레벨 정의"""
    PERMISSIVE = "permissive"    # 관대한 정책
    MODERATE = "moderate"        # 중간 정책
    STRICT = "strict"           # 엄격한 정책
    LOCKDOWN = "lockdown"       # 매우 엄격한 정책


@dataclass
class UserAgentConfig:
    """User-Agent 검증 설정"""
    enabled: bool = True
    security_level: SecurityLevel = SecurityLevel.MODERATE
    
    # 차단할 User-Agent 패턴들
    blocked_patterns: List[str] = None
    
    # 허용할 User-Agent 패턴들 (화이트리스트)
    allowed_patterns: List[str] = None
    
    # 엔드포인트별 예외 설정
    endpoint_exceptions: Dict[str, SecurityLevel] = None
    
    # 완전히 제외할 경로들
    exempt_paths: List[str] = None
    
    # 경고만 할 패턴들 (차단하지 않음)
    warning_patterns: List[str] = None
    
    # 커스텀 응답 메시지
    custom_block_message: str = "요청이 차단되었습니다. 올바른 클라이언트를 사용해주세요."
    
    def __post_init__(self):
        if self.blocked_patterns is None:
            self.blocked_patterns = self._get_default_blocked_patterns()
        
        if self.allowed_patterns is None:
            self.allowed_patterns = self._get_default_allowed_patterns()
        
        if self.endpoint_exceptions is None:
            self.endpoint_exceptions = {}
        
        if self.exempt_paths is None:
            self.exempt_paths = [
                "/docs", 
                "/redoc", 
                "/openapi.json",
                "/health",
                "/health/basic",
                "/favicon.ico"
            ]
        
        if self.warning_patterns is None:
            self.warning_patterns = []
    
    def _get_default_blocked_patterns(self) -> List[str]:
        """기본 차단 패턴 목록"""
        return [
            # 자동화 도구들
            r"^curl/.*",
            r"^wget/.*",
            r"^python-requests/.*",
            r"^requests/.*",
            r"^urllib.*",
            r"^http\.client.*",
            r"^aiohttp/.*",
            r"^httpx/.*",
            
            # 스크래핑/크롤링 도구들
            r"^Scrapy/.*",
            r"^BeautifulSoup.*",
            r"^selenium.*",
            r"^puppeteer.*",
            r"^playwright.*",
            r"^PhantomJS.*",
            r"^HeadlessChrome.*",
            
            # 테스팅 도구들
            r"^PostmanRuntime/.*",
            r"^Insomnia/.*",
            r"^HTTPie/.*",
            r"^Apache-HttpClient/.*",
            r"^okhttp/.*",
            
            # 의심스러운 패턴들
            r"^Python/.*",
            r"^Java/.*",
            r"^Go-http-client/.*",
            r"^node-fetch/.*",
            r"^axios/.*",
            
            # 비어있거나 의심스러운 User-Agent
            r"^$",  # 빈 User-Agent
            r"^-$",
            r"^None$",
            r"^null$",
            r"^undefined$",
            r"^test.*",
            r"^bot.*",
            r"^crawler.*",
            r"^spider.*",
            
            # 일반적인 악성/스팸 패턴
            r".*[Bb]ot.*",
            r".*[Cc]rawler.*",
            r".*[Ss]pider.*",
            r".*[Ss]craper.*",
        ]
    
    def _get_default_allowed_patterns(self) -> List[str]:
        """기본 허용 패턴 목록 (주요 브라우저들)"""
        return [
            # Chrome 계열
            r".*Chrome/.*",
            r".*Chromium/.*",
            r".*Edge/.*",
            r".*Edg/.*",
            
            # Firefox
            r".*Firefox/.*",
            r".*Gecko/.*",
            
            # Safari
            r".*Safari/.*",
            r".*AppleWebKit/.*",
            
            # 모바일 브라우저
            r".*Mobile.*Safari.*",
            r".*Android.*",
            r".*iPhone.*",
            r".*iPad.*",
            
            # 기타 정상적인 브라우저
            r".*Opera/.*",
            r".*OPR/.*",
            r".*Brave/.*",
            r".*Vivaldi/.*",
            r".*SamsungBrowser/.*",
            
            # API 클라이언트 (허용하려는 경우)
            r".*Postman.*",  # API 테스트용
            r".*Thunder Client.*",
        ]


class UserAgentValidator:
    """User-Agent 검증 클래스"""
    
    def __init__(self, config: UserAgentConfig = None):
        self.config = config or UserAgentConfig()
        
        # 패턴들을 컴파일된 정규식으로 변환
        self.blocked_patterns = self._compile_patterns(self.config.blocked_patterns)
        self.allowed_patterns = self._compile_patterns(self.config.allowed_patterns)
        self.warning_patterns = self._compile_patterns(self.config.warning_patterns)
        
        # 통계 추적
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "warned_requests": 0,
            "allowed_requests": 0,
            "blocked_user_agents": set(),
            "start_time": time.time()
        }
        
        logger.info(f"🛡️ User-Agent 검증기 초기화 완료 (보안 레벨: {self.config.security_level.value})")
    
    def _compile_patterns(self, patterns: List[str]) -> List[Pattern]:
        """문자열 패턴들을 컴파일된 정규식으로 변환"""
        compiled = []
        for pattern in patterns:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"⚠️ 잘못된 정규식 패턴: {pattern} - {e}")
        return compiled
    
    def get_client_info(self, request: Request) -> Dict[str, str]:
        """클라이언트 정보 추출"""
        user_agent = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else "unknown"
        
        return {
            "user_agent": user_agent,
            "client_ip": client_ip,
            "path": str(request.url.path),
            "method": request.method,
            "referer": request.headers.get("referer", ""),
            "x_forwarded_for": request.headers.get("x-forwarded-for", ""),
            "x_real_ip": request.headers.get("x-real-ip", "")
        }
    
    def get_security_level_for_path(self, path: str) -> SecurityLevel:
        """경로별 보안 레벨 결정"""
        # 엔드포인트별 예외 설정 확인
        for endpoint_pattern, level in self.config.endpoint_exceptions.items():
            if re.match(endpoint_pattern, path):
                return level
        
        # 기본 보안 레벨 반환
        return self.config.security_level
    
    def is_user_agent_allowed(self, user_agent: str, security_level: SecurityLevel) -> tuple[bool, str, bool]:
        """
        User-Agent가 허용되는지 확인
        
        Returns:
            (허용 여부, 이유, 경고 여부)
        """
        if not user_agent:
            return False, "User-Agent 헤더가 없습니다", False
        
        # 보안 레벨별 검증 로직
        if security_level == SecurityLevel.PERMISSIVE:
            # 관대한 정책: 명시적으로 차단된 것들만 차단
            for pattern in self.blocked_patterns:
                if pattern.search(user_agent):
                    return False, f"차단된 User-Agent 패턴: {pattern.pattern}", False
            return True, "허용됨 (관대한 정책)", False
        
        elif security_level == SecurityLevel.MODERATE:
            # 중간 정책: 화이트리스트 우선, 블랙리스트 확인
            
            # 먼저 허용 패턴 확인
            for pattern in self.allowed_patterns:
                if pattern.search(user_agent):
                    return True, f"허용된 User-Agent: {pattern.pattern}", False
            
            # 차단 패턴 확인
            for pattern in self.blocked_patterns:
                if pattern.search(user_agent):
                    return False, f"차단된 User-Agent 패턴: {pattern.pattern}", False
            
            # 경고 패턴 확인
            for pattern in self.warning_patterns:
                if pattern.search(user_agent):
                    return True, f"경고 User-Agent: {pattern.pattern}", True
            
            # 알 수 없는 User-Agent는 허용 (중간 정책)
            return True, "알 수 없는 User-Agent (허용)", False
        
        elif security_level == SecurityLevel.STRICT:
            # 엄격한 정책: 화이트리스트에만 의존
            
            # 허용 패턴 확인
            for pattern in self.allowed_patterns:
                if pattern.search(user_agent):
                    return True, f"허용된 User-Agent: {pattern.pattern}", False
            
            # 화이트리스트에 없으면 차단
            return False, "화이트리스트에 없는 User-Agent", False
        
        elif security_level == SecurityLevel.LOCKDOWN:
            # 잠금 정책: 매우 제한적
            
            # 매우 엄격한 브라우저 패턴만 허용
            strict_patterns = [
                re.compile(r".*Chrome/\d+.*Safari.*", re.IGNORECASE),
                re.compile(r".*Firefox/\d+.*Gecko.*", re.IGNORECASE),
                re.compile(r".*Safari/\d+.*AppleWebKit.*", re.IGNORECASE),
                re.compile(r".*Edge/\d+.*", re.IGNORECASE),
            ]
            
            for pattern in strict_patterns:
                if pattern.search(user_agent):
                    return True, f"엄격한 검증 통과: {pattern.pattern}", False
            
            return False, "매우 엄격한 정책에 의해 차단", False
        
        return False, "알 수 없는 보안 레벨", False
    
    async def validate_request(self, request: Request) -> tuple[bool, Dict[str, any]]:
        """요청 검증"""
        self.stats["total_requests"] += 1
        
        # 클라이언트 정보 추출
        client_info = self.get_client_info(request)
        path = client_info["path"]
        user_agent = client_info["user_agent"]
        
        # 제외 경로 확인
        if path in self.config.exempt_paths:
            self.stats["allowed_requests"] += 1
            return True, {"status": "exempt", "reason": "제외 경로"}
        
        # 정적 파일 요청 허용
        if path.startswith(("/static", "/assets", "/favicon")):
            self.stats["allowed_requests"] += 1
            return True, {"status": "static", "reason": "정적 파일"}
        
        # 보안 레벨 결정
        security_level = self.get_security_level_for_path(path)
        
        # User-Agent 검증
        allowed, reason, is_warning = self.is_user_agent_allowed(user_agent, security_level)
        
        result_info = {
            "status": "allowed" if allowed else "blocked",
            "reason": reason,
            "security_level": security_level.value,
            "client_info": client_info,
            "is_warning": is_warning
        }
        
        if allowed:
            if is_warning:
                self.stats["warned_requests"] += 1
                logger.warning(
                    f"⚠️ 의심스러운 User-Agent: {user_agent} | "
                    f"IP: {client_info['client_ip']} | 경로: {path}"
                )
            else:
                self.stats["allowed_requests"] += 1
        else:
            self.stats["blocked_requests"] += 1
            self.stats["blocked_user_agents"].add(user_agent)
            logger.warning(
                f"🚫 User-Agent 차단: {user_agent} | "
                f"IP: {client_info['client_ip']} | 경로: {path} | 이유: {reason}"
            )
        
        return allowed, result_info


class UserAgentMiddleware:
    """User-Agent 검증 미들웨어"""
    
    def __init__(self, config: UserAgentConfig = None):
        self.validator = UserAgentValidator(config)
        self.config = config or UserAgentConfig()
        
        logger.info("🛡️ User-Agent 검증 미들웨어 활성화")
    
    async def __call__(self, request: Request, call_next):
        """미들웨어 실행"""
        if not self.config.enabled:
            return await call_next(request)
        
        try:
            # User-Agent 검증
            allowed, info = await self.validator.validate_request(request)
            
            if not allowed:
                # 차단 응답
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Forbidden",
                        "message": self.config.custom_block_message,
                        "reason": info.get("reason", "User-Agent 검증 실패"),
                        "security_level": info.get("security_level"),
                        "timestamp": time.time()
                    },
                    headers={
                        "X-Security-Check": "Failed",
                        "X-Block-Reason": "Invalid User-Agent"
                    }
                )
            
            # 요청 처리
            response = await call_next(request)
            
            # 보안 헤더 추가
            response.headers["X-Security-Check"] = "Passed"
            if info.get("is_warning"):
                response.headers["X-Security-Warning"] = "Suspicious User-Agent"
            
            return response
            
        except Exception as e:
            logger.error(f"User-Agent 미들웨어 오류: {e}")
            # 오류 발생시 요청 허용 (안전한 실패)
            return await call_next(request)
    
    def get_stats(self) -> Dict[str, any]:
        """통계 정보 반환"""
        stats = self.validator.stats.copy()
        runtime = time.time() - stats["start_time"]
        
        stats.update({
            "runtime_seconds": runtime,
            "requests_per_minute": (stats["total_requests"] / max(runtime / 60, 1)),
            "block_rate": (stats["blocked_requests"] / max(stats["total_requests"], 1)) * 100,
            "blocked_user_agents_count": len(stats["blocked_user_agents"]),
            "unique_blocked_agents": list(stats["blocked_user_agents"])[:20]  # 상위 20개만
        })
        
        return stats


# 전역 인스턴스 및 설정 함수들
def create_user_agent_config(
    security_level: SecurityLevel = SecurityLevel.MODERATE,
    custom_blocked_patterns: List[str] = None,
    custom_allowed_patterns: List[str] = None,
    endpoint_exceptions: Dict[str, SecurityLevel] = None
) -> UserAgentConfig:
    """User-Agent 검증 설정 생성"""
    config = UserAgentConfig(
        security_level=security_level,
        endpoint_exceptions=endpoint_exceptions or {}
    )
    
    if custom_blocked_patterns:
        config.blocked_patterns.extend(custom_blocked_patterns)
    
    if custom_allowed_patterns:
        config.allowed_patterns.extend(custom_allowed_patterns)
    
    return config


def create_permissive_config() -> UserAgentConfig:
    """관대한 정책 설정"""
    return UserAgentConfig(
        security_level=SecurityLevel.PERMISSIVE,
        custom_block_message="요청이 차단되었습니다. 의심스러운 클라이언트가 감지되었습니다."
    )


def create_strict_config() -> UserAgentConfig:
    """엄격한 정책 설정"""
    return UserAgentConfig(
        security_level=SecurityLevel.STRICT,
        custom_block_message="접근이 거부되었습니다. 승인된 브라우저만 사용 가능합니다."
    )


# 기본 설정
default_config = UserAgentConfig()
user_agent_middleware = UserAgentMiddleware(default_config) 