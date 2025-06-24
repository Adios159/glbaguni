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

from ..models import HistoryResponse
from ..utils.executors import SafeExecutor
from ..utils.validators import InputSanitizer


def create_history_router(app_state, importer):
    """히스토리 라우터 생성"""
    router = APIRouter()

    @router.get("/history", response_model=HistoryResponse)
    async def get_user_history(
        user_id: str = Query(..., description="사용자 ID"),
        page: int = Query(1, ge=1, description="페이지 번호"),
        per_page: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
        language: Optional[str] = Query(None, description="언어 필터 (ko/en)"),
        db: Session = Depends(importer.services["get_db"]),
    ):
        """사용자 히스토리 조회 API"""
        request_id = str(uuid.uuid4())[:8]
        logger = logging.getLogger("glbaguni")
        logger.info(f"📚 [{request_id}] 히스토리 조회: user_id={user_id}")

        try:
            # 입력 검증
            validated_user_id = InputSanitizer.sanitize_text(user_id, 100, "사용자 ID")

            if not app_state.history_service:
                raise HTTPException(500, "히스토리 서비스가 초기화되지 않았습니다")

            # 히스토리 조회
            result = await SafeExecutor.safe_call(
                app_state.history_service.get_user_history,
                db,
                validated_user_id,
                page,
                per_page,
                language,
                description="사용자 히스토리 조회",
            )

            logger.info(f"✅ [{request_id}] 히스토리 조회 완료")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ [{request_id}] 히스토리 조회 중 오류: {e}")
            raise HTTPException(500, "히스토리 조회 중 내부 오류가 발생했습니다")

    return router 