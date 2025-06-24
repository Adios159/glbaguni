"""
Unit tests for summarizer module
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock


class TestArticleSummarizer:
    """Test ArticleSummarizer class"""
    
    @pytest.fixture
    def summarizer(self):
        """Create ArticleSummarizer instance for testing"""
        try:
            from summarizer import ArticleSummarizer
            return ArticleSummarizer()
        except ImportError:
            pytest.skip("Summarizer module not available")
    
    @patch('summarizer.openai.ChatCompletion.create')
    async def test_summarize_success(self, mock_openai, summarizer):
        """Test successful summarization"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = {"content": "요약된 내용입니다."}
        mock_openai.return_value = mock_response
        
        text = "이것은 긴 텍스트입니다. 요약이 필요합니다. 여러 문장으로 구성되어 있습니다."
        result = await summarizer.summarize(text, language="ko")
        
        assert isinstance(result, (str, dict))
        if isinstance(result, dict):
            assert "summary" in result
        
    async def test_summarize_empty_text(self, summarizer):
        """Test summarization with empty text"""
        result = await summarizer.summarize("", language="ko")
        
        # Should handle empty input gracefully
        assert result is not None
    
    async def test_summarize_short_text(self, summarizer):
        """Test summarization with very short text"""
        short_text = "짧은 텍스트"
        result = await summarizer.summarize(short_text, language="ko")
        
        # Should handle short text appropriately
        assert result is not None 