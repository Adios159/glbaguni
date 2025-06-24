#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전역 컴포넌트 관리 모듈
서버 전반에서 사용되는 공유 컴포넌트들을 관리
"""

import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger("glbaguni.components")


class GlobalComponents:
    """전역 컴포넌트 관리 클래스"""

    http_client: Optional[httpx.AsyncClient] = None
    fetcher: Optional[object] = None
    summarizer: Optional[object] = None
    notifier: Optional[object] = None
    history_service: Optional[object] = None
    news_aggregator: Optional[object] = None


# 전역 인스턴스
components = GlobalComponents()


async def initialize_components():
    """모든 컴포넌트 초기화"""
    start_time = time.time()
    logger.info("🔧 컴포넌트 초기화 시작...")

    try:
        # 모듈 import
        try:
            # 절대 임포트로 변경
            import os
            import sys

            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

            # Import settings instance from config.py (the original one with Settings instance)
            import config
            settings = config.settings
            from database import init_database
            from fetcher import ArticleFetcher
            from history_service import HistoryService
            from news_aggregator import NewsAggregator
            from notifier import EmailNotifier
            from summarizer import ArticleSummarizer
        except ImportError as e:
            # 백업 경로 추가
            try:
                import os
                import sys

                backend_path = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                if backend_path not in sys.path:
                    sys.path.insert(0, backend_path)

                # Import settings instance from config.py
                import config
                settings = config.settings
                from database import init_database
                from fetcher import ArticleFetcher
                from history_service import HistoryService
                from news_aggregator import NewsAggregator
                from notifier import EmailNotifier
                from summarizer import ArticleSummarizer
            except ImportError as e:
                logger.error(f"임포트 실패: {e}")
                raise

        # HTTP 클라이언트 초기화
        components.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=60.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            headers={
                "User-Agent": "Glbaguni/3.0.0 (RSS Summarizer Bot)",
                "Accept": "application/json, text/plain, */*",
            },
        )
        logger.info("✅ HTTP 클라이언트 초기화 완료")

        # 데이터베이스 초기화
        try:
            if init_database is not None and callable(init_database):
                # 함수가 비동기인지 확인
                import inspect
                if inspect.iscoroutinefunction(init_database):
                    await init_database()
                else:
                    init_database()
                logger.info("✅ 데이터베이스 초기화 완료")
            else:
                logger.info("⚠️ 데이터베이스 초기화 함수를 찾을 수 없습니다")
        except Exception as e:
            logger.warning(f"⚠️ 데이터베이스 초기화 실패: {e}")
            # 데이터베이스 초기화 실패는 치명적이지 않으므로 계속 진행

        # 컴포넌트 초기화
        components.fetcher = ArticleFetcher()
        components.summarizer = ArticleSummarizer()
        components.history_service = HistoryService()

        # NewsAggregator 초기화 (OPENAI_API_KEY 사용)
        try:
            openai_key = settings.OPENAI_API_KEY
        except AttributeError:
            # Fallback to environment variable
            openai_key = os.getenv("OPENAI_API_KEY")
        
        if openai_key:
            components.news_aggregator = NewsAggregator(openai_api_key=openai_key)

        # 이메일 컴포넌트 (선택적)
        try:
            components.notifier = EmailNotifier()
            logger.info("✅ 이메일 알림 서비스 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ 이메일 알림 서비스 초기화 실패: {e}")
            components.notifier = None

        elapsed = time.time() - start_time
        logger.info(f"🎉 컴포넌트 초기화 완료! (소요시간: {elapsed:.2f}초)")

    except Exception as e:
        logger.error(f"❌ 컴포넌트 초기화 실패: {str(e)}")
        raise


async def cleanup_components():
    """컴포넌트 정리"""
    logger.info("🔄 컴포넌트 정리 중...")

    if components.http_client:
        await components.http_client.aclose()
        logger.info("✅ HTTP 클라이언트 종료 완료")

    logger.info("✅ 컴포넌트 정리 완료")
