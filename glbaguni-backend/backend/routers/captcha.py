#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAPTCHA 관련 라우터
CAPTCHA 생성, 검증 및 관리 기능을 제공합니다.
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any, Optional

try:
    from utils.logging_config import get_logger
    from utils.captcha_validator import (
        CaptchaValidator, 
        CaptchaConfig, 
        CaptchaRequest, 
        CaptchaResponse,
        ProtectionLevel,
        captcha_validator
    )
except ImportError:
    from backend.utils.logging_config import get_logger
    from backend.utils.captcha_validator import (
        CaptchaValidator, 
        CaptchaConfig, 
        CaptchaRequest, 
        CaptchaResponse,
        ProtectionLevel,
        captcha_validator
    )
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("captcha_router")

router = APIRouter(prefix="/captcha", tags=["CAPTCHA & Bot Protection"])


@router.get("/challenge/math")
async def get_math_challenge() -> Dict[str, Any]:
    """
    수학 문제 생성
    간단한 산수 문제를 생성하여 반환합니다.
    """
    try:
        challenge = captcha_validator.generate_math_challenge()
        
        return {
            "challenge_id": challenge.challenge_id,
            "question": challenge.question,
            "expires_at": challenge.expires_at,
            "timeout_seconds": captcha_validator.config.math_problem_timeout,
            "instructions": "주어진 수학 문제를 풀어서 답을 입력하세요."
        }
    except Exception as e:
        logger.error(f"수학 문제 생성 중 오류: {e}")
        raise HTTPException(status_code=500, detail="수학 문제 생성에 실패했습니다")


@router.get("/challenge/logic")
async def get_logic_challenge() -> Dict[str, Any]:
    """
    로직 체크 문제 생성
    간단한 상식 문제를 생성하여 반환합니다.
    """
    try:
        challenge = captcha_validator.generate_logic_challenge()
        
        return {
            "challenge_id": challenge.challenge_id,
            "question": challenge.question,
            "options": challenge.options,
            "expires_at": challenge.expires_at,
            "timeout_seconds": captcha_validator.config.logic_check_timeout,
            "instructions": "다음 질문에 대한 올바른 답을 선택하세요."
        }
    except Exception as e:
        logger.error(f"로직 문제 생성 중 오류: {e}")
        raise HTTPException(status_code=500, detail="로직 문제 생성에 실패했습니다")


@router.post("/verify")
async def verify_captcha(
    request: Request,
    captcha_data: CaptchaRequest,
    endpoint: str = "/test"
) -> CaptchaResponse:
    """
    CAPTCHA 검증
    제공된 CAPTCHA 데이터를 검증합니다.
    """
    try:
        result = await captcha_validator.validate_request(request, captcha_data, endpoint)
        
        if not result.success:
            logger.warning(
                f"CAPTCHA 검증 실패: {result.message} | "
                f"IP: {request.client.host if request.client else 'unknown'} | "
                f"엔드포인트: {endpoint}"
            )
        
        return result
    except Exception as e:
        logger.error(f"CAPTCHA 검증 중 오류: {e}")
        return CaptchaResponse(
            success=False,
            message="검증 처리 중 오류가 발생했습니다",
            challenge_type="error"
        )


@router.get("/config")
async def get_captcha_config() -> Dict[str, Any]:
    """
    CAPTCHA 설정 정보 조회
    현재 CAPTCHA 설정을 반환합니다.
    """
    config = captcha_validator.config
    
    return {
        "enabled": config.enabled,
        "protection_level": config.protection_level.value,
        "recaptcha_enabled": bool(config.recaptcha_secret_key),
        "recaptcha_version": config.recaptcha_version,
        "recaptcha_site_key": config.recaptcha_site_key,  # 공개 키는 노출 가능
        "simple_checks_enabled": config.simple_checks_enabled,
        "protected_endpoints": {
            endpoint: level.value 
            for endpoint, level in config.protected_endpoints.items()
        },
        "math_problem_timeout": config.math_problem_timeout,
        "logic_check_timeout": config.logic_check_timeout,
        "max_failures_per_ip": config.max_failures_per_ip,
        "failure_window_minutes": config.failure_window_minutes,
        "lockout_duration_minutes": config.lockout_duration_minutes
    }


@router.get("/stats")
async def get_captcha_stats(request: Request) -> Dict[str, Any]:
    """
    CAPTCHA 통계 정보
    현재 활성 챌린지 및 실패 통계를 반환합니다.
    """
    client_id = captcha_validator.get_client_identifier(request)
    
    # 현재 활성 챌린지 수
    active_math_challenges = len(captcha_validator.math_challenges)
    active_logic_challenges = len(captcha_validator.logic_challenges)
    
    # 클라이언트별 실패 기록
    client_failures = len(captcha_validator.failure_tracker.get(client_id, []))
    is_locked_out = captcha_validator.is_locked_out(client_id)
    
    # 전체 통계
    total_locked_clients = len(captcha_validator.lockout_tracker)
    total_clients_with_failures = len(captcha_validator.failure_tracker)
    
    return {
        "timestamp": time.time(),
        "active_challenges": {
            "math_problems": active_math_challenges,
            "logic_problems": active_logic_challenges,
            "total": active_math_challenges + active_logic_challenges
        },
        "client_status": {
            "client_id": client_id,
            "failures_in_window": client_failures,
            "is_locked_out": is_locked_out,
            "lockout_until": captcha_validator.lockout_tracker.get(client_id, 0)
        },
        "global_stats": {
            "total_locked_clients": total_locked_clients,
            "clients_with_failures": total_clients_with_failures
        }
    }


@router.post("/test/math")
async def test_math_verification(
    request: Request,
    challenge_id: str,
    answer: int
) -> Dict[str, Any]:
    """
    수학 문제 검증 테스트
    """
    success, message = captcha_validator.verify_math_challenge(challenge_id, answer)
    
    return {
        "success": success,
        "message": message,
        "timestamp": time.time(),
        "challenge_id": challenge_id,
        "submitted_answer": answer
    }


@router.post("/test/logic")
async def test_logic_verification(
    request: Request,
    challenge_id: str,
    answer: str
) -> Dict[str, Any]:
    """
    로직 체크 검증 테스트
    """
    success, message = captcha_validator.verify_logic_challenge(challenge_id, answer)
    
    return {
        "success": success,
        "message": message,
        "timestamp": time.time(),
        "challenge_id": challenge_id,
        "submitted_answer": answer
    }


@router.get("/info")
async def captcha_info() -> Dict[str, Any]:
    """
    CAPTCHA 시스템 정보
    """
    return {
        "captcha_system": {
            "name": "글바구니 봇 방지 시스템",
            "version": "1.0.0",
            "description": "다중 레이어 봇 방지 및 CAPTCHA 시스템"
        },
        "protection_methods": {
            "recaptcha": {
                "description": "Google reCAPTCHA v2/v3",
                "purpose": "고급 봇 감지",
                "levels": ["MEDIUM", "HIGH", "PARANOID"]
            },
            "math_challenge": {
                "description": "간단한 산수 문제",
                "purpose": "기본적인 자동화 방지",
                "levels": ["LOW", "MEDIUM", "HIGH", "PARANOID"]
            },
            "logic_check": {
                "description": "상식 기반 질문",
                "purpose": "AI 봇 구별",
                "levels": ["MEDIUM", "HIGH", "PARANOID"]
            },
            "honeypot": {
                "description": "숨겨진 폼 필드",
                "purpose": "자동 양식 작성 감지",
                "levels": ["모든 레벨"]
            }
        },
        "protection_levels": {
            "DISABLED": "보호 비활성화",
            "LOW": "기본적인 체크만",
            "MEDIUM": "CAPTCHA + 로직 체크",
            "HIGH": "모든 검증 + 추가 보안",
            "PARANOID": "최대 보안"
        },
        "usage_instructions": {
            "step1": "GET /captcha/challenge/math 또는 /captcha/challenge/logic으로 문제 받기",
            "step2": "사용자가 문제 풀기",
            "step3": "POST /captcha/verify로 답 검증",
            "step4": "성공 시 실제 API 요청 진행"
        },
        "integration_examples": {
            "simple_check": {
                "description": "간단한 수학 문제만 사용",
                "suitable_for": ["회원가입", "댓글 작성"]
            },
            "recaptcha_integration": {
                "description": "Google reCAPTCHA 통합",
                "suitable_for": ["로그인", "결제", "민감한 작업"]
            },
            "multi_layer": {
                "description": "모든 방법 조합",
                "suitable_for": ["관리자 접근", "중요한 API"]
            }
        }
    }


@router.delete("/cleanup")
async def cleanup_expired_challenges() -> Dict[str, Any]:
    """
    만료된 챌린지 정리 (관리용)
    """
    try:
        before_math = len(captcha_validator.math_challenges)
        before_logic = len(captcha_validator.logic_challenges)
        
        captcha_validator.cleanup_expired_challenges()
        
        after_math = len(captcha_validator.math_challenges)
        after_logic = len(captcha_validator.logic_challenges)
        
        return {
            "message": "만료된 챌린지 정리 완료",
            "cleaned_up": {
                "math_challenges": before_math - after_math,
                "logic_challenges": before_logic - after_logic
            },
            "remaining": {
                "math_challenges": after_math,
                "logic_challenges": after_logic
            },
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"챌린지 정리 중 오류: {e}")
        raise HTTPException(status_code=500, detail="정리 작업에 실패했습니다")


@router.get("/honeypot/fields")
async def get_honeypot_fields() -> Dict[str, Any]:
    """
    허니팟 필드 정보
    프론트엔드에서 숨겨진 필드를 만들 때 사용할 필드명들을 제공합니다.
    """
    return {
        "honeypot_fields": captcha_validator.config.honeypot_fields,
        "instructions": {
            "usage": "이 필드들을 숨겨진 입력 필드로 추가하세요 (CSS로 display:none)",
            "warning": "사용자가 이 필드에 값을 입력하면 봇으로 판단됩니다",
            "example": "input type='text' name='website' style='display:none' tabindex='-1'"
        },
        "field_descriptions": {
            "website": "가짜 웹사이트 입력 필드",
            "url": "가짜 URL 입력 필드", 
            "homepage": "가짜 홈페이지 입력 필드"
        }
    } 