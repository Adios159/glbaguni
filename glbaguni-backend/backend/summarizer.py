import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import openai

# Simple imports with fallback
try:
    from backend.models import Article, ArticleSummary
    from backend.config import settings
except ImportError:
    try:
        from models import Article, ArticleSummary
        from config import settings
    except ImportError:
        from models import Article, ArticleSummary
        # Create fallback settings
        import os
        class Settings:
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
            OPENAI_MODEL = "gpt-3.5-turbo"
            SUMMARIZATION_PROMPT = "Summarize the following text:"
        settings = Settings()

logger = logging.getLogger(__name__)


def build_summary_prompt(text: str, language: str = "en") -> list:
    """
    Build summary prompt messages for OpenAI API based on language preference.

    Args:
        text: The text content to summarize
        language: Language preference ('ko' for Korean, 'en' or other for English)

    Returns:
        List of message objects for OpenAI API
    """
    if language == "ko":
        system_message = "너는 훌륭한 요약가야. 사용자가 제공한 긴 글을 명확하고 간결하게 한국어로 요약해줘. 핵심 내용을 중심으로 3-4문장으로 간결하게 요약하고, 중요한 사실과 정보에 집중하며, 불필요한 수사나 감정적 표현은 제외해줘. 요약 결과는 반드시 한국어로 작성해줘."
    else:
        system_message = "You are a helpful assistant that summarizes long texts into concise English summaries. Focus on key facts and important information, providing a clear and objective summary in 3-4 sentences."

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": text},
    ]


