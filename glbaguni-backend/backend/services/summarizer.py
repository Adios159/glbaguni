#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
요약 서비스 모듈
뉴스 기사 및 텍스트 요약 로직을 담당
"""

import asyncio
import time
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    from ..models import Article, ArticleSummary
    from .gpt import safe_gpt_call, get_gpt_service
    from ..config import settings
except ImportError:
    try:
        from models import Article, ArticleSummary
        from services.gpt import safe_gpt_call, get_gpt_service
        from config import settings
    except ImportError:
        # Fallback imports
        import logging
        
        async def safe_gpt_call(prompt: str, language: str = "ko", max_retries: int = 3) -> str:
            return "요약을 생성할 수 없습니다."
        
        def get_gpt_service():
            return None

logger = logging.getLogger(__name__)


class ArticleSummarizer:
    """뉴스 기사 및 텍스트 요약을 담당하는 서비스 클래스"""
    
    def __init__(self):
        """요약 서비스 초기화"""
        self.gpt_service = get_gpt_service()
        self.max_content_length = 8000  # GPT 토큰 제한을 고려한 최대 길이
        
        logger.info("ArticleSummarizer initialized")
    
    async def summarize(self, input_text: str, language: str = "ko") -> Dict[str, Any]:
        """
        텍스트 요약 (하위 호환성 유지)
        
        Args:
            input_text: 요약할 텍스트
            language: 요약 언어
            
        Returns:
            요약 결과 딕셔너리
        """
        if not input_text:
            return {"error": "Missing input text for summarization."}
        
        try:
            # 텍스트 길이 제한
            if len(input_text) > self.max_content_length:
                input_text = input_text[:self.max_content_length] + "..."
                logger.warning(f"Text truncated to {self.max_content_length} characters")
            
            logger.info(f"Summarizing text - Length: {len(input_text)}, Language: {language}")
            
            # GPT 서비스를 통한 요약 생성
            summary = await safe_gpt_call(input_text, language)
            
            return {
                "summary": summary,
                "language": language,
                "model": "gpt-3.5-turbo",
                "input_length": len(input_text),
                "output_length": len(summary)
            }
            
        except Exception as e:
            logger.error(f"Error in text summarization: {e}")
            return {"error": f"Summarization failed: {str(e)}"}
    
    async def summarize_article(
        self,
        article: Article,
        custom_prompt: Optional[str] = None,
        language: str = "ko"
    ) -> Optional[ArticleSummary]:
        """
        단일 기사 요약
        
        Args:
            article: 요약할 기사
            custom_prompt: 커스텀 프롬프트
            language: 요약 언어
            
        Returns:
            요약된 기사 객체 또는 None
        """
        try:
            # 기사 내용 준비
            if custom_prompt:
                content = f"{custom_prompt}\n\n제목: {article.title}\n\n내용: {article.content}"
            else:
                content = f"제목: {article.title}\n\n내용: {article.content}"
            
            # 텍스트 길이 제한
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + "..."
            
            logger.info(f"Summarizing article: {article.title[:50]}... (Language: {language})")
            
            # 요약 생성
            summary_text = await safe_gpt_call(content, language)
            
            if not summary_text or "요약을 생성할 수 없습니다" in summary_text:
                logger.error(f"Failed to summarize article: {article.title}")
                return None
            
            # ArticleSummary 객체 생성
            article_summary = ArticleSummary(
                title=article.title,
                url=str(article.url),
                summary=summary_text,
                source=getattr(article, 'source', 'unknown'),
                original_length=len(article.content),
                summary_length=len(summary_text)
            )
            
            logger.info(f"Successfully summarized article: {article.title[:50]}...")
            return article_summary
            
        except Exception as e:
            logger.error(f"Error summarizing article {article.title}: {e}")
            return None
    
    async def summarize_articles(
        self,
        articles: List[Article],
        custom_prompt: Optional[str] = None,
        language: str = "ko"
    ) -> List[ArticleSummary]:
        """여러 기사 일괄 요약"""
        if not articles:
            return []
        
        start_time = time.time()
        max_articles = min(len(articles), 10)
        articles_to_process = articles[:max_articles]
        
        logger.info(f"Batch summarizing {len(articles_to_process)} articles")
        
        summaries = []
        for i, article in enumerate(articles_to_process):
            if time.time() - start_time > 60:  # 60초 제한
                break
            
            try:
                summary = await self.summarize_article(article, custom_prompt, language)
                if summary:
                    summaries.append(summary)
            except Exception as e:
                logger.error(f"Error processing article {i+1}: {e}")
                continue
        
        logger.info(f"Batch completed: {len(summaries)} summaries")
        return summaries
    
    def get_summary_stats(self, summaries: List[ArticleSummary]) -> Dict[str, Any]:
        """요약 통계 정보 반환"""
        if not summaries:
            return {}
        
        total_original_length = sum(s.original_length for s in summaries)
        total_summary_length = sum(s.summary_length for s in summaries)
        
        return {
            "total_articles": len(summaries),
            "total_original_length": total_original_length,
            "total_summary_length": total_summary_length,
            "compression_ratio": round((1 - total_summary_length / total_original_length) * 100, 2) if total_original_length > 0 else 0,
            "average_summary_length": round(total_summary_length / len(summaries), 2)
        }


# 하위 호환성을 위한 별칭
SummarizerService = ArticleSummarizer


# 전역 인스턴스 관리
_summarizer_instance: Optional[ArticleSummarizer] = None


def get_summarizer_service() -> ArticleSummarizer:
    """전역 요약 서비스 인스턴스 반환"""
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = ArticleSummarizer()
    return _summarizer_instance


# 프롬프트 구성 유틸리티 함수
def build_summary_prompt(text: str, language: str = "ko") -> str:
    """
    요약용 프롬프트 구성
    
    Args:
        text: 요약할 텍스트
        language: 언어 ('ko' 또는 'en')
    
    Returns:
        구성된 프롬프트
    """
    if language == "ko":
        prompt = f"다음 텍스트를 한국어로 간결하게 요약해주세요:\n\n{text}"
    else:
        prompt = f"Please summarize the following text concisely:\n\n{text}"
    
    return prompt 