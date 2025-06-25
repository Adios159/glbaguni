#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메모리 관리 시스템
서버 메모리를 주기적으로 모니터링하고 최적화하는 기능을 제공합니다.
"""

import asyncio
import gc
import logging
import os
import psutil
import time
import tracemalloc
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Callable
import weakref
import threading

try:
    from utils.logging_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("memory_manager")


@dataclass
class MemoryStats:
    """메모리 통계 정보"""
    timestamp: datetime
    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    memory_percent: float
    process_memory_mb: float
    process_memory_percent: float
    swap_memory_mb: float
    swap_percent: float
    gc_collections: Dict[int, int] = field(default_factory=dict)
    cache_size: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_memory_mb": self.total_memory_mb,
            "available_memory_mb": self.available_memory_mb,
            "used_memory_mb": self.used_memory_mb,
            "memory_percent": self.memory_percent,
            "process_memory_mb": self.process_memory_mb,
            "process_memory_percent": self.process_memory_percent,
            "swap_memory_mb": self.swap_memory_mb,
            "swap_percent": self.swap_percent,
            "gc_collections": self.gc_collections,
            "cache_size": self.cache_size
        }


@dataclass
class MemoryConfig:
    """메모리 관리 설정"""
    # 모니터링 설정
    monitoring_interval_seconds: int = 60  # 1분마다 모니터링
    cleanup_interval_seconds: int = 300    # 5분마다 정리
    
    # 임계값 설정 (백분율)
    warning_threshold: float = 70.0    # 경고 임계값
    critical_threshold: float = 85.0   # 심각 임계값
    cleanup_threshold: float = 80.0    # 정리 시작 임계값
    
    # 캐시 관리
    max_cache_size: int = 1000
    cache_cleanup_ratio: float = 0.3   # 30% 정리
    
    # 히스토리 관리
    max_history_size: int = 288        # 24시간 (5분 간격)
    
    # 알림 설정
    enable_alerts: bool = True
    alert_cooldown_minutes: int = 15   # 15분간 동일 알림 방지


class CacheManager:
    """캐시 관리자"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.caches: Dict[str, Any] = {}
        self.access_times: Dict[str, float] = {}
        self.lock = threading.RLock()
        
    def register_cache(self, name: str, cache_object: Any):
        """캐시 객체 등록"""
        with self.lock:
            self.caches[name] = weakref.ref(cache_object)
            logger.debug(f"캐시 등록: {name}")
    
    def get_cache_size(self) -> int:
        """전체 캐시 크기 반환"""
        total_size = 0
        with self.lock:
            for name, cache_ref in list(self.caches.items()):
                cache = cache_ref()
                if cache is None:
                    del self.caches[name]
                    continue
                    
                if hasattr(cache, '__len__'):
                    total_size += len(cache)
                elif hasattr(cache, 'size'):
                    total_size += cache.size()
                    
        return total_size
    
    def cleanup_caches(self, cleanup_ratio: float = 0.3):
        """캐시 정리"""
        cleaned_count = 0
        
        with self.lock:
            for name, cache_ref in list(self.caches.items()):
                cache = cache_ref()
                if cache is None:
                    del self.caches[name]
                    continue
                
                # 캐시별 정리 로직
                if hasattr(cache, 'clear'):
                    # 딕셔너리 타입 캐시
                    if hasattr(cache, 'items'):
                        items = list(cache.items())
                        items_to_remove = int(len(items) * cleanup_ratio)
                        
                        # LRU 방식으로 정리 (가장 오래된 항목부터)
                        if items_to_remove > 0:
                            for i in range(items_to_remove):
                                if items:
                                    key = items[i][0]
                                    cache.pop(key, None)
                                    cleaned_count += 1
                
                elif hasattr(cache, 'cleanup'):
                    # 커스텀 정리 메서드가 있는 경우
                    try:
                        cache.cleanup(cleanup_ratio)
                        cleaned_count += 10  # 대략적인 추정
                    except Exception as e:
                        logger.warning(f"캐시 {name} 정리 실패: {e}")
        
        if cleaned_count > 0:
            logger.info(f"🧹 캐시 정리 완료: {cleaned_count}개 항목 제거")
        
        return cleaned_count