class ArticleSummarizer:
    """Handles article summarization using OpenAI GPT-4 API."""

    def __init__(self):
        # Get settings either from the settings object or from environment variables
        try:
            openai_api_key = settings.OPENAI_API_KEY
            openai_model = settings.OPENAI_MODEL
            summarization_prompt = settings.SUMMARIZATION_PROMPT
        except (AttributeError, ImportError):
            # Fallback to environment variables
            import os
            openai_api_key = os.getenv("OPENAI_API_KEY", "")
            openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            summarization_prompt = os.getenv(
                "SUMMARIZATION_PROMPT",
                "다음은 뉴스 기사입니다. 핵심 내용을 중심으로 3~4문장으로 간결하게 요약해 주세요. 중요한 사실과 정보에 집중하고, 불필요한 수사나 감정적 표현은 제외해 주세요."
            )

        if not openai_api_key:
            raise ValueError("OpenAI API key is required")

        self.client = openai.OpenAI(api_key=openai_api_key)
        self.model = openai_model
        self.default_prompt = summarization_prompt

    def summarize(self, input_text: str, language: str = "en") -> dict:
        """
        Summarize input text with language support.

        Args:
            input_text: The text to summarize
            language: Language preference ('ko' for Korean, 'en' or other for English)

        Returns:
            Dictionary with summary or error information
        """
        if not input_text:
            return {"error": "Missing input text for summarization."}

        try:
            # Build messages using the helper function
            messages = build_summary_prompt(input_text, language)

            # Log debugging information
            logger.info(f"🔍 [SUMMARIZE] Language: {language}")
            logger.info(f"📨 [SUMMARIZE] Messages being sent to OpenAI:")
            for i, msg in enumerate(messages):
                logger.info(
                    f"   Message {i+1} [{msg['role']}]: {msg['content'][:200]}..."
                )

            # Make API call with updated client
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using gpt-3.5-turbo for cost efficiency
                messages=messages,
                temperature=0.5,
                max_tokens=400,
                timeout=30,
            )

            # Extract summary from response
            if response.choices and response.choices[0].message.content:
                summary = response.choices[0].message.content.strip()
                return {
                    "summary": summary,
                    "language": language,
                    "model": "gpt-3.5-turbo",
                    "input_length": len(input_text),
                    "output_length": len(summary),
                }
            else:
                return {"error": "OpenAI API returned no content"}

        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            return {"error": f"Summarization failed: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error during summarization: {e}")
            return {"error": f"Summarization failed: {str(e)}"}

    def summarize_article(
        self,
        article: Article,
        custom_prompt: Optional[str] = None,
        language: str = "en",
    ) -> Optional[ArticleSummary]:
        f"""Summarize a single article using GPT with language support.
        
        Args:
            article: Article object to summarize
            custom_prompt: Optional custom prompt to use
            language: Target language for summary ("ko" for Korean, "en" for English)
        """
        try:
            # Prepare the content for the API
            content = f"Title: {article.title}\n\nContent: {article.content}"

            # Truncate content if too long (GPT has token limits)
            max_content_length = 8000  # Conservative limit
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."

            logger.info(
                f"🌐 [OPENAI] Target language: {'Korean' if language == 'ko' else 'English'} - {article.title}"
            )
            logger.info(
                f"📝 [OPENAI] Content length after truncation: {len(content)} characters"
            )

            # Build language-appropriate messages
            if language == "ko":
                system_message = "너는 훌륭한 요약가야. 사용자가 제공한 긴 글을 명확하고 간결하게 한국어로 요약해줘. 핵심 내용을 중심으로 3-4문장으로 간결하게 요약하고, 중요한 사실과 정보에 집중하며, 불필요한 수사나 감정적 표현은 제외해줘. 요약 결과는 반드시 한국어로 작성해줘."
            else:
                system_message = "You are a helpful assistant that summarizes long texts into concise English summaries. Focus on key facts and important information, providing a clear and objective summary in 3-4 sentences."

            # Use custom prompt if provided, otherwise use the content directly
            if custom_prompt:
                user_content = f"{custom_prompt}\n\n{content}"
            else:
                # For Korean, add explicit instruction to the user content
                if language == "ko":
                    user_content = f"아래 기사를 한국어로 간결하게 요약해줘. 영어로 쓰지 마.\n\n{content}"
                else:
                    user_content = content

            # Build the messages for OpenAI API
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_content},
            ]

            # Log detailed information for debugging
            logger.info(
                f"💬 [OPENAI] Using {'Korean' if language == 'ko' else 'English'} system prompt"
            )
            logger.info(f"🔍 [OPENAI] System message: {system_message[:100]}...")
            logger.info(f"👤 [OPENAI] User content preview: {user_content[:150]}...")
            logger.info(f"🤖 [OPENAI] Model: {self.model}")
            logger.info(f"📨 [OPENAI] Full messages array:")
            for i, msg in enumerate(messages):
                logger.info(
                    f"   Message {i+1} [{msg['role']}]: {msg['content'][:200]}..."
                )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=300,  # 400에서 300으로 단축하여 속도 향상
                temperature=0.3,  # Lower temperature for more consistent summaries
                timeout=15,  # 30초에서 15초로 단축
            )

            # Check if response has choices
            if not response.choices:
                logger.error("OpenAI API returned no choices")
                return None

            # Get the content safely
            summary_text = response.choices[0].message.content
            if summary_text is None:
                logger.error("OpenAI API returned None content")
                return None

            summary_text = summary_text.strip()

            # Check if we got meaningful content
            if not summary_text:
                logger.error("OpenAI API returned empty content")
                return None

            article_summary = ArticleSummary(
                title=article.title,
                url=article.url,
                summary=summary_text,
                source=article.source,
                original_length=len(article.content),
                summary_length=len(summary_text),
            )

            logger.info(f"Successfully summarized article: {article.title}")
            return article_summary

        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error summarizing article {article.title}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error summarizing article {article.title}: {e}")
            return None

    def summarize_articles(
        self,
        articles: List[Article],
        custom_prompt: Optional[str] = None,
        language: str = "en",
    ) -> List[ArticleSummary]:
        """Summarize multiple articles with comprehensive debugging and timeout protection."""
        start_time = time.time()
        max_total_time = 60  # 전체 요약 작업에 최대 60초 제한
        max_per_article = 10  # 개별 기사당 최대 10초 제한

        summaries = []

        if not articles:
            logger.warning("No articles provided for summarization")
            return summaries

        # 처리할 기사 수 제한
        max_articles_to_process = min(len(articles), 10)  # 최대 10개 기사만 처리
        articles_to_process = articles[:max_articles_to_process]

        logger.info(
            f"🚀 [SUMMARIZER] Starting batch summarization for {len(articles_to_process)} articles"
        )
        logger.info(
            f"🌐 [SUMMARIZER] Target language: {'Korean' if language == 'ko' else 'English'}"
        )

        successful_summaries = 0
        failed_summaries = 0

        for i, article in enumerate(articles_to_process):
            # 전체 시간 초과 체크
            if time.time() - start_time > max_total_time:
                logger.warning(
                    f"⏰ [SUMMARIZER] Total time limit exceeded, stopping at {i} articles"
                )
                break

            article_start_time = time.time()

            try:
                logger.info(
                    f"📄 [SUMMARIZER] Processing {i+1}/{len(articles_to_process)}: {article.title[:50]}..."
                )

                summary = self.summarize_article(article, custom_prompt, language)

                # 개별 기사 시간 초과 체크
                article_processing_time = time.time() - article_start_time
                if article_processing_time > max_per_article:
                    logger.warning(
                        f"⏰ [SUMMARIZER] Article processing took too long: {article_processing_time:.2f}s"
                    )

                if summary:
                    summaries.append(summary)
                    successful_summaries += 1
                    logger.info(
                        f"✅ [SUMMARIZER] Summary {i+1} completed in {article_processing_time:.2f}s"
                    )
                else:
                    failed_summaries += 1
                    logger.warning(f"❌ [SUMMARIZER] Summary {i+1} failed")

            except Exception as e:
                failed_summaries += 1
                logger.error(f"💥 [SUMMARIZER] Error processing article {i+1}: {e}")
                continue

        total_time = time.time() - start_time
        logger.info(f"📊 [SUMMARIZER] Batch completed in {total_time:.2f}s:")
        logger.info(f"   ✅ Successful: {successful_summaries}")
        logger.info(f"   ❌ Failed: {failed_summaries}")
        logger.info(
            f"   📈 Success rate: {(successful_summaries / len(articles_to_process) * 100):.1f}%"
        )

        return summaries

    def _is_korean_content(self, content: str) -> bool:
        """Detect if content is primarily Korean."""
        import re

        # Count Korean characters (Hangul syllables, Jamo, compatibility Jamo)
        korean_chars = len(
            re.findall(r"[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF]", content)
        )

        # Count English characters
        english_chars = len(re.findall(r"[a-zA-Z]", content))

        # Consider it Korean if Korean characters make up more than 30% of alphanumeric content
        total_alpha = korean_chars + english_chars
        if total_alpha > 0:
            korean_ratio = korean_chars / total_alpha
            return korean_ratio > 0.3

        return False

    def _get_system_message(self, is_korean: bool) -> str:
        """Get appropriate system message based on content language."""
        if is_korean:
            return (
                "당신은 한국어 뉴스 기사를 정확하고 간결하게 요약하는 전문 어시스턴트입니다. "
                "핵심 정보를 명확하게 전달하고, 객관적인 톤을 유지하며, "
                "중요한 사실과 맥락을 놓치지 않고 요약해 주세요."
            )
        else:
            return (
                "You are a helpful assistant that summarizes news articles concisely and accurately. "
                "Focus on key facts, maintain objectivity, and ensure important context is preserved."
            )

    def get_summary_stats(self, summaries: List[ArticleSummary]) -> dict:
        """Get statistics about the summarization process."""
        if not summaries:
            return {}

        total_original_length = sum(s.original_length for s in summaries)
        total_summary_length = sum(s.summary_length for s in summaries)

        return {
            "total_articles": len(summaries),
            "total_original_length": total_original_length,
            "total_summary_length": total_summary_length,
            "compression_ratio": (
                round((1 - total_summary_length / total_original_length) * 100, 2)
                if total_original_length > 0
                else 0
            ),
            "average_summary_length": round(total_summary_length / len(summaries), 2),
        }
