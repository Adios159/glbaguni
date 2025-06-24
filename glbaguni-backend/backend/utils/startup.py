#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
스타트업 관련 유틸리티들
- 모듈 임포트 관리
- 로깅 시스템 초기화  
- 환경변수 검증
"""

import logging
import os
import sys
from dotenv import load_dotenv

# 환경변수 우선 로드
load_dotenv()


class SafeImporter:
    """안전한 모듈 임포트를 위한 클래스"""

    def __init__(self):
        self.models = {}
        self.services = {}
        self.security_available = False
        self._import_all_modules()

    def _import_all_modules(self):
        """모든 필요한 모듈을 안전하게 임포트"""
        try:
            self._import_models()
            self._import_services()
            self._import_security()
        except Exception as e:
            logging.error(f"모듈 임포트 실패: {e}")
            sys.exit(1)

    def _import_models(self):
        """모델 클래스들 임포트"""
        try:
            # 상대 임포트 시도
            from ..models import (
                Article,
                ArticleSummary,
                HistoryItem,
                HistoryResponse,
                NewsSearchRequest,
                NewsSearchResponse,
                RecommendationItem,
                RecommendationResponse,
                SummaryRequest,
                SummaryResponse,
                UserStatsResponse,
            )
            self._store_models(locals())
            logging.info("✅ 상대 임포트로 모델 로드 완료")
        except ImportError:
            # 절대 임포트로 폴백
            try:
                from models import (
                    Article,
                    ArticleSummary,
                    HistoryItem,
                    HistoryResponse,
                    NewsSearchRequest,
                    NewsSearchResponse,
                    RecommendationItem,
                    RecommendationResponse,
                    SummaryRequest,
                    SummaryResponse,
                    UserStatsResponse,
                )
                self._store_models(locals())
                logging.info("✅ 절대 임포트로 모델 로드 완료")
            except ImportError as e:
                logging.error(f"모델 임포트 실패: {e}")
                raise

    def _import_services(self):
        """서비스 클래스들 임포트"""
        try:
            # 상대 임포트 시도
            from ..config import settings
            from ..database import get_db, init_database
            from ..fetcher import ArticleFetcher
            from ..history_service import HistoryService
            from ..news_aggregator import NewsAggregator
            from ..notifier import EmailNotifier
            from ..summarizer import ArticleSummarizer

            self.services.update({
                "ArticleFetcher": ArticleFetcher,
                "ArticleSummarizer": ArticleSummarizer,
                "EmailNotifier": EmailNotifier,
                "settings": settings,
                "get_db": get_db,
                "init_database": init_database,
                "HistoryService": HistoryService,
                "NewsAggregator": NewsAggregator,
            })
            logging.info("✅ 상대 임포트로 서비스 로드 완료")
        except ImportError:
            # 절대 임포트로 폴백
            try:
                from config import settings
                from database import get_db, init_database
                from fetcher import ArticleFetcher
                from history_service import HistoryService
                from news_aggregator import NewsAggregator
                from notifier import EmailNotifier
                from summarizer import ArticleSummarizer

                self.services.update({
                    "ArticleFetcher": ArticleFetcher,
                    "ArticleSummarizer": ArticleSummarizer,
                    "EmailNotifier": EmailNotifier,
                    "settings": settings,
                    "get_db": get_db,
                    "init_database": init_database,
                    "HistoryService": HistoryService,
                    "NewsAggregator": NewsAggregator,
                })
                logging.info("✅ 절대 임포트로 서비스 로드 완료")
            except ImportError as e:
                logging.error(f"서비스 임포트 실패: {e}")
                raise

    def _import_security(self):
        """보안 모듈 임포트 (선택적)"""
        try:
            from ..security import sanitize_response, validate_input
            self.services.update({
                "validate_input": validate_input,
                "sanitize_response": sanitize_response,
            })
            self.security_available = True
            logging.info("✅ 보안 모듈 로드 완료")
        except ImportError:
            try:
                from security import sanitize_response, validate_input
                self.services.update({
                    "validate_input": validate_input,
                    "sanitize_response": sanitize_response,
                })
                self.security_available = True
                logging.info("✅ 보안 모듈 로드 완료")
            except ImportError:
                logging.warning("⚠️ 보안 모듈을 찾을 수 없습니다")
                self.security_available = False

    def _store_models(self, local_vars):
        """모델 클래스들을 저장"""
        model_names = [
            "SummaryRequest", "SummaryResponse", "ArticleSummary", "HistoryResponse",
            "RecommendationResponse", "UserStatsResponse", "HistoryItem", 
            "RecommendationItem", "NewsSearchRequest", "NewsSearchResponse", "Article",
        ]
        for name in model_names:
            if name in local_vars:
                self.models[name] = local_vars[name]


class LoggingSystem:
    """로깅 시스템 관리"""

    @staticmethod
    def setup_logging() -> logging.Logger:
        """로깅 시스템 초기화"""
        try:
            # 로그 디렉토리 생성
            os.makedirs("logs", exist_ok=True)

            # 로그 포맷 설정
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

            # 핸들러 설정
            handlers = [
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("logs/glbaguni_optimized.log", encoding="utf-8"),
            ]

            # 기본 로깅 설정
            logging.basicConfig(
                level=logging.INFO, format=log_format, handlers=handlers, force=True
            )

            # 외부 라이브러리 로그 레벨 조정
            for lib in ["httpx", "httpcore", "urllib3", "uvicorn.access"]:
                logging.getLogger(lib).setLevel(logging.WARNING)

            logger = logging.getLogger("glbaguni")
            logger.info("🚀 글바구니 서버 v2.2.0 로깅 시스템 초기화 완료")
            return logger
        except Exception as e:
            print(f"로깅 시스템 초기화 실패: {e}")
            sys.exit(1)


class EnvironmentChecker:
    """환경변수 검증 클래스"""

    REQUIRED_VARS = ["OPENAI_API_KEY"]
    OPTIONAL_VARS = ["SMTP_SERVER", "SMTP_USERNAME", "SMTP_PASSWORD"]

    @classmethod
    def validate_environment(cls) -> bool:
        """환경변수 검증"""
        try:
            logger = logging.getLogger("glbaguni")
            
            # 필수 환경변수 확인
            missing_required = []
            for var in cls.REQUIRED_VARS:
                value = os.getenv(var)
                if not value:
                    missing_required.append(var)
                elif var == "OPENAI_API_KEY":
                    if not value.startswith("sk-") or len(value) < 20:
                        logger.error(f"❌ {var}의 형식이 올바르지 않습니다")
                        return False

            if missing_required:
                logger.error(f"❌ 필수 환경변수 누락: {', '.join(missing_required)}")
                logger.error("💡 .env 파일을 확인하거나 환경변수를 설정하세요")
                return False

            # 선택적 환경변수 확인
            missing_optional = [var for var in cls.OPTIONAL_VARS if not os.getenv(var)]
            if missing_optional:
                logger.warning(f"⚠️ 선택적 환경변수 누락: {', '.join(missing_optional)}")
                logger.warning("💡 이메일 기능이 제한될 수 있습니다")

            logger.info("✅ 환경변수 검증 완료")
            return True
        except Exception as e:
            logger = logging.getLogger("glbaguni")
            logger.error(f"환경변수 검증 중 오류: {e}")
            return False 