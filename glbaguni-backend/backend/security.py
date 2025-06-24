#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
보안 유틸리티 모듈
사용자 입력 검증, Prompt Injection 방지, 데이터 sanitization, JWT 토큰 관리
"""

import logging
import re
import unicodedata
from datetime import datetime, timedelta
from html import escape
from typing import Any, Dict, List, Optional

import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError, InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DELTA = timedelta(minutes=30)  # 기본 30분 만료


def get_secret_key() -> str:
    """SECRET_KEY를 환경변수에서 가져오거나 설정에서 로드합니다."""
    try:
        from backend.config.settings import get_settings
        settings = get_settings()
        return settings.secret_key
    except ImportError:
        import os
        return os.getenv("SECRET_KEY", "glbaguni-default-secret-key-change-in-production")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 액세스 토큰을 생성합니다.
    
    Args:
        data: 토큰에 포함할 데이터 (user_id 등)
        expires_delta: 토큰 만료 시간 (기본값: 30분)
    
    Returns:
        str: JWT 토큰 문자열
        
    Example:
        >>> token = create_access_token({"user_id": 123})
        >>> print(token)  # eyJ0eXAiOiJKV1QiLCJhbGci...
    """
    to_encode = data.copy()
    
    # 만료 시간 설정
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + JWT_EXPIRATION_DELTA
    
    # 표준 JWT 클레임 추가
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    try:
        secret_key = get_secret_key()
        encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=JWT_ALGORITHM)
        logger.info(f"JWT 토큰 생성 성공 (만료: {expire})")
        return encoded_jwt
    except Exception as e:
        logger.error(f"JWT 토큰 생성 실패: {e}")
        raise ValueError(f"토큰 생성에 실패했습니다: {e}")


def decode_access_token(token: str) -> Optional[int]:
    """
    JWT 액세스 토큰을 검증하고 user_id를 반환합니다.
    
    Args:
        token: JWT 토큰 문자열
        
    Returns:
        Optional[int]: 유효한 토큰이면 user_id, 그렇지 않으면 None
        
    Example:
        >>> user_id = decode_access_token("eyJ0eXAiOiJKV1QiLCJhbGci...")
        >>> print(user_id)  # 123 또는 None
    """
    if not token or not isinstance(token, str):
        logger.warning("빈 토큰 또는 유효하지 않은 토큰 형식")
        return None
    
    try:
        secret_key = get_secret_key()
        payload = jwt.decode(token, secret_key, algorithms=[JWT_ALGORITHM])
        
        # 토큰 타입 검증
        if payload.get("type") != "access":
            logger.warning("유효하지 않은 토큰 타입")
            return None
        
        # user_id 추출
        user_id = payload.get("user_id")
        if user_id is None:
            logger.warning("토큰에 user_id가 없음")
            return None
            
        logger.info(f"JWT 토큰 검증 성공 (user_id: {user_id})")
        return int(user_id)
        
    except ExpiredSignatureError:
        logger.warning("만료된 JWT 토큰")
        return None
    except DecodeError:
        logger.warning("JWT 토큰 디코딩 실패")
        return None
    except InvalidTokenError:
        logger.warning("유효하지 않은 JWT 토큰")
        return None
    except (ValueError, TypeError) as e:
        logger.warning(f"JWT 토큰 처리 중 오류: {e}")
        return None
    except Exception as e:
        logger.error(f"JWT 토큰 검증 중 예상치 못한 오류: {e}")
        return None


