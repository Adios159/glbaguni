#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAPTCHA 검증 및 봇 방지 유틸리티
Google reCAPTCHA와 간단한 로직 체크를 통한 봇 방지 기능을 제공합니다.
"""

import asyncio
import hashlib
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import base64

import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

try:
    from utils.logging_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("captcha_validator")


class CaptchaType(Enum):
    """CAPTCHA 타입 정의"""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    SIMPLE_MATH = "simple_math"
    LOGIC_CHECK = "logic_check"
    HONEYPOT = "honeypot"


class ProtectionLevel(Enum):
    """보호 레벨 정의"""
    DISABLED = "disabled"
    LOW = "low"           # 간단한 체크만
    MEDIUM = "medium"     # CAPTCHA + 로직 체크
    HIGH = "high"         # 모든 검증 + 추가 보안
    PARANOID = "paranoid" # 최대 보안


@dataclass
class CaptchaConfig:
    """CAPTCHA 설정"""
    enabled: bool = True
    protection_level: ProtectionLevel = ProtectionLevel.MEDIUM
    
    # Google reCAPTCHA 설정
    recaptcha_secret_key: Optional[str] = None
    recaptcha_site_key: Optional[str] = None
    recaptcha_version: str = "v2"  # v2 또는 v3
    recaptcha_threshold: float = 0.5  # v3용 스코어 임계값
    
    # 엔드포인트별 보호 설정
    protected_endpoints: Dict[str, ProtectionLevel] = field(default_factory=dict)
    
    # 간단한 검증 설정
    simple_checks_enabled: bool = True
    math_problem_timeout: int = 300  # 수학 문제 유효 시간 (초)
    logic_check_timeout: int = 180   # 로직 체크 유효 시간 (초)
    
    # 허니팟 설정
    honeypot_fields: List[str] = field(default_factory=lambda: ["website", "url", "homepage"])
    
    # 실패 제한
    max_failures_per_ip: int = 5
    failure_window_minutes: int = 15
    lockout_duration_minutes: int = 30
    
    def __post_init__(self):
        if not self.protected_endpoints:
            self.protected_endpoints = {
                "/auth/register": ProtectionLevel.HIGH,
                "/auth/login": ProtectionLevel.MEDIUM,
                "/summarize": ProtectionLevel.LOW,
                "/news-search": ProtectionLevel.LOW,
                "/contact": ProtectionLevel.MEDIUM,
            }


class SimpleMathChallenge(BaseModel):
    """간단한 수학 문제"""
    challenge_id: str
    question: str
    answer: int
    created_at: float
    expires_at: float


class LogicChallenge(BaseModel):
    """로직 체크 문제"""
    challenge_id: str
    question: str
    answer: str
    options: List[str]
    created_at: float
    expires_at: float


class CaptchaRequest(BaseModel):
    """CAPTCHA 요청 모델"""
    recaptcha_token: Optional[str] = Field(None, description="Google reCAPTCHA 토큰")
    math_challenge_id: Optional[str] = Field(None, description="수학 문제 ID")
    math_answer: Optional[int] = Field(None, description="수학 문제 답")
    logic_challenge_id: Optional[str] = Field(None, description="로직 체크 ID")
    logic_answer: Optional[str] = Field(None, description="로직 체크 답")
    honeypot_fields: Optional[Dict[str, str]] = Field(None, description="허니팟 필드들")


class CaptchaResponse(BaseModel):
    """CAPTCHA 응답 모델"""
    success: bool
    message: str
    challenge_type: Optional[str] = None
    challenge_data: Optional[Dict[str, Any]] = None
    timestamp: float = Field(default_factory=time.time)


class CaptchaValidator:
    """CAPTCHA 검증 클래스"""
    
    def __init__(self, config: CaptchaConfig = None):
        self.config = config or CaptchaConfig()
        
        # 활성 챌린지 저장소 (실제 환경에서는 Redis 사용 권장)
        self.math_challenges: Dict[str, SimpleMathChallenge] = {}
        self.logic_challenges: Dict[str, LogicChallenge] = {}
        
        # 실패 추적
        self.failure_tracker: Dict[str, List[float]] = {}
        self.lockout_tracker: Dict[str, float] = {}
        
        # HTTP 클라이언트
        self.http_client = httpx.AsyncClient(timeout=10.0)
        
        logger.info(f"🤖 CAPTCHA 검증기 초기화 완료 (보호 레벨: {self.config.protection_level.value})")
    
    def get_client_identifier(self, request: Request) -> str:
        """클라이언트 식별자 생성"""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")
        
        # IP + User-Agent 해시로 식별자 생성
        identifier_string = f"{client_ip}:{user_agent}"
        return hashlib.md5(identifier_string.encode()).hexdigest()[:16]
    
    def is_locked_out(self, client_id: str) -> bool:
        """클라이언트가 잠금 상태인지 확인"""
        if client_id not in self.lockout_tracker:
            return False
        
        lockout_until = self.lockout_tracker[client_id]
        if time.time() < lockout_until:
            return True
        
        # 잠금 해제
        del self.lockout_tracker[client_id]
        return False
    
    def record_failure(self, client_id: str):
        """실패 기록"""
        now = time.time()
        
        if client_id not in self.failure_tracker:
            self.failure_tracker[client_id] = []
        
        # 윈도우 밖의 오래된 실패 기록 제거
        window_start = now - (self.config.failure_window_minutes * 60)
        self.failure_tracker[client_id] = [
            fail_time for fail_time in self.failure_tracker[client_id] 
            if fail_time > window_start
        ]
        
        # 새 실패 기록
        self.failure_tracker[client_id].append(now)
        
        # 잠금 조건 확인
        if len(self.failure_tracker[client_id]) >= self.config.max_failures_per_ip:
            lockout_until = now + (self.config.lockout_duration_minutes * 60)
            self.lockout_tracker[client_id] = lockout_until
            
            logger.warning(f"🔒 클라이언트 잠금: {client_id} ({self.config.lockout_duration_minutes}분)")
    
    def generate_math_challenge(self) -> SimpleMathChallenge:
        """간단한 수학 문제 생성"""
        challenge_id = str(uuid.uuid4())[:12]
        
        # 다양한 수학 문제 타입
        problem_types = [
            ("addition", lambda: (random.randint(1, 50), random.randint(1, 50), "+")),
            ("subtraction", lambda: (random.randint(20, 100), random.randint(1, 19), "-")),
            ("multiplication", lambda: (random.randint(2, 12), random.randint(2, 12), "×")),
        ]
        
        problem_type, generator = random.choice(problem_types)
        a, b, op = generator()
        
        if op == "+":
            answer = a + b
            question = f"{a} + {b} = ?"
        elif op == "-":
            answer = a - b
            question = f"{a} - {b} = ?"
        elif op == "×":
            answer = a * b
            question = f"{a} × {b} = ?"
        
        now = time.time()
        challenge = SimpleMathChallenge(
            challenge_id=challenge_id,
            question=question,
            answer=answer,
            created_at=now,
            expires_at=now + self.config.math_problem_timeout
        )
        
        self.math_challenges[challenge_id] = challenge
        return challenge
    
    def generate_logic_challenge(self) -> LogicChallenge:
        """로직 체크 문제 생성"""
        challenge_id = str(uuid.uuid4())[:12]
        
        # 다양한 로직 문제들
        logic_problems = [
            {
                "question": "다음 중 과일이 아닌 것은?",
                "options": ["사과", "바나나", "자동차", "딸기"],
                "answer": "자동차"
            },
            {
                "question": "1주일은 며칠입니까?",
                "options": ["5일", "6일", "7일", "8일"],
                "answer": "7일"
            },
            {
                "question": "다음 중 색깔이 아닌 것은?",
                "options": ["빨강", "파랑", "음악", "노랑"],
                "answer": "음악"
            },
            {
                "question": "지구에서 가장 큰 바다는?",
                "options": ["대서양", "태평양", "인도양", "북극해"],
                "answer": "태평양"
            },
            {
                "question": "다음 중 숫자가 아닌 것은?",
                "options": ["1", "2", "안녕", "3"],
                "answer": "안녕"
            }
        ]
        
        problem = random.choice(logic_problems)
        random.shuffle(problem["options"])  # 옵션 순서 섞기
        
        now = time.time()
        challenge = LogicChallenge(
            challenge_id=challenge_id,
            question=problem["question"],
            answer=problem["answer"],
            options=problem["options"],
            created_at=now,
            expires_at=now + self.config.logic_check_timeout
        )
        
        self.logic_challenges[challenge_id] = challenge
        return challenge
    
    async def verify_recaptcha(self, token: str, client_ip: str) -> Tuple[bool, str]:
        """Google reCAPTCHA 검증"""
        if not self.config.recaptcha_secret_key:
            return False, "reCAPTCHA 설정이 되어있지 않습니다"
        
        try:
            data = {
                "secret": self.config.recaptcha_secret_key,
                "response": token,
                "remoteip": client_ip
            }
            
            response = await self.http_client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data=data
            )
            
            result = response.json()
            
            if not result.get("success", False):
                errors = result.get("error-codes", [])
                return False, f"reCAPTCHA 검증 실패: {', '.join(errors)}"
            
            # v3의 경우 스코어 확인
            if self.config.recaptcha_version == "v3":
                score = result.get("score", 0.0)
                if score < self.config.recaptcha_threshold:
                    return False, f"reCAPTCHA 스코어가 낮습니다: {score}"
            
            return True, "reCAPTCHA 검증 성공"
            
        except Exception as e:
            logger.error(f"reCAPTCHA 검증 중 오류: {e}")
            return False, f"reCAPTCHA 검증 오류: {str(e)}"
    
    def verify_math_challenge(self, challenge_id: str, answer: int) -> Tuple[bool, str]:
        """수학 문제 검증"""
        if challenge_id not in self.math_challenges:
            return False, "수학 문제를 찾을 수 없습니다"
        
        challenge = self.math_challenges[challenge_id]
        
        # 만료 확인
        if time.time() > challenge.expires_at:
            del self.math_challenges[challenge_id]
            return False, "수학 문제가 만료되었습니다"
        
        # 답 확인
        if answer != challenge.answer:
            return False, "수학 문제 답이 틀렸습니다"
        
        # 성공 시 챌린지 제거
        del self.math_challenges[challenge_id]
        return True, "수학 문제 검증 성공"
    
    def verify_logic_challenge(self, challenge_id: str, answer: str) -> Tuple[bool, str]:
        """로직 체크 검증"""
        if challenge_id not in self.logic_challenges:
            return False, "로직 문제를 찾을 수 없습니다"
        
        challenge = self.logic_challenges[challenge_id]
        
        # 만료 확인
        if time.time() > challenge.expires_at:
            del self.logic_challenges[challenge_id]
            return False, "로직 문제가 만료되었습니다"
        
        # 답 확인
        if answer.strip() != challenge.answer:
            return False, "로직 문제 답이 틀렸습니다"
        
        # 성공 시 챌린지 제거
        del self.logic_challenges[challenge_id]
        return True, "로직 문제 검증 성공"
    
    def verify_honeypot(self, honeypot_fields: Dict[str, str]) -> Tuple[bool, str]:
        """허니팟 필드 검증"""
        if not honeypot_fields:
            return True, "허니팟 검증 통과"
        
        # 허니팟 필드에 값이 있으면 봇으로 판단
        for field_name, field_value in honeypot_fields.items():
            if field_name in self.config.honeypot_fields and field_value.strip():
                return False, f"허니팟 필드 감지: {field_name}"
        
        return True, "허니팟 검증 통과"
    
    async def validate_request(
        self, 
        request: Request, 
        captcha_data: CaptchaRequest,
        endpoint: str
    ) -> CaptchaResponse:
        """요청 검증"""
        client_id = self.get_client_identifier(request)
        client_ip = request.client.host if request.client else "unknown"
        
        # 잠금 상태 확인
        if self.is_locked_out(client_id):
            return CaptchaResponse(
                success=False,
                message="너무 많은 실패로 인해 일시적으로 차단되었습니다. 나중에 다시 시도해주세요.",
                challenge_type="lockout"
            )
        
        # 엔드포인트별 보호 레벨 확인
        protection_level = self.config.protected_endpoints.get(
            endpoint, 
            self.config.protection_level
        )
        
        if protection_level == ProtectionLevel.DISABLED:
            return CaptchaResponse(success=True, message="검증 비활성화됨")
        
        validation_results = []
        
        try:
            # 허니팟 검증 (모든 레벨에서)
            if captcha_data.honeypot_fields:
                honeypot_success, honeypot_msg = self.verify_honeypot(captcha_data.honeypot_fields)
                if not honeypot_success:
                    self.record_failure(client_id)
                    return CaptchaResponse(success=False, message=honeypot_msg, challenge_type="honeypot")
            
            # 보호 레벨별 검증
            if protection_level in [ProtectionLevel.LOW, ProtectionLevel.MEDIUM, ProtectionLevel.HIGH, ProtectionLevel.PARANOID]:
                
                # 간단한 체크 (LOW 이상)
                if self.config.simple_checks_enabled and protection_level != ProtectionLevel.LOW:
                    if captcha_data.math_challenge_id and captcha_data.math_answer is not None:
                        math_success, math_msg = self.verify_math_challenge(
                            captcha_data.math_challenge_id, 
                            captcha_data.math_answer
                        )
                        validation_results.append(("math", math_success, math_msg))
                    
                    if captcha_data.logic_challenge_id and captcha_data.logic_answer:
                        logic_success, logic_msg = self.verify_logic_challenge(
                            captcha_data.logic_challenge_id,
                            captcha_data.logic_answer
                        )
                        validation_results.append(("logic", logic_success, logic_msg))
                
                # reCAPTCHA 검증 (MEDIUM 이상)
                if protection_level in [ProtectionLevel.MEDIUM, ProtectionLevel.HIGH, ProtectionLevel.PARANOID]:
                    if captcha_data.recaptcha_token:
                        recaptcha_success, recaptcha_msg = await self.verify_recaptcha(
                            captcha_data.recaptcha_token,
                            client_ip
                        )
                        validation_results.append(("recaptcha", recaptcha_success, recaptcha_msg))
            
            # 검증 결과 평가
            if not validation_results:
                # 검증이 필요하지만 데이터가 없음
                if protection_level == ProtectionLevel.LOW:
                    return CaptchaResponse(success=True, message="낮은 보호 레벨 - 검증 통과")
                else:
                    return CaptchaResponse(
                        success=False,
                        message="검증 데이터가 필요합니다",
                        challenge_type="required"
                    )
            
            # 모든 검증이 성공해야 함
            failed_checks = [check for check in validation_results if not check[1]]
            if failed_checks:
                self.record_failure(client_id)
                failure_messages = [check[2] for check in failed_checks]
                return CaptchaResponse(
                    success=False,
                    message=f"검증 실패: {', '.join(failure_messages)}",
                    challenge_type="validation_failed"
                )
            
            # 모든 검증 통과
            return CaptchaResponse(
                success=True,
                message="모든 검증을 통과했습니다",
                challenge_type="success"
            )
            
        except Exception as e:
            logger.error(f"CAPTCHA 검증 중 오류: {e}")
            return CaptchaResponse(
                success=False,
                message="검증 처리 중 오류가 발생했습니다",
                challenge_type="error"
            )
    
    def cleanup_expired_challenges(self):
        """만료된 챌린지 정리"""
        now = time.time()
        
        # 만료된 수학 문제 제거
        expired_math = [
            cid for cid, challenge in self.math_challenges.items() 
            if challenge.expires_at < now
        ]
        for cid in expired_math:
            del self.math_challenges[cid]
        
        # 만료된 로직 문제 제거
        expired_logic = [
            cid for cid, challenge in self.logic_challenges.items() 
            if challenge.expires_at < now
        ]
        for cid in expired_logic:
            del self.logic_challenges[cid]
        
        if expired_math or expired_logic:
            logger.debug(f"만료된 챌린지 정리: 수학 {len(expired_math)}, 로직 {len(expired_logic)}")


# CAPTCHA 미들웨어 및 데코레이터
class CaptchaMiddleware:
    """CAPTCHA 검증 미들웨어"""
    
    def __init__(self, config: CaptchaConfig = None):
        self.validator = CaptchaValidator(config)
        self.config = config or CaptchaConfig()
        
        # 정리 작업 스케줄링
        asyncio.create_task(self._cleanup_task())
        
        logger.info("🤖 CAPTCHA 미들웨어 활성화")
    
    async def _cleanup_task(self):
        """백그라운드 정리 작업"""
        while True:
            try:
                self.validator.cleanup_expired_challenges()
                await asyncio.sleep(300)  # 5분마다 정리
            except Exception as e:
                logger.error(f"CAPTCHA 정리 작업 오류: {e}")
                await asyncio.sleep(60)


# 전역 인스턴스
default_captcha_config = CaptchaConfig()
captcha_validator = CaptchaValidator(default_captcha_config)
captcha_middleware = CaptchaMiddleware(default_captcha_config)

# 설정 함수들
def configure_captcha(
    recaptcha_secret_key: str = None,
    recaptcha_site_key: str = None,
    protection_level: ProtectionLevel = ProtectionLevel.MEDIUM,
    protected_endpoints: Dict[str, ProtectionLevel] = None
):
    """CAPTCHA 설정 업데이트"""
    global default_captcha_config, captcha_validator, captcha_middleware
    
    default_captcha_config.recaptcha_secret_key = recaptcha_secret_key
    default_captcha_config.recaptcha_site_key = recaptcha_site_key
    default_captcha_config.protection_level = protection_level
    
    if protected_endpoints:
        default_captcha_config.protected_endpoints.update(protected_endpoints)
    
    # 인스턴스 재생성
    captcha_validator = CaptchaValidator(default_captcha_config)
    captcha_middleware = CaptchaMiddleware(default_captcha_config)
    
    logger.info(f"✅ CAPTCHA 설정 업데이트 완료 (보호 레벨: {protection_level.value})") 