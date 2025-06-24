#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
요청 스키마 정의
사용자 입력에 대한 Pydantic 모델들
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, validator


class SummarizeRequest(BaseModel):
    """
    뉴스 요약 요청 모델
    RSS URL 또는 키워드를 통한 뉴스 수집 및 요약 요청
    """

    rss_urls: List[str] = Field(
        ..., min_items=1, max_items=10, description="RSS 피드 URL 목록 (최대 10개)"
    )

    max_articles: int = Field(
        default=10, ge=1, le=50, description="수집할 최대 기사 수 (1-50)"
    )

    summary_style: str = Field(
        default="compact", description="요약 스타일 (compact, detailed, bullet)"
    )

    language: str = Field(default="ko", description="요약 언어 (ko, en)")

    filter_keywords: Optional[List[str]] = Field(
        default=None, max_items=20, description="필터링할 키워드 목록 (포함할 키워드)"
    )

    exclude_keywords: Optional[List[str]] = Field(
        default=None, max_items=20, description="제외할 키워드 목록"
    )

    user_email: Optional[str] = Field(
        default=None, description="결과 전송용 이메일 주소"
    )

    save_to_history: bool = Field(default=True, description="히스토리 저장 여부")

    @validator("rss_urls")
    def validate_rss_urls(cls, v):
        """RSS URL 목록 검증"""
        if not v:
            raise ValueError("최소 하나의 RSS URL이 필요합니다")

        for url in v:
            if not url.strip():
                raise ValueError("빈 URL은 허용되지 않습니다")

            # 기본적인 URL 형식 검증
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError(f"올바른 URL 형식이 아닙니다: {url}")

        return [url.strip() for url in v]

    @validator("summary_style")
    def validate_summary_style(cls, v):
        """요약 스타일 검증"""
        allowed_styles = ["compact", "detailed", "bullet", "academic"]
        if v not in allowed_styles:
            raise ValueError(f"요약 스타일은 다음 중 하나여야 합니다: {allowed_styles}")
        return v

    @validator("language")
    def validate_language(cls, v):
        """언어 코드 검증"""
        allowed_languages = ["ko", "en", "ja", "zh"]
        if v not in allowed_languages:
            raise ValueError(f"지원되는 언어: {allowed_languages}")
        return v

    @validator("filter_keywords", "exclude_keywords")
    def validate_keywords(cls, v):
        """키워드 목록 검증"""
        if v is None:
            return v

        # 빈 키워드 제거
        clean_keywords = [kw.strip() for kw in v if kw.strip()]

        # 키워드 길이 검증
        for keyword in clean_keywords:
            if len(keyword) > 50:
                raise ValueError("키워드는 50자를 초과할 수 없습니다")

        return clean_keywords

    @validator("user_email")
    def validate_email(cls, v):
        """이메일 주소 검증"""
        if v is None:
            return v

        import re

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("올바른 이메일 형식이 아닙니다")

        return v.lower()


class TextSummarizeRequest(BaseModel):
    """
    텍스트 직접 요약 요청 모델
    사용자가 직접 입력한 텍스트의 요약 요청
    """

    text: str = Field(
        ..., min_length=50, max_length=50000, description="요약할 텍스트 (50-50000자)"
    )

    summary_length: int = Field(
        default=300, ge=50, le=1000, description="요약 길이 (50-1000자)"
    )

    summary_style: str = Field(default="compact", description="요약 스타일")

    language: str = Field(default="ko", description="요약 언어")

    focus_keywords: Optional[List[str]] = Field(
        default=None, max_items=10, description="중점적으로 다룰 키워드"
    )

    @validator("text")
    def validate_text(cls, v):
        """텍스트 내용 검증"""
        text = v.strip()

        if not text:
            raise ValueError("요약할 텍스트가 필요합니다")

        # 기본적인 유해 콘텐츠 검사
        prohibited_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
        ]

        import re

        for pattern in prohibited_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError("허용되지 않는 콘텐츠가 포함되어 있습니다")

        return text


