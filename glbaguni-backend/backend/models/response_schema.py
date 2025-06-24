#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
응답 스키마 정의
API 응답에 대한 Pydantic 모델들
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# 기본 응답 모델
class BaseResponse(BaseModel):
    """기본 응답 모델"""

    success: bool = Field(description="요청 성공 여부")
    message: str = Field(description="응답 메시지")
    timestamp: datetime = Field(default_factory=datetime.now, description="응답 시간")
    request_id: Optional[str] = Field(default=None, description="요청 ID")


class ErrorResponse(BaseResponse):
    """오류 응답 모델"""

    success: bool = Field(default=False, description="요청 성공 여부")
    error: Dict[str, Any] = Field(description="오류 정보")

    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "요청 처리 중 오류가 발생했습니다",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "details": "입력값이 올바르지 않습니다",
                },
                "timestamp": "2024-01-01T00:00:00",
                "request_id": "abc123",
            }
        }


# 공통 데이터 모델들
class Article(BaseModel):
    """뉴스 기사 모델"""

    title: str = Field(description="기사 제목")
    content: Optional[str] = Field(default=None, description="기사 내용")
    summary: Optional[str] = Field(default=None, description="기사 요약")
    url: str = Field(description="기사 URL")
    source: str = Field(description="뉴스 소스")
    published_at: Optional[datetime] = Field(default=None, description="발행 시간")
    category: Optional[str] = Field(default=None, description="카테고리")
    keywords: Optional[List[str]] = Field(default=None, description="키워드 목록")
    language: str = Field(default="ko", description="언어")

    class Config:
        schema_extra = {
            "example": {
                "title": "AI 기술의 최신 동향",
                "content": "인공지능 기술이 빠르게 발전하고 있습니다...",
                "summary": "AI 기술이 다양한 분야에서 혁신을 이끌고 있음",
                "url": "https://example.com/news/ai-trend",
                "source": "Tech News",
                "published_at": "2024-01-01T09:00:00",
                "category": "technology",
                "keywords": ["AI", "인공지능", "기술"],
                "language": "ko",
            }
        }


class Summary(BaseModel):
    """요약 결과 모델"""

    original_length: int = Field(description="원본 텍스트 길이")
    summary_length: int = Field(description="요약 텍스트 길이")
    summary_text: str = Field(description="요약 내용")
    key_points: Optional[List[str]] = Field(default=None, description="주요 포인트")
    keywords: Optional[List[str]] = Field(default=None, description="핵심 키워드")
    confidence_score: Optional[float] = Field(
        default=None, description="요약 신뢰도 점수"
    )
    language: str = Field(default="ko", description="요약 언어")
    style: str = Field(default="compact", description="요약 스타일")

    class Config:
        schema_extra = {
            "example": {
                "original_length": 1500,
                "summary_length": 200,
                "summary_text": "AI 기술이 다양한 분야에서 혁신을 이끌고 있으며...",
                "key_points": ["AI 기술 발전", "산업 혁신", "미래 전망"],
                "keywords": ["AI", "혁신", "기술"],
                "confidence_score": 0.85,
                "language": "ko",
                "style": "compact",
            }
        }


class RSSSource(BaseModel):
    """RSS 소스 모델"""

    id: Optional[int] = Field(default=None, description="RSS 소스 ID")
    name: str = Field(description="RSS 소스 이름")
    url: str = Field(description="RSS URL")
    category: str = Field(default="general", description="카테고리")
    language: str = Field(default="ko", description="언어")
    is_active: bool = Field(default=True, description="활성화 상태")
    last_updated: Optional[datetime] = Field(
        default=None, description="마지막 업데이트 시간"
    )
    article_count: Optional[int] = Field(default=0, description="수집된 기사 수")

    class Config:
        schema_extra = {
            "example": {
                "id": 1,
                "name": "BBC News Korea",
                "url": "https://feeds.bbci.co.uk/news/rss.xml",
                "category": "news",
                "language": "ko",
                "is_active": True,
                "last_updated": "2024-01-01T09:00:00",
                "article_count": 25,
            }
        }


