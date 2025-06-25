#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메모리 관리 API 라우터
메모리 모니터링 및 관리 기능을 제공하는 API 엔드포인트들
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

try:
    from utils.memory_manager import (
        MemoryManager, 
        MemoryConfig, 
        get_memory_manager,
        initialize_memory_manager,
        cleanup_memory_manager
    )
    from utils.logging_config import get_logger
except ImportError:
    from backend.utils.memory_manager import (
        MemoryManager, 
        MemoryConfig, 
        get_memory_manager,
        initialize_memory_manager,
        cleanup_memory_manager
    )
    from backend.utils.logging_config import get_logger

logger = get_logger("memory_router")


# === Pydantic 모델들 ===

class MemoryStatusResponse(BaseModel):
    """메모리 상태 응답 모델"""
    status: str = Field(description="메모리 상태 (healthy/warning/critical)")
    message: str = Field(description="상태 메시지")
    memory_percent: float = Field(description="메모리 사용률 (%)")
    process_memory_mb: float = Field(description="프로세스 메모리 사용량 (MB)")
    cache_size: int = Field(description="캐시 크기")
    timestamp: str = Field(description="확인 시간")


class MemoryStatsResponse(BaseModel):
    """메모리 통계 응답 모델"""
    current: Dict[str, Any] = Field(description="현재 메모리 통계")
    trend: Dict[str, Any] = Field(description="메모리 사용 트렌드")
    history_size: int = Field(description="히스토리 크기")
    optimization_count: int = Field(description="최적화 실행 횟수")
    cache_size: int = Field(description="캐시 크기")
    is_running: bool = Field(description="메모리 관리자 실행 상태")


class MemoryCleanupResponse(BaseModel):
    """메모리 정리 응답 모델"""
    success: bool = Field(description="정리 성공 여부")
    optimization_time: float = Field(description="최적화 소요 시간 (초)")
    gc_collected: int = Field(description="가비지 컬렉션으로 수집된 객체 수")
    cache_cleaned: int = Field(description="정리된 캐시 항목 수")
    memory_freed_mb: float = Field(description="해제된 메모리 (MB)")
    message: str = Field(description="결과 메시지")


class MemoryConfigRequest(BaseModel):
    """메모리 설정 요청 모델"""
    monitoring_interval_seconds: Optional[int] = Field(default=60, description="모니터링 간격 (초)")
    cleanup_interval_seconds: Optional[int] = Field(default=300, description="정리 간격 (초)")
    warning_threshold: Optional[float] = Field(default=70.0, description="경고 임계값 (%)")
    critical_threshold: Optional[float] = Field(default=85.0, description="심각 임계값 (%)")
    cleanup_threshold: Optional[float] = Field(default=80.0, description="정리 시작 임계값 (%)")
    max_cache_size: Optional[int] = Field(default=1000, description="최대 캐시 크기")
    enable_alerts: Optional[bool] = Field(default=True, description="알림 활성화")


# === 라우터 생성 ===

