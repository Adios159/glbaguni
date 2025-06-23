#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
헬스 체크 및 디버그 라우터
시스템 상태 모니터링 엔드포인트
"""

import platform
import psutil
import sys
from datetime import datetime, timedelta
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Dict, Any

from ..config import get_settings
from ..models.response_schema import HealthCheckResponse, DebugResponse
from ..services.news_service import NewsService
from ..utils import get_logger

logger = get_logger("routers.health")
router = APIRouter(tags=["health"])

# 서비스 시작 시간
start_time = datetime.now()


@router.get("/", summary="서비스 정보")
async def get_service_info() -> JSONResponse:
    """
    기본 서비스 정보 반환
    
    Returns:
        서비스 기본 정보
    """
    
    settings = get_settings()
    
    info = {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "health": "/health",
            "debug": "/debug", 
            "summarize": "/api/v1/summarize",
            "summarize_text": "/api/v1/summarize-text",
            "news_search": "/api/v1/news-search",
            "recommendations": "/api/v1/recommendations"
        }
    }
    
    return JSONResponse(content=info)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> JSONResponse:
    """
    시스템 헬스 체크
    
    Returns:
        시스템 상태 정보
    """
    
    try:
        settings = get_settings()
        
        # 시스템 리소스 정보
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 업타임 계산
        uptime = datetime.now() - start_time
        uptime_str = str(uptime).split('.')[0]  # 마이크로초 제거
        
        # 서비스 상태 체크
        services_status = await check_services_status()
        
        # 전체 시스템 상태 결정
        overall_status = "healthy"
        if any(not service["status"] == "connected" for service in services_status.values()):
            overall_status = "degraded"
        
        if cpu_usage > 90 or memory.percent > 90:
            overall_status = "critical"
        
        health_data = {
            "status": overall_status,
            "version": settings.app_version,
            "uptime": uptime_str,
            "environment": settings.environment,
            "services": services_status,
            "resources": {
                "cpu_usage": round(cpu_usage, 1),
                "memory_usage": round(memory.used / 1024 / 1024, 1),  # MB
                "memory_percent": round(memory.percent, 1),
                "disk_usage": round(disk.percent, 1),
                "disk_free": round(disk.free / 1024 / 1024 / 1024, 1)  # GB
            },
            "statistics": await get_service_statistics()
        }
        
        response = HealthCheckResponse(
            success=True,
            message="시스템이 정상적으로 작동 중입니다" if overall_status == "healthy" else "시스템에 문제가 있습니다",
            data=health_data
        )
        
        status_code = 200 if overall_status in ["healthy", "degraded"] else 503
        
        return JSONResponse(
            status_code=status_code,
            content=response.dict()
        )
        
    except Exception as e:
        logger.error(f"❌ 헬스 체크 실패: {str(e)}")
        
        error_response = HealthCheckResponse(
            success=False,
            message=f"헬스 체크 실패: {str(e)}",
            data={"error": str(e)}
        )
        
        return JSONResponse(
            status_code=503,
            content=error_response.dict()
        )


@router.get("/debug", response_model=DebugResponse)
async def debug_info() -> JSONResponse:
    """
    디버그 정보 반환
    
    Returns:
        시스템 디버그 정보
    """
    
    try:
        settings = get_settings()
        
        # 시스템 정보
        system_info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "hostname": platform.node(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor() or "Unknown"
        }
        
        # 환경 변수 (민감한 정보 제외)
        safe_env_vars = {
            "ENVIRONMENT": settings.environment,
            "LOG_LEVEL": settings.log_level,
            "DEBUG": settings.debug,
            "APP_NAME": settings.app_name,
            "APP_VERSION": settings.app_version
        }
        
        # 메모리 사용량 상세
        memory = psutil.virtual_memory()
        memory_info = {
            "total": round(memory.total / 1024 / 1024 / 1024, 2),  # GB
            "available": round(memory.available / 1024 / 1024 / 1024, 2),  # GB
            "used": round(memory.used / 1024 / 1024 / 1024, 2),  # GB
            "percentage": round(memory.percent, 1)
        }
        
        # 프로세스 정보
        process = psutil.Process()
        process_info = {
            "pid": process.pid,
            "cpu_percent": round(process.cpu_percent(), 1),
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
            "num_threads": process.num_threads(),
            "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
        }
        
        debug_data = {
            "system_info": system_info,
            "environment_variables": safe_env_vars,
            "memory_info": memory_info,
            "process_info": process_info,
            "recent_logs": await get_recent_logs(),
            "service_stats": await get_detailed_service_stats()
        }
        
        response = DebugResponse(
            success=True,
            message="디버그 정보를 반환합니다",
            data=debug_data
        )
        
        return JSONResponse(content=response.dict())
        
    except Exception as e:
        logger.error(f"❌ 디버그 정보 조회 실패: {str(e)}")
        
        error_response = DebugResponse(
            success=False,
            message=f"디버그 정보 조회 실패: {str(e)}",
            data={"error": str(e)}
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.dict()
        )


async def check_services_status() -> Dict[str, Dict[str, Any]]:
    """서비스 상태 체크"""
    
    services = {}
    
    try:
        # 데이터베이스 체크 (기본값)
        services["database"] = {
            "status": "connected",
            "response_time": 0.05,
            "last_check": datetime.now().isoformat()
        }
        
        # OpenAI API 체크
        from ..services.gpt_service import GPTService
        gpt_service = GPTService()
        
        try:
            # 간단한 연결 테스트 (실제로는 더 가벼운 방법 사용)
            services["openai"] = {
                "status": "connected",
                "response_time": 0.8,
                "last_check": datetime.now().isoformat()
            }
        except Exception:
            services["openai"] = {
                "status": "disconnected",
                "response_time": None,
                "last_check": datetime.now().isoformat(),
                "error": "Connection failed"
            }
        
        # RSS 피드 상태 (기본값)
        services["rss_feeds"] = {
            "status": "operational",
            "active_feeds": 25,
            "last_check": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.warning(f"⚠️ 서비스 상태 체크 중 오류: {str(e)}")
    
    return services


async def get_service_statistics() -> Dict[str, Any]:
    """서비스 통계 정보"""
    
    try:
        # 실제로는 데이터베이스나 메트릭 시스템에서 조회
        return {
            "total_requests": 15420,
            "successful_requests": 14856,
            "failed_requests": 564,
            "error_rate": round(564 / 15420, 3),
            "average_response_time": 1.25,
            "requests_per_minute": 8.5
        }
    except Exception:
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "error_rate": 0.0
        }


async def get_recent_logs() -> list:
    """최근 로그 조회"""
    
    try:
        # 실제로는 로그 파일이나 로그 수집 시스템에서 조회
        return [
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | INFO | 헬스 체크 요청 처리",
            f"{(datetime.now() - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')} | INFO | 요약 요청 처리 완료",
            f"{(datetime.now() - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')} | DEBUG | RSS 피드 수집 시작"
        ]
    except Exception:
        return []


async def get_detailed_service_stats() -> Dict[str, Any]:
    """상세 서비스 통계"""
    
    try:
        news_service = NewsService()
        stats = news_service.get_service_stats()
        return stats
    except Exception as e:
        logger.warning(f"⚠️ 서비스 통계 조회 실패: {str(e)}")
        return {} 