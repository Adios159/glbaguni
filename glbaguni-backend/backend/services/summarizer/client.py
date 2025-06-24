#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarizer Client Module
OpenAI API 클라이언트 관리
"""

import logging
import time
from typing import Any, Dict, List, Optional

import openai

try:
    from backend.config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)


class SummarizerClient:
    """OpenAI API 클라이언트 관리 클래스"""

    def __init__(self):
        """클라이언트 초기화"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required")

        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo")
        self.request_count = 0
        self.total_tokens = 0

        logger.info(f"SummarizerClient 초기화 완료 - 모델: {self.model}")

    def call_openai_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 400,
        temperature: float = 0.3,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        """
        OpenAI API를 호출하여 요약을 생성합니다.

        Args:
            messages: OpenAI API 메시지 리스트
            max_tokens: 최대 토큰 수
            temperature: 창의성 수준
            timeout: 타임아웃 (초)

        Returns:
            API 응답 결과 딕셔너리
        """
        try:
            self.request_count += 1
            start_time = time.time()

            logger.info(f"🤖 OpenAI API 호출 시작 (요청 #{self.request_count})")
            logger.debug(
                f"모델: {self.model}, 최대토큰: {max_tokens}, 온도: {temperature}"
            )

            # API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )

            # 응답 시간 계산
            elapsed_time = time.time() - start_time

            # 응답 검증
            if not response.choices:
                logger.error("OpenAI API returned no choices")
                return {"error": "OpenAI API returned no choices"}

            # 내용 추출
            summary_text = response.choices[0].message.content
            if summary_text is None:
                logger.error("OpenAI API returned None content")
                return {"error": "OpenAI API returned None content"}

            summary_text = summary_text.strip()

            if not summary_text:
                logger.error("OpenAI API returned empty content")
                return {"error": "OpenAI API returned empty content"}

            # 사용량 추적
            if hasattr(response, "usage") and response.usage:
                tokens_used = response.usage.total_tokens
                self.total_tokens += tokens_used
            else:
                tokens_used = 0

            logger.info(
                f"✅ OpenAI API 호출 성공 - "
                f"시간: {elapsed_time:.2f}초, 토큰: {tokens_used}, "
                f"응답길이: {len(summary_text)}자"
            )

            return {
                "summary": summary_text,
                "model": self.model,
                "tokens_used": tokens_used,
                "response_time": elapsed_time,
                "success": True,
            }

        except openai.OpenAIError as e:
            logger.error(f"OpenAI API 오류: {e}")
            return {"error": f"OpenAI API 오류: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"요약 처리 중 예상치 못한 오류: {e}")
            return {"error": f"요약 처리 실패: {str(e)}", "success": False}

    def summarize_text(
        self,
        text: str,
        language: str = "ko",
        custom_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        텍스트를 요약합니다.

        Args:
            text: 요약할 텍스트
            language: 언어 설정
            custom_params: 사용자 정의 매개변수

        Returns:
            요약 결과 딕셔너리
        """
        if not text:
            return {"error": "Missing input text for summarization.", "success": False}

        # 기본 매개변수 설정
        params = {"max_tokens": 400, "temperature": 0.3, "timeout": 30}

        # 사용자 정의 매개변수 적용
        if custom_params:
            params.update(custom_params)

        # 프롬프트 생성 (외부 모듈에서 가져오기)
        from .prompts import SummarizerPrompts

        messages = SummarizerPrompts.build_summary_prompt(text, language)

        # API 호출
        result = self.call_openai_api(messages, **params)

        # 결과에 추가 정보 포함
        if result.get("success"):
            result.update(
                {
                    "language": language,
                    "input_length": len(text),
                    "output_length": len(result.get("summary", "")),
                }
            )

        return result

    def test_connection(self) -> Dict[str, Any]:
        """
        OpenAI API 연결을 테스트합니다.

        Returns:
            연결 테스트 결과
        """
        try:
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello in one word."},
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=test_messages,
                max_tokens=10,
                temperature=0.1,
                timeout=10,
            )

            if response.choices and response.choices[0].message.content:
                logger.info("✅ OpenAI API 연결 테스트 성공")
                return {
                    "success": True,
                    "message": "OpenAI API 연결 정상",
                    "model": self.model,
                }
            else:
                logger.warning("⚠️ OpenAI API 연결 테스트 - 응답 없음")
                return {"success": False, "message": "OpenAI API 응답 없음"}

        except Exception as e:
            logger.error(f"❌ OpenAI API 연결 테스트 실패: {e}")
            return {"success": False, "message": f"OpenAI API 연결 실패: {str(e)}"}

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        사용량 통계를 반환합니다.

        Returns:
            사용량 통계 딕셔너리
        """
        return {
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "average_tokens_per_request": (
                self.total_tokens / self.request_count if self.request_count > 0 else 0
            ),
        }

    def reset_stats(self):
        """사용량 통계를 초기화합니다."""
        self.request_count = 0
        self.total_tokens = 0
        logger.info("📊 사용량 통계 초기화 완료")