class MemoryMonitor:
    """메모리 모니터링 클래스"""
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        self.process = psutil.Process()
        self.stats_history: deque = deque(maxlen=config.max_history_size)
        self.last_alert_time: Dict[str, datetime] = {}
        self.cache_manager = CacheManager(config.max_cache_size)
        
        # tracemalloc 시작
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            logger.info("📊 메모리 추적 시작")
    
    def get_current_stats(self) -> MemoryStats:
        """현재 메모리 통계 수집"""
        try:
            # 시스템 메모리 정보
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # 프로세스 메모리 정보
            process_memory = self.process.memory_info()
            
            # GC 통계
            gc_stats = {}
            for i in range(3):
                gc_stats[i] = gc.get_count()[i]
            
            # 캐시 크기
            cache_size = self.cache_manager.get_cache_size()
            
            stats = MemoryStats(
                timestamp=datetime.now(),
                total_memory_mb=memory.total / 1024 / 1024,
                available_memory_mb=memory.available / 1024 / 1024,
                used_memory_mb=memory.used / 1024 / 1024,
                memory_percent=memory.percent,
                process_memory_mb=process_memory.rss / 1024 / 1024,
                process_memory_percent=self.process.memory_percent(),
                swap_memory_mb=swap.used / 1024 / 1024,
                swap_percent=swap.percent,
                gc_collections=gc_stats,
                cache_size=cache_size
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"메모리 통계 수집 실패: {e}")
            # 기본값 반환
            return MemoryStats(
                timestamp=datetime.now(),
                total_memory_mb=0,
                available_memory_mb=0,
                used_memory_mb=0,
                memory_percent=0,
                process_memory_mb=0,
                process_memory_percent=0,
                swap_memory_mb=0,
                swap_percent=0
            )
    
    def add_stats(self, stats: MemoryStats):
        """통계 히스토리에 추가"""
        self.stats_history.append(stats)
        
        # 임계값 확인 및 알림
        self._check_thresholds(stats)
    
    def _check_thresholds(self, stats: MemoryStats):
        """임계값 확인 및 알림"""
        if not self.config.enable_alerts:
            return
        
        current_time = datetime.now()
        
        # 메모리 사용률 확인
        if stats.memory_percent >= self.config.critical_threshold:
            if self._should_send_alert("critical_memory", current_time):
                logger.critical(
                    f"🚨 CRITICAL: 메모리 사용률 {stats.memory_percent:.1f}% "
                    f"(임계값: {self.config.critical_threshold}%)"
                )
                self.last_alert_time["critical_memory"] = current_time
                
        elif stats.memory_percent >= self.config.warning_threshold:
            if self._should_send_alert("warning_memory", current_time):
                logger.warning(
                    f"⚠️ WARNING: 메모리 사용률 {stats.memory_percent:.1f}% "
                    f"(경고값: {self.config.warning_threshold}%)"
                )
                self.last_alert_time["warning_memory"] = current_time
        
        # 스왑 사용률 확인
        if stats.swap_percent > 50:
            if self._should_send_alert("swap_usage", current_time):
                logger.warning(f"⚠️ 스왑 메모리 사용률 높음: {stats.swap_percent:.1f}%")
                self.last_alert_time["swap_usage"] = current_time
    
    def _should_send_alert(self, alert_type: str, current_time: datetime) -> bool:
        """알림 발송 여부 확인 (쿨다운 적용)"""
        last_time = self.last_alert_time.get(alert_type)
        if last_time is None:
            return True
        
        cooldown = timedelta(minutes=self.config.alert_cooldown_minutes)
        return current_time - last_time > cooldown
    
    def get_memory_trend(self, minutes: int = 30) -> Dict[str, Any]:
        """메모리 사용 트렌드 분석"""
        if not self.stats_history:
            return {"trend": "stable", "avg_usage": 0, "peak_usage": 0}
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_stats = [s for s in self.stats_history if s.timestamp > cutoff_time]
        
        if len(recent_stats) < 2:
            return {"trend": "stable", "avg_usage": 0, "peak_usage": 0}
        
        usage_values = [s.memory_percent for s in recent_stats]
        avg_usage = sum(usage_values) / len(usage_values)
        peak_usage = max(usage_values)
        
        # 트렌드 계산 (첫 10개와 마지막 10개 비교)
        if len(recent_stats) >= 20:
            early_avg = sum(usage_values[:10]) / 10
            late_avg = sum(usage_values[-10:]) / 10
            
            if late_avg > early_avg + 5:
                trend = "increasing"
            elif late_avg < early_avg - 5:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "avg_usage": avg_usage,
            "peak_usage": peak_usage,
            "sample_count": len(recent_stats)
        }


