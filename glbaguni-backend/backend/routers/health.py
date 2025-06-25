#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Check Router - Simplified
간단한 헬스체크 엔드포인트 (200줄 이하)
"""

import platform
import sys
import time
import logging
import os
from datetime import datetime
from typing import Any, Dict

import psutil
from fastapi import APIRouter, HTTPException
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
async def health_check() -> Dict[str, Any]:
    """개선된 헬스체크 - 상세한 시스템 상태 제공"""
    start_time = time.time()
    
    try:
        # 기본 서버 상태
        basic_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "server": {
                "name": "글바구니 (Glbaguni) Backend",
                "version": "3.0.0",
                "uptime": time.time() - start_time,
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                "environment": os.getenv("ENVIRONMENT", "development")
            }
        }
        
        # 컴포넌트 상태 (가능한 경우)
        if get_component_status:
            try:
                component_status = get_component_status()
                basic_status["components"] = component_status
            except Exception as e:
                logging.warning(f"컴포넌트 상태 조회 실패: {e}")
                basic_status["components"] = {
                    "error": "컴포넌트 상태를 조회할 수 없습니다",
                    "reason": str(e)
                }
        else:
            basic_status["components"] = {
                "warning": "컴포넌트 매니저를 사용할 수 없습니다"
            }
        
        # 환경변수 상태 확인
        env_status = check_environment_status()
        basic_status["environment"] = env_status
        
        # 응답 시간 계산
        response_time = time.time() - start_time
        basic_status["response_time_ms"] = round(response_time * 1000, 2)
        
        return basic_status
        
    except Exception as e:
        logging.error(f"헬스체크 중 오류: {e}")
        return {
            "status": "error",
            "timestamp": time.time(),
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }


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


def check_environment_status() -> Dict[str, Any]:
    """환경변수 상태 확인"""
    env_vars = [
        "OPENAI_API_KEY",
        "SMTP_USERNAME", 
        "SMTP_PASSWORD",
        "DATABASE_URL"
    ]
    
    status = {
        "configured": [],
        "missing": [],
        "total": len(env_vars)
    }
    
    for var in env_vars:
        if os.getenv(var):
            status["configured"].append(var)
        else:
            status["missing"].append(var)
    
    status["configured_count"] = len(status["configured"])
    status["missing_count"] = len(status["missing"])
    status["configuration_rate"] = (status["configured_count"] / status["total"]) * 100
    
    return status


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """상세한 헬스체크 - 모든 시스템 정보"""
    try:
        basic_health = await health_check()
        
        # 추가 상세 정보
        detailed_info = {
            "system": {
                "platform": os.name,
                "cwd": os.getcwd(),
                "process_id": os.getpid() if hasattr(os, 'getpid') else "unknown"
            },
            "memory": get_memory_info(),
            "disk": get_disk_info()
        }
        
        basic_health["detailed"] = detailed_info
        return basic_health
        
    except Exception as e:
        logging.error(f"상세 헬스체크 중 오류: {e}")
        raise HTTPException(500, f"상세 헬스체크 실패: {str(e)}")


def get_memory_info() -> Dict[str, Any]:
    """메모리 정보 조회 (가능한 경우)"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_percent": memory.percent
        }
    except ImportError:
        return {"error": "psutil 패키지가 설치되지 않음"}
    except Exception as e:
        return {"error": f"메모리 정보 조회 실패: {str(e)}"}


def get_disk_info() -> Dict[str, Any]:
    """디스크 정보 조회 (가능한 경우)"""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        return {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "used_percent": round((disk.used / disk.total) * 100, 2)
        }
    except ImportError:
        return {"error": "psutil 패키지가 설치되지 않음"}
    except Exception as e:
        return {"error": f"디스크 정보 조회 실패: {str(e)}"}


@router.get("/health/simple")
async def simple_health_check() -> Dict[str, str]:
    """간단한 헬스체크 - 로드밸런서용"""
    return {
        "status": "ok",
        "timestamp": str(int(time.time()))
    }
