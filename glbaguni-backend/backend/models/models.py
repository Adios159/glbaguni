import re
import uuid
from datetime import datetime, date
from typing import List, Optional, Union

from pydantic import BaseModel, HttpUrl, field_validator
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Try to import EmailStr, fallback to str if not available
try:
    from pydantic import EmailStr

    EmailType = EmailStr
except ImportError:
    EmailType = str

# SQLAlchemy Base for database models
Base = declarative_base()


# Database Models
class User(Base):
    """SQLAlchemy model for user authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    birth_year = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)  # '남성', '여성', '선택 안함'
    interests = Column(JSON, nullable=True)  # 배열 저장
    created_at = Column(DateTime, default=datetime.utcnow)


class UserHistory(Base):
    """SQLAlchemy model for user summary history."""

    __tablename__ = "user_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # UUID for user identification
    article_title = Column(String, index=True)
    article_url = Column(String, index=True)
    article_source = Column(String, index=True)
    content_excerpt = Column(Text)  # First 500 chars of content
    summary_text = Column(Text)
    summary_language = Column(String, default="en")  # "ko" or "en"
    original_length = Column(Integer)
    summary_length = Column(Integer)
    keywords = Column(Text)  # JSON string of extracted keywords
    category = Column(String, nullable=True)  # Article category if available
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with recommendations
    recommendations = relationship("RecommendationLog", back_populates="history_item")


class RecommendationLog(Base):
    """SQLAlchemy model for recommendation tracking."""

    __tablename__ = "recommendation_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    history_item_id = Column(Integer, ForeignKey("user_history.id"), nullable=True)
    recommended_article_url = Column(String)
    recommended_article_title = Column(String)
    recommendation_type = Column(String)  # "keyword", "category", "trending"
    recommendation_score = Column(Float)
    clicked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with history
    history_item = relationship("UserHistory", back_populates="recommendations")


class UserPreferences(Base):
    """SQLAlchemy model for user preferences."""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    preferred_language = Column(String, default="en")
    preferred_categories = Column(Text)  # JSON string of preferred categories
    email_notifications = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# New models for news search functionality
class NewsSearchRequest(BaseModel):
    """Request model for natural language news search."""

    query: str  # Natural language query like "요즘 반도체 뉴스 알려줘"
    max_articles: Optional[int] = 10
    language: Optional[str] = "ko"  # Language for summarization
    recipient_email: Optional[EmailType] = None  # Optional email for results
    user_id: Optional[str] = None  # User identifier for history tracking

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        """Validate query is not empty."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        """Validate and normalize language code."""
        if v is None:
            return "ko"
        v = v.lower().strip()
        if v in ["ko", "kr", "korean"]:
            return "ko"
        elif v in ["en", "english"]:
            return "en"
        else:
            return "ko"  # Default to Korean for Korean news search


class NewsSearchResponse(BaseModel):
    """Response model for news search endpoint."""

    success: bool
    message: str
    articles: Optional[List[dict]] = None
    total_articles: int = 0
    extracted_keywords: Optional[List[str]] = None
    processed_at: datetime
    user_id: Optional[str] = None


# Pydantic Models (existing ones remain the same)
class Article(BaseModel):
    """Represents a single article from RSS feed or URL."""

    title: str
    url: HttpUrl
    content: str
    published_date: Optional[datetime] = None
    author: Optional[str] = None
    source: str


class SummaryRequest(BaseModel):
    """Request model for summarization endpoint."""

    rss_urls: Optional[List[HttpUrl]] = None
    article_urls: Optional[List[HttpUrl]] = None
    recipient_email: EmailType
    custom_prompt: Optional[str] = None
    max_articles: Optional[int] = 10
    language: Optional[str] = (
        "en"  # Language for summarization: "ko" for Korean, "en" for English
    )
    user_id: Optional[str] = None  # User identifier for history tracking

    @field_validator("recipient_email")
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if not v or "@" not in v:
            raise ValueError("Invalid email format")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        """Validate and normalize language code."""
        if v is None:
            return "en"
        v = v.lower().strip()
        # Allow common language codes, default to English if invalid
        valid_languages = ["ko", "en", "kr", "english", "korean"]
        if v in ["ko", "kr", "korean"]:
            return "ko"
        elif v in ["en", "english"]:
            return "en"
        else:
            return "en"  # Default to English for unknown codes


class SummaryResponse(BaseModel):
    """Response model for summarization endpoint."""

    success: bool
    message: str
    summaries: Optional[List[dict]] = None
    total_articles: int = 0
    processed_at: datetime
    user_id: Optional[str] = None  # Return user ID for tracking


class ArticleSummary(BaseModel):
    """Represents a summarized article."""

    title: str
    url: HttpUrl
    summary: str
    source: str
    original_length: int
    summary_length: int


class EmailNotification(BaseModel):
    """Email notification configuration."""

    recipient: EmailType
    subject: str
    body: str
    html_body: Optional[str] = None

    @field_validator("recipient")
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if not v or "@" not in v:
            raise ValueError("Invalid email format")
        return v


# New Pydantic Models for API responses
class HistoryItem(BaseModel):
    """Pydantic model for history API response."""

    id: int
    article_title: str
    article_url: str
    article_source: str
    content_excerpt: str
    summary_text: str
    summary_language: str
    original_length: int
    summary_length: int
    keywords: Optional[List[str]] = None
    category: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class HistoryResponse(BaseModel):
    """Response model for user history endpoint."""

    success: bool
    history: List[HistoryItem]
    total_items: int
    page: int
    per_page: int


class RecommendationItem(BaseModel):
    """Pydantic model for recommendation API response."""

    article_title: str
    article_url: str
    article_source: str
    recommendation_type: str
    recommendation_score: float
    keywords: Optional[List[str]] = None
    category: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Response model for recommendations endpoint."""

    success: bool
    recommendations: List[RecommendationItem]
    total_recommendations: int
    recommendation_types: List[str]


