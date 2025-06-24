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
            # backend.* 절대 경로로 import
            from backend.config import settings
            from backend.database import init_database
            from backend.fetcher import ArticleFetcher
            from backend.history_service import HistoryService
            from backend.news_aggregator import NewsAggregator
            from backend.notifier import EmailNotifier
            from backend.summarizer import ArticleSummarizer
            logger.info("✅ 모든 모듈 backend.* 경로로 import 성공")
        except ImportError as e:
            logger.warning(f"⚠️ backend.* import 실패, 상대경로 시도: {e}")
            try:
                # 폴백: 상대경로 import
                import os
                import sys

                backend_path = os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
                if backend_path not in sys.path:
                    sys.path.insert(0, backend_path)

                from config import settings
                from database import init_database
                from fetcher import ArticleFetcher
                from history_service import HistoryService
                from news_aggregator import NewsAggregator
                from notifier import EmailNotifier
                from summarizer import ArticleSummarizer
                logger.info("✅ 상대경로로 import 성공")
            except ImportError as e:
                logger.error(f"❌ 모든 import 실패: {e}")
                # 필수 컴포넌트만 초기화
                components.http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=60.0),
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                    headers={
                        "User-Agent": "Glbaguni/3.0.0 (RSS Summarizer Bot)",
                        "Accept": "application/json, text/plain, */*",
                    },
                )
                logger.info("✅ HTTP 클라이언트만 초기화 완료")
                return

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

        # 컴포넌트 초기화 (개별 try-catch로 실패 시 건너뛰기)
        # ArticleFetcher 초기화
        try:
            components.fetcher = ArticleFetcher()
            logger.info("✅ ArticleFetcher 초기화 완료")
        except Exception as e:
            logger.error(f"❌ ArticleFetcher 초기화 실패: {e}")
            components.fetcher = None

        # ArticleSummarizer 초기화
        try:
            components.summarizer = ArticleSummarizer()
            logger.info("✅ ArticleSummarizer 초기화 완료")
        except Exception as e:
            logger.error(f"❌ ArticleSummarizer 초기화 실패: {e}")
            components.summarizer = None

        # HistoryService 초기화
        try:
            components.history_service = HistoryService()
            logger.info("✅ HistoryService 초기화 완료")
        except Exception as e:
            logger.error(f"❌ HistoryService 초기화 실패: {e}")
            components.history_service = None

        # NewsAggregator 초기화 (OPENAI_API_KEY 사용) - 안전한 방식
        try:
            # 환경변수에서 직접 가져오기 (가장 안전한 방식)
            openai_key = os.getenv("OPENAI_API_KEY")
            
            if openai_key:
                components.news_aggregator = NewsAggregator(openai_api_key=openai_key)
                logger.info("✅ NewsAggregator 초기화 완료")
            else:
                logger.warning("⚠️ OPENAI_API_KEY 없음, NewsAggregator 건너뜀")
                components.news_aggregator = None
        except Exception as e:
            logger.error(f"❌ NewsAggregator 초기화 실패: {e}")
            components.news_aggregator = None

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
        # 전체 실패 시에도 HTTP 클라이언트는 최소한 초기화
        if not components.http_client:
            components.http_client = httpx.AsyncClient()
            logger.info("✅ 최소한의 HTTP 클라이언트 초기화 완료")
        # 예외를 다시 발생시키지 않고 부분적으로라도 서비스 제공


async def cleanup_components():
    """컴포넌트 정리"""
    logger.info("🔄 컴포넌트 정리 중...")

    if components.http_client:
        await components.http_client.aclose()
        logger.info("✅ HTTP 클라이언트 종료 완료")

    logger.info("✅ 컴포넌트 정리 완료")
