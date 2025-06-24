#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT Client
OpenAI API 클라이언트 관리
"""

import asyncio
import time
from typing import Optional

from openai import AsyncOpenAI

try:
    from ..config import get_settings
    from ..utils import get_logger
    from ..utils.exception_handler import ExternalServiceError
except ImportError:
    from config import get_settings
    from utils import get_logger
    from utils.exception_handler import ExternalServiceError

logger = get_logger("services.gpt_client")


class GPTClient:
    """OpenAI GPT API 클라이언트"""

    def __init__(self):
        """GPT 클라이언트 초기화"""
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self._request_count = 0
        self._total_tokens = 0

        logger.info(
            f"✅ GPT 클라이언트 초기화 완료 - 모델: {self.settings.openai_model}"
        )

    async def call_gpt(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> str:
        """
        GPT API 호출

        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 창의성 수준
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 간격

        Returns:
            GPT 응답 텍스트
        """

        for attempt in range(max_retries):
            try:
                self._request_count += 1
                start_time = time.time()

                logger.debug(f"🔄 GPT API 호출 시도 {attempt + 1}/{max_retries}")

                response = await self.client.chat.completions.create(
                    model=self.settings.openai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=30.0,
                )

                # 응답 처리
                content = response.choices[0].message.content
                if not content:
                    raise ExternalServiceError("OpenAI", "빈 응답을 받았습니다")

                # 사용량 추적
                if hasattr(response, "usage") and response.usage:
                    self._total_tokens += response.usage.total_tokens
                    tokens_used = response.usage.total_tokens
                else:
                    tokens_used = 0

                elapsed_time = time.time() - start_time

                logger.info(
                    f"✅ GPT API 호출 성공 - "
                    f"토큰: {tokens_used}, 시간: {elapsed_time:.2f}초"
                )

                return content.strip()

            except Exception as e:
                logger.warning(f"⚠️ GPT API 호출 실패 (시도 {attempt + 1}): {str(e)}")

                if attempt == max_retries - 1:
                    logger.error(f"❌ GPT API 호출 최종 실패: {str(e)}")
                    raise ExternalServiceError("OpenAI", f"API 호출 실패: {str(e)}")

                # 재시도 전 대기
                await asyncio.sleep(retry_delay * (attempt + 1))

    async def test_connection(self) -> bool:
        """GPT API 연결 테스트"""
        try:
            test_prompt = "테스트 메시지입니다. '연결 성공'이라고 답변해주세요."
            response = await self.call_gpt(test_prompt, max_tokens=50)

            if "연결 성공" in response or "success" in response.lower():
                logger.info("✅ GPT API 연결 테스트 성공")
                return True
            else:
                logger.warning(
                    f"⚠️ GPT API 연결 테스트 실패: 예상과 다른 응답 - {response}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ GPT API 연결 테스트 실패: {str(e)}")
            return False

    def get_usage_stats(self) -> dict:
        """사용량 통계 반환"""
        return {
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
            "model": self.settings.openai_model,
        }

    def reset_stats(self):
        """통계 초기화"""
        self._request_count = 0
        self._total_tokens = 0
        logger.info("📊 GPT 클라이언트 통계 초기화됨")
