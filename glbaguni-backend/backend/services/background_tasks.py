#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백그라운드 작업 함수들
"""

import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..models import Article, ArticleSummary
else:
    # 런타임에서는 문자열로 참조
    Article = "Article"
    ArticleSummary = "ArticleSummary"

from ..utils.executors import SafeExecutor
from ..utils.validators import InputSanitizer


async def send_summary_email(
    recipient_email: str, summaries: List["ArticleSummary"], request_id: str, app_state
):
    """요약 결과 이메일 발송 (백그라운드)"""
    try:
        logger = logging.getLogger("glbaguni")
        
        if not InputSanitizer.validate_email(recipient_email):
            logger.error(f"❌ [{request_id}] 잘못된 이메일 형식: {recipient_email}")
            return

        if app_state.notifier:
            await SafeExecutor.safe_call(
                app_state.notifier.send_summary_email,
                recipient_email,
                summaries,
                description="이메일 발송",
            )
            logger.info(f"✅ [{request_id}] 이메일 발송 완료: {recipient_email}")
        else:
            logger.warning(f"⚠️ [{request_id}] 이메일 서비스 없음")

    except Exception as e:
        logger = logging.getLogger("glbaguni")
        logger.error(f"❌ [{request_id}] 이메일 발송 실패: {e}")


async def save_to_history(
    user_id: str, summaries: List["ArticleSummary"], db, request_id: str, app_state
):
    """히스토리 저장 (백그라운드)"""
    try:
        logger = logging.getLogger("glbaguni")
        
        if app_state.history_service:
            for summary in summaries:
                await SafeExecutor.safe_call(
                    app_state.history_service.save_summary_history,
                    db,
                    user_id,
                    {
                        "title": summary.title,
                        "url": summary.url,
                        "content": "",  # 원본 내용은 저장하지 않음
                        "source": summary.source,
                    },
                    summary.summary,
                    "ko",  # 기본 언어
                    description="히스토리 저장",
                )
            logger.info(f"✅ [{request_id}] 히스토리 저장 완료: {len(summaries)}개")
        else:
            logger.warning(f"⚠️ [{request_id}] 히스토리 서비스 없음")

    except Exception as e:
        logger = logging.getLogger("glbaguni")
        logger.error(f"❌ [{request_id}] 히스토리 저장 실패: {e}") 