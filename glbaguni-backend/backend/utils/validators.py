#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
입력 데이터 검증 및 정화 유틸리티
"""

import logging
import re
from fastapi import HTTPException


class InputSanitizer:
    """입력 데이터 검증 및 정화"""

    # 위험한 패턴들
    DANGEROUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript\s*:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"<object[^>]*>.*?</object>",
        r"<embed[^>]*>.*?</embed>",
    ]

    @classmethod
    def sanitize_text(
        cls, text: str, max_length: int = 1000, field_name: str = "텍스트"
    ) -> str:
        """텍스트 입력 정화 및 검증"""
        try:
            # 기본 검증
            if not text or not isinstance(text, str):
                raise HTTPException(400, f"{field_name}가 비어있습니다")

            # 앞뒤 공백 제거
            text = text.strip()
            if not text:
                raise HTTPException(400, f"{field_name}가 비어있습니다")

            # 길이 제한
            if len(text) > max_length:
                raise HTTPException(
                    400, f"{field_name}가 너무 깁니다 (최대 {max_length}자)"
                )

            # 위험한 패턴 검사
            for pattern in cls.DANGEROUS_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                    raise HTTPException(
                        400, f"{field_name}에 허용되지 않는 패턴이 감지되었습니다"
                    )

            return text

        except HTTPException:
            raise
        except Exception as e:
            logger = logging.getLogger("glbaguni")
            logger.error(f"입력 정화 중 오류: {e}")
            raise HTTPException(500, "입력 검증 중 내부 오류가 발생했습니다")

    @classmethod
    def validate_email(cls, email: str) -> bool:
        """이메일 형식 검증"""
        if not email:
            return False

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(email_pattern, email)) 