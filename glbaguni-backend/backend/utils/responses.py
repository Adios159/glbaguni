#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
표준 응답 형식 생성 유틸리티
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class ResponseBuilder:
    """표준 응답 형식 생성"""

    @staticmethod
    def success(
        data: Any, message: str = "요청이 성공적으로 처리되었습니다", **kwargs
    ) -> Dict[str, Any]:
        """성공 응답 생성"""
        response = {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())[:8],
        }
        response.update(kwargs)
        return response


# 표준 API 응답 유틸리티 함수
def success(data: Any = None, message: str = "요청이 성공적으로 처리되었습니다.") -> Dict[str, Any]:
    """
    성공 응답을 반환합니다.
    
    Args:
        data: 응답 데이터
        message: 성공 메시지
        
    Returns:
        dict: 표준 성공 응답 형식
        
    Example:
        >>> success({"user_id": 123}, "사용자가 생성되었습니다.")
        {
            "status": "success",
            "message": "사용자가 생성되었습니다.",
            "data": {"user_id": 123}
        }
    """
    return {
        "status": "success",
        "message": message,
        "data": data
    }


def error(message: str, code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> None:
    """
    에러 응답을 위해 HTTPException을 발생시킵니다.
    
    Args:
        message: 에러 메시지
        code: HTTP 상태 코드 (기본값: 500)
        
    Raises:
        HTTPException: FastAPI HTTPException
        
    Example:
        >>> error("사용자를 찾을 수 없습니다.", 404)
        # HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")이 발생
    """
    raise HTTPException(status_code=code, detail=message)


# 자주 사용되는 에러 응답들
def bad_request(message: str = "잘못된 요청입니다.") -> None:
    """400 Bad Request 에러"""
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def unauthorized(message: str = "인증이 필요합니다.") -> None:
    """401 Unauthorized 에러"""
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def forbidden(message: str = "접근 권한이 없습니다.") -> None:
    """403 Forbidden 에러"""
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)


def not_found(message: str = "요청한 리소스를 찾을 수 없습니다.") -> None:
    """404 Not Found 에러"""
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def conflict(message: str = "이미 존재하는 리소스입니다.") -> None:
    """409 Conflict 에러"""
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


def internal_server_error(message: str = "서버 내부 오류가 발생했습니다.") -> None:
    """500 Internal Server Error"""
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

    @staticmethod
    def error(
        error_code: str, message: str, status_code: int = 500, **kwargs
    ) -> Dict[str, Any]:
        """오류 응답 생성"""
        response = {
            "success": False,
            "error_code": error_code,
            "message": message,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())[:8],
        }
        response.update(kwargs)
        return response 