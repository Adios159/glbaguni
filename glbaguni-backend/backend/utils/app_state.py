#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
애플리케이션 상태 관리
"""

import asyncio
import logging
import time
import traceback
from typing import Any, Dict, Optional

import httpx


class ApplicationState:
    """애플리케이션 상태 관리 클래스"""

    def __init__(self):
        # 컴포넌트들
        self.http_client: Optional[httpx.AsyncClient] = None
        self.news_aggregator = None
        self.fetcher = None
        self.summarizer = None
        self.notifier = None
        self.history_service = None

        # 상태 정보
        self.initialized = False
        self.start_time = None
        self.request_count = 0

    async def initialize(self, importer) -> None:
        """애플리케이션 컴포넌트 초기화"""
        try:
            self.start_time = time.time()
            logger = logging.getLogger("glbaguni")
            logger.info("🔧 애플리케이션 컴포넌트 초기화 시작...")

            # HTTP 클라이언트 초기화
            await self._init_http_client()

            # 데이터베이스 초기화
            await self._init_database(importer)

            # 서비스 컴포넌트 초기화
            await self._init_services(importer)

            elapsed = time.time() - self.start_time
            self.initialized = True
            logger.info(f"🎉 애플리케이션 초기화 완료! ({elapsed:.2f}초)")

        except Exception as e:
            logger = logging.getLogger("glbaguni")
            logger.error(f"❌ 애플리케이션 초기화 실패: {e}")
            logger.error(traceback.format_exc())
            raise

    async def _init_http_client(self) -> None:
        """HTTP 클라이언트 초기화"""
        try:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                headers={"User-Agent": "Glbaguni/2.2.0"},
            )
            logger = logging.getLogger("glbaguni")
            logger.info("✅ HTTP 클라이언트 초기화 완료")
        except Exception as e:
            logger = logging.getLogger("glbaguni")
            logger.error(f"HTTP 클라이언트 초기화 실패: {e}")
            raise

    async def _init_database(self, importer) -> None:
        """데이터베이스 초기화"""
        try:
            init_db_func = importer.services["init_database"]
            # 동기 함수를 비동기로 실행
            await asyncio.to_thread(init_db_func)
            logger = logging.getLogger("glbaguni")
            logger.info("✅ 데이터베이스 초기화 완료")
        except Exception as e:
            logger = logging.getLogger("glbaguni")
            logger.error(f"데이터베이스 초기화 실패: {e}")
            raise

    async def _init_services(self, importer) -> None:
        """서비스 컴포넌트들 초기화"""
        try:
            logger = logging.getLogger("glbaguni")
            
            # 필수 서비스들
            self.fetcher = importer.services["ArticleFetcher"]()
            self.summarizer = importer.services["ArticleSummarizer"]()
            self.history_service = importer.services["HistoryService"]()

            # 뉴스 애그리게이터 (API 키 필요)
            openai_key = importer.services["settings"].OPENAI_API_KEY
            self.news_aggregator = importer.services["NewsAggregator"](
                openai_api_key=openai_key
            )

            # 이메일 노티파이어 (선택적)
            try:
                self.notifier = importer.services["EmailNotifier"]()
                logger.info("✅ 이메일 서비스 초기화 완료")
            except Exception as e:
                logger.warning(f"⚠️ 이메일 서비스 초기화 실패: {e}")
                self.notifier = None

            logger.info("✅ 서비스 컴포넌트 초기화 완료")

        except Exception as e:
            logger = logging.getLogger("glbaguni")
            logger.error(f"서비스 초기화 중 오류: {e}")
            raise

    async def cleanup(self) -> None:
        """애플리케이션 정리"""
        try:
            logger = logging.getLogger("glbaguni")
            logger.info("🔄 애플리케이션 정리 중...")

            if self.http_client:
                await self.http_client.aclose()
                logger.info("✅ HTTP 클라이언트 종료 완료")

            self.initialized = False
            logger.info("✅ 애플리케이션 정리 완료")

        except Exception as e:
            logger = logging.getLogger("glbaguni")
            logger.error(f"애플리케이션 정리 중 오류: {e}")

    def increment_request_count(self):
        """요청 카운트 증가"""
        self.request_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """애플리케이션 통계 반환"""
        return {
            "initialized": self.initialized,
            "uptime_seconds": time.time() - self.start_time if self.start_time else 0,
            "request_count": self.request_count,
            "components": {
                "http_client": bool(self.http_client),
                "fetcher": bool(self.fetcher),
                "summarizer": bool(self.summarizer),
                "notifier": bool(self.notifier),
                "history_service": bool(self.history_service),
                "news_aggregator": bool(self.news_aggregator),
            },
        } 