"""
Models package for glbaguni backend.
Contains data models and schema definitions.
"""

from .request_schema import *
from .response_schema import *

# Import all models from the local models module (avoiding circular imports)
from .models import (
    # Database Models (SQLAlchemy)
    Base,
    User,
    UserHistory,
    RecommendationLog,
    UserPreferences,
    SummaryFeedback,
    # Pydantic Models
    Article,
    ArticleSummary,
    EmailNotification,
    SummaryRequest,
    SummaryResponse,
    NewsSearchRequest,
    NewsSearchResponse,
    HistoryItem,
    HistoryResponse,
    RecommendationItem,
    RecommendationResponse,
    UserStatsResponse,
    # Feedback Models
    SummaryFeedbackRequest,
    SummaryFeedbackResponse,
    FeedbackStatsResponse,
    # User Authentication Schemas
    UserCreate,
    UserRead,
)

__all__ = [
    # Schema models from submodules
    "SummaryRequest",
    "TextSummaryRequest",
    "NewsSearchRequest", 
    "Article",
    "Summary",
    "SummaryResponse",
    "NewsSearchResponse",
    "HistoryResponse",
    "RecommendationResponse",
    "UserStatsResponse",
    # Database models from local models module
    "Base",
    "User",
    "UserHistory",
    "RecommendationLog", 
    "UserPreferences",
    "SummaryFeedback",
    # Additional Pydantic models from local models module
    "ArticleSummary",
    "EmailNotification",
    "HistoryItem",
    "RecommendationItem",
    # Feedback models
    "SummaryFeedbackRequest",
    "SummaryFeedbackResponse", 
    "FeedbackStatsResponse",
    # User Authentication Schemas
    "UserCreate",
    "UserRead",
] 