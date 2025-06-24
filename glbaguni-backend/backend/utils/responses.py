#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
표준 응답 형식 생성 유틸리티
"""

import uuid
from datetime import datetime
from typing import Any, Dict


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