# 비밀번호 해싱 및 검증 함수
def get_password_hash(password: str) -> str:
    """
    비밀번호를 bcrypt로 해싱합니다.
    
    Args:
        password: 평문 비밀번호
        
    Returns:
        str: 해싱된 비밀번호
        
    Example:
        >>> hashed = get_password_hash("mypassword123")
        >>> print(hashed)  # $2b$12$...
    """
    if not password or not isinstance(password, str):
        raise ValueError("비밀번호는 비어있지 않은 문자열이어야 합니다.")
    
    try:
        hashed_password = pwd_context.hash(password)
        logger.info("비밀번호 해싱 완료")
        return hashed_password
    except Exception as e:
        logger.error(f"비밀번호 해싱 실패: {e}")
        raise ValueError(f"비밀번호 해싱에 실패했습니다: {e}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    평문 비밀번호와 해시된 비밀번호를 비교합니다.
    
    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해시된 비밀번호
        
    Returns:
        bool: 비밀번호가 일치하면 True, 아니면 False
        
    Example:
        >>> is_valid = verify_password("mypassword123", hashed)
        >>> print(is_valid)  # True 또는 False
    """
    if not plain_password or not hashed_password:
        logger.warning("비밀번호 검증: 빈 값 입력")
        return False
    
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        logger.info(f"비밀번호 검증 결과: {'성공' if result else '실패'}")
        return result
    except Exception as e:
        logger.error(f"비밀번호 검증 중 오류: {e}")
        return False


# 사용자 생성 및 인증 함수
def create_user(db: Session, email: str, password: str) -> dict:
    """
    새로운 사용자를 생성합니다.
    
    Args:
        db: SQLAlchemy 세션
        email: 사용자 이메일
        password: 평문 비밀번호
        
    Returns:
        dict: 생성된 사용자 정보 또는 오류 정보
        
    Example:
        >>> result = create_user(db, "user@example.com", "password123")
        >>> print(result["success"])  # True 또는 False
    """
    if not email or not password:
        logger.warning("사용자 생성: 필수 파라미터 누락")
        return {
            "success": False,
            "message": "이메일과 비밀번호는 필수입니다.",
            "user": None
        }
    
    try:
        from backend.models.models import User
        
        # 중복 이메일 확인
        existing_user = db.query(User).filter(User.email == email.lower().strip()).first()
        if existing_user:
            logger.warning(f"사용자 생성 실패: 이메일 중복 ({email})")
            return {
                "success": False,
                "message": "이미 사용 중인 이메일입니다.",
                "user": None
            }
        
        # 비밀번호 해싱
        hashed_password = get_password_hash(password)
        
        # 새 사용자 생성
        new_user = User(
            email=email.lower().strip(),
            hashed_password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"새 사용자 생성 성공: {email}")
        return {
            "success": True,
            "message": "사용자가 성공적으로 생성되었습니다.",
            "user": {"id": new_user.id, "email": new_user.email}
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"사용자 생성 중 오류: {e}")
        return {
            "success": False,
            "message": f"사용자 생성에 실패했습니다: {str(e)}",
            "user": None
        }


def authenticate_user(db: Session, email: str, password: str) -> dict:
    """
    사용자 인증을 수행합니다.
    
    Args:
        db: SQLAlchemy 세션
        email: 사용자 이메일
        password: 평문 비밀번호
        
    Returns:
        dict: 인증 결과 및 사용자 정보
        
    Example:
        >>> result = authenticate_user(db, "user@example.com", "password123")
        >>> print(result["success"])  # True 또는 False
    """
    if not email or not password:
        logger.warning("사용자 인증: 필수 파라미터 누락")
        return {
            "success": False,
            "message": "이메일과 비밀번호는 필수입니다.",
            "user": None
        }
    
    try:
        from backend.models.models import User
        
        # 사용자 조회
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if not user:
            logger.warning(f"사용자 인증 실패: 존재하지 않는 이메일 ({email})")
            return {
                "success": False,
                "message": "이메일 또는 비밀번호가 올바르지 않습니다.",
                "user": None
            }
        
        # 비밀번호 검증
        if not verify_password(password, user.hashed_password):
            logger.warning(f"사용자 인증 실패: 잘못된 비밀번호 ({email})")
            return {
                "success": False,
                "message": "이메일 또는 비밀번호가 올바르지 않습니다.",
                "user": None
            }
        
        logger.info(f"사용자 인증 성공: {email}")
        return {
            "success": True,
            "message": "인증이 성공했습니다.",
            "user": {"id": user.id, "email": user.email}
        }
        
    except Exception as e:
        logger.error(f"사용자 인증 중 오류: {e}")
        return {
            "success": False,
            "message": f"인증 과정에서 오류가 발생했습니다: {str(e)}",
            "user": None
        }


class SecurityValidator:
    """보안 검증 및 입력 정화 클래스"""

    # 위험한 패턴들 (Prompt Injection 방지)
    DANGEROUS_PATTERNS = [
        # 시스템 명령어 시도
        r"(?i)(ignore|forget|override)\s+(previous|above|prior|earlier)\s+(instruction|prompt|rule)",
        r"(?i)(you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay)",
        r"(?i)(system\s*:|assistant\s*:|user\s*:)",
        r"(?i)(execute|run|eval|compile)\s*[\(\[]",
        # 스크립트 삽입 시도
        r"<script[^>]*>.*?</script>",
        r"javascript\s*:",
        r"vbscript\s*:",
        r"on\w+\s*=",
        # SQL Injection 시도
        r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)",
        r'[\'"]\s*;\s*--',
        r'[\'"]\s*or\s+[\'"]\d+[\'"]\s*=\s*[\'"]\d+[\'"]',
        # 특수 명령어 시도
        r"(?i)(\\n\\n|\\r\\n)+(system|user|assistant):\s*",
        r"(?i)###\s*(instruction|system|prompt)",
        r"(?i)\[system\]|\[user\]|\[assistant\]",
        # 인코딩 우회 시도
        r"%[0-9a-fA-F]{2}",  # URL 인코딩
        r"\\u[0-9a-fA-F]{4}",  # Unicode 이스케이프
    ]

    # 허용되지 않는 특수문자
    FORBIDDEN_CHARS = ["<", ">", '"', "'", ";", "`", "\\", "\x00", "\x01", "\x02"]

    # 최대 입력 길이
    MAX_INPUT_LENGTH = 500
    MAX_QUERY_LENGTH = 200

    @classmethod
    def validate_user_input(cls, text: str, input_type: str = "general") -> str:
        """
        사용자 입력을 검증하고 안전하게 정화합니다.

        Args:
            text: 사용자 입력 텍스트
            input_type: 입력 타입 ("query", "prompt", "general")

        Returns:
            str: 정화된 안전한 텍스트

        Raises:
            ValueError: 위험한 입력이 감지된 경우
        """
        if not text or not isinstance(text, str):
            raise ValueError("입력 텍스트가 비어있거나 유효하지 않습니다.")

        original_length = len(text)

        # 1. 길이 제한 검사
        max_length = (
            cls.MAX_QUERY_LENGTH if input_type == "query" else cls.MAX_INPUT_LENGTH
        )
        if len(text) > max_length:
            logger.warning(f"입력 길이 초과: {len(text)} > {max_length}")
            text = text[:max_length]

        # 2. Unicode 정규화
        text = unicodedata.normalize("NFKC", text)

        # 3. 위험한 패턴 검사
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                logger.error(f"위험한 패턴 감지: {pattern}")
                raise ValueError("입력에 허용되지 않는 내용이 포함되어 있습니다.")

        # 4. 금지된 문자 제거
        for char in cls.FORBIDDEN_CHARS:
            if char in text:
                logger.warning(f"금지된 문자 제거: {char}")
                text = text.replace(char, "")

        # 5. HTML 이스케이핑
        text = escape(text)

        # 6. 연속된 특수문자 정리
        text = re.sub(r"[^\w\s가-힣.,!?()-]{2,}", "", text)

        # 7. 과도한 공백 정리
        text = re.sub(r"\s+", " ", text).strip()

        # 8. 최종 검증
        if not text:
            raise ValueError("입력 정화 후 유효한 내용이 남지 않았습니다.")

        if len(text) != original_length:
            logger.info(f"입력 정화 완료: {original_length} -> {len(text)} 문자")

        return text

    @classmethod
    def create_safe_prompt(
        cls, user_input: str, system_message: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        안전한 OpenAI 프롬프트 구조를 생성합니다.

        Args:
            user_input: 정화된 사용자 입력
            system_message: 시스템 메시지
            context: 추가 컨텍스트 (선택사항)

        Returns:
            Dict: OpenAI API 호출용 메시지 구조
        """
        # 사용자 입력 재검증
        safe_input = cls.validate_user_input(user_input, "query")

        messages = [{"role": "system", "content": system_message}]

        # 컨텍스트가 있는 경우 추가
        if context:
            safe_context = cls.validate_user_input(context, "general")
            messages.append({"role": "system", "content": f"참고 정보: {safe_context}"})

        # 사용자 입력을 별도 메시지로 분리
        messages.append({"role": "user", "content": safe_input})

        return {
            "messages": messages,
            "temperature": 0.3,  # 일관된 응답을 위해 낮은 온도 설정
            "max_tokens": 500,  # 토큰 제한으로 과도한 응답 방지
        }

    @classmethod
    def validate_api_key(cls, api_key: str) -> bool:
        """
        OpenAI API 키 형식을 검증합니다.

        Args:
            api_key: API 키 문자열

        Returns:
            bool: 유효한 형식인지 여부
        """
        if not api_key or not isinstance(api_key, str):
            return False

        # OpenAI API 키 형식: sk-... (최소 20자)
        if not api_key.startswith("sk-") or len(api_key) < 20:
            return False

        # 허용된 문자만 포함하는지 확인
        allowed_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        )
        if not all(c in allowed_chars for c in api_key):
            return False

        return True

    @classmethod
    def sanitize_response_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        API 응답 데이터에서 민감한 정보를 제거합니다.

        Args:
            data: 응답 데이터 딕셔너리

        Returns:
            Dict: 정화된 응답 데이터
        """
        sensitive_keys = [
            "api_key",
            "apikey",
            "key",
            "token",
            "password",
            "secret",
            "openai_api_key",
            "smtp_password",
            "smtp_username",
        ]

        def recursive_sanitize(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {
                    k: (
                        recursive_sanitize(v)
                        if k.lower() not in sensitive_keys
                        else "***REDACTED***"
                    )
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [recursive_sanitize(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith("sk-"):
                return "***REDACTED***"
            else:
                return obj

        result = recursive_sanitize(data)
        return result if isinstance(result, dict) else {}


# 보안 검증 인스턴스 (싱글톤 패턴)
security_validator = SecurityValidator()


# 편의 함수들
def validate_input(text: str, input_type: str = "general") -> str:
    """사용자 입력 검증 편의 함수"""
    return security_validator.validate_user_input(text, input_type)


def create_safe_prompt(
    user_input: str, system_message: str, context: Optional[str] = None
) -> Dict[str, Any]:
    """안전한 프롬프트 생성 편의 함수"""
    return security_validator.create_safe_prompt(user_input, system_message, context)


def validate_api_key(api_key: str) -> bool:
    """API 키 검증 편의 함수"""
    return security_validator.validate_api_key(api_key)


def sanitize_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """응답 데이터 정화 편의 함수"""
    return security_validator.sanitize_response_data(data)
