#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
예외 처리 핸들러 모듈
전체 프로젝트의 예외 처리를 중앙에서 관리
"""

import traceback
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .logging_config import get_logger
from .validator import ValidationError

logger = get_logger("exception_handler")


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    표준화된 오류 응답 생성
    
    Args:
        error_code: 오류 코드
        message: 사용자 친화적 메시지
        status_code: HTTP 상태 코드
        details: 추가 세부정보
        request_id: 요청 ID (추적용)
    
    Returns:
        표준화된 오류 응답 딕셔너리
    """
    
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "status_code": status_code
        },
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id or str(uuid.uuid4())[:8]
    }
    
    if details:
        response["error"]["details"] = details
    
    return response


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    HTTP 예외 핸들러
    
    Args:
        request: FastAPI 요청 객체
        exc: HTTP 예외
    
    Returns:
        JSON 응답
    """
    
    # 요청 정보 로깅
    client_ip = request.client.host if request.client else "unknown"
    logger.warning(
        f"HTTP {exc.status_code} - {exc.detail} | "
        f"Path: {request.url.path} | "
        f"Method: {request.method} | "
        f"Client: {client_ip}"
    )
    
    # 상태 코드별 사용자 친화적 메시지
    user_messages = {
        400: "잘못된 요청입니다. 입력값을 확인해주세요.",
        401: "인증이 필요합니다.",
        403: "접근 권한이 없습니다.",
        404: "요청한 리소스를 찾을 수 없습니다.",
        405: "허용되지 않는 HTTP 메서드입니다.",
        422: "입력 데이터에 오류가 있습니다.",
        429: "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
        500: "서버 내부 오류가 발생했습니다.",
        502: "외부 서비스 연결에 실패했습니다.",
        503: "서비스를 일시적으로 사용할 수 없습니다."
    }
    
    user_message = user_messages.get(exc.status_code, exc.detail)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_code=f"HTTP_{exc.status_code}",
            message=user_message,
            status_code=exc.status_code,
            details={"original_message": exc.detail} if exc.detail != user_message else None
        )
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    요청 검증 오류 핸들러
    
    Args:
        request: FastAPI 요청 객체
        exc: 요청 검증 예외
    
    Returns:
        JSON 응답
    """
    
    client_ip = request.client.host if request.client else "unknown"
    logger.warning(
        f"Validation Error | "
        f"Path: {request.url.path} | "
        f"Method: {request.method} | "
        f"Client: {client_ip} | "
        f"Errors: {exc.errors()}"
    )
    
    # 검증 오류를 사용자 친화적으로 변환
    error_messages = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_type = error["type"]
        
        # 타입별 친화적 메시지
        if error_type == "missing":
            friendly_msg = f"'{field}' 필드가 누락되었습니다."
        elif error_type == "type_error":
            friendly_msg = f"'{field}' 필드의 타입이 올바르지 않습니다."
        elif error_type == "value_error":
            friendly_msg = f"'{field}' 필드의 값이 유효하지 않습니다."
        else:
            friendly_msg = f"'{field}': {message}"
        
        error_messages.append(friendly_msg)
    
    return JSONResponse(
        status_code=422,
        content=create_error_response(
            error_code="VALIDATION_ERROR",
            message="입력 데이터 검증에 실패했습니다.",
            status_code=422,
            details={
                "field_errors": error_messages,
                "raw_errors": exc.errors()
            }
        )
    )


async def custom_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    커스텀 검증 오류 핸들러
    
    Args:
        request: FastAPI 요청 객체
        exc: 커스텀 검증 예외
    
    Returns:
        JSON 응답
    """
    
    client_ip = request.client.host if request.client else "unknown"
    logger.warning(
        f"Custom Validation Error: {str(exc)} | "
        f"Path: {request.url.path} | "
        f"Client: {client_ip}"
    )
    
    return JSONResponse(
        status_code=400,
        content=create_error_response(
            error_code="CUSTOM_VALIDATION_ERROR",
            message=str(exc),
            status_code=400
        )
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    전역 예외 핸들러 (최후의 보루)
    
    Args:
        request: FastAPI 요청 객체
        exc: 예외
    
    Returns:
        JSON 응답
    """
    
    # 고유한 오류 ID 생성
    error_id = str(uuid.uuid4())[:8]
    
    # 상세한 오류 정보 로깅
    client_ip = request.client.host if request.client else "unknown"
    logger.error(
        f"💥 Unhandled Exception [{error_id}] | "
        f"Type: {type(exc).__name__} | "
        f"Message: {str(exc)} | "
        f"Path: {request.url.path} | "
        f"Method: {request.method} | "
        f"Client: {client_ip}"
    )
    
    # 전체 스택 트레이스 로깅
    logger.error(f"Stack trace [{error_id}]:\n{traceback.format_exc()}")
    
    # 운영 환경에서는 내부 오류 정보를 숨김
    import os
    is_development = os.getenv("ENVIRONMENT", "production").lower() == "development"
    
    details = None
    if is_development:
        details = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "error_id": error_id
        }
    else:
        details = {"error_id": error_id}
    
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            error_code="INTERNAL_SERVER_ERROR",
            message="서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            status_code=500,
            details=details
        )
    )


