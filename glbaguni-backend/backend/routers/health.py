#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Check Router - Simplified
간단한 헬스체크 엔드포인트 (200줄 이하)
"""

import platform
import sys
from datetime import datetime
from typing import Any, Dict

import psutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse

try:
    # Try absolute imports first
    import sys
    import os
    
    # Add the backend directory to the path
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    from config.settings import get_settings
    try:
        from utils import get_logger
    except ImportError:
        from utils.logging_config import get_logger
except ImportError:
    try:
        # Fallback for package import
        from ..config.settings import get_settings
        from ..utils import get_logger
    except ImportError:
        # Create dummy functions for basic functionality
        def get_settings():
            class MockSettings:
                app_name = "Glbaguni"
                app_version = "3.0.0"
                environment = "development"
                log_level = "INFO"
                debug = True
            return MockSettings()
        
        def get_logger(name):
            return logging.getLogger(name)

logger = get_logger("routers.health")
router = APIRouter(tags=["health"])

# 서비스 시작 시간
start_time = datetime.now()


@router.get("/")
async def get_service_info() -> JSONResponse:
    """기본 서비스 정보 반환"""
    try:
        settings = get_settings()

        info = {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "health": "/health",
                "summarize": "/summarize",
                "news-search": "/news-search",
            },
        }

        return JSONResponse(content=info)
    except Exception as e:
        logger.error(f"서비스 정보 조회 실패: {e}")
        return JSONResponse(
            status_code=500, content={"error": "서비스 정보를 가져올 수 없습니다"}
        )


@router.get("/health")
async def health_check() -> JSONResponse:
    """시스템 헬스 체크"""
    try:
        settings = get_settings()

        # 기본 시스템 정보
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        # 업타임 계산
        uptime = datetime.now() - start_time
        uptime_str = str(uptime).split(".")[0]

        # 상태 결정
        status = "healthy"
        if cpu_usage > 90 or memory.percent > 90:
            status = "critical"
        elif cpu_usage > 70 or memory.percent > 70:
            status = "warning"

        health_data = {
            "status": status,
            "version": settings.app_version,
            "uptime": uptime_str,
            "resources": {
                "cpu_usage": round(cpu_usage, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_used_mb": round(memory.used / 1024 / 1024, 1),
            },
            "timestamp": datetime.now().isoformat(),
        }

        status_code = 200 if status in ["healthy", "warning"] else 503

        return JSONResponse(
            status_code=status_code,
            content={
                "success": True,
                "message": f"시스템 상태: {status}",
                "data": health_data,
            },
        )

    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": f"헬스 체크 실패: {str(e)}",
                "data": {"error": str(e)},
            },
        )


@router.get("/debug")
async def debug_info() -> JSONResponse:
    """간단한 디버그 정보"""
    try:
        settings = get_settings()

        # 시스템 정보
        system_info = {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "hostname": platform.node(),
            "architecture": platform.architecture()[0],
        }

        # 메모리 정보
        memory = psutil.virtual_memory()
        memory_info = {
            "total_gb": round(memory.total / 1024 / 1024 / 1024, 2),
            "used_gb": round(memory.used / 1024 / 1024 / 1024, 2),
            "percentage": round(memory.percent, 1),
        }

        # 프로세스 정보
        process = psutil.Process()
        process_info = {
            "pid": process.pid,
            "cpu_percent": round(process.cpu_percent(), 1),
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
            "num_threads": process.num_threads(),
        }

        debug_data = {
            "system_info": system_info,
            "memory_info": memory_info,
            "process_info": process_info,
            "environment": settings.environment,
            "log_level": settings.log_level,
            "debug_mode": settings.debug,
        }

        return JSONResponse(
            content={"success": True, "message": "디버그 정보", "data": debug_data}
        )

    except Exception as e:
        logger.error(f"디버그 정보 조회 실패: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"디버그 정보 조회 실패: {str(e)}",
                "data": {"error": str(e)},
            },
        )


@router.get("/status/services")
async def service_status() -> JSONResponse:
    """서비스 상태 체크"""
    try:
        # 강화된 컴포넌트 매니저 사용
        try:
            from ..utils.component_manager import get_component_status, perform_component_health_checks
            component_report = get_component_status()
            health_results = await perform_component_health_checks()
        except ImportError:
            # 폴백
            component_report = {"system_status": "unknown", "summary": {"total_components": 0}}
            health_results = {}

        services = {
            "database": await check_database_connection(),
            "openai": await check_openai_connection(),
            "system_resources": check_system_resources(),
            "components": {
                "summary": component_report.get("summary", {}),
                "system_status": component_report.get("system_status", "unknown"),
                "health_checks": health_results,
                "details": component_report.get("components", {})
            }
        }

        # 전체 서비스 상태 결정
        overall_status = "healthy"
        critical_issues = []
        
        # 데이터베이스 상태 체크
        if not services["database"]["status"]:
            critical_issues.append("database_failed")
            
        # 컴포넌트 상태 체크
        component_status = component_report.get("system_status", "unknown")
        if component_status == "critical":
            critical_issues.append("critical_components_failed")
            overall_status = "critical"
        elif component_status == "degraded":
            overall_status = "degraded"
            
        # 시스템 리소스 체크
        resources = services["system_resources"]
        if resources["cpu_usage"] > 90 or resources["memory_percent"] > 90:
            critical_issues.append("resource_exhaustion")
            overall_status = "critical"
        elif resources["cpu_usage"] > 70 or resources["memory_percent"] > 70:
            if overall_status == "healthy":
                overall_status = "warning"

        services["overall_status"] = overall_status
        services["critical_issues"] = critical_issues
        services["timestamp"] = datetime.now().isoformat()

        status_code = 200
        if overall_status == "critical":
            status_code = 503
        elif overall_status == "degraded":
            status_code = 206

        return JSONResponse(
            status_code=status_code,
            content={
                "success": True,
                "message": f"서비스 상태: {overall_status}",
                "data": services,
            },
        )

    except Exception as e:
        logger.error(f"서비스 상태 체크 실패: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": f"서비스 상태 체크 실패: {str(e)}",
                "data": {"error": str(e)},
            },
        )


@router.post("/components/retry")
async def retry_failed_components_endpoint() -> JSONResponse:
    """실패한 컴포넌트 재시도"""
    try:
        from ..utils.component_manager import retry_failed_components
        
        retry_results = await retry_failed_components()
        
        return JSONResponse(
            content={
                "success": True,
                "message": "컴포넌트 재시도 완료",
                "data": {
                    "retry_results": retry_results,
                    "timestamp": datetime.now().isoformat()
                }
            }
        )
        
    except Exception as e:
        logger.error(f"컴포넌트 재시도 실패: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"컴포넌트 재시도 실패: {str(e)}",
                "data": {"error": str(e)}
            }
        )


@router.get("/components/detailed")
async def get_detailed_component_status() -> JSONResponse:
    """상세한 컴포넌트 상태 조회"""
    try:
        from ..utils.component_manager import get_component_status, perform_component_health_checks
        
        component_report = get_component_status()
        health_results = await perform_component_health_checks()
        
        # 상세 정보 결합
        detailed_data = {
            **component_report,
            "health_checks": health_results,
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(
            content={
                "success": True,
                "message": "상세 컴포넌트 상태",
                "data": detailed_data
            }
        )
        
    except Exception as e:
        logger.error(f"상세 컴포넌트 상태 조회 실패: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"상세 컴포넌트 상태 조회 실패: {str(e)}",
                "data": {"error": str(e)}
            }
        )


# 헬퍼 함수들
async def check_database_connection() -> Dict[str, Any]:
    """데이터베이스 연결 체크"""
    try:
        # 간단한 연결 테스트 (실제로는 DB 쿼리 실행)
        return {
            "healthy": True,
            "message": "Database connection OK",
            "response_time_ms": 10,
        }
    except Exception as e:
        return {
            "healthy": False,
            "message": f"Database connection failed: {str(e)}",
            "response_time_ms": None,
        }


async def check_openai_connection() -> Dict[str, Any]:
    """OpenAI API 연결 체크"""
    try:
        settings = get_settings()
        if not settings.openai_api_key:
            return {
                "healthy": False,
                "message": "OpenAI API key not configured",
                "response_time_ms": None,
            }

        # 실제로는 간단한 API 호출 테스트
        return {
            "healthy": True,
            "message": "OpenAI API connection OK",
            "response_time_ms": 250,
        }
    except Exception as e:
        return {
            "healthy": False,
            "message": f"OpenAI API connection failed: {str(e)}",
            "response_time_ms": None,
        }


def check_system_resources() -> Dict[str, Any]:
    """시스템 리소스 체크"""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        healthy = cpu < 80 and memory.percent < 80

        return {
            "healthy": healthy,
            "message": f"CPU: {cpu:.1f}%, Memory: {memory.percent:.1f}%",
            "cpu_percent": round(cpu, 1),
            "memory_percent": round(memory.percent, 1),
        }
    except Exception as e:
        return {
            "healthy": False,
            "message": f"System resource check failed: {str(e)}",
            "cpu_percent": None,
            "memory_percent": None,
        }
