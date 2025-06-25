#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
애플리케이션 설정 관리 모듈
환경 변수를 안전하게 로드하고 검증
"""

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings

try:
    from utils.logging_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("config.settings")


class Settings(BaseSettings):
    """
    애플리케이션 설정 클래스
    환경 변수와 .env 파일에서 설정을 로드
    """

    # 기본 애플리케이션 설정
    app_name: str = Field(
        default="글바구니 뉴스 요약 서비스", description="애플리케이션 이름"
    )
    app_version: str = Field(default="3.0.0", description="애플리케이션 버전")
    environment: str = Field(default="production", description="실행 환경")
    debug: bool = Field(default=False, description="디버그 모드")

    # 서버 설정
    host: str = Field(default="0.0.0.0", description="서버 호스트")
    port: int = Field(default=8003, description="서버 포트")
    reload: bool = Field(default=False, description="개발 모드 자동 재시작")

    # 보안 설정
    secret_key: str = Field(default="glbaguni-default-secret-key-change-in-production", description="애플리케이션 비밀 키")
    api_key_header: str = Field(default="X-API-Key", description="API 키 헤더명")
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="CORS 허용 오리진"
    )

    # 외부 API 설정
    openai_api_key: str = Field(..., description="OpenAI API 키")
    openai_model: str = Field(default="gpt-3.5-turbo", description="OpenAI 모델명")
    openai_max_tokens: int = Field(default=1000, description="OpenAI 최대 토큰 수")
    openai_temperature: float = Field(default=0.7, description="OpenAI 온도 설정")

    # 데이터베이스 설정
    database_url: str = Field(
        default="sqlite:///glbaguni.db", description="데이터베이스 URL"
    )
    database_echo: bool = Field(default=False, description="SQL 쿼리 로깅")

    # RSS 및 크롤링 설정
    max_articles_per_source: int = Field(default=10, description="소스당 최대 기사 수")
    rss_timeout: int = Field(default=30, description="RSS 요청 타임아웃 (초)")
    crawling_timeout: int = Field(default=15, description="크롤링 요청 타임아웃 (초)")
    max_concurrent_requests: int = Field(default=5, description="동시 요청 수")

    # 요약 설정
    summary_max_length: int = Field(default=300, description="요약 최대 길이")
    summary_language: str = Field(default="ko", description="요약 언어")

    # 로깅 설정
    log_level: str = Field(default="INFO", description="로그 레벨")
    log_dir: str = Field(default="logs", description="로그 디렉토리")
    log_rotation_size: str = Field(default="10MB", description="로그 파일 회전 크기")
    log_retention_days: int = Field(default=30, description="로그 보존 기간 (일)")

    # 캐싱 설정
    cache_ttl: int = Field(default=3600, description="캐시 TTL (초)")
    cache_max_size: int = Field(default=1000, description="캐시 최대 크기")

    # Rate Limiting 설정
    rate_limit_enabled: bool = Field(default=True, description="Rate Limiting 활성화")
    rate_limit_requests_per_minute: int = Field(default=60, description="분당 허용 요청 수")
    rate_limit_requests_per_hour: int = Field(default=1000, description="시간당 허용 요청 수")
    rate_limit_requests_per_day: int = Field(default=10000, description="일일 허용 요청 수")
    rate_limit_window_size: int = Field(default=60, description="Rate Limit 윈도우 크기 (초)")
    
    # User-Agent 검증 설정
    user_agent_validation_enabled: bool = Field(default=True, description="User-Agent 검증 활성화")
    user_agent_security_level: str = Field(default="moderate", description="보안 레벨 (permissive/moderate/strict/lockdown)")
    user_agent_block_message: str = Field(
        default="요청이 차단되었습니다. 올바른 클라이언트를 사용해주세요.", 
        description="차단 시 표시할 메시지"
    )
    
    # CAPTCHA 설정
    captcha_enabled: bool = Field(default=True, description="CAPTCHA 기능 활성화")
    captcha_protection_level: str = Field(default="medium", description="CAPTCHA 보호 레벨")
    recaptcha_site_key: Optional[str] = Field(default=None, description="Google reCAPTCHA 사이트 키")
    recaptcha_secret_key: Optional[str] = Field(default=None, description="Google reCAPTCHA 비밀 키")
    recaptcha_version: str = Field(default="v2", description="reCAPTCHA 버전 (v2/v3)")
    recaptcha_threshold: float = Field(default=0.5, description="reCAPTCHA v3 스코어 임계값")
    
    # 봇 방지 설정
    simple_math_enabled: bool = Field(default=True, description="간단한 수학 문제 활성화")
    logic_check_enabled: bool = Field(default=True, description="로직 체크 활성화")
    honeypot_enabled: bool = Field(default=True, description="허니팟 필드 활성화")
    max_captcha_failures: int = Field(default=5, description="CAPTCHA 최대 실패 횟수")
    captcha_lockout_minutes: int = Field(default=30, description="CAPTCHA 실패 시 잠금 시간(분)")
    
    # Redis 설정 (Rate Limiting 및 캐싱용)
    redis_enabled: bool = Field(default=False, description="Redis 사용 여부")
    redis_host: str = Field(default="localhost", description="Redis 호스트")
    redis_port: int = Field(default=6379, description="Redis 포트")
    redis_db: int = Field(default=0, description="Redis 데이터베이스 번호")
    redis_password: Optional[str] = Field(default=None, description="Redis 비밀번호")
    redis_max_connections: int = Field(default=10, description="Redis 최대 연결 수")

    # 이메일 설정 (선택사항)
    smtp_server: Optional[str] = Field(default=None, description="SMTP 서버")
    smtp_port: Optional[int] = Field(default=587, description="SMTP 포트")
    smtp_username: Optional[str] = Field(default=None, description="SMTP 사용자명")
    smtp_password: Optional[str] = Field(default=None, description="SMTP 비밀번호")
    smtp_use_tls: bool = Field(default=True, description="SMTP TLS 사용")

    # 파일 업로드 설정
    upload_max_size: int = Field(
        default=10 * 1024 * 1024, description="업로드 최대 크기 (바이트)"
    )
    upload_allowed_extensions: List[str] = Field(
        default=["txt", "json", "csv"], description="허용된 업로드 파일 확장자"
    )

    # ===== IP 차단 시스템 설정 =====
    # IP 차단 기능 활성화
    IP_BLOCKER_ENABLED: bool = Field(default=True, description="IP 차단 기능 활성화")

    # Redis 연결 설정
    IP_BLOCKER_REDIS_ENABLED: bool = Field(default=False, description="Redis 사용 여부")
    IP_BLOCKER_REDIS_HOST: str = Field(default="localhost", description="Redis 호스트")
    IP_BLOCKER_REDIS_PORT: int = Field(default=6379, description="Redis 포트")
    IP_BLOCKER_REDIS_DB: int = Field(default=1, description="Redis 데이터베이스 번호")
    IP_BLOCKER_REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis 비밀번호")

    # 패턴 감지 설정
    IP_BLOCKER_ANALYSIS_WINDOW_MINUTES: int = Field(default=15, description="패턴 감지 분석 윈도우 (분)")
    IP_BLOCKER_SUSPICIOUS_REQUEST_COUNT: int = Field(default=100, description="의심 요청 수")
    IP_BLOCKER_RAPID_REQUEST_THRESHOLD: int = Field(default=20, description="급증 요청 임계값")

    # 차단 임계값
    IP_BLOCKER_FAILED_AUTH_THRESHOLD: int = Field(default=10, description="인증 실패 임계값")
    IP_BLOCKER_CAPTCHA_FAILURE_THRESHOLD: int = Field(default=5, description="CAPTCHA 실패 임계값")
    IP_BLOCKER_ENDPOINT_SCAN_THRESHOLD: int = Field(default=20, description="엔드포인트 스캔 임계값")
    IP_BLOCKER_DIFFERENT_UA_THRESHOLD: int = Field(default=10, description="다른 User-Agent 임계값")

    # 차단 시간 (초)
    IP_BLOCKER_LOW_THREAT_BLOCK_TIME: int = Field(default=900, description="낮은 위험 차단 시간 (초)")
    IP_BLOCKER_MEDIUM_THREAT_BLOCK_TIME: int = Field(default=3600, description="중간 위험 차단 시간 (초)")
    IP_BLOCKER_HIGH_THREAT_BLOCK_TIME: int = Field(default=7200, description="높은 위험 차단 시간 (초)")
    IP_BLOCKER_CRITICAL_THREAT_BLOCK_TIME: int = Field(default=86400, description="심각한 위험 차단 시간 (초)")

    # 화이트리스트 IP (쉼표로 구분)
    IP_BLOCKER_WHITELIST_IPS: str = Field(default="127.0.0.1,::1,localhost", description="화이트리스트 IP")

    # ===== 요청 로깅 시스템 설정 =====
    # 요청 로깅 기능 활성화
    REQUEST_LOGGER_ENABLED: bool = Field(default=True, description="요청 로깅 기능 활성화")
    
    # 로그 저장 설정
    REQUEST_LOGGER_LOG_DIR: str = Field(default="logs/requests", description="로그 저장 디렉토리")
    REQUEST_LOGGER_LOG_FORMATS: str = Field(default="json,csv", description="로그 형식 (쉼표로 구분)")
    REQUEST_LOGGER_MAX_LOG_SIZE_MB: int = Field(default=100, description="최대 로그 파일 크기 (MB)")
    REQUEST_LOGGER_MAX_LOG_FILES: int = Field(default=30, description="최대 로그 파일 수")
    REQUEST_LOGGER_RETENTION_DAYS: int = Field(default=30, description="로그 보존 기간 (일)")
    
    # 데이터베이스 저장 설정
    REQUEST_LOGGER_DATABASE_ENABLED: bool = Field(default=False, description="데이터베이스 저장 활성화")
    REQUEST_LOGGER_DATABASE_PATH: str = Field(default="logs/requests.db", description="데이터베이스 파일 경로")
    
    # 제외할 경로 (쉼표로 구분)
    REQUEST_LOGGER_EXCLUDE_PATHS: str = Field(
        default="/docs,/redoc,/openapi.json,/static/,/favicon.ico,/health,/metrics",
        description="로깅에서 제외할 경로"
    )
    
    # 추가 로깅 옵션
    REQUEST_LOGGER_INCLUDE_REQUEST_BODY: bool = Field(default=False, description="요청 본문 포함")
    REQUEST_LOGGER_INCLUDE_RESPONSE_BODY: bool = Field(default=False, description="응답 본문 포함")
    REQUEST_LOGGER_COMPRESS_OLD_LOGS: bool = Field(default=True, description="오래된 로그 압축")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 추가 필드 무시

        # 환경 변수 접두사
        env_prefix = ""

    # 검증자들
    @validator("environment")
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"environment must be one of {allowed}")
        return v.lower()

    @validator("log_level")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v.upper()

    @validator("openai_model")
    def validate_openai_model(cls, v):
        allowed_models = [
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
            "gpt-4",
            "gpt-4-32k",
            "gpt-4-turbo",
        ]
        if v not in allowed_models:
            logger.warning(f"Unknown OpenAI model: {v}. Allowed: {allowed_models}")
        return v

    @validator("port")
    def validate_port(cls, v):
        if not (1 <= v <= 65535):
            raise ValueError("port must be between 1 and 65535")
        return v

    @validator("openai_temperature")
    def validate_temperature(cls, v):
        if not (0.0 <= v <= 2.0):
            raise ValueError("openai_temperature must be between 0.0 and 2.0")
        return v

    @validator("openai_max_tokens")
    def validate_max_tokens(cls, v):
        if v <= 0:
            raise ValueError("openai_max_tokens must be positive")
        return v

    @validator("allowed_origins")
    def validate_cors_origins(cls, v):
        """CORS 허용 오리진 검증"""
        if "*" in v:
            logger.warning("⚠️  CORS에서 모든 도메인(*)을 허용하고 있습니다. 보안상 위험할 수 있습니다.")
        return v

    @validator("secret_key")
    def validate_secret_key(cls, v):
        """비밀키 보안 검증"""
        if v == "glbaguni-default-secret-key-change-in-production":
            logger.warning("⚠️  기본 SECRET_KEY를 사용하고 있습니다. 프로덕션에서는 반드시 변경하세요!")
        elif len(v) < 32:
            logger.warning("⚠️  SECRET_KEY가 너무 짧습니다. 최소 32자 이상 권장합니다.")
        return v

    # 속성 접근자들
    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """운영 환경 여부"""
        return self.environment == "production"

    @property
    def database_is_sqlite(self) -> bool:
        """SQLite 데이터베이스 여부"""
        return self.database_url.startswith("sqlite")

    @property
    def log_file_path(self) -> str:
        """메인 로그 파일 경로"""
        return os.path.join(self.log_dir, "glbaguni.log")

    @property
    def cors_settings(self) -> dict:
        """CORS 설정 딕셔너리"""
        return {
            "allow_origins": self.allowed_origins,
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

    def get_openai_config(self) -> dict:
        """OpenAI 설정 딕셔너리"""
        return {
            "api_key": self.openai_api_key,
            "model": self.openai_model,
            "max_tokens": self.openai_max_tokens,
            "temperature": self.openai_temperature,
        }

    def get_smtp_config(self) -> Optional[dict]:
        """SMTP 설정 딕셔너리 (설정된 경우에만)"""
        if not all([self.smtp_server, self.smtp_username, self.smtp_password]):
            return None

        return {
            "server": self.smtp_server,
            "port": self.smtp_port,
            "username": self.smtp_username,
            "password": self.smtp_password,
            "use_tls": self.smtp_use_tls,
        }

    def get_database_config(self) -> dict:
        """데이터베이스 설정 딕셔너리"""
        return {
            "url": self.database_url,
            "echo": self.database_echo,
        }


def load_env_file() -> bool:
    """
    .env 파일 로드

    Returns:
        로드 성공 여부
    """

    # 가능한 .env 파일 경로들
    possible_paths = [
        Path(".env"),
        Path("glbaguni/.env"),
        Path("../glbaguni/.env"),
        Path("../../.env"),
    ]

    for env_path in possible_paths:
        if env_path.exists():
            logger.info(f"✅ .env 파일 발견: {env_path.absolute()}")
            return True

    logger.warning("⚠️ .env 파일을 찾을 수 없습니다")
    return False


def validate_required_env_vars(settings: Settings) -> None:
    """필수 환경변수가 설정되었는지 검증"""
    missing_vars = []
    
    # OpenAI API 키 검증
    if not settings.openai_api_key:
        missing_vars.append("OPENAI_API_KEY")
    
    # 보안 키 검증 - 기본값 사용 시 에러
    if (not settings.secret_key or 
        settings.secret_key == "glbaguni-default-secret-key-change-in-production"):
        missing_vars.append("SECRET_KEY")
        logger.error("❌ SECRET_KEY가 기본값으로 설정되어 있습니다. 보안상 위험합니다!")
    
    if missing_vars:
        error_msg = f"""
