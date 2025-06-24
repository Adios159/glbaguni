"""
Unit tests for security module
"""
import pytest


class TestSecurity:
    """Test security functions"""
    
    def test_validate_input_basic(self):
        """Test basic input validation"""
        try:
            from security import validate_input
            
            # Test normal text
            result = validate_input("안전한 텍스트입니다")
            assert result == "안전한 텍스트입니다"
            
        except ImportError:
            pytest.skip("Security module not available")
    
    def test_validate_input_xss_prevention(self):
        """Test XSS prevention in input validation"""
        try:
            from security import validate_input
            
            # Test potentially dangerous input
            dangerous_input = "<script>alert('xss')</script>일반 텍스트"
            result = validate_input(dangerous_input)
            
            # Should not contain script tags
            assert "<script>" not in result
            assert "일반 텍스트" in result
            
        except ImportError:
            pytest.skip("Security module not available")
    
    def test_sanitize_response_basic(self):
        """Test response sanitization"""
        try:
            from security import sanitize_response
            
            response_data = {
                "message": "정상적인 응답입니다",
                "data": ["항목1", "항목2"]
            }
            
            result = sanitize_response(response_data)
            assert isinstance(result, dict)
            assert "message" in result
            
        except ImportError:
            pytest.skip("Security module not available") 