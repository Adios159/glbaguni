import uuid
from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, HttpUrl, field_validator
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
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