❌ 필수 환경변수가 설정되지 않았습니다:

누락된 변수: {', '.join(missing_vars)}

.env 파일을 생성하고 다음 환경변수들을 설정하세요:

   OPENAI_API_KEY=your-openai-api-key
   SECRET_KEY=your-super-secret-key-here

현재 설정값:
   OPENAI_API_KEY={settings.openai_api_key if settings.openai_api_key else "❌ 설정되지 않음"}
   SECRET_KEY={"❌ 기본값 또는 설정되지 않음" if not settings.secret_key or settings.secret_key == "glbaguni-default-secret-key-change-in-production" else "✅ 설정됨"}

보안상의 이유로 서버를 시작할 수 없습니다.
        """.strip()
        
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("✅ 모든 필수 환경 변수가 설정되었습니다")


def create_directories(settings: Settings) -> None:
    """
    필요한 디렉토리 생성

    Args:
        settings: 설정 객체
    """

    directories = [settings.log_dir, "data", "cache", "uploads"]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"📁 디렉토리 생성/확인: {directory}")


@lru_cache()
def get_settings() -> Settings:
    """
    설정 객체 생성 및 반환 (싱글톤 패턴)

    Returns:
        설정 객체
    """

    logger.info("🔧 애플리케이션 설정 로드 중...")

    # .env 파일 로드 시도
    env_loaded = load_env_file()

    try:
        # 설정 객체 생성
        settings = Settings()

        # 필수 환경 변수 검증
        validate_required_env_vars(settings)

        # 필요한 디렉토리 생성
        create_directories(settings)

        # 설정 정보 로깅
        logger.info(f"애플리케이션: {settings.app_name} v{settings.app_version}")
        logger.info(f"🌍 환경: {settings.environment}")
        logger.info(f"🖥️ 서버: {settings.host}:{settings.port}")
        logger.info(f"🤖 OpenAI 모델: {settings.openai_model}")
        logger.info(f"📊 로그 레벨: {settings.log_level}")
        logger.info(
            f"💾 데이터베이스: {'SQLite' if settings.database_is_sqlite else 'Other'}"
        )

        if settings.is_development:
            logger.info("🔧 개발 모드가 활성화되었습니다")

        smtp_config = settings.get_smtp_config()
        if smtp_config:
            logger.info(f"📧 이메일 알림 사용: {smtp_config['server']}")
        else:
            logger.info("📧 이메일 알림 비활성화")

        return settings

    except Exception as e:
        logger.error(f"❌ 설정 로드 실패: {str(e)}")
        logger.error("환경 변수 또는 .env 파일을 확인해주세요")
        sys.exit(1)


def print_environment_info():
    """환경 정보 출력 (디버깅용)"""

    logger.info("🔍 환경 정보:")
    logger.info(f"Python 버전: {sys.version}")
    logger.info(f"작업 디렉토리: {os.getcwd()}")
    logger.info(f"PATH: {os.environ.get('PATH', 'N/A')[:100]}...")

    # 중요한 환경 변수들 (값은 마스킹)
    important_vars = [
        "OPENAI_API_KEY",
        "SECRET_KEY",
        "DATABASE_URL",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "HOST",
        "PORT",
    ]

    for var in important_vars:
        value = os.environ.get(var, "NOT_SET")
        if var in ["OPENAI_API_KEY", "SECRET_KEY"] and value != "NOT_SET":
            masked_value = (
                value[:8] + "*" * (len(value) - 8) if len(value) > 8 else "****"
            )
            logger.info(f"{var}: {masked_value}")
        else:
            logger.info(f"{var}: {value}")


# 설정 검증 함수들
def validate_openai_connection(settings: Settings) -> bool:
    """
    OpenAI API 연결 테스트

    Args:
        settings: 설정 객체

    Returns:
        연결 성공 여부
    """

    try:
        import openai

        # 임시 클라이언트 생성
        client = openai.OpenAI(api_key=settings.openai_api_key)

        # 간단한 요청으로 연결 테스트
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=1,
        )

        logger.info("✅ OpenAI API 연결 테스트 성공")
        return True

    except Exception as e:
        logger.error(f"❌ OpenAI API 연결 테스트 실패: {str(e)}")
        return False


def validate_database_connection(settings: Settings) -> bool:
    """
    데이터베이스 연결 테스트

    Args:
        settings: 설정 객체

    Returns:
        연결 성공 여부
    """

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        logger.info("✅ 데이터베이스 연결 테스트 성공")
        return True

    except Exception as e:
        logger.error(f"❌ 데이터베이스 연결 테스트 실패: {str(e)}")
        return False


if __name__ == "__main__":
    # 테스트 및 디버깅
    print("설정 모듈 테스트:")

    try:
        settings = get_settings()
        print(f"✅ 설정 로드 성공")
        print(f"앱 이름: {settings.app_name}")
        print(f"환경: {settings.environment}")
        print(f"개발 모드: {settings.is_development}")

        # 환경 정보 출력
        print_environment_info()

    except Exception as e:
        print(f"❌ 설정 로드 실패: {e}")

    print("\n설정 모듈 테스트 완료!")
