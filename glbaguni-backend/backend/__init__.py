"""
글바구니 (Glbaguni) - AI RSS Summarizer Backend

A FastAPI-based backend service for AI-powered RSS feed summarization.
"""

__version__ = "1.0.0"
__author__ = "Glbaguni Team"

from backend.config import settings
from backend.fetcher import ArticleFetcher
from backend.main import app
from backend.models import (
    Article,
    ArticleSummary,
    EmailNotification,
    SummaryRequest,
    SummaryResponse,
)
from backend.notifier import EmailNotifier
from backend.summarizer import ArticleSummarizer

__all__ = [
    "app",
    "ArticleFetcher",
    "ArticleSummarizer",
    "EmailNotifier",
    "Article",
    "SummaryRequest",
    "SummaryResponse",
    "ArticleSummary",
    "EmailNotification",
    "settings",
]