class UserStatsResponse(BaseModel):
    """Response model for user statistics."""

    success: bool
    user_id: str
    total_summaries: int
    preferred_language: str
    favorite_categories: List[str]
    recent_activity: List[HistoryItem]
    recommendations_count: int


# User Authentication Schemas
class UserCreate(BaseModel):
    """Request model for user registration."""

    username: str
    email: str
    password: str
    birth_year: Optional[int] = None
    gender: Optional[str] = None
    interests: Optional[List[str]] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username format and requirements."""
        if not v or not isinstance(v, str):
            raise ValueError("사용자명은 필수입니다")
        
        v = v.strip()
        if len(v) < 3:
            raise ValueError("사용자명은 3자 이상이어야 합니다")
        if len(v) > 30:
            raise ValueError("사용자명은 30자 이하여야 합니다")
        
        # 영문, 숫자, 언더스코어만 허용
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError("사용자명은 영문, 숫자, 언더스코어(_)만 사용 가능합니다")
        
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        if not v or not isinstance(v, str):
            raise ValueError("이메일은 필수입니다")
        
        v = v.strip().lower()
        if not v:
            raise ValueError("이메일은 필수입니다")
        
        # 기본적인 이메일 형식 검증
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("올바른 이메일 형식이 아닙니다")
        
        return v

    @field_validator("birth_year")
    @classmethod
    def validate_birth_year(cls, v):
        """Validate birth year."""
        if v is None:
            return v
        
        if not isinstance(v, int):
            raise ValueError("출생년도는 숫자여야 합니다")
        
        current_year = datetime.now().year
        if v < 1900 or v > current_year:
            raise ValueError(f"출생년도는 1900년부터 {current_year}년까지 입력 가능합니다")
        
        # 만 14세 미만 가입 제한
        age = current_year - v
        if age < 14:
            raise ValueError("만 14세 이상만 가입 가능합니다")
        
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        """Validate gender value."""
        if v is None or v == "":
            return None
        
        valid_genders = ["남성", "여성", "선택 안함"]
        if v not in valid_genders:
            raise ValueError(f"성별은 {', '.join(valid_genders)} 중 하나여야 합니다")
        
        return v

    @field_validator("interests")
    @classmethod
    def validate_interests(cls, v):
        """Validate interests list."""
        if v is None:
            return []
        
        if not isinstance(v, list):
            raise ValueError("관심사는 배열이어야 합니다")
        
        if len(v) > 10:
            raise ValueError("관심사는 최대 10개까지 선택 가능합니다")
        
        # 유효한 관심사 목록
        valid_interests = [
            "음악", "산책", "글쓰기", "독서", "영화", "운동", "요리", "여행", 
            "게임", "그림", "사진", "춤", "노래", "악기연주", "프로그래밍",
            "언어학습", "반려동물", "가드닝", "수공예", "명상"
        ]
        
        for interest in v:
            if not isinstance(interest, str):
                raise ValueError("관심사는 문자열이어야 합니다")
            if interest not in valid_interests:
                raise ValueError(f"유효하지 않은 관심사: {interest}")
        
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate password strength."""
        if not v or not isinstance(v, str):
            raise ValueError("비밀번호는 필수입니다")
        
        if len(v) < 10:
            raise ValueError("비밀번호는 최소 10자 이상이어야 합니다")
        if len(v) > 128:
            raise ValueError("비밀번호는 128자 이하여야 합니다")
        
        # 대문자 포함 검증
        if not re.search(r'[A-Z]', v):
            raise ValueError("비밀번호에 영어 대문자가 1개 이상 포함되어야 합니다")
        
        # 특수문자 포함 검증
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError("비밀번호에 특수문자가 1개 이상 포함되어야 합니다")
        
        return v


class UserRead(BaseModel):
    """Response model for user data."""

    id: int
    username: str
    email: str
    birth_year: Optional[int] = None
    gender: Optional[str] = None
    interests: Optional[List[str]] = None

    class Config:
        from_attributes = True
