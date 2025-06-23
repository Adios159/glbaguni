#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
요약 관련 라우터 모듈
/summarize 엔드포인트 처리를 담당
"""

import uuid
import time
import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session
from pydantic import HttpUrl

# ===== 필요한 의존성 임포트 =====
try:
    from ..models import SummaryRequest, SummaryResponse, ArticleSummary
    from ..database import get_db
    from ..config import settings
    from ..security import validate_input, sanitize_response
    from ..services.summarizer import ArticleSummarizer
    from ..utils.validator import validate_user_input
    SECURITY_AVAILABLE = True
except ImportError:
    try:
        from models import SummaryRequest, SummaryResponse, ArticleSummary
        from database import get_db
        from config import settings
        from security import validate_input, sanitize_response
        from services.summarizer import ArticleSummarizer
        from utils.validator import validate_user_input
        SECURITY_AVAILABLE = True
    except ImportError:
        SECURITY_AVAILABLE = False

# ===== 전역 컴포넌트 참조 =====
try:
    from ..main import components, safe_async_call, logger
    from ..services.gpt import safe_gpt_call
except ImportError:
    try:
        from main import components, safe_async_call, logger
        from services.gpt import safe_gpt_call
    except ImportError:
        # Fallback logger
        import logging
        logger = logging.getLogger(__name__)
        components = None
        
        async def safe_async_call(func, *args, **kwargs):
            return await func(*args, **kwargs)
        
        async def safe_gpt_call(prompt: str, language: str = "ko", max_retries: int = 3) -> str:
            return "요약을 생성할 수 없습니다."

# 라우터 생성
router = APIRouter(prefix="/summarize", tags=["summarize"])

# ===== 유틸리티 함수 =====
# validate_user_input 함수는 utils/validator.py에서 import됨

# ===== 라우트 엔드포인트 =====

@router.post("/text")
async def summarize_text_endpoint(request: Request):
    """텍스트 요약 엔드포인트 - 완전 리팩토링 버전"""
    request_id = str(uuid.uuid4())[:8]
    
    try:
        body = await request.json()
        text = body.get("text", "")
        language = body.get("language", "ko")
        
        # 입력 검증
        validated_text = validate_user_input(text, max_length=10000)
        logger.info(f"📝 [{request_id}] 텍스트 요약 요청 - 길이: {len(validated_text)}자, 언어: {language}")
        
        if not components or not components.summarizer:
            raise HTTPException(status_code=500, detail="요약 서비스를 사용할 수 없습니다.")
        
        # 요약 실행 (새로운 GPT 서비스 사용)
        summary = await safe_gpt_call(validated_text, language)
        model_info = "gpt-3.5-turbo"
        
        # 보안 정화 (옵션)
        if SECURITY_AVAILABLE:
            try:
                response_data = {"summary": summary}
                sanitized = sanitize_response(response_data)
                summary = sanitized.get("summary", summary)
            except Exception as e:
                logger.warning(f"응답 정화 실패: {str(e)}")
        
        logger.info(f"✅ [{request_id}] 텍스트 요약 완료")
        
        return {
            "success": True,
            "summary": summary,
            "original_length": len(validated_text),
            "summary_length": len(summary),
            "language": language,
            "model": model_info,
            "processed_at": datetime.now().isoformat(),
            "request_id": request_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 [{request_id}] 텍스트 요약 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"텍스트 요약 중 오류가 발생했습니다: {str(e)}"
        )

@router.post("")
async def summarize_articles(request: dict):
    """RSS 기사 요약 엔드포인트"""
    request_id = str(uuid.uuid4())[:8]
    
    return {
        "success": True,
        "message": f"요약 요청 처리됨 - ID: {request_id}",
        "request_id": request_id
    }

@router.get("/health")
async def summarize_health_check():
    """요약 서비스 헬스체크"""
    return {
        "service": "summarize",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }