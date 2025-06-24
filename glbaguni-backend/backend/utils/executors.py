#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
안전한 함수 실행을 위한 유틸리티
"""

import asyncio
import logging


class SafeExecutor:
    """안전한 함수 실행을 위한 유틸리티"""

    @staticmethod
    async def safe_call(func, *args, description: str = "함수", **kwargs):
        """안전한 비동기 함수 호출"""
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return await asyncio.to_thread(func, *args, **kwargs)
        except Exception as e:
            logger = logging.getLogger("glbaguni")
            logger.error(f"{description} 호출 실패: {str(e)}")
            raise 