def create_memory_router() -> APIRouter:
    """메모리 관리 라우터 생성"""
    router = APIRouter(prefix="/memory", tags=["Memory Management"])
    
    @router.get("/status", response_model=MemoryStatusResponse)
    async def get_memory_status():
        """
        현재 메모리 상태 조회
        
        Returns:
            메모리 상태 정보 (healthy/warning/critical)
        """
        try:
            memory_manager = get_memory_manager()
            health_status = memory_manager.get_health_status()
            
            return MemoryStatusResponse(
                status=health_status["status"],
                message=health_status["message"],
                memory_percent=health_status["memory_percent"],
                process_memory_mb=health_status["process_memory_mb"],
                cache_size=health_status["cache_size"],
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"메모리 상태 조회 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"메모리 상태 조회 중 오류가 발생했습니다: {str(e)}"
            )
    
    @router.get("/stats", response_model=MemoryStatsResponse)
    async def get_memory_stats():
        """
        상세 메모리 통계 조회
        
        Returns:
            상세한 메모리 사용 통계 및 트렌드 정보
        """
        try:
            memory_manager = get_memory_manager()
            stats = memory_manager.get_stats()
            
            return MemoryStatsResponse(**stats)
            
        except Exception as e:
            logger.error(f"메모리 통계 조회 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"메모리 통계 조회 중 오류가 발생했습니다: {str(e)}"
            )
    
    @router.post("/cleanup", response_model=MemoryCleanupResponse)
    async def force_memory_cleanup():
        """
        강제 메모리 정리 실행
        
        Returns:
            메모리 정리 결과
        """
        try:
            memory_manager = get_memory_manager()
            
            logger.info("📞 API를 통한 강제 메모리 정리 요청")
            result = await memory_manager.force_cleanup()
            
            success = "error" not in result
            message = "메모리 정리가 성공적으로 완료되었습니다." if success else f"메모리 정리 중 오류: {result.get('error')}"
            
            return MemoryCleanupResponse(
                success=success,
                optimization_time=result.get("optimization_time", 0),
                gc_collected=result.get("gc_collected", 0),
                cache_cleaned=result.get("cache_cleaned", 0),
                memory_freed_mb=result.get("memory_freed_mb", 0),
                message=message
            )
            
        except Exception as e:
            logger.error(f"강제 메모리 정리 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"메모리 정리 중 오류가 발생했습니다: {str(e)}"
            )
    
    @router.post("/cleanup/background")
    async def schedule_memory_cleanup(background_tasks: BackgroundTasks):
        """
        백그라운드에서 메모리 정리 실행
        
        Returns:
            즉시 응답하고 백그라운드에서 정리 수행
        """
        try:
            async def cleanup_task():
                try:
                    memory_manager = get_memory_manager()
                    result = await memory_manager.force_cleanup()
                    logger.info(f"백그라운드 메모리 정리 완료: {result}")
                except Exception as e:
                    logger.error(f"백그라운드 메모리 정리 실패: {e}")
            
            background_tasks.add_task(cleanup_task)
            
            return JSONResponse(
                status_code=202,
                content={
                    "message": "메모리 정리가 백그라운드에서 시작되었습니다.",
                    "status": "scheduled"
                }
            )
            
        except Exception as e:
            logger.error(f"백그라운드 메모리 정리 스케줄링 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"백그라운드 작업 스케줄링 중 오류가 발생했습니다: {str(e)}"
            )
    
    @router.get("/history")
    async def get_memory_history(
        hours: int = Query(default=1, ge=1, le=24, description="조회할 시간 범위 (시간)")
    ):
        """
        메모리 사용 히스토리 조회
        
        Args:
            hours: 조회할 시간 범위 (1-24시간)
            
        Returns:
            지정된 시간 범위의 메모리 사용 히스토리
        """
        try:
            memory_manager = get_memory_manager()
            trend = memory_manager.monitor.get_memory_trend(minutes=hours * 60)
            
            # 히스토리 데이터 추출
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            history_data = []
            
            for stats in memory_manager.monitor.stats_history:
                if stats.timestamp.timestamp() > cutoff_time:
                    history_data.append(stats.to_dict())
            
            return {
                "hours": hours,
                "trend": trend,
                "history_count": len(history_data),
                "data": history_data[-100:]  # 최근 100개만 반환 (너무 많은 데이터 방지)
            }
            
        except Exception as e:
            logger.error(f"메모리 히스토리 조회 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"메모리 히스토리 조회 중 오류가 발생했습니다: {str(e)}"
            )
    
    @router.post("/config")
    async def update_memory_config(config_request: MemoryConfigRequest):
        """
        메모리 관리 설정 업데이트
        
        Args:
            config_request: 새로운 메모리 관리 설정
            
        Returns:
            설정 업데이트 결과
        """
        try:
            # 새 설정 객체 생성
            new_config = MemoryConfig(
                monitoring_interval_seconds=config_request.monitoring_interval_seconds,
                cleanup_interval_seconds=config_request.cleanup_interval_seconds,
                warning_threshold=config_request.warning_threshold,
                critical_threshold=config_request.critical_threshold,
                cleanup_threshold=config_request.cleanup_threshold,
                max_cache_size=config_request.max_cache_size,
                enable_alerts=config_request.enable_alerts
            )
            
            logger.info("🔧 메모리 관리 설정 업데이트 요청")
            
            # 메모리 관리자 재초기화
            await initialize_memory_manager(new_config)
            
            return {
                "message": "메모리 관리 설정이 성공적으로 업데이트되었습니다.",
                "config": {
                    "monitoring_interval_seconds": new_config.monitoring_interval_seconds,
                    "cleanup_interval_seconds": new_config.cleanup_interval_seconds,
                    "warning_threshold": new_config.warning_threshold,
                    "critical_threshold": new_config.critical_threshold,
                    "cleanup_threshold": new_config.cleanup_threshold,
                    "max_cache_size": new_config.max_cache_size,
                    "enable_alerts": new_config.enable_alerts
                }
            }
            
        except Exception as e:
            logger.error(f"메모리 설정 업데이트 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"메모리 설정 업데이트 중 오류가 발생했습니다: {str(e)}"
            )
    
    @router.get("/config")
    async def get_memory_config():
        """
        현재 메모리 관리 설정 조회
        
        Returns:
            현재 메모리 관리 설정
        """
        try:
            memory_manager = get_memory_manager()
            config = memory_manager.config
            
            return {
                "monitoring_interval_seconds": config.monitoring_interval_seconds,
                "cleanup_interval_seconds": config.cleanup_interval_seconds,
                "warning_threshold": config.warning_threshold,
                "critical_threshold": config.critical_threshold,
                "cleanup_threshold": config.cleanup_threshold,
                "max_cache_size": config.max_cache_size,
                "cache_cleanup_ratio": config.cache_cleanup_ratio,
                "max_history_size": config.max_history_size,
                "enable_alerts": config.enable_alerts,
                "alert_cooldown_minutes": config.alert_cooldown_minutes
            }
            
        except Exception as e:
            logger.error(f"메모리 설정 조회 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"메모리 설정 조회 중 오류가 발생했습니다: {str(e)}"
            )
    
    @router.post("/start")
    async def start_memory_management():
        """
        메모리 관리 시작
        
        Returns:
            메모리 관리 시작 결과
        """
        try:
            memory_manager = get_memory_manager()
            await memory_manager.start()
            
            return {
                "message": "메모리 관리가 시작되었습니다.",
                "status": "started"
            }
            
        except Exception as e:
            logger.error(f"메모리 관리 시작 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"메모리 관리 시작 중 오류가 발생했습니다: {str(e)}"
            )
    
    @router.post("/stop")
    async def stop_memory_management():
        """
        메모리 관리 중지
        
        Returns:
            메모리 관리 중지 결과
        """
        try:
            await cleanup_memory_manager()
            
            return {
                "message": "메모리 관리가 중지되었습니다.",
                "status": "stopped"
            }
            
        except Exception as e:
            logger.error(f"메모리 관리 중지 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"메모리 관리 중지 중 오류가 발생했습니다: {str(e)}"
            )
    
    @router.get("/cache/register")
    async def register_cache_endpoint(
        name: str = Query(..., description="캐시 이름"),
        size: int = Query(default=0, description="캐시 크기")
    ):
        """
        캐시 등록 (테스트용)
        
        Args:
            name: 캐시 이름
            size: 캐시 크기
            
        Returns:
            캐시 등록 결과
        """
        try:
            memory_manager = get_memory_manager()
            
            # 테스트용 캐시 객체 생성
            test_cache = {f"item_{i}": f"data_{i}" for i in range(size)}
            memory_manager.register_cache(name, test_cache)
            
            return {
                "message": f"캐시 '{name}'이 성공적으로 등록되었습니다.",
                "cache_name": name,
                "cache_size": len(test_cache),
                "total_cache_size": memory_manager.monitor.cache_manager.get_cache_size()
            }
            
        except Exception as e:
            logger.error(f"캐시 등록 실패: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"캐시 등록 중 오류가 발생했습니다: {str(e)}"
            )
    
    return router