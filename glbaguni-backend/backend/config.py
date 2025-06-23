import os
from dotenv import load_dotenv
from typing import Optional
import logging

# Configure logging for config debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to load .env file from multiple possible locations
env_paths = [
    ".env",  # Current directory
    "../.env",  # Parent directory
    "../../.env",  # Two levels up
    os.path.join(os.path.dirname(__file__), "..", ".env"),  # Relative to this file
]

env_loaded = False
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
        logger.info(f"✅ Loaded .env file from: {os.path.abspath(env_path)}")
        env_loaded = True
        break

if not env_loaded:
    logger.warning("⚠️  No .env file found. Using default values.")
    logger.info(f"Searched in: {env_paths}")

class Settings:
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    # App Configuration
    DEFAULT_SUMMARY_LENGTH: int = int(os.getenv("DEFAULT_SUMMARY_LENGTH", "3"))
    MAX_ARTICLES_PER_REQUEST: int = int(os.getenv("MAX_ARTICLES_PER_REQUEST", "10"))
    
    # Summarization Prompt (customizable, Korean-optimized)
    SUMMARIZATION_PROMPT: str = os.getenv(
        "SUMMARIZATION_PROMPT", 
        "다음은 뉴스 기사입니다. 핵심 내용을 중심으로 3~4문장으로 간결하게 요약해 주세요. 중요한 사실과 정보에 집중하고, 불필요한 수사나 감정적 표현은 제외해 주세요."
    )
    
    def __init__(self):
        """Initialize settings and log debug information."""
        self.debug_environment_variables()
    
    def debug_environment_variables(self):
        """Print environment variables for debugging (without exposing sensitive data)."""
        logger.info("🔍 Environment Variables Debug:")
        logger.info(f"  OPENAI_API_KEY: {'✅ SET' if self.OPENAI_API_KEY else '❌ NOT SET'}")
        logger.info(f"  OPENAI_MODEL: {self.OPENAI_MODEL}")
        logger.info(f"  SMTP_HOST: {self.SMTP_HOST}")
        logger.info(f"  SMTP_PORT: {self.SMTP_PORT}")
        logger.info(f"  SMTP_USERNAME: {'✅ SET' if self.SMTP_USERNAME else '❌ NOT SET'}")
        logger.info(f"  SMTP_PASSWORD: {'✅ SET' if self.SMTP_PASSWORD else '❌ NOT SET'}")
        logger.info(f"  SMTP_USE_TLS: {self.SMTP_USE_TLS}")
        
        # Show actual values for non-sensitive variables
        if self.SMTP_USERNAME:
            logger.info(f"  SMTP_USERNAME value: {self.SMTP_USERNAME}")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required environment variables are set and secure."""
        instance = cls()
        
        # 보안 검증을 위해 security 모듈 임포트
        try:
            from .security import validate_api_key
        except ImportError:
            try:
                from security import validate_api_key
            except ImportError:
                logger.warning("⚠️ Security module not available. Skipping API key validation.")
                validate_api_key = lambda x: True  # type: ignore
        
        required_vars = [
            ("OPENAI_API_KEY", instance.OPENAI_API_KEY),
            ("SMTP_USERNAME", instance.SMTP_USERNAME),
            ("SMTP_PASSWORD", instance.SMTP_PASSWORD)
        ]
        
        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
        
        if missing_vars:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            logger.info("💡 Please create a .env file with the required variables.")
            logger.info("💡 You can copy env_template.txt to .env and fill in the values.")
            return False
        
        # OpenAI API 키 형식 검증
        if instance.OPENAI_API_KEY and not validate_api_key(instance.OPENAI_API_KEY):
            logger.error("❌ Invalid OpenAI API key format. Please check your API key.")
            return False
        
        logger.info("✅ All required environment variables are set and validated.")
        return True

# Global settings instance
settings = Settings()
