#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
입력 검증 유틸리티 모듈
사용자 입력 데이터의 검증과 정제를 담당
"""

import re
import html
from typing import List, Optional, Union
from urllib.parse import urlparse
from fastapi import HTTPException
from pydantic import HttpUrl

try:
    from ..security import validate_input
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

try:
    from ..utils.logging_config import get_logger
except ImportError:
    import logging
    get_logger = logging.getLogger

logger = get_logger("validator")


def validate_user_input(text: str, max_length: int = 5000) -> str:
    """사용자 입력 텍스트 검증 및 정화"""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="입력 텍스트가 비어있습니다.")
    
    text = text.strip()
    
    if len(text) > max_length:
        raise HTTPException(
            status_code=400, 
            detail=f"입력 텍스트가 너무 깁니다. (현재: {len(text)}자, 최대: {max_length}자)"
        )
    
    # XSS 방지
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'eval\s*\(',
        r'document\.',
        r'window\.',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise HTTPException(status_code=400, detail="허용되지 않는 문자패턴이 감지되었습니다.")
    
    if SECURITY_AVAILABLE:
        try:
            return validate_input(text, "text")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"보안 검증 실패: {str(e)}")
    
    return text


def validate_and_sanitize_text(text: str, max_length: int = 5000, min_length: int = 10) -> str:
    """텍스트 입력 검증 및 정제"""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="입력 텍스트가 비어있습니다.")
    
    text = html.unescape(text).strip()
    
    if len(text) > max_length:
        raise HTTPException(
            status_code=400, 
            detail=f"입력 텍스트가 너무 깁니다. (현재: {len(text)}자, 최대: {max_length}자)"
        )
    
    if len(text) < min_length:
        raise HTTPException(
            status_code=400,
            detail=f"입력 텍스트가 너무 짧습니다. (최소 {min_length}자 이상 필요)"
        )
    
    # 악성 패턴 검증
    malicious_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'on\w+\s*=',
    ]
    
    for pattern in malicious_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail="허용되지 않는 스크립트 패턴이 감지되었습니다."
            )
    
    return text


def validate_email(email: str) -> str:
    """이메일 주소 검증"""
    if not email or not email.strip():
        raise HTTPException(status_code=400, detail="이메일 주소가 비어있습니다.")
    
    email = email.strip().lower()
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise HTTPException(status_code=400, detail="올바르지 않은 이메일 형식입니다.")
    
    return email


def validate_url(url: Union[str, HttpUrl]) -> str:
    """URL 검증"""
    url_str = str(url)
    
    if not url_str or not url_str.strip():
        raise HTTPException(status_code=400, detail="URL이 비어있습니다.")
    
    url_str = url_str.strip()
    
    try:
        parsed = urlparse(url_str)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=400, detail="올바르지 않은 URL 형식입니다.")
        
        if parsed.scheme not in ['http', 'https']:
            raise HTTPException(status_code=400, detail="HTTP 또는 HTTPS URL만 허용됩니다.")
    except Exception:
        raise HTTPException(status_code=400, detail="URL 파싱 중 오류가 발생했습니다.")
    
    return url_str


def validate_urls(urls: List[Union[str, HttpUrl]], max_count: int = 20) -> List[str]:
    """여러 URL 일괄 검증"""
    if not urls:
        return []
    
    if len(urls) > max_count:
        raise HTTPException(
            status_code=400,
            detail=f"URL 개수가 너무 많습니다. (현재: {len(urls)}개, 최대: {max_count}개)"
        )
    
    validated_urls = []
    for i, url in enumerate(urls):
        try:
            validated_url = validate_url(url)
            validated_urls.append(validated_url)
        except HTTPException as e:
            raise HTTPException(
                status_code=400,
                detail=f"URL {i+1}번 검증 실패: {e.detail}"
            )
    
    return validated_urls


def validate_language(language: Optional[str]) -> str:
    """언어 코드 검증 및 정규화"""
    if not language:
        return "ko"
    
    language = language.lower().strip()
    lang_mapping = {"korean": "ko", "한국어": "ko", "english": "en", "영어": "en"}
    
    if language in lang_mapping:
        return lang_mapping[language]
    
    return "ko" if language not in ["ko", "en"] else language


def validate_positive_integer(value: Optional[int], default: int, max_value: int = 100) -> int:
    """양의 정수 검증"""
    if value is None or not isinstance(value, int) or value <= 0:
        return default
    
    return min(value, max_value)


def sanitize_filename(filename: str) -> str:
    """파일명 정제"""
    if not filename:
        return "untitled"
    
    # 위험한 문자 제거
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip('. ')
    
    return filename[:100] if filename else "untitled"


# 하위 호환성을 위한 별칭
sanitize_text = validate_and_sanitize_text