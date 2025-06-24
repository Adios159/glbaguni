#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
예외 처리 핸들러 모듈
FastAPI 예외 처리 핸들러들을 관리
"""

import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("glbaguni.exceptions")


def create_error_response(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 500,
) -> Dict[str, Any]:
    """표준화된 오류 응답 생성"""
    response = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "request_id": str(uuid.uuid4())[:8],
    }

    if details:
        response["details"] = details

    return response


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 예외 처리"""
    logger.error(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_code=f"HTTP_{exc.status_code}",
            message=exc.detail,
            status_code=exc.status_code,
        ),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 오류 처리"""
    logger.error(f"Validation Error: {exc.errors()} - {request.url}")
    return JSONResponse(
        status_code=422,
        content=create_error_response(
            error_code="VALIDATION_ERROR",
            message="입력 데이터 검증에 실패했습니다.",
            details={"errors": exc.errors()},
            status_code=422,
        ),
    )


async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    error_id = str(uuid.uuid4())[:8]
    logger.error(f"💥 Unexpected error [{error_id}]: {str(exc)}")
    logger.error(traceback.format_exc())

    return JSONResponse(
        status_code=500,
        content=create_error_response(
            error_code="INTERNAL_ERROR",
            message="서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            details={"error_id": error_id},
            status_code=500,
        ),
    )
