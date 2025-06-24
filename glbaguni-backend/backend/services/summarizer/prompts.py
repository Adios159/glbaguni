#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summarizer Prompts Module
요약 프롬프트 생성 및 관리 (200줄 이하)
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SummarizerPrompts:
    """요약 프롬프트 생성 및 관리 클래스"""

    # 언어별 시스템 메시지 템플릿
    SYSTEM_MESSAGES = {
        "ko": """너는 훌륭한 요약가야. 사용자가 제공한 긴 글을 명확하고 간결하게 한국어로 요약해줘. 
        핵심 내용을 중심으로 3-4문장으로 간결하게 요약하고, 중요한 사실과 정보에 집중하며, 
        불필요한 수사나 감정적 표현은 제외해줘. 요약 결과는 반드시 한국어로 작성해줘.""",
        "en": """You are a helpful assistant that summarizes long texts into concise English summaries. 
        Focus on key facts and important information, providing a clear and objective summary in 3-4 sentences.""",
    }

    @classmethod
    def build_summary_prompt(
        cls, text: str, language: str = "ko"
    ) -> List[Dict[str, str]]:
        """
        요약을 위한 프롬프트 메시지를 구성합니다.

        Args:
            text: 요약할 텍스트
            language: 언어 설정 ('ko' 또는 'en')

        Returns:
            OpenAI API용 메시지 리스트
        """
        # 기본 시스템 메시지 가져오기
        system_message = cls.SYSTEM_MESSAGES.get(language, cls.SYSTEM_MESSAGES["ko"])

        # 메시지 구성
        messages = [{"role": "system", "content": system_message}]

        # 사용자 콘텐츠 구성
        if language == "ko":
            user_content = f"아래 텍스트를 한국어로 간결하게 요약해줘:\n\n{text}"
        else:
            user_content = f"Please summarize the following text:\n\n{text}"

        messages.append({"role": "user", "content": user_content})

        logger.debug(f"프롬프트 생성 완료: 언어={language}")
        return messages

    @classmethod
    def build_article_prompt(
        cls, title: str, content: str, language: str = "ko", max_length: int = 8000
    ) -> List[Dict[str, str]]:
        """
        기사 요약을 위한 특화된 프롬프트를 구성합니다.

        Args:
            title: 기사 제목
            content: 기사 내용
            language: 언어 설정
            max_length: 최대 콘텐츠 길이

        Returns:
            OpenAI API용 메시지 리스트
        """
        # 콘텐츠 길이 제한
        if len(content) > max_length:
            content = content[:max_length] + "..."
            logger.info(f"콘텐츠 길이 제한 적용: {max_length}자로 단축")

        # 기사 형태로 텍스트 구성
        article_text = f"제목: {title}\n\n내용: {content}"

        # 기사 전용 시스템 메시지
        if language == "ko":
            system_message = """너는 뉴스 기사 요약 전문가야. 
            제공된 뉴스 기사를 핵심 내용 중심으로 3-4문장으로 간결하게 한국어로 요약해줘.
            중요한 사실, 인물, 날짜, 장소 등을 포함하되 불필요한 세부사항은 제외해줘."""

            user_content = f"다음 뉴스 기사를 한국어로 요약해줘:\n\n{article_text}"
        else:
            system_message = """You are a news article summarization expert. 
            Summarize the provided news article into 3-4 concise sentences focusing on key facts, 
            important people, dates, and locations while excluding unnecessary details."""

            user_content = f"Please summarize this news article:\n\n{article_text}"

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content},
        ]

    @classmethod
    def get_system_message(cls, language: str = "ko") -> str:
        """
        언어에 따른 시스템 메시지를 반환합니다.

        Args:
            language: 대상 언어

        Returns:
            적절한 시스템 메시지
        """
        return cls.SYSTEM_MESSAGES.get(language, cls.SYSTEM_MESSAGES["ko"])

    @classmethod
    def validate_prompt_input(cls, text: str) -> bool:
        """
        프롬프트 입력값의 유효성을 검사합니다.

        Args:
            text: 검사할 텍스트

        Returns:
            유효성 검사 결과
        """
        if not text or not isinstance(text, str):
            return False

        # 최소 길이 검사
        if len(text.strip()) < 10:
            logger.warning("텍스트가 너무 짧습니다")
            return False

        # 최대 길이 검사 (OpenAI 토큰 제한 고려)
        if len(text) > 10000:
            logger.warning("텍스트가 너무 깁니다")
            return False

        return True


# 하위 호환성을 위한 래퍼 함수
def build_summary_prompt(text: str, language: str = "ko") -> List[Dict[str, str]]:
    """
    하위 호환성을 위한 래퍼 함수

    Args:
        text: 요약할 텍스트
        language: 언어 설정

    Returns:
        OpenAI API용 메시지 리스트
    """
    return SummarizerPrompts.build_summary_prompt(text, language)