def setup_exception_handlers(app):
    """
    FastAPI 앱에 예외 핸들러 등록
    
    Args:
        app: FastAPI 애플리케이션 인스턴스
    """
    
    # 기본 예외 핸들러들
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, custom_validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    
    logger.info("✅ 예외 핸들러 등록 완료")


class ServiceError(Exception):
    """서비스 계층에서 발생하는 예외"""
    
    def __init__(self, message: str, error_code: str = "SERVICE_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ExternalServiceError(ServiceError):
    """외부 서비스 호출 실패 예외"""
    
    def __init__(self, service_name: str, message: str, details: Optional[Dict] = None):
        self.service_name = service_name
        super().__init__(
            message=f"{service_name} 서비스 오류: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service_name, **(details or {})}
        )


class RateLimitError(ServiceError):
    """요청 제한 초과 예외"""
    
    def __init__(self, message: str = "요청 제한을 초과했습니다", retry_after: Optional[int] = None):
        details = {"retry_after": retry_after} if retry_after else None
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


class ConfigurationError(ServiceError):
    """설정 오류 예외"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {"config_key": config_key} if config_key else None
        super().__init__(
            message=f"설정 오류: {message}",
            error_code="CONFIGURATION_ERROR",
            details=details
        )


# 편의 함수들
def log_and_raise_service_error(message: str, error_code: str = "SERVICE_ERROR", details: Optional[Dict] = None):
    """서비스 오류를 로깅하고 예외 발생"""
    logger.error(f"Service Error [{error_code}]: {message}")
    if details:
        logger.error(f"Details: {details}")
    raise ServiceError(message, error_code, details)


def handle_external_api_error(service_name: str, response_status: int, response_text: str):
    """외부 API 오류 처리"""
    if response_status == 429:
        raise RateLimitError(f"{service_name} API 요청 제한 초과")
    elif response_status >= 500:
        raise ExternalServiceError(service_name, f"서버 오류 (상태코드: {response_status})")
    elif response_status >= 400:
        raise ExternalServiceError(service_name, f"클라이언트 오류 (상태코드: {response_status}): {response_text}")
    else:
        raise ExternalServiceError(service_name, f"알 수 없는 오류 (상태코드: {response_status})")


def safe_execute(func, *args, **kwargs):
    """
    함수를 안전하게 실행하고 예외를 로깅
    
    Args:
        func: 실행할 함수
        *args: 함수 인수
        **kwargs: 함수 키워드 인수
    
    Returns:
        함수 실행 결과 또는 None (예외 발생 시)
    """
    
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Safe execution failed for {func.__name__}: {str(e)}")
        logger.error(f"Args: {args}, Kwargs: {kwargs}")
        logger.error(traceback.format_exc())
        return None


# 데코레이터
def handle_exceptions(default_return=None, log_errors=True):
    """
    함수 데코레이터: 예외를 자동으로 처리
    
    Args:
        default_return: 예외 발생 시 반환할 기본값
        log_errors: 오류 로깅 여부
    
    Returns:
        데코레이터 함수
    """
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Exception in {func.__name__}: {str(e)}")
                    logger.error(traceback.format_exc())
                return default_return
        
        return wrapper
    
    return decorator


if __name__ == "__main__":
    # 테스트 코드
    print("예외 처리 모듈 테스트:")
    
    # 커스텀 예외 테스트
    try:
        raise ServiceError("테스트 서비스 오류", "TEST_ERROR", {"key": "value"})
    except ServiceError as e:
        print(f"✅ ServiceError 테스트: {e.message} ({e.error_code})")
    
    try:
        raise ExternalServiceError("TestAPI", "연결 실패")
    except ExternalServiceError as e:
        print(f"✅ ExternalServiceError 테스트: {e.message}")
    
    # Safe execution 테스트
    def test_function():
        raise ValueError("테스트 오류")
    
    result = safe_execute(test_function)
    print(f"✅ Safe execution 테스트: {result}")
    
    # 데코레이터 테스트
    @handle_exceptions(default_return="오류 발생", log_errors=False)
    def test_decorated_function():
        raise RuntimeError("데코레이터 테스트")
    
    result = test_decorated_function()
    print(f"✅ 데코레이터 테스트: {result}")
    
    print("\n예외 처리 모듈 테스트 완료!")