#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAI GPT API 서비스 모듈
OpenAI API 호출과 응답 처리를 전담
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union

import openai

try:
    from ..config.settings import get_settings
    from ..utils.logging_config import get_logger
except ImportError:
    try:
        from ..config import settings
        from ..utils.logging_config import get_logger
    except ImportError:
        import logging

        class MockSettings:
            OPENAI_API_KEY = ""
            OPENAI_MODEL = "gpt-3.5-turbo"

        settings = MockSettings()
        get_logger = logging.getLogger

logger = get_logger("gpt_service")


class GPTService:
    """OpenAI GPT API 호출을 담당하는 서비스 클래스"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        GPT 서비스 초기화

        Args:
            api_key: OpenAI API 키 (없으면 설정에서 가져옴)
            model: 사용할 모델명 (없으면 설정에서 가져옴)
        """
        try:
            self.api_key = api_key or get_settings().openai_api_key
            self.model = model or get_settings().openai_model
        except:
            self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", "")
            self.model = model or getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo")

        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = openai.OpenAI(api_key=self.api_key)

        # 기본 설정
        self.default_temperature = 0.5
        self.default_max_tokens = 400
        self.default_timeout = 30

        logger.info(f"GPT Service initialized with model: {self.model}")

    async def safe_gpt_call(
        self, prompt: str, language: str = "ko", max_retries: int = 3
    ) -> str:
        """
        안전한 GPT API 호출 (재시도 로직 포함)

        Args:
            prompt: GPT에게 전달할 프롬프트
            language: 응답 언어 ('ko' 또는 'en')
            max_retries: 최대 재시도 횟수

        Returns:
            GPT 응답 텍스트
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"🤖 GPT API 호출 시도 {attempt + 1}/{max_retries}")

                # 요약 생성
                result = await self.generate_summary(prompt, language)

                if result.get("success"):
                    summary = result.get("summary", "")
                    logger.info("✅ GPT API 호출 성공")
                    return summary
                else:
                    error = result.get("error", "Unknown error")
                    logger.warning(f"⚠️ GPT API 오류: {error}")

                    if attempt == max_retries - 1:
                        # 마지막 시도 실패 시 대안 반환
                        return self._generate_fallback_summary(prompt)

            except Exception as e:
                logger.error(f"❌ GPT API 호출 실패 (시도 {attempt + 1}): {str(e)}")

                if attempt == max_retries - 1:
                    logger.error("❌ 모든 GPT API 호출 시도 실패")
                    return "죄송합니다. 현재 AI 서비스에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요."

                # 재시도 전 대기 (지수 백오프)
                await asyncio.sleep(2**attempt)

        return "요약을 생성할 수 없습니다."

    def _generate_fallback_summary(self, text: str) -> str:
        """
        GPT API 실패 시 대안 요약 생성

        Args:
            text: 원본 텍스트

        Returns:
            간단한 요약 텍스트
        """
        try:
            # 간단한 문장 분할 요약
            sentences = text.split(".")[:3]
            if sentences:
                result = ". ".join(s.strip() for s in sentences if s.strip()) + "."
                logger.info("✅ 대안 요약 생성 완료")
                return result
            else:
                return text[:200] + "..." if len(text) > 200 else text
        except Exception:
            return "요약을 생성할 수 없습니다."

    async def generate_summary(
        self,
        text: str,
        language: str = "ko",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        텍스트 요약 생성

        Args:
            text: 요약할 텍스트
            language: 요약 언어 ('ko' 또는 'en')
            max_tokens: 최대 토큰 수
            temperature: 생성 온도
            custom_prompt: 커스텀 프롬프트

        Returns:
            요약 결과 딕셔너리
        """
        try:
            # 파라미터 설정
            max_tokens = max_tokens or self.default_max_tokens
            temperature = temperature or self.default_temperature

            # 메시지 구성
            messages = self._build_summary_messages(text, language, custom_prompt)

            logger.info(
                f"Generating summary - Language: {language}, Length: {len(text)} chars"
            )

            # API 호출
            start_time = time.time()
            response = await self._call_openai_api(
                messages=messages, max_tokens=max_tokens, temperature=temperature
            )
            call_duration = time.time() - start_time

            # 응답 처리
            if not response.choices or not response.choices[0].message.content:
                return {
                    "success": False,
                    "error": "OpenAI API returned no content",
                    "duration": call_duration,
                }

            summary = response.choices[0].message.content.strip()

            result = {
                "success": True,
                "summary": summary,
                "language": language,
                "model": self.model,
                "input_length": len(text),
                "output_length": len(summary),
                "duration": call_duration,
                "tokens_used": response.usage.total_tokens if response.usage else None,
            }

            logger.info(f"Summary generated successfully in {call_duration:.2f}s")
            return result

        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                "success": False,
                "error": f"OpenAI API error: {str(e)}",
                "error_type": "openai_error",
            }
        except Exception as e:
            logger.error(f"Unexpected error in summary generation: {e}")
            return {
                "success": False,
                "error": f"Summary generation failed: {str(e)}",
                "error_type": "general_error",
            }

    def _build_summary_messages(
        self, text: str, language: str, custom_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """요약을 위한 메시지 구성"""

        if custom_prompt:
            system_message = custom_prompt
        else:
            if language == "ko":
                system_message = """당신은 전문적인 텍스트 요약 어시스턴트입니다. 
주어진 텍스트를 명확하고 간결하게 한국어로 요약해주세요.
- 핵심 내용을 놓치지 않도록 주의하세요
- 3-5문장으로 요약하세요  
- 객관적이고 정확한 정보만 포함하세요"""
            else:
                system_message = """You are a professional text summarization assistant.
Please summarize the given text clearly and concisely in English.
- Make sure not to miss key content
- Summarize in 3-5 sentences
- Include only objective and accurate information"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"다음 텍스트를 요약해주세요:\n\n{text}"},
        ]

        return messages

    async def _call_openai_api(
        self, messages: List[Dict[str, str]], max_tokens: int, temperature: float
    ) -> Any:
        """OpenAI API 비동기 호출"""

        def sync_call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.default_timeout,
            )

        return await asyncio.to_thread(sync_call)


# 전역 GPT 서비스 인스턴스 관리
_gpt_service_instance: Optional[GPTService] = None


def get_gpt_service() -> GPTService:
    """전역 GPT 서비스 인스턴스 반환"""
    global _gpt_service_instance
    if _gpt_service_instance is None:
        _gpt_service_instance = GPTService()
    return _gpt_service_instance


async def safe_gpt_call(prompt: str, language: str = "ko", max_retries: int = 3) -> str:
    """
    전역 safe_gpt_call 함수 (하위 호환성 유지)

    Args:
        prompt: GPT에게 전달할 프롬프트
        language: 응답 언어
        max_retries: 최대 재시도 횟수

    Returns:
        GPT 응답 텍스트
    """
    try:
        gpt_service = get_gpt_service()
        return await gpt_service.safe_gpt_call(prompt, language, max_retries)
    except Exception as e:
        logger.error(f"Global safe_gpt_call failed: {e}")
        return "요약을 생성할 수 없습니다."