class MemoryOptimizer:
    """메모리 최적화 클래스"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.optimization_count = 0
    
    async def optimize_memory(self, force: bool = False) -> Dict[str, Any]:
        """메모리 최적화 실행"""
        optimization_start = time.time()
        results = {
            "optimization_time": 0,
            "gc_collected": 0,
            "cache_cleaned": 0,
            "memory_freed_mb": 0
        }
        
        try:
            # 최적화 전 메모리 사용량
            before_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # 1. 가비지 컬렉션 실행
            collected_objects = 0
            for generation in range(3):
                collected = gc.collect(generation)
                collected_objects += collected
            
            results["gc_collected"] = collected_objects
            
            # 2. 캐시 정리
            if force or self.cache_manager.get_cache_size() > self.cache_manager.max_size:
                cleaned_count = self.cache_manager.cleanup_caches(0.3)
                results["cache_cleaned"] = cleaned_count
            
            # 3. 약한 참조 정리
            try:
                import weakref
                weakref._remove_dead_weakref = True
            except:
                pass
            
            # 최적화 후 메모리 사용량
            after_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_freed = max(0, before_memory - after_memory)
            
            results["memory_freed_mb"] = memory_freed
            results["optimization_time"] = time.time() - optimization_start
            
            self.optimization_count += 1
            
            if memory_freed > 1:  # 1MB 이상 해제된 경우만 로그
                logger.info(
                    f"🔧 메모리 최적화 완료: "
                    f"GC {collected_objects}개 객체, "
                    f"캐시 {cleaned_count}개 항목, "
                    f"{memory_freed:.1f}MB 해제"
                )
            
            return results
            
        except Exception as e:
            logger.error(f"메모리 최적화 실패: {e}")
            results["error"] = str(e)
            return results


class MemoryManager:
    """통합 메모리 관리자"""
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.monitor = MemoryMonitor(self.config)
        self.optimizer = MemoryOptimizer(self.monitor.cache_manager)
        
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        logger.info(f"🧠 메모리 관리자 초기화 완료")
    
    async def start(self):
        """메모리 관리 시작"""
        if self._is_running:
            logger.warning("메모리 관리자가 이미 실행 중입니다")
            return
        
        self._is_running = True
        
        # 모니터링 태스크 시작
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        # 정리 태스크 시작
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("🚀 메모리 관리 시작")
    
    async def stop(self):
        """메모리 관리 중지"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # 태스크 취소
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("⏹️ 메모리 관리 중지")
    
    async def _monitoring_loop(self):
        """메모리 모니터링 루프"""
        while self._is_running:
            try:
                stats = self.monitor.get_current_stats()
                self.monitor.add_stats(stats)
                
                # 디버그 로그 (10분마다)
                if len(self.monitor.stats_history) % 10 == 0:
                    logger.debug(
                        f"💾 메모리 상태: "
                        f"시스템 {stats.memory_percent:.1f}%, "
                        f"프로세스 {stats.process_memory_mb:.1f}MB, "
                        f"캐시 {stats.cache_size}개"
                    )
                
                await asyncio.sleep(self.config.monitoring_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"메모리 모니터링 오류: {e}")
                await asyncio.sleep(10)  # 오류 시 10초 대기
    
    async def _cleanup_loop(self):
        """메모리 정리 루프"""
        while self._is_running:
            try:
                # 현재 메모리 상태 확인
                stats = self.monitor.get_current_stats()
                
                # 정리 필요 여부 확인
                should_cleanup = (
                    stats.memory_percent >= self.config.cleanup_threshold or
                    stats.cache_size > self.config.max_cache_size
                )
                
                if should_cleanup:
                    await self.optimizer.optimize_memory()
                
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"메모리 정리 오류: {e}")
                await asyncio.sleep(30)  # 오류 시 30초 대기
    
    def register_cache(self, name: str, cache_object: Any):
        """캐시 객체 등록"""
        self.monitor.cache_manager.register_cache(name, cache_object)
    
    async def force_cleanup(self) -> Dict[str, Any]:
        """강제 메모리 정리"""
        logger.info("🧹 강제 메모리 정리 시작")
        return await self.optimizer.optimize_memory(force=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """현재 메모리 통계 반환"""
        current_stats = self.monitor.get_current_stats()
        trend = self.monitor.get_memory_trend()
        
        return {
            "current": current_stats.to_dict(),
            "trend": trend,
            "history_size": len(self.monitor.stats_history),
            "optimization_count": self.optimizer.optimization_count,
            "cache_size": self.monitor.cache_manager.get_cache_size(),
            "is_running": self._is_running
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """메모리 건강 상태 반환"""
        stats = self.monitor.get_current_stats()
        
        if stats.memory_percent >= self.config.critical_threshold:
            status = "critical"
            message = f"메모리 사용률이 매우 높습니다 ({stats.memory_percent:.1f}%)"
        elif stats.memory_percent >= self.config.warning_threshold:
            status = "warning"
            message = f"메모리 사용률이 높습니다 ({stats.memory_percent:.1f}%)"
        else:
            status = "healthy"
            message = f"메모리 상태가 양호합니다 ({stats.memory_percent:.1f}%)"
        
        return {
            "status": status,
            "message": message,
            "memory_percent": stats.memory_percent,
            "process_memory_mb": stats.process_memory_mb,
            "cache_size": stats.cache_size
        }


# 전역 메모리 관리자 인스턴스
_global_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """전역 메모리 관리자 반환"""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager()
    return _global_memory_manager


async def initialize_memory_manager(config: Optional[MemoryConfig] = None):
    """메모리 관리자 초기화"""
    global _global_memory_manager
    
    if _global_memory_manager is not None:
        await _global_memory_manager.stop()
    
    _global_memory_manager = MemoryManager(config)
    await _global_memory_manager.start()
    
    logger.info("🎉 메모리 관리자 초기화 완료")


async def cleanup_memory_manager():
    """메모리 관리자 정리"""
    global _global_memory_manager
    
    if _global_memory_manager is not None:
        await _global_memory_manager.stop()
        _global_memory_manager = None
    
    logger.info("✅ 메모리 관리자 정리 완료")