#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
미들웨어 모듈
FastAPI 미들웨어 함수들을 관리
"""

import time
import uuid
import logging
from fastapi import Request

logger = logging.getLogger("glbaguni.middleware")


async def logging_middleware(request: Request, call_next):
    """요청/응답 로깅 미들웨어"""
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    
    # 요청 로깅
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"📥 [{request_id}] {request.method} {request.url.path} from {client_ip}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 응답 로깅
        logger.info(f"📤 [{request_id}] {response.status_code} in {process_time:.3f}s")
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"💥 [{request_id}] Error in {process_time:.3f}s: {str(e)}")
        raise 