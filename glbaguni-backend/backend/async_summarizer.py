#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
비동기 요약 모듈 v3.0.0
완전한 async/await 패턴으로 리팩토링
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import openai
from openai.types.chat import ChatCompletionMessageParam

try:
    from .config import settings
    from .models import Article, ArticleSummary
except ImportError:
    from config import settings
    from models import Article, ArticleSummary

logger = logging.getLogger("glbaguni.summarizer")


class AsyncArticleSummarizer:
    """완전 비동기 기사 요약기"""

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API 키가 필요합니다")

        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = getattr(settings, "OPENAI_MODEL", "gpt-3.5-turbo")
        self.max_retries = 3
        self.base_delay = 1.0

    async def summarize(
        self, text: str, language: str = "ko", max_retries: int = None
    ) -> Dict[str, Any]:
        """텍스트 요약 (완전 비동기, 재시도 로직 포함)"""
        req_id = str(uuid.uuid4())[:8]
        retries = max_retries if max_retries is not None else self.max_retries

        logger.info(f"📝 [{req_id}] 요약 시작 - 언어: {language}, 길이: {len(text)}자")

        if not text or not text.strip():
            return {"error": "입력 텍스트가 비어있습니다"}

        # 텍스트 길이 제한
        max_length = 8000
        if len(text) > max_length:
            text = text[:max_length] + "..."
            logger.info(f"📏 [{req_id}] 텍스트 길이 제한 적용: {max_length}자")

        for attempt in range(retries):
            try:
                logger.info(f"🔄 [{req_id}] 요약 시도 {attempt + 1}/{retries}")

                # 언어별 메시지 구성
                messages = self._build_messages(text, language)

                # OpenAI API 호출 (비동기)
                start_time = time.time()
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=400,
                    temperature=0.3,
                    timeout=30.0,
                )

                elapsed = time.time() - start_time

                # 응답 처리
                if not response.choices or not response.choices[0].message.content:
                    raise Exception("OpenAI API에서 빈 응답을 반환했습니다")

                summary_text = response.choices[0].message.content.strip()

                logger.info(f"✅ [{req_id}] 요약 완료 ({elapsed:.2f}초)")

                return {
                    "summary": summary_text,
                    "language": language,
                    "model": self.model,
                    "input_length": len(text),
                    "output_length": len(summary_text),
                    "processing_time": elapsed,
                    "attempt": attempt + 1,
                }

            except openai.RateLimitError as e:
                wait_time = self.base_delay * (2**attempt)
                logger.warning(
                    f"⏳ [{req_id}] Rate limit 도달, {wait_time}초 대기 후 재시도"
                )
                if attempt < retries - 1:
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    return {"error": f"Rate limit 초과: {str(e)}"}

            except openai.APITimeoutError as e:
                logger.warning(f"⏰ [{req_id}] API 타임아웃 (시도 {attempt + 1})")
                if attempt < retries - 1:
                    await asyncio.sleep(self.base_delay * (attempt + 1))
                    continue
                else:
                    return {"error": f"API 타임아웃: {str(e)}"}

            except openai.OpenAIError as e:
                logger.error(f"❌ [{req_id}] OpenAI API 오류: {str(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(self.base_delay * (attempt + 1))
                    continue
                else:
                    return {"error": f"OpenAI API 오류: {str(e)}"}

            except Exception as e:
                logger.error(f"💥 [{req_id}] 예상치 못한 오류: {str(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(self.base_delay * (attempt + 1))
                    continue
                else:
                    return {"error": f"요약 실패: {str(e)}"}

        return {"error": "모든 재시도 실패"}

    def _build_messages(
        self, text: str, language: str
    ) -> List[ChatCompletionMessageParam]:
        """언어별 메시지 구성"""
        if language == "ko":
            system_message = (
                "너는 뉴스 기사를 요약하는 전문가야. "
                "다음 규칙에 따라 한국어로 요약해줘:\n"
                "1. 핵심 사실과 중요한 정보만 포함\n"
                "2. 3-4문장으로 간결하게 작성\n"
                "3. 객관적이고 중립적인 톤 유지\n"
                "4. 불필요한 수사나 감정적 표현 제외\n"
                "5. 반드시 한국어로만 응답"
            )
            user_message = f"다음 기사를 한국어로 요약해줘:\n\n{text}"
        else:
            system_message = (
                "You are a professional news summarizer. "
                "Summarize the following article according to these rules:\n"
                "1. Include only key facts and important information\n"
                "2. Write concisely in 3-4 sentences\n"
                "3. Maintain objective and neutral tone\n"
                "4. Exclude unnecessary rhetoric or emotional expressions\n"
                "5. Respond only in English"
            )
            user_message = f"Summarize the following article in English:\n\n{text}"

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

    async def summarize_article(
        self,
        article: Article,
        language: str = "ko",
        custom_prompt: Optional[str] = None,
    ) -> Optional[ArticleSummary]:
        """단일 기사 요약 (비동기)"""
        req_id = str(uuid.uuid4())[:8]

        try:
            logger.info(f"📰 [{req_id}] 기사 요약: {article.title[:50]}...")

            # 요약할 텍스트 구성
            content_to_summarize = f"제목: {article.title}\n\n내용: {article.content}"

            # 커스텀 프롬프트 적용
            if custom_prompt:
                content_to_summarize = f"{custom_prompt}\n\n{content_to_summarize}"

            # 요약 실행
            result = await self.summarize(content_to_summarize, language)

            if "error" in result:
                logger.error(f"❌ [{req_id}] 기사 요약 실패: {result['error']}")
                return None

            # ArticleSummary 객체 생성
            summary = ArticleSummary(
                title=article.title,
                url=str(article.url),
                summary=result["summary"],
                source=getattr(article, "source", "unknown"),
                original_length=len(article.content),
                summary_length=result["output_length"],
            )

            logger.info(f"✅ [{req_id}] 기사 요약 완료")
            return summary

        except Exception as e:
            logger.error(f"💥 [{req_id}] 기사 요약 처리 실패: {str(e)}")
            return None

    async def summarize_articles(
        self,
        articles: List[Article],
        language: str = "ko",
        custom_prompt: Optional[str] = None,
        max_concurrent: int = 3,
    ) -> List[ArticleSummary]:
        """여러 기사 동시 요약 (병렬 처리)"""
        req_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        logger.info(f"📚 [{req_id}] 다중 기사 요약 시작: {len(articles)}개")

        if not articles:
            return []

        # 세마포어로 동시 요청 수 제한
        semaphore = asyncio.Semaphore(max_concurrent)

        async def summarize_with_semaphore(
            article: Article,
        ) -> Optional[ArticleSummary]:
            async with semaphore:
                return await self.summarize_article(article, language, custom_prompt)

        # 모든 기사를 병렬로 처리
        tasks = [summarize_with_semaphore(article) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 성공한 결과만 수집
        summaries = []
        failed_count = 0

        for i, result in enumerate(results):
            if isinstance(result, ArticleSummary):
                summaries.append(result)
            elif isinstance(result, Exception):
                logger.error(f"❌ [{req_id}] 기사 {i+1} 요약 실패: {result}")
                failed_count += 1
            elif result is None:
                failed_count += 1

        elapsed = time.time() - start_time
        success_count = len(summaries)

        logger.info(
            f"🎉 [{req_id}] 다중 기사 요약 완료: "
            f"성공 {success_count}개, 실패 {failed_count}개 ({elapsed:.2f}초)"
        )

        return summaries

    async def summarize_with_keywords(
        self, text: str, language: str = "ko"
    ) -> Dict[str, Any]:
        """키워드 추출과 함께 요약 (비동기)"""
        req_id = str(uuid.uuid4())[:8]

        try:
            logger.info(f"🔍 [{req_id}] 키워드 포함 요약 시작")

            # 기본 요약과 키워드 추출을 동시에 실행
            summary_task = self.summarize(text, language)
            keywords_task = self._extract_keywords(text, language)

            summary_result, keywords_result = await asyncio.gather(
                summary_task, keywords_task, return_exceptions=True
            )

            # 결과 처리
            result = {}

            if isinstance(summary_result, dict) and "summary" in summary_result:
                result.update(summary_result)
            else:
                result["summary"] = "요약 실패"
                result["error"] = (
                    str(summary_result)
                    if isinstance(summary_result, Exception)
                    else "요약 오류"
                )

            if isinstance(keywords_result, list):
                result["keywords"] = keywords_result
            else:
                result["keywords"] = []
                logger.warning(f"⚠️ [{req_id}] 키워드 추출 실패")

            logger.info(f"✅ [{req_id}] 키워드 포함 요약 완료")
            return result

        except Exception as e:
            logger.error(f"💥 [{req_id}] 키워드 포함 요약 실패: {str(e)}")
            return {"error": str(e), "summary": "", "keywords": []}

    async def _extract_keywords(self, text: str, language: str = "ko") -> List[str]:
        """키워드 추출 (비동기)"""
        try:
            if language == "ko":
                system_message = (
                    "너는 텍스트에서 핵심 키워드를 추출하는 전문가야. "
                    "다음 텍스트에서 가장 중요한 키워드 5-7개를 추출해줘. "
                    "키워드는 쉼표로 구분하고, 한국어로만 응답해줘."
                )
                user_message = (
                    f"다음 텍스트에서 핵심 키워드를 추출해줘:\n\n{text[:1000]}..."
                )
            else:
                system_message = (
                    "You are an expert at extracting key terms from text. "
                    "Extract 5-7 most important keywords from the following text. "
                    "Separate keywords with commas and respond only in English."
                )
                user_message = (
                    f"Extract key keywords from the following text:\n\n{text[:1000]}..."
                )

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ]

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=100,
                temperature=0.1,
                timeout=20.0,
            )

            if response.choices and response.choices[0].message.content:
                keywords_text = response.choices[0].message.content.strip()
                keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
                return keywords[:7]  # 최대 7개

            return []

        except Exception as e:
            logger.error(f"키워드 추출 실패: {str(e)}")
            return []

    async def get_summary_stats(
        self, summaries: List[ArticleSummary]
    ) -> Dict[str, Any]:
        """요약 통계 정보 생성 (비동기)"""
        if not summaries:
            return {
                "total_articles": 0,
                "total_original_length": 0,
                "total_summary_length": 0,
                "average_compression_ratio": 0,
                "sources": {},
            }

        total_original = sum(s.original_length for s in summaries)
        total_summary = sum(s.summary_length for s in summaries)

        # 소스별 통계
        source_stats = {}
        for summary in summaries:
            source = summary.source
            if source not in source_stats:
                source_stats[source] = 0
            source_stats[source] += 1

        compression_ratio = (
            (total_original - total_summary) / total_original * 100
            if total_original > 0
            else 0
        )

        return {
            "total_articles": len(summaries),
            "total_original_length": total_original,
            "total_summary_length": total_summary,
            "average_compression_ratio": round(compression_ratio, 2),
            "average_original_length": round(total_original / len(summaries)),
            "average_summary_length": round(total_summary / len(summaries)),
            "sources": source_stats,
        }


# 편의 함수들
async def summarize_text_async(
    text: str, language: str = "ko", api_key: Optional[str] = None
) -> Dict[str, Any]:
    """텍스트 비동기 요약 (편의 함수)"""
    if api_key:
        # 임시 요약기 생성
        temp_settings = type("TempSettings", (), {"OPENAI_API_KEY": api_key})()
        summarizer = AsyncArticleSummarizer()
        summarizer.client = openai.AsyncOpenAI(api_key=api_key)
    else:
        summarizer = AsyncArticleSummarizer()

    return await summarizer.summarize(text, language)


async def summarize_articles_async(
    articles: List[Article], language: str = "ko", max_concurrent: int = 3
) -> List[ArticleSummary]:
    """기사 목록 비동기 요약 (편의 함수)"""
    summarizer = AsyncArticleSummarizer()
    return await summarizer.summarize_articles(
        articles, language, max_concurrent=max_concurrent
    )
