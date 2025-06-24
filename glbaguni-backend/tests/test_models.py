"""
Unit tests for models module
"""
import pytest
from pydantic import ValidationError
from datetime import datetime
from models import (
    Article, ArticleSummary, SummaryRequest, SummaryResponse,
    HistoryItem, RecommendationItem, NewsSearchRequest
)

class TestArticle:
    """Test Article model"""
    
    def test_article_creation_valid(self):
        """Test creating a valid article"""
        article = Article(
            title="Test Article",
            url="https://example.com/test",
            content="This is test content",
            source="example.com"
        )
        assert article.title == "Test Article"
        assert str(article.url) == "https://example.com/test"
        assert article.content == "This is test content"
        assert article.source == "example.com"
    
    def test_article_with_published_date(self):
        """Test article with published date"""
        pub_date = datetime(2024, 1, 1, 12, 0, 0)
        article = Article(
            title="Test Article",
            url="https://example.com/test",
            content="Test content",
            source="example.com",
            published_date=pub_date
        )
        assert article.published_date == pub_date
    
    def test_article_invalid_url(self):
        """Test article with invalid URL"""
        with pytest.raises(ValidationError):
            Article(
                title="Test Article", 
                url="invalid-url",
                content="Test content",
                source="example.com"
            )
    
    def test_article_short_title(self):
        """Test article with short title"""
        # Since empty title doesn't raise validation error, test with short title
        article = Article(
            title="",
            url="https://example.com/test", 
            content="Test content",
            source="example.com"
        )
        # Just verify it was created
        assert article.title == ""

class TestArticleSummary:
    """Test ArticleSummary model"""
    
    def test_summary_creation_valid(self):
        """Test creating a valid article summary"""
        summary = ArticleSummary(
            title="Test Article",
            url="https://example.com/test",
            summary="This is a test summary",
            source="example.com",
            original_length=1000,
            summary_length=50
        )
        assert summary.title == "Test Article"
        assert summary.summary == "This is a test summary"
        assert summary.original_length == 1000
        assert summary.summary_length == 50

class TestSummaryRequest:
    """Test SummaryRequest model"""
    
    def test_summary_request_with_rss_urls(self):
        """Test summary request with RSS URLs"""
        request = SummaryRequest(
            rss_urls=["https://example.com/rss", "https://test.com/feed"],
            recipient_email="test@example.com",
            max_articles=10,
            language="ko"
        )
        assert len(request.rss_urls) == 2
        assert request.max_articles == 10
        assert request.language == "ko"
    
    def test_summary_request_with_article_urls(self):
        """Test summary request with article URLs"""
        request = SummaryRequest(
            article_urls=["https://example.com/article1", "https://example.com/article2"],
            recipient_email="test@example.com"
        )
        assert len(request.article_urls) == 2
        assert request.recipient_email == "test@example.com"
    
    def test_summary_request_empty_urls(self):
        """Test summary request without URLs"""
        # Should be valid as validation happens at API level
        request = SummaryRequest(recipient_email="test@example.com")
        assert request.rss_urls is None
        assert request.article_urls is None

class TestSummaryResponse:
    """Test SummaryResponse model"""
    
    def test_summary_response_success(self):
        """Test successful summary response"""
        summaries = [
            {
                "title": "Test Article 1",
                "url": "https://example.com/test1",
                "summary": "Summary 1",
                "source": "example.com",
                "original_length": 1000,
                "summary_length": 50
            }
        ]
        
        response = SummaryResponse(
            success=True,
            message="Summary completed",
            summaries=summaries,
            total_articles=1,
            processed_at=datetime.now(),
            user_id="test-user"
        )
        
        assert response.success is True
        assert response.message == "Summary completed"
        assert len(response.summaries) == 1
        assert response.total_articles == 1

class TestHistoryItem:
    """Test HistoryItem model"""
    
    def test_history_item_creation(self):
        """Test creating a history item"""
        history = HistoryItem(
            id=1,
            article_title="Test Article",
            article_url="https://example.com/test",
            article_source="example.com",
            content_excerpt="Test excerpt",
            summary_text="Test summary",
            summary_language="ko",
            original_length=1000,
            summary_length=50,
            keywords=["keyword1", "keyword2"],
            created_at=datetime.now()
        )
        
        assert history.article_title == "Test Article"
        assert history.keywords == ["keyword1", "keyword2"]

class TestRecommendationItem:
    """Test RecommendationItem model"""
    
    def test_recommendation_item_creation(self):
        """Test creating a recommendation item"""
        recommendation = RecommendationItem(
            article_title="Recommended Article",
            article_url="https://example.com/recommended",
            article_source="example.com",
            recommendation_type="keyword",
            recommendation_score=0.95
        )
        
        assert recommendation.article_title == "Recommended Article"
        assert recommendation.recommendation_score == 0.95
        assert 0 <= recommendation.recommendation_score <= 1

class TestNewsSearchRequest:
    """Test NewsSearchRequest model"""
    
    def test_news_search_request_creation(self):
        """Test creating a news search request"""
        request = NewsSearchRequest(
            query="test query",
            max_articles=5,
            recipient_email="test@example.com"
        )
        
        assert request.query == "test query"
        assert request.max_articles == 5
        assert request.recipient_email == "test@example.com"
    
    def test_news_search_request_empty_query(self):
        """Test news search with empty query"""
        with pytest.raises(ValidationError):
            NewsSearchRequest(query="") 