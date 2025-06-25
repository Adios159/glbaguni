#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
히스토리 관련 엔드포인트들
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

# Import 에러 방지를 위한 안전한 import 구조
try:
    from ..models import HistoryResponse
    from ..utils.executors import SafeExecutor
    from ..utils.validators import InputSanitizer
except ImportError:
    try:
        from backend.models import HistoryResponse
        from backend.utils.executors import SafeExecutor
        from backend.utils.validators import InputSanitizer
    except ImportError as e:
        logging.error(f"History router import error: {e}")
        # 기본값으로 fallback
        HistoryResponse = dict
        SafeExecutor = None
        InputSanitizer = None

# 라우터 생성
router = APIRouter(prefix="/api", tags=["history"])

def create_history_router(app_state=None, importer=None):
    """히스토리 라우터 생성 (호환성 유지)"""
    return router

@router.get("/history")
async def get_user_history(
    user_id: str = Query(..., description="사용자 ID"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    per_page: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    language: Optional[str] = Query(None, description="언어 필터 (ko/en)"),
):
    """사용자 히스토리 조회 API"""
    request_id = str(uuid.uuid4())[:8]
    logger = logging.getLogger("glbaguni")
    logger.info(f"📚 [{request_id}] 히스토리 조회: user_id={user_id}")

    try:
        # 기본적인 입력 검증
        if not user_id or len(user_id) > 100:
            raise HTTPException(400, "잘못된 사용자 ID입니다")

        # 컴포넌트 매니저에서 히스토리 서비스 가져오기
        try:
            from backend.utils.component_manager import get_history_service
            history_service = get_history_service()
        except ImportError:
            try:
                from utils.component_manager import get_history_service
                history_service = get_history_service()
            except ImportError:
                history_service = None

        if not history_service:
            logger.warning(f"⚠️ [{request_id}] 히스토리 서비스가 초기화되지 않았습니다")
            return {
                "status": "warning",
                "message": "히스토리 서비스가 현재 이용할 수 없습니다",
                "data": {
                    "items": [],
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": 0,
                        "pages": 0
                    }
                }
            }

        # 히스토리 조회 시도
        try:
            if hasattr(history_service, 'get_user_history'):
                result = await history_service.get_user_history(
                    user_id, page, per_page, language
                )
            else:
                # 기본 응답
                result = {
                    "status": "success",
                    "data": {
                        "items": [],
                        "pagination": {
                            "page": page,
                            "per_page": per_page,
                            "total": 0,
                            "pages": 0
                        }
                    }
                }
        except Exception as service_error:
            logger.error(f"❌ [{request_id}] 히스토리 서비스 호출 오류: {service_error}")
            result = {
                "status": "error",
                "message": "히스토리 조회 중 오류가 발생했습니다",
                "data": {
                    "items": [],
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": 0,
                        "pages": 0
                    }
                }
            }

        logger.info(f"✅ [{request_id}] 히스토리 조회 완료")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [{request_id}] 히스토리 조회 중 오류: {e}")
        raise HTTPException(500, "히스토리 조회 중 내부 오류가 발생했습니다") 