#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
환경변수 검증 모듈
서버 시작시 필요한 환경변수들을 검증
"""

import os
import sys
import logging

logger = logging.getLogger("glbaguni.environment")


def validate_environment_comprehensive() -> bool:
    """포괄적인 환경변수 검증"""
    logger.info("🔍 환경변수 검증 시작...")
    
    required_vars = {
        'OPENAI_API_KEY': '필수 - OpenAI API 키',
        'SMTP_USERNAME': '선택 - 이메일 발송용',
        'SMTP_PASSWORD': '선택 - 이메일 발송용'
    }
    
    missing_required = []
    missing_optional = []
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value:
            if var_name == 'OPENAI_API_KEY':
                missing_required.append(f"{var_name} ({description})")
            else:
                missing_optional.append(f"{var_name} ({description})")
        else:
            logger.info(f"✅ {var_name}: 설정됨")
    
    if missing_required:
        logger.error("❌ 필수 환경변수 누락:")
        for var in missing_required:
            logger.error(f"   - {var}")
        logger.error("서버를 종료합니다. .env 파일을 확인해주세요.")
        return False
    
    if missing_optional:
        logger.warning("⚠️ 선택적 환경변수 누락 (일부 기능 제한):")
        for var in missing_optional:
            logger.warning(f"   - {var}")
    
    # OpenAI API 키 형식 검증
    api_key = os.getenv('OPENAI_API_KEY', '')
    if not api_key.startswith('sk-'):
        logger.error("❌ OpenAI API 키 형식이 올바르지 않습니다.")
        return False
    
    logger.info("✅ 환경변수 검증 완료")
    return True 