class NewsSearchRequest(BaseModel):
    """
    뉴스 검색 요청 모델
    키워드 기반 뉴스 검색 요청
    """

    query: str = Field(..., min_length=1, max_length=200, description="검색 쿼리")

    sources: Optional[List[str]] = Field(
        default=None, max_items=20, description="검색할 뉴스 소스 목록"
    )

    date_from: Optional[datetime] = Field(default=None, description="검색 시작 날짜")

    date_to: Optional[datetime] = Field(default=None, description="검색 종료 날짜")

    max_results: int = Field(default=20, ge=1, le=100, description="최대 검색 결과 수")

    sort_by: str = Field(
        default="relevance", description="정렬 기준 (relevance, date, popularity)"
    )

    language: str = Field(default="ko", description="검색 언어")

    @validator("query")
    def validate_query(cls, v):
        """검색 쿼리 검증"""
        query = v.strip()

        if not query:
            raise ValueError("검색 쿼리가 필요합니다")

        # 특수 문자 제한
        import re

        if re.search(r'[<>"\';{}]', query):
            raise ValueError("허용되지 않는 특수 문자가 포함되어 있습니다")

        return query

    @validator("sort_by")
    def validate_sort_by(cls, v):
        """정렬 기준 검증"""
        allowed_sorts = ["relevance", "date", "popularity"]
        if v not in allowed_sorts:
            raise ValueError(f"정렬 기준은 다음 중 하나여야 합니다: {allowed_sorts}")
        return v

    @validator("date_to")
    def validate_date_range(cls, v, values):
        """날짜 범위 검증"""
        if v and "date_from" in values and values["date_from"]:
            if v <= values["date_from"]:
                raise ValueError("종료 날짜는 시작 날짜보다 나중이어야 합니다")
        return v


class RSSFeedRequest(BaseModel):
    """
    RSS 피드 추가/관리 요청 모델
    RSS 피드 소스 등록 및 관리
    """

    url: str = Field(..., description="RSS 피드 URL")

    name: str = Field(..., min_length=1, max_length=100, description="RSS 피드 이름")

    category: str = Field(default="general", description="카테고리")

    language: str = Field(default="ko", description="언어 코드")

    is_active: bool = Field(default=True, description="활성화 상태")

    update_frequency: int = Field(
        default=3600, ge=300, le=86400, description="업데이트 주기 (초, 5분-24시간)"
    )

    @validator("url")
    def validate_url(cls, v):
        """RSS URL 검증"""
        url = v.strip()

        if not url:
            raise ValueError("RSS URL이 필요합니다")

        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("올바른 URL 형식이 아닙니다")

        return url

    @validator("name")
    def validate_name(cls, v):
        """RSS 피드 이름 검증"""
        name = v.strip()

        if not name:
            raise ValueError("RSS 피드 이름이 필요합니다")

        # 특수 문자 제한
        import re

        if re.search(r'[<>"\';{}]', name):
            raise ValueError("이름에 허용되지 않는 문자가 포함되어 있습니다")

        return name


class HistoryRequest(BaseModel):
    """
    히스토리 조회 요청 모델
    사용자 요약 히스토리 조회
    """

    user_id: Optional[str] = Field(default=None, description="사용자 ID")

    date_from: Optional[datetime] = Field(default=None, description="조회 시작 날짜")

    date_to: Optional[datetime] = Field(default=None, description="조회 종료 날짜")

    limit: int = Field(default=20, ge=1, le=100, description="최대 조회 개수")

    offset: int = Field(default=0, ge=0, description="조회 시작 위치")

    search_query: Optional[str] = Field(
        default=None, max_length=200, description="히스토리 내 검색 쿼리"
    )


class RecommendationRequest(BaseModel):
    """
    추천 요청 모델
    사용자 맞춤 뉴스 추천 요청
    """

    user_interests: List[str] = Field(
        ..., min_items=1, max_items=20, description="사용자 관심사 키워드"
    )

    preferred_sources: Optional[List[str]] = Field(
        default=None, max_items=10, description="선호하는 뉴스 소스"
    )

    excluded_topics: Optional[List[str]] = Field(
        default=None, max_items=10, description="제외할 주제"
    )

    max_recommendations: int = Field(
        default=15, ge=1, le=50, description="최대 추천 수"
    )

    time_range: str = Field(default="24h", description="시간 범위 (1h, 6h, 24h, 7d)")

    @validator("user_interests")
    def validate_interests(cls, v):
        """관심사 키워드 검증"""
        if not v:
            raise ValueError("최소 하나의 관심사가 필요합니다")

        clean_interests = []
        for interest in v:
            clean_interest = interest.strip()
            if clean_interest and len(clean_interest) <= 50:
                clean_interests.append(clean_interest)

        if not clean_interests:
            raise ValueError("유효한 관심사가 없습니다")

        return clean_interests

    @validator("time_range")
    def validate_time_range(cls, v):
        """시간 범위 검증"""
        allowed_ranges = ["1h", "6h", "24h", "7d", "30d"]
        if v not in allowed_ranges:
            raise ValueError(f"시간 범위는 다음 중 하나여야 합니다: {allowed_ranges}")
        return v


class ConfigUpdateRequest(BaseModel):
    """
    설정 업데이트 요청 모델
    시스템 설정 변경 요청 (관리자용)
    """

    max_articles_per_source: Optional[int] = Field(
        default=None, ge=1, le=100, description="소스당 최대 기사 수"
    )

    rss_timeout: Optional[int] = Field(
        default=None, ge=5, le=300, description="RSS 타임아웃 (초)"
    )

    summary_max_length: Optional[int] = Field(
        default=None, ge=50, le=2000, description="요약 최대 길이"
    )

    openai_model: Optional[str] = Field(default=None, description="OpenAI 모델명")

    openai_temperature: Optional[float] = Field(
        default=None, ge=0.0, le=2.0, description="OpenAI 온도 설정"
    )

    log_level: Optional[str] = Field(default=None, description="로그 레벨")

    @validator("openai_model")
    def validate_openai_model(cls, v):
        """OpenAI 모델 검증"""
        if v is None:
            return v

        allowed_models = [
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-4",
            "gpt-4-32k",
            "gpt-4-turbo",
        ]

        if v not in allowed_models:
            raise ValueError(f"지원되는 모델: {allowed_models}")

        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        """로그 레벨 검증"""
        if v is None:
            return v

        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"로그 레벨은 다음 중 하나여야 합니다: {allowed_levels}")

        return v.upper()


# 공통 모델들
class PaginationParams(BaseModel):
    """페이지네이션 파라미터"""

    page: int = Field(default=1, ge=1, description="페이지 번호")
    size: int = Field(default=20, ge=1, le=100, description="페이지 크기")

    @property
    def offset(self) -> int:
        """오프셋 계산"""
        return (self.page - 1) * self.size


class SortParams(BaseModel):
    """정렬 파라미터"""

    sort_by: str = Field(default="created_at", description="정렬 필드")
    sort_order: str = Field(default="desc", description="정렬 순서")

    @validator("sort_order")
    def validate_sort_order(cls, v):
        """정렬 순서 검증"""
        if v.lower() not in ["asc", "desc"]:
            raise ValueError("정렬 순서는 'asc' 또는 'desc'여야 합니다")
        return v.lower()


if __name__ == "__main__":
    # 테스트 코드
    print("요청 스키마 테스트:")

    # SummarizeRequest 테스트
    try:
        request = SummarizeRequest(
            rss_urls=["https://feeds.bbci.co.uk/news/rss.xml"],
            max_articles=5,
            summary_style="compact",
            language="ko",
        )
        print(f"✅ SummarizeRequest 생성 성공: {request.rss_urls}")
    except Exception as e:
        print(f"❌ SummarizeRequest 실패: {e}")

    # TextSummarizeRequest 테스트
    try:
        text_request = TextSummarizeRequest(
            text="이것은 테스트를 위한 충분히 긴 텍스트입니다. 요약 기능을 테스트하기 위해 작성된 샘플 텍스트입니다.",
            summary_length=100,
            language="ko",
        )
        print(f"✅ TextSummarizeRequest 생성 성공")
    except Exception as e:
        print(f"❌ TextSummarizeRequest 실패: {e}")

    print("\n요청 스키마 테스트 완료!")
