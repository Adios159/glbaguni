"""
글바구니 (Glbaguni) - AI RSS Summarizer Backend

A FastAPI-based backend service for AI-powered RSS feed summarization.
"""

__version__ = "1.0.0"
__author__ = "Glbaguni Team"

from .main import app
from .fetcher import ArticleFetcher
from .summarizer import ArticleSummarizer
from .notifier import EmailNotifier
from .models import Article, SummaryRequest, SummaryResponse, ArticleSummary, EmailNotification
from .config import settings

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
    "settings"
] 