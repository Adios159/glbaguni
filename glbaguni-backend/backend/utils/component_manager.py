#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
강화된 컴포넌트 관리 시스템
안전하고 체계적인 컴포넌트 초기화 및 관리 with 재시도 로직
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional, Type, Callable
from datetime import datetime

import httpx

logger = logging.getLogger("glbaguni.component_manager")


class ComponentStatus:
    """컴포넌트 상태 관리 (강화버전)"""
    def __init__(self, name: str):
        self.name = name
        self.initialized = False
        self.error: Optional[str] = None
        self.instance = None
        self.init_time: Optional[float] = None
        self.retry_count = 0
        self.last_attempt: Optional[datetime] = None
        self.health_check_func: Optional[Callable] = None
        self.is_critical = False  # 필수 컴포넌트 여부
        
    def reset(self):
        """상태 초기화"""
        self.initialized = False
        self.error = None
        self.instance = None
        self.retry_count = 0
        self.last_attempt = None


class RobustComponentManager:
    """견고한 컴포넌트 관리자 (재시도 로직 포함)"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.components: Dict[str, ComponentStatus] = {}
        self.http_client: Optional[httpx.AsyncClient] = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.initialization_complete = False
        
    def register_component(self, name: str, is_critical: bool = False, health_check_func: Optional[Callable] = None) -> ComponentStatus:
        """컴포넌트 등록 (강화버전)"""
        if name not in self.components:
            self.components[name] = ComponentStatus(name)
            self.components[name].is_critical = is_critical
            self.components[name].health_check_func = health_check_func
        return self.components[name]
    
    async def initialize_http_client(self) -> bool:
        """HTTP 클라이언트 초기화 (재시도 포함)"""
        for attempt in range(self.max_retries + 1):
            try:
                if self.http_client:
                    await self.http_client.aclose()
                    
                self.http_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=60.0),
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
                    headers={
                        "User-Agent": "Glbaguni/3.0.0 (RSS Summarizer Bot)",
                        "Accept": "application/json, text/plain, */*",
                    },
                )
                logger.info("✅ HTTP 클라이언트 초기화 완료")
                return True
                
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"⚠️ HTTP 클라이언트 초기화 실패 (시도 {attempt + 1}/{self.max_retries + 1}): {e}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"❌ HTTP 클라이언트 초기화 최종 실패: {e}")
                    return False
        return False
    
    async def safe_initialize_component(
        self, 
        name: str, 
        component_class: Type, 
        is_critical: bool = False,
        health_check_func: Optional[Callable] = None,
        **kwargs
    ) -> bool:
        """안전한 컴포넌트 초기화 (재시도 로직 포함)"""
        component_status = self.register_component(name, is_critical, health_check_func)
        
        for attempt in range(self.max_retries + 1):
            start_time = time.time()
            component_status.last_attempt = datetime.now()
            component_status.retry_count = attempt
            
            try:
                logger.info(f"🔧 {name} 초기화 시작... (시도 {attempt + 1}/{self.max_retries + 1})")
                
                # 이전 인스턴스가 있으면 정리
                if component_status.instance:
                    await self._cleanup_component_instance(component_status.instance)
                
                # 컴포넌트 인스턴스 생성
                if asyncio.iscoroutinefunction(component_class):
                    component_status.instance = await component_class(**kwargs)
                else:
                    component_status.instance = component_class(**kwargs)
                
                # 헬스체크 수행 (있으면)
                if health_check_func:
                    health_ok = await self._perform_health_check(health_check_func, component_status.instance)
                    if not health_ok:
                        raise Exception("헬스체크 실패")
                
                component_status.initialized = True
                component_status.error = None
                component_status.init_time = time.time() - start_time
                
                logger.info(f"✅ {name} 초기화 완료 ({component_status.init_time:.2f}초)")
                return True
                
            except Exception as e:
                component_status.error = str(e)
                component_status.init_time = time.time() - start_time
                component_status.initialized = False
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (attempt + 1)
                    logger.warning(f"⚠️ {name} 초기화 실패 (시도 {attempt + 1}/{self.max_retries + 1}): {e}")
                    logger.info(f"🔄 {delay}초 후 재시도...")
                    await asyncio.sleep(delay)
                else:
                    error_level = "error" if is_critical else "warning"
                    getattr(logger, error_level)(f"❌ {name} 초기화 최종 실패: {e}")
                    
        return False
    
    async def _cleanup_component_instance(self, instance):
        """컴포넌트 인스턴스 정리"""
        try:
            if hasattr(instance, 'cleanup') and callable(instance.cleanup):
                if asyncio.iscoroutinefunction(instance.cleanup):
                    await instance.cleanup()
                else:
                    instance.cleanup()
            elif hasattr(instance, 'close') and callable(instance.close):
                if asyncio.iscoroutinefunction(instance.close):
                    await instance.close()
                else:
                    instance.close()
        except Exception as e:
            logger.warning(f"⚠️ 컴포넌트 인스턴스 정리 중 오류: {e}")
    
    async def _perform_health_check(self, health_check_func: Callable, instance) -> bool:
        """헬스체크 수행"""
        try:
            if asyncio.iscoroutinefunction(health_check_func):
                return await health_check_func(instance)
            else:
                return health_check_func(instance)
        except Exception as e:
            logger.warning(f"⚠️ 헬스체크 실패: {e}")
            return False
    
    async def retry_failed_components(self) -> Dict[str, bool]:
        """실패한 컴포넌트 재시도"""
        retry_results = {}
        
        for name, status in self.components.items():
            if not status.initialized and status.error:
                logger.info(f"🔄 실패한 컴포넌트 재시도: {name}")
                status.reset()
                # 여기서는 원래 초기화 함수를 다시 호출해야 하지만, 
                # 간단히 상태만 재설정하고 실제 재시도는 manual trigger로 처리
                retry_results[name] = False
                
        return retry_results
    
    def get_component(self, name: str) -> Optional[Any]:
        """컴포넌트 가져오기"""
        if name in self.components and self.components[name].initialized:
            return self.components[name].instance
        return None
    
    def is_component_available(self, name: str) -> bool:
        """컴포넌트 사용 가능 여부 확인"""
        return name in self.components and self.components[name].initialized
    
    def get_detailed_status_report(self) -> Dict[str, Any]:
        """상세한 컴포넌트 상태 리포트"""
        now = datetime.now()
        total = len(self.components)
        initialized = sum(1 for c in self.components.values() if c.initialized)
        failed = sum(1 for c in self.components.values() if c.error and not c.initialized)
        critical_failed = sum(1 for c in self.components.values() if c.error and not c.initialized and c.is_critical)
        
        # 전체 시스템 상태 결정
        system_status = "healthy"
        if critical_failed > 0:
            system_status = "critical"
        elif failed > 0:
            system_status = "degraded"
        elif initialized < total:
            system_status = "warning"
        
        report = {
            "system_status": system_status,
            "summary": {
                "total_components": total,
                "initialized_components": initialized,
                "failed_components": failed,
                "critical_failed": critical_failed,
                "success_rate": round((initialized / total * 100) if total > 0 else 0, 1),
                "initialization_complete": self.initialization_complete,
            },
            "components": {}
        }
        
        for name, status in self.components.items():
            report["components"][name] = {
                "name": name,
                "initialized": status.initialized,
                "is_critical": status.is_critical,
                "error": status.error,
                "init_time": status.init_time,
                "retry_count": status.retry_count,
                "last_attempt": status.last_attempt.isoformat() if status.last_attempt else None,
                "status": "ok" if status.initialized else ("failed" if status.error else "pending")
            }
        
        return report
    
    async def perform_health_checks(self) -> Dict[str, bool]:
        """모든 컴포넌트 헬스체크 수행"""
        health_results = {}
        
        for name, status in self.components.items():
            if status.initialized and status.health_check_func:
                try:
                    is_healthy = await self._perform_health_check(status.health_check_func, status.instance)
                    health_results[name] = is_healthy
                    if not is_healthy:
                        logger.warning(f"⚠️ {name} 헬스체크 실패")
                except Exception as e:
                    health_results[name] = False
                    logger.warning(f"⚠️ {name} 헬스체크 오류: {e}")
            else:
                health_results[name] = status.initialized
                
        return health_results
    
    async def cleanup(self):
        """리소스 정리 (강화버전)"""
        logger.info("🔄 컴포넌트 정리 시작...")
        
        # 각 컴포넌트 개별 정리
        for name, status in self.components.items():
            if status.instance:
                try:
                    await self._cleanup_component_instance(status.instance)
                    logger.info(f"✅ {name} 정리 완료")
                except Exception as e:
                    logger.warning(f"⚠️ {name} 정리 실패: {e}")
        
        # HTTP 클라이언트 정리
        if self.http_client:
            try:
                await self.http_client.aclose()
                logger.info("✅ HTTP 클라이언트 종료 완료")
            except Exception as e:
                logger.warning(f"⚠️ HTTP 클라이언트 종료 실패: {e}")


# 전역 컴포넌트 관리자 인스턴스 (강화버전)
component_manager = RobustComponentManager(max_retries=2, retry_delay=1.0)


# === 헬스체크 함수들 ===
async def check_fetcher_health(instance) -> bool:
    """Fetcher 헬스체크 - ArticleFetcher 실제 메서드에 맞춤"""
    try:
        # 1. 실제 ArticleFetcher 메서드들 확인
        required_methods = ['fetch_html_article', 'fetch_rss_articles', 'fetch_multiple_sources']
        
        for method_name in required_methods:
            if not hasattr(instance, method_name):
                logger.debug(f"❌ Fetcher: {method_name} 메서드 없음")
                return False
            
            if not callable(getattr(instance, method_name)):
                logger.debug(f"❌ Fetcher: {method_name}가 호출 가능하지 않음")
                return False
        
        # 2. session 속성 확인 (HTTP 요청을 위해 필요)
        if not hasattr(instance, 'session'):
            logger.debug("❌ Fetcher: session 속성 없음")
            return False
        
        logger.debug("✅ Fetcher: 모든 필수 메서드 및 속성 확인됨")
        return True
        
    except Exception as e:
        logger.debug(f"❌ Fetcher: 헬스체크 실패: {e}")
        return False

async def check_summarizer_health(instance) -> bool:
    """Summarizer 헬스체크"""
    try:
        return hasattr(instance, 'summarize') and callable(instance.summarize)
    except:
        return False

async def check_notifier_health(instance) -> bool:
    """Notifier 헬스체크"""
    try:
        return hasattr(instance, 'send_summary_email') and callable(instance.send_summary_email)
    except:
        return False


async def initialize_all_components():
    """모든 컴포넌트 안전 초기화 (강화버전)"""
    start_time = time.time()
    logger.info("🚀 강화된 컴포넌트 초기화 시작...")
    
    try:
        # 1. HTTP 클라이언트 먼저 초기화
        await component_manager.initialize_http_client()
        
        # 2. 데이터베이스 초기화
        await safe_init_database()
        
        # 3. 핵심 컴포넌트들 초기화 (is_critical=True)
        await init_core_components()
        
        # 4. 선택적 컴포넌트들 초기화
        await init_optional_components()
        
        # 5. 초기화 완료 표시
        component_manager.initialization_complete = True
        
        # 6. 상태 리포트
        elapsed = time.time() - start_time
        report = component_manager.get_detailed_status_report()
        
        logger.info(f"🎉 컴포넌트 초기화 완료! (소요시간: {elapsed:.2f}초)")
        logger.info(f"📊 초기화 결과: {report['summary']['initialized_components']}/{report['summary']['total_components']} 성공 ({report['summary']['success_rate']}%)")
        
        if report['summary']['critical_failed'] > 0:
            logger.error(f"❌ {report['summary']['critical_failed']}개 필수 컴포넌트 실패!")
        elif report['summary']['failed_components'] > 0:
            logger.warning(f"⚠️ {report['summary']['failed_components']}개 선택적 컴포넌트 실패 (서버는 정상 작동)")
            
    except Exception as e:
        logger.error(f"❌ 컴포넌트 초기화 중 심각한 오류: {e}")
        raise


async def safe_init_database():
    """안전한 데이터베이스 초기화"""
    try:
        # 동적 import로 순환 참조 방지
        from backend.database import init_database
        
        if callable(init_database):
            if asyncio.iscoroutinefunction(init_database):
                await init_database()
            else:
                init_database()
        
        logger.info("✅ 데이터베이스 초기화 완료")
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ 데이터베이스 초기화 실패: {e}")
        return False


async def init_core_components():
    """핵심 컴포넌트 초기화 (필수)"""
    try:
        from backend.fetcher import ArticleFetcher
        from backend.summarizer import ArticleSummarizer
        from backend.history_service import HistoryService
        
        # fetcher는 선택적 컴포넌트로 변경 (네트워크 문제로 인한 실패를 방지)
        await component_manager.safe_initialize_component(
            "fetcher", 
            ArticleFetcher, 
            is_critical=False,  # 선택적 컴포넌트로 변경
            health_check_func=check_fetcher_health
        )
        await component_manager.safe_initialize_component(
            "summarizer", 
            ArticleSummarizer, 
            is_critical=True,
            health_check_func=check_summarizer_health
        )
        await component_manager.safe_initialize_component(
            "history_service", 
            HistoryService, 
            is_critical=False  # 히스토리는 선택적
        )
        
    except ImportError as e:
        logger.error(f"❌ 핵심 컴포넌트 import 실패: {e}")


async def init_optional_components():
    """선택적 컴포넌트 초기화 (실패해도 서버 계속 실행)"""
    
    # NewsAggregator 초기화
    await init_news_aggregator()
    
    # EmailNotifier 초기화  
    await init_email_notifier()


async def init_news_aggregator():
    """NewsAggregator 안전 초기화"""
    try:
        from backend.news_aggregator import NewsAggregator
        
        # 환경변수에서 API 키 가져오기
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if openai_key:
            await component_manager.safe_initialize_component(
                "news_aggregator", 
                NewsAggregator, 
                is_critical=False,  # 선택적 컴포넌트
                openai_api_key=openai_key
            )
        else:
            logger.warning("⚠️ OPENAI_API_KEY 없음, NewsAggregator 건너뜀")
            
    except Exception as e:
        logger.error(f"❌ NewsAggregator 초기화 준비 실패: {e}")


async def init_email_notifier():
    """EmailNotifier 안전 초기화"""
    try:
        from backend.notifier import EmailNotifier
        
        # SMTP 설정 체크
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        
        if smtp_username and smtp_password:
            await component_manager.safe_initialize_component(
                "notifier", 
                EmailNotifier, 
                is_critical=False,  # 선택적 컴포넌트
                health_check_func=check_notifier_health
            )
        else:
            logger.warning("⚠️ SMTP 설정 없음, EmailNotifier 건너뜀")
            
    except Exception as e:
        logger.error(f"❌ EmailNotifier 초기화 준비 실패: {e}")


# 편의 함수들
def get_fetcher():
    return component_manager.get_component("fetcher")

def get_summarizer():
    return component_manager.get_component("summarizer")

def get_history_service():
    return component_manager.get_component("history_service")

def get_news_aggregator():
    return component_manager.get_component("news_aggregator")

def get_notifier():
    return component_manager.get_component("notifier")

def get_http_client():
    return component_manager.http_client

def get_component_status():
    """컴포넌트 상태 조회"""
    return component_manager.get_detailed_status_report()

async def retry_failed_components():
    """실패한 컴포넌트 재시도"""
    return await component_manager.retry_failed_components()

async def perform_component_health_checks():
    """모든 컴포넌트 헬스체크"""
    return await component_manager.perform_health_checks()

async def cleanup_components():
    """컴포넌트 정리 (강화버전)"""
    await component_manager.cleanup() 