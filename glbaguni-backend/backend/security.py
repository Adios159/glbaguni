#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보안 유틸리티 모듈
사용자 입력 검증, Prompt Injection 방지, 데이터 sanitization
"""

import re
import logging
from typing import Optional, List, Dict, Any
from html import escape
import unicodedata

logger = logging.getLogger(__name__)

class SecurityValidator:
    """보안 검증 및 입력 정화 클래스"""
    
    # 위험한 패턴들 (Prompt Injection 방지)
    DANGEROUS_PATTERNS = [
        # 시스템 명령어 시도
        r'(?i)(ignore|forget|override)\s+(previous|above|prior|earlier)\s+(instruction|prompt|rule)',
        r'(?i)(you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay)',
        r'(?i)(system\s*:|assistant\s*:|user\s*:)',
        r'(?i)(execute|run|eval|compile)\s*[\(\[]',
        
        # 스크립트 삽입 시도
        r'<script[^>]*>.*?</script>',
        r'javascript\s*:',
        r'vbscript\s*:',
        r'on\w+\s*=',
        
        # SQL Injection 시도
        r'(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)',
        r'[\'"]\s*;\s*--',
        r'[\'"]\s*or\s+[\'"]\d+[\'"]\s*=\s*[\'"]\d+[\'"]',
        
        # 특수 명령어 시도
        r'(?i)(\\n\\n|\\r\\n)+(system|user|assistant):\s*',
        r'(?i)###\s*(instruction|system|prompt)',
        r'(?i)\[system\]|\[user\]|\[assistant\]',
        
        # 인코딩 우회 시도
        r'%[0-9a-fA-F]{2}',  # URL 인코딩
        r'\\u[0-9a-fA-F]{4}',  # Unicode 이스케이프
    ]
    
    # 허용되지 않는 특수문자
    FORBIDDEN_CHARS = ['<', '>', '"', "'", ';', '`', '\\', '\x00', '\x01', '\x02']
    
    # 최대 입력 길이
    MAX_INPUT_LENGTH = 500
    MAX_QUERY_LENGTH = 200
    
    @classmethod
    def validate_user_input(cls, text: str, input_type: str = "general") -> str:
        """
        사용자 입력을 검증하고 안전하게 정화합니다.
        
        Args:
            text: 사용자 입력 텍스트
            input_type: 입력 타입 ("query", "prompt", "general")
            
        Returns:
            str: 정화된 안전한 텍스트
            
        Raises:
            ValueError: 위험한 입력이 감지된 경우
        """
        if not text or not isinstance(text, str):
            raise ValueError("입력 텍스트가 비어있거나 유효하지 않습니다.")
        
        original_length = len(text)
        
        # 1. 길이 제한 검사
        max_length = cls.MAX_QUERY_LENGTH if input_type == "query" else cls.MAX_INPUT_LENGTH
        if len(text) > max_length:
            logger.warning(f"입력 길이 초과: {len(text)} > {max_length}")
            text = text[:max_length]
        
        # 2. Unicode 정규화
        text = unicodedata.normalize('NFKC', text)
        
        # 3. 위험한 패턴 검사
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                logger.error(f"위험한 패턴 감지: {pattern}")
                raise ValueError("입력에 허용되지 않는 내용이 포함되어 있습니다.")
        
        # 4. 금지된 문자 제거
        for char in cls.FORBIDDEN_CHARS:
            if char in text:
                logger.warning(f"금지된 문자 제거: {char}")
                text = text.replace(char, '')
        
        # 5. HTML 이스케이핑
        text = escape(text)
        
        # 6. 연속된 특수문자 정리
        text = re.sub(r'[^\w\s가-힣.,!?()-]{2,}', '', text)
        
        # 7. 과도한 공백 정리
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 8. 최종 검증
        if not text:
            raise ValueError("입력 정화 후 유효한 내용이 남지 않았습니다.")
        
        if len(text) != original_length:
            logger.info(f"입력 정화 완료: {original_length} -> {len(text)} 문자")
        
        return text
    
    @classmethod
    def create_safe_prompt(cls, user_input: str, system_message: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        안전한 OpenAI 프롬프트 구조를 생성합니다.
        
        Args:
            user_input: 정화된 사용자 입력
            system_message: 시스템 메시지
            context: 추가 컨텍스트 (선택사항)
            
        Returns:
            Dict: OpenAI API 호출용 메시지 구조
        """
        # 사용자 입력 재검증
        safe_input = cls.validate_user_input(user_input, "query")
        
        messages = [
            {
                "role": "system",
                "content": system_message
            }
        ]
        
        # 컨텍스트가 있는 경우 추가
        if context:
            safe_context = cls.validate_user_input(context, "general")
            messages.append({
                "role": "system", 
                "content": f"참고 정보: {safe_context}"
            })
        
        # 사용자 입력을 별도 메시지로 분리
        messages.append({
            "role": "user",
            "content": safe_input
        })
        
        return {
            "messages": messages,
            "temperature": 0.3,  # 일관된 응답을 위해 낮은 온도 설정
            "max_tokens": 500,   # 토큰 제한으로 과도한 응답 방지
        }
    
    @classmethod
    def validate_api_key(cls, api_key: str) -> bool:
        """
        OpenAI API 키 형식을 검증합니다.
        
        Args:
            api_key: API 키 문자열
            
        Returns:
            bool: 유효한 형식인지 여부
        """
        if not api_key or not isinstance(api_key, str):
            return False
        
        # OpenAI API 키 형식: sk-... (최소 20자)
        if not api_key.startswith('sk-') or len(api_key) < 20:
            return False
        
        # 허용된 문자만 포함하는지 확인
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')
        if not all(c in allowed_chars for c in api_key):
            return False
        
        return True
    
    @classmethod
    def sanitize_response_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        API 응답 데이터에서 민감한 정보를 제거합니다.
        
        Args:
            data: 응답 데이터 딕셔너리
            
        Returns:
            Dict: 정화된 응답 데이터
        """
        sensitive_keys = [
            'api_key', 'apikey', 'key', 'token', 'password', 'secret',
            'openai_api_key', 'smtp_password', 'smtp_username'
        ]
        
        def recursive_sanitize(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {
                    k: recursive_sanitize(v) if k.lower() not in sensitive_keys 
                    else "***REDACTED***" 
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [recursive_sanitize(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith('sk-'):
                return "***REDACTED***"
            else:
                return obj
        
        result = recursive_sanitize(data)
        return result if isinstance(result, dict) else {}

# 보안 검증 인스턴스 (싱글톤 패턴)
security_validator = SecurityValidator()

# 편의 함수들
def validate_input(text: str, input_type: str = "general") -> str:
    """사용자 입력 검증 편의 함수"""
    return security_validator.validate_user_input(text, input_type)

def create_safe_prompt(user_input: str, system_message: str, context: Optional[str] = None) -> Dict[str, Any]:
    """안전한 프롬프트 생성 편의 함수"""
    return security_validator.create_safe_prompt(user_input, system_message, context)

def validate_api_key(api_key: str) -> bool:
    """API 키 검증 편의 함수"""
    return security_validator.validate_api_key(api_key)

def sanitize_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """응답 데이터 정화 편의 함수"""
    return security_validator.sanitize_response_data(data)