# API 응답 모델들
class SummarizeResponse(BaseResponse):
    """뉴스 요약 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="요약 결과 데이터")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "뉴스 요약이 완료되었습니다",
                "data": {
                    "total_articles": 15,
                    "processed_articles": 12,
                    "failed_articles": 3,
                    "summary": {
                        "original_length": 12500,
                        "summary_length": 800,
                        "summary_text": "오늘의 주요 뉴스는...",
                        "key_points": ["주요 이슈 1", "주요 이슈 2"],
                        "keywords": ["정치", "경제", "사회"],
                        "confidence_score": 0.88,
                        "language": "ko",
                        "style": "compact",
                    },
                    "articles": [
                        {
                            "title": "뉴스 제목",
                            "url": "https://example.com/news/1",
                            "source": "News Source",
                            "summary": "기사 요약...",
                        }
                    ],
                    "sources": [
                        {
                            "name": "BBC News",
                            "url": "https://feeds.bbci.co.uk/news/rss.xml",
                            "articles_count": 8,
                            "success_rate": 0.8,
                        }
                    ],
                    "processing_time": 45.2,
                    "generated_at": "2024-01-01T09:00:00",
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "req_123",
            }
        }


class TextSummarizeResponse(BaseResponse):
    """텍스트 요약 응답 모델"""

    success: bool = Field(default=True)
    data: Summary = Field(description="요약 결과")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "텍스트 요약이 완료되었습니다",
                "data": {
                    "original_length": 1500,
                    "summary_length": 200,
                    "summary_text": "제공된 텍스트의 주요 내용은...",
                    "key_points": ["포인트 1", "포인트 2"],
                    "keywords": ["키워드1", "키워드2"],
                    "confidence_score": 0.92,
                    "language": "ko",
                    "style": "compact",
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "req_456",
            }
        }


class NewsSearchResponse(BaseResponse):
    """뉴스 검색 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="검색 결과 데이터")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "뉴스 검색이 완료되었습니다",
                "data": {
                    "query": "AI 기술",
                    "total_results": 45,
                    "returned_results": 20,
                    "articles": [
                        {
                            "title": "AI 기술의 미래",
                            "content": "AI 기술이 빠르게 발전하고 있습니다...",
                            "url": "https://example.com/ai-future",
                            "source": "Tech Today",
                            "published_at": "2024-01-01T08:00:00",
                            "relevance_score": 0.95,
                        }
                    ],
                    "search_time": 2.1,
                    "filters": {
                        "date_from": "2024-01-01",
                        "date_to": "2024-01-02",
                        "sources": ["Tech Today", "AI News"],
                    },
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "req_789",
            }
        }


class HistoryResponse(BaseResponse):
    """히스토리 조회 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="히스토리 데이터")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "히스토리 조회가 완료되었습니다",
                "data": {
                    "total_count": 150,
                    "returned_count": 20,
                    "current_page": 1,
                    "total_pages": 8,
                    "history": [
                        {
                            "id": "hist_001",
                            "request_type": "summarize",
                            "summary": "뉴스 요약 결과...",
                            "articles_count": 12,
                            "sources": ["BBC", "Reuters"],
                            "created_at": "2024-01-01T09:00:00",
                            "processing_time": 35.2,
                        }
                    ],
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "req_hist",
            }
        }


class RecommendationResponse(BaseResponse):
    """추천 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="추천 결과 데이터")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "개인화된 뉴스 추천이 완료되었습니다",
                "data": {
                    "user_interests": ["AI", "기술", "혁신"],
                    "recommendation_count": 15,
                    "articles": [
                        {
                            "title": "추천 뉴스 제목",
                            "url": "https://example.com/recommended",
                            "source": "Tech News",
                            "relevance_score": 0.92,
                            "reason": "사용자의 AI 관심사와 높은 연관성",
                            "published_at": "2024-01-01T08:30:00",
                        }
                    ],
                    "generated_at": "2024-01-01T09:00:00",
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "req_recommend",
            }
        }


class HealthCheckResponse(BaseResponse):
    """헬스 체크 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="시스템 상태 정보")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "시스템이 정상적으로 작동 중입니다",
                "data": {
                    "status": "healthy",
                    "version": "3.0.0",
                    "uptime": "2 days, 3 hours, 45 minutes",
                    "environment": "production",
                    "services": {
                        "database": {"status": "connected", "response_time": 0.05},
                        "openai": {"status": "connected", "response_time": 0.8},
                        "rss_feeds": {"status": "operational", "active_feeds": 25},
                    },
                    "resources": {
                        "cpu_usage": 15.2,
                        "memory_usage": 512.7,
                        "disk_usage": 45.6,
                    },
                    "statistics": {
                        "total_requests": 15420,
                        "successful_requests": 14856,
                        "error_rate": 0.037,
                    },
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "health_check",
            }
        }


class DebugResponse(BaseResponse):
    """디버그 정보 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="디버그 정보")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "디버그 정보를 반환합니다",
                "data": {
                    "system_info": {
                        "python_version": "3.9.7",
                        "platform": "Linux",
                        "hostname": "server-001",
                    },
                    "environment_variables": {
                        "ENVIRONMENT": "development",
                        "LOG_LEVEL": "DEBUG",
                        "OPENAI_MODEL": "gpt-3.5-turbo",
                    },
                    "recent_logs": [
                        "2024-01-01 09:00:00 | INFO | Request processed successfully",
                        "2024-01-01 08:59:55 | DEBUG | Starting RSS feed collection",
                    ],
                    "active_connections": 5,
                    "cache_status": {
                        "total_entries": 120,
                        "hit_rate": 0.78,
                        "memory_usage": "45MB",
                    },
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "debug_info",
            }
        }


class RSSManagementResponse(BaseResponse):
    """RSS 관리 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="RSS 관리 결과")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "RSS 피드가 성공적으로 추가되었습니다",
                "data": {
                    "rss_source": {
                        "id": 26,
                        "name": "New Tech Feed",
                        "url": "https://example.com/rss",
                        "category": "technology",
                        "is_active": True,
                        "created_at": "2024-01-01T09:00:00",
                    },
                    "validation_result": {
                        "is_valid": True,
                        "article_count": 15,
                        "last_updated": "2024-01-01T08:45:00",
                    },
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "rss_add",
            }
        }


class ConfigResponse(BaseResponse):
    """설정 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="설정 정보")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "현재 설정 정보입니다",
                "data": {
                    "current_config": {
                        "max_articles_per_source": 10,
                        "rss_timeout": 30,
                        "summary_max_length": 300,
                        "openai_model": "gpt-3.5-turbo",
                        "openai_temperature": 0.7,
                        "log_level": "INFO",
                    },
                    "allowed_models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                    "last_updated": "2024-01-01T08:00:00",
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "config_get",
            }
        }


# 페이지네이션을 위한 응답 모델
class PaginatedResponse(BaseResponse):
    """페이지네이션이 적용된 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="페이지네이션된 데이터")
    pagination: Dict[str, Any] = Field(description="페이지네이션 정보")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "데이터 조회가 완료되었습니다",
                "data": {"items": []},
                "pagination": {
                    "current_page": 1,
                    "total_pages": 10,
                    "total_items": 195,
                    "items_per_page": 20,
                    "has_next": True,
                    "has_previous": False,
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "paginated",
            }
        }


# 통계 응답 모델
class StatisticsResponse(BaseResponse):
    """통계 정보 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="통계 데이터")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "통계 정보를 반환합니다",
                "data": {
                    "period": "last_30_days",
                    "summary_requests": 1250,
                    "successful_requests": 1198,
                    "failed_requests": 52,
                    "success_rate": 0.958,
                    "average_processing_time": 28.5,
                    "popular_sources": [
                        {"name": "BBC News", "requests": 245},
                        {"name": "Reuters", "requests": 198},
                    ],
                    "daily_stats": [
                        {"date": "2024-01-01", "requests": 45, "success_rate": 0.96}
                    ],
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "stats",
            }
        }


# 업로드 응답 모델
class UploadResponse(BaseResponse):
    """파일 업로드 응답 모델"""

    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(description="업로드 결과")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "파일이 성공적으로 업로드되었습니다",
                "data": {
                    "file_id": "upload_123",
                    "filename": "news_data.csv",
                    "file_size": 2048576,
                    "content_type": "text/csv",
                    "upload_time": "2024-01-01T09:00:00",
                    "processing_status": "completed",
                    "processed_records": 150,
                },
                "timestamp": "2024-01-01T09:00:00",
                "request_id": "upload",
            }
        }


if __name__ == "__main__":
    # 테스트 코드
    print("응답 스키마 테스트:")

    # SummarizeResponse 테스트
    try:
        response = SummarizeResponse(
            success=True,
            message="요약 완료",
            data={
                "total_articles": 10,
                "summary": {
                    "summary_text": "테스트 요약",
                    "original_length": 1000,
                    "summary_length": 100,
                },
            },
        )
        print(f"✅ SummarizeResponse 생성 성공: {response.success}")
    except Exception as e:
        print(f"❌ SummarizeResponse 실패: {e}")

    # Article 모델 테스트
    try:
        article = Article(
            title="테스트 기사", url="https://example.com/test", source="Test Source"
        )
        print(f"✅ Article 모델 생성 성공: {article.title}")
    except Exception as e:
        print(f"❌ Article 모델 실패: {e}")

    print("\n응답 스키마 테스트 완료!")
