#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT 서비스 모듈
OpenAI API를 사용한 텍스트 요약 서비스
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from ..config import get_settings
from ..utils import get_logger, ContextLogger
from ..utils.exception_handler import ExternalServiceError, handle_external_api_error
from ..models.response_schema import Summary

logger = get_logger("services.gpt")


class GPTService:
    """
    GPT를 사용한 텍스트 처리 서비스
    요약, 키워드 추출, 분석 등의 기능을 제공
    """
    
    def __init__(self):
        """GPT 서비스 초기화"""
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self._prompt_templates = self._load_prompt_templates()
        self._request_count = 0
        self._total_tokens = 0
        
        logger.info(f"✅ GPT 서비스 초기화 완료 - 모델: {self.settings.openai_model}")
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """프롬프트 템플릿 로드"""
        return {
            "summarize_compact": """
다음 뉴스 기사들을 간결하게 요약해주세요.

요약 규칙:
1. 핵심 내용만 {max_length}자 이내로 요약
2. 객관적이고 정확한 정보만 포함
3. 시간순 또는 중요도순으로 정리
4. 한국어로 작성

기사 내용:
{content}

요약:""",
            
            "summarize_detailed": """
다음 뉴스 기사들을 상세하게 요약해주세요.

요약 규칙:
1. 주요 사실과 배경 정보 포함
2. {max_length}자 이내로 작성
3. 객관적이고 균형잡힌 시각 유지
4. 중요한 인용문이나 수치 포함
5. 한국어로 작성

기사 내용:
{content}

상세 요약:""",
            
            "summarize_bullet": """
다음 뉴스 기사들을 불릿 포인트로 요약해주세요.

요약 규칙:
1. 주요 내용을 3-7개의 불릿 포인트로 정리
2. 각 포인트는 한 문장으로 명확하게 작성
3. 중요도순으로 배열
4. 총 {max_length}자 이내
5. 한국어로 작성

기사 내용:
{content}

• 
""",
            
            "extract_keywords": """
다음 텍스트에서 핵심 키워드 5-10개를 추출해주세요.

규칙:
1. 가장 중요하고 의미있는 키워드만 선택
2. 고유명사, 전문용어, 핵심 개념 포함
3. 중요도순으로 배열
4. 콤마로 구분하여 나열

텍스트:
{content}

키워드:""",
            
            "extract_key_points": """
다음 텍스트의 핵심 포인트 3-5개를 추출해주세요.

규칙:
1. 가장 중요한 내용만 선별
2. 각 포인트는 한 문장으로 작성
3. 순서대로 번호를 매겨 나열
4. 한국어로 작성

텍스트:
{content}

핵심 포인트:
"""
        }
    
    async def summarize_text(
        self,
        text: str,
        style: str = "compact",
        max_length: int = 300,
        language: str = "ko",
        focus_keywords: Optional[List[str]] = None
    ) -> Summary:
        """
        텍스트 요약
        
        Args:
            text: 요약할 텍스트
            style: 요약 스타일 (compact, detailed, bullet)
            max_length: 최대 길이
            language: 언어
            focus_keywords: 중점 키워드
        
        Returns:
            요약 결과
        """
        
        with ContextLogger(f"GPT 텍스트 요약 ({style}, {max_length}자)", "gpt.summarize"):
            try:
                # 텍스트 전처리
                cleaned_text = self._preprocess_text(text)
                
                # 프롬프트 생성
                prompt = self._create_prompt(cleaned_text, style, max_length, focus_keywords)
                
                # GPT 요청
                summary_text = await self._call_gpt(prompt)
                
                # 후처리
                summary_text = self._postprocess_summary(summary_text, max_length)
                
                # 추가 정보 추출 (병렬 실행)
                keywords_task = self._extract_keywords_async(cleaned_text)
                key_points_task = self._extract_key_points_async(cleaned_text)
                
                keywords, key_points = await asyncio.gather(
                    keywords_task, key_points_task, return_exceptions=True
                )
                
                # 예외 처리
                if isinstance(keywords, Exception):
                    logger.warning(f"키워드 추출 실패: {keywords}")
                    keywords = []
                
                if isinstance(key_points, Exception):
                    logger.warning(f"핵심 포인트 추출 실패: {key_points}")
                    key_points = []
                
                # 신뢰도 점수 계산
                confidence_score = self._calculate_confidence_score(
                    len(cleaned_text), len(summary_text), style
                )
                
                # 요약 객체 생성
                summary = Summary(
                    original_length=len(text),
                    summary_length=len(summary_text),
                    summary_text=summary_text,
                    key_points=key_points if key_points else None,
                    keywords=keywords if keywords else None,
                    confidence_score=confidence_score,
                    language=language,
                    style=style
                )
                
                logger.info(
                    f"✅ 요약 완료 - 원본: {len(text)}자 → 요약: {len(summary_text)}자 "
                    f"(압축률: {len(summary_text)/len(text)*100:.1f}%)"
                )
                
                return summary
                
            except Exception as e:
                logger.error(f"❌ 텍스트 요약 실패: {str(e)}")
                raise ExternalServiceError("OpenAI", f"텍스트 요약 중 오류 발생: {str(e)}")
    
    async def summarize_articles(
        self,
        articles: List[Dict[str, Any]],
        style: str = "compact",
        max_length: int = 500,
        language: str = "ko"
    ) -> Summary:
        """
        여러 기사를 종합 요약
        
        Args:
            articles: 기사 목록
            style: 요약 스타일
            max_length: 최대 길이
            language: 언어
        
        Returns:
            종합 요약 결과
        """
        
        with ContextLogger(f"GPT 기사 종합요약 ({len(articles)}개)", "gpt.summarize_articles"):
            try:
                # 기사들을 하나의 텍스트로 결합
                combined_text = self._combine_articles(articles)
                
                # 너무 길면 분할 처리
                if len(combined_text) > 12000:  # 토큰 제한 고려
                    return await self._summarize_long_content(
                        combined_text, articles, style, max_length, language
                    )
                
                # 일반 요약 처리
                return await self.summarize_text(
                    combined_text, style, max_length, language
                )
                
            except Exception as e:
                logger.error(f"❌ 기사 종합요약 실패: {str(e)}")
                raise ExternalServiceError("OpenAI", f"기사 요약 중 오류 발생: {str(e)}")
    
    async def _call_gpt(
        self,
        prompt: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> str:
        """
        GPT API 호출 (재시도 로직 포함)
        
        Args:
            prompt: 프롬프트
            max_retries: 최대 재시도 횟수
            retry_delay: 재시도 간격
        
        Returns:
            GPT 응답 텍스트
        """
        
        self._request_count += 1
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                response = await self.client.chat.completions.create(
                    model=self.settings.openai_model,
                    messages=[
                        {"role": "system", "content": "당신은 뉴스 요약 전문가입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.settings.openai_max_tokens,
                    temperature=self.settings.openai_temperature,
                    timeout=30.0
                )
                
                duration = time.time() - start_time
                
                # 토큰 사용량 추적
                if hasattr(response, 'usage') and response.usage:
                    self._total_tokens += response.usage.total_tokens
                    logger.debug(f"토큰 사용량: {response.usage.total_tokens}")
                
                # 응답 텍스트 추출
                content = response.choices[0].message.content.strip()
                
                logger.debug(f"✅ GPT 응답 완료 ({duration:.2f}초, 시도 {attempt + 1}/{max_retries})")
                
                return content
                
            except Exception as e:
                logger.warning(f"⚠️ GPT 요청 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt == max_retries - 1:
                    # 마지막 시도도 실패
                    raise ExternalServiceError(
                        "OpenAI", 
                        f"GPT API 호출 실패 (최대 재시도 초과): {str(e)}"
                    )
                
                # 재시도 전 대기
                await asyncio.sleep(retry_delay * (2 ** attempt))  # 지수 백오프
    
    def _preprocess_text(self, text: str) -> str:
        """텍스트 전처리"""
        # 기본 정리
        text = text.strip()
        
        # 중복 공백 제거
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # HTML 태그 제거 (기본적인)
        text = re.sub(r'<[^>]+>', '', text)
        
        # 특수 문자 정리
        text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)]', '', text)
        
        return text
    
    def _create_prompt(
        self,
        text: str,
        style: str,
        max_length: int,
        focus_keywords: Optional[List[str]] = None
    ) -> str:
        """프롬프트 생성"""
        
        # 기본 템플릿 선택
        template_key = f"summarize_{style}"
        if template_key not in self._prompt_templates:
            template_key = "summarize_compact"
        
        template = self._prompt_templates[template_key]
        
        # 템플릿에 값 대입
        prompt = template.format(
            content=text,
            max_length=max_length
        )
        
        # 중점 키워드 추가
        if focus_keywords:
            keyword_text = ", ".join(focus_keywords)
            prompt += f"\n\n중점적으로 다룰 키워드: {keyword_text}"
        
        return prompt
    
    def _postprocess_summary(self, summary: str, max_length: int) -> str:
        """요약 후처리"""
        
        # 기본 정리
        summary = summary.strip()
        
        # 불필요한 접두어 제거
        prefixes_to_remove = [
            "요약:", "요약 결과:", "Summary:", "다음은 요약입니다:",
            "기사 요약:", "내용 요약:", "주요 내용:"
        ]
        
        for prefix in prefixes_to_remove:
            if summary.startswith(prefix):
                summary = summary[len(prefix):].strip()
        
        # 길이 제한 적용
        if len(summary) > max_length:
            # 문장 단위로 자르기
            sentences = summary.split('.')
            truncated = ""
            for sentence in sentences:
                if len(truncated + sentence + '.') <= max_length:
                    truncated += sentence + '.'
                else:
                    break
            
            if truncated:
                summary = truncated
            else:
                # 강제로 자르기
                summary = summary[:max_length-3] + "..."
        
        return summary
    
    async def _extract_keywords_async(self, text: str) -> List[str]:
        """비동기 키워드 추출"""
        try:
            prompt = self._prompt_templates["extract_keywords"].format(content=text[:2000])
            response = await self._call_gpt(prompt)
            
            # 키워드 파싱
            keywords = [kw.strip() for kw in response.split(',') if kw.strip()]
            return keywords[:10]  # 최대 10개
            
        except Exception as e:
            logger.warning(f"키워드 추출 실패: {str(e)}")
            return []
    
    async def _extract_key_points_async(self, text: str) -> List[str]:
        """비동기 핵심 포인트 추출"""
        try:
            prompt = self._prompt_templates["extract_key_points"].format(content=text[:2000])
            response = await self._call_gpt(prompt)
            
            # 포인트 파싱 (번호 제거)
            import re
            points = re.split(r'\d+\.', response)
            points = [point.strip() for point in points if point.strip()]
            return points[:5]  # 최대 5개
            
        except Exception as e:
            logger.warning(f"핵심 포인트 추출 실패: {str(e)}")
            return []
    
    def _calculate_confidence_score(
        self,
        original_length: int,
        summary_length: int,
        style: str
    ) -> float:
        """요약 신뢰도 점수 계산"""
        
        # 기본 점수
        base_score = 0.7
        
        # 압축률 기반 점수 조정
        compression_ratio = summary_length / original_length if original_length > 0 else 0
        
        if 0.1 <= compression_ratio <= 0.3:  # 적절한 압축률
            compression_score = 0.2
        elif 0.05 <= compression_ratio <= 0.5:  # 괜찮은 압축률
            compression_score = 0.1
        else:  # 부적절한 압축률
            compression_score = -0.1
        
        # 스타일별 점수 조정
        style_scores = {
            "compact": 0.1,
            "detailed": 0.05,
            "bullet": 0.08
        }
        style_score = style_scores.get(style, 0)
        
        # 최종 점수 계산
        final_score = base_score + compression_score + style_score
        
        # 0-1 범위로 제한
        return max(0.0, min(1.0, final_score))
    
    def _combine_articles(self, articles: List[Dict[str, Any]]) -> str:
        """기사들을 하나의 텍스트로 결합"""
        
        combined_parts = []
        
        for i, article in enumerate(articles, 1):
            title = article.get('title', '제목 없음')
            content = article.get('content', '')
            source = article.get('source', '출처 없음')
            
            # 기사 정보 추가
            article_text = f"[기사 {i}] {title}\n출처: {source}\n\n{content}\n"
            combined_parts.append(article_text)
        
        return "\n".join(combined_parts)
    
    async def _summarize_long_content(
        self,
        content: str,
        articles: List[Dict[str, Any]],
        style: str,
        max_length: int,
        language: str
    ) -> Summary:
        """긴 콘텐츠의 분할 요약"""
        
        logger.info(f"📄 긴 콘텐츠 분할 요약 시작 (총 {len(content)}자)")
        
        # 기사별로 개별 요약
        article_summaries = []
        
        # 병렬 처리를 위한 태스크 생성
        summary_tasks = []
        for article in articles:
            content_text = article.get('content', '')
            if content_text and len(content_text) > 100:
                task = self.summarize_text(
                    content_text,
                    style="compact",  # 개별 요약은 간결하게
                    max_length=100,   # 개별 요약은 짧게
                    language=language
                )
                summary_tasks.append(task)
        
        # 병렬 실행
        if summary_tasks:
            individual_summaries = await asyncio.gather(*summary_tasks, return_exceptions=True)
            
            for summary in individual_summaries:
                if isinstance(summary, Summary):
                    article_summaries.append(summary.summary_text)
                elif not isinstance(summary, Exception):
                    article_summaries.append(str(summary))
        
        # 개별 요약들을 종합
        if article_summaries:
            combined_summary = "\n\n".join(article_summaries)
            return await self.summarize_text(
                combined_summary,
                style=style,
                max_length=max_length,
                language=language
            )
        else:
            # 개별 요약 실패 시 원본의 일부만 요약
            truncated_content = content[:8000]  # 8000자로 제한
            return await self.summarize_text(
                truncated_content,
                style=style,
                max_length=max_length,
                language=language
            )
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """사용량 통계 반환"""
        return {
            "request_count": self._request_count,
            "total_tokens": self._total_tokens,
            "model": self.settings.openai_model,
            "avg_tokens_per_request": self._total_tokens / max(1, self._request_count)
        }
    
    async def test_connection(self) -> bool:
        """OpenAI API 연결 테스트"""
        try:
            response = await self._call_gpt("Hello, this is a connection test.")
            logger.info("✅ OpenAI API 연결 테스트 성공")
            return True
        except Exception as e:
            logger.error(f"❌ OpenAI API 연결 테스트 실패: {str(e)}")
            return False


if __name__ == "__main__":
    # 테스트 코드
    import asyncio
    
    async def test_gpt_service():
        print("GPT 서비스 테스트:")
        
        try:
            service = GPTService()
            
            # 연결 테스트
            connected = await service.test_connection()
            print(f"✅ 연결 테스트: {'성공' if connected else '실패'}")
            
            if connected:
                # 간단한 요약 테스트
                test_text = "이것은 GPT 서비스의 요약 기능을 테스트하기 위한 샘플 텍스트입니다. " * 10
                
                summary = await service.summarize_text(
                    test_text,
                    style="compact",
                    max_length=100
                )
                
                print(f"✅ 요약 테스트 성공:")
                print(f"  원본 길이: {summary.original_length}")
                print(f"  요약 길이: {summary.summary_length}")
                print(f"  요약 내용: {summary.summary_text[:50]}...")
                
                # 사용량 통계
                stats = service.get_usage_stats()
                print(f"✅ 사용량 통계: {stats}")
            
        except Exception as e:
            print(f"❌ GPT 서비스 테스트 실패: {e}")
    
    # 실제 테스트 실행
    # asyncio.run(test_gpt_service())
    print("GPT 서비스 모듈 로드 완료")