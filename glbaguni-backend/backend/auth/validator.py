#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auth Validator Module
사용자 입력 검증 및 보안 유틸리티 (200줄 이하)
"""

import logging
import re
import unicodedata
from html import escape
from typing import List, Optional

logger = logging.getLogger(__name__)


class AuthValidator:
    """인증 및 보안 검증 클래스"""

    # 위험한 패턴들 (Prompt Injection 방지)
    DANGEROUS_PATTERNS = [
        r"(?i)(ignore|forget|override)\s+(previous|above|prior|earlier)\s+(instruction|prompt|rule)",
        r"(?i)(you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay)",
        r"(?i)(system\s*:|assistant\s*:|user\s*:)",
        r"(?i)(execute|run|eval|compile)\s*[\(\[]",
        r"<script[^>]*>.*?</script>",
        r"javascript\s*:",
        r"vbscript\s*:",
        r"on\w+\s*=",
        r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)",
        r'[\'"]\s*;\s*--',
        r'[\'"]\s*or\s+[\'"]\d+[\'"]\s*=\s*[\'"]\d+[\'"]',
    ]

    # 허용되지 않는 특수문자
    FORBIDDEN_CHARS = ["<", ">", '"', "'", ";", "`", "\\", "\x00", "\x01", "\x02"]

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
        max_length = (
            cls.MAX_QUERY_LENGTH if input_type == "query" else cls.MAX_INPUT_LENGTH
        )
        if len(text) > max_length:
            logger.warning(f"입력 길이 초과: {len(text)} > {max_length}")
            text = text[:max_length]

        # 2. Unicode 정규화
        text = unicodedata.normalize("NFKC", text)

        # 3. 위험한 패턴 검사
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                logger.error(f"위험한 패턴 감지: {pattern}")
                raise ValueError("입력에 허용되지 않는 내용이 포함되어 있습니다.")

        # 4. 금지된 문자 제거
        for char in cls.FORBIDDEN_CHARS:
            if char in text:
                logger.warning(f"금지된 문자 제거: {char}")
                text = text.replace(char, "")

        # 5. HTML 이스케이핑
        text = escape(text)

        # 6. 연속된 특수문자 정리
        text = re.sub(r"[^\w\s가-힣.,!?()-]{2,}", "", text)

        # 7. 과도한 공백 정리
        text = re.sub(r"\s+", " ", text).strip()

        # 8. 최종 검증
        if not text:
            raise ValueError("입력 정화 후 유효한 내용이 남지 않았습니다.")

        if len(text) != original_length:
            logger.info(f"입력 정화 완료: {original_length} -> {len(text)} 문자")

        return text

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
        if not api_key.startswith("sk-") or len(api_key) < 20:
            return False

        # 허용된 문자만 포함하는지 확인
        allowed_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        )
        if not all(c in allowed_chars for c in api_key):
            return False

        return True


# 하위 호환성을 위한 래퍼 함수들
def validate_input(text: str, input_type: str = "general") -> str:
    """하위 호환성을 위한 래퍼 함수"""
    return AuthValidator.validate_user_input(text, input_type)


def validate_api_key(api_key: str) -> bool:
    """하위 호환성을 위한 래퍼 함수"""
    return AuthValidator.validate_api_key(api_key)
