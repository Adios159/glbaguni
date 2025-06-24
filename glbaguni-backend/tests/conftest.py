"""
Pytest configuration and shared fixtures for glbaguni-backend tests
"""
import os
import sys
import pytest
from unittest.mock import Mock, AsyncMock
from typing import Generator, AsyncGenerator
import tempfile
import shutil

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

@pytest.fixture
def mock_env_vars() -> Generator[None, None, None]:
    """Mock environment variables for testing"""
    original_env = os.environ.copy()
    test_env = {
        "OPENAI_API_KEY": "sk-test-key-123456789",
        "SMTP_SERVER": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "test@example.com",
        "SMTP_PASSWORD": "test_password",
        "DATABASE_URL": "sqlite:///test.db"
    }
    
    os.environ.update(test_env)
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Create a temporary database file for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    yield db_path
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html; charset=utf-8"}
    mock_response.content = b"<html><body><h1>Test Article</h1><p>Test content</p></body></html>"
    mock_response.text = "<html><body><h1>Test Article</h1><p>Test content</p></body></html>"
    mock_client.get.return_value = mock_response
    return mock_client

@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed for testing"""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test News</title>
            <description>Test RSS Feed</description>
            <link>https://test.com</link>
            <item>
                <title>Test Article 1</title>
                <link>https://test.com/article1</link>
                <description>Test article description</description>
                <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
            </item>
            <item>
                <title>Test Article 2</title>
                <link>https://test.com/article2</link>
                <description>Another test article</description>
                <pubDate>Mon, 01 Jan 2024 13:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>"""

@pytest.fixture
def sample_article_data():
    """Sample article data for testing"""
    return {
        "title": "Test Article Title",
        "url": "https://example.com/test-article",
        "content": "This is a test article content with enough text to be considered valid content for testing purposes.",
        "source": "test.com",
        "published_date": None
    }

@pytest.fixture 
def mock_openai_client():
    """Mock OpenAI client for testing"""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "Test summary content"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client 