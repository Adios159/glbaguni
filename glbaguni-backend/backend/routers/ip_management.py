#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP 차단 관리 라우터
IP 차단 목록 조회, 수동 차단/해제, 통계 등을 관리하는 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import ipaddress

try:
    from utils.logging_config import get_logger
    from utils.ip_blocker import (
        IPBlockerMiddleware,
        IPBlockerConfig,
        BlockedIP,
        BlockReason,
        ThreatLevel,
        ip_blocker_middleware
    )
except ImportError:
    from backend.utils.logging_config import get_logger
    from backend.utils.ip_blocker import (
        IPBlockerMiddleware,
        IPBlockerConfig,
        BlockedIP,
        BlockReason,
        ThreatLevel,
        ip_blocker_middleware
    )
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("ip_management")

router = APIRouter(prefix="/ip-management", tags=["IP Management"])


class ManualBlockRequest(BaseModel):
    """수동 차단 요청 모델"""
    ip: str = Field(..., description="차단할 IP 주소")
    reason: str = Field(default="Manual block", description="차단 이유")
    duration_hours: int = Field(default=24, ge=1, le=8760, description="차단 시간 (시간)")


class IPAnalysisRequest(BaseModel):
    """IP 분석 요청 모델"""
    ip: str = Field(..., description="분석할 IP 주소")


@router.get("/blocked-ips")
async def get_blocked_ips() -> Dict[str, Any]:
    """
    현재 차단된 IP 목록 조회
    """
    try:
        blocked_ips = await ip_blocker_middleware.storage.get_blocked_ips()
        
        # 위협 레벨별 분류
        by_threat_level = {level.value: [] for level in ThreatLevel}
        by_reason = {reason.value: [] for reason in BlockReason}
        
        for blocked_ip in blocked_ips:
            by_threat_level[blocked_ip.threat_level.value].append(blocked_ip.to_dict())
            by_reason[blocked_ip.reason.value].append(blocked_ip.to_dict())
        
        return {
            "total_blocked": len(blocked_ips),
            "blocked_ips": [ip.to_dict() for ip in blocked_ips],
            "by_threat_level": by_threat_level,
            "by_reason": by_reason,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"차단된 IP 목록 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="차단된 IP 목록 조회에 실패했습니다")


@router.get("/blocked-ips/{ip}")
async def get_blocked_ip_info(ip: str) -> Dict[str, Any]:
    """
    특정 IP의 차단 정보 조회
    """
    try:
        # IP 주소 유효성 검증
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 IP 주소입니다")
        
        is_blocked, blocked_info = await ip_blocker_middleware.storage.is_blocked(ip)
        
        if not is_blocked:
            # 요청 히스토리 확인
            request_history = ip_blocker_middleware.analyzer.request_history.get(ip, [])
            ip_stats = ip_blocker_middleware.analyzer.ip_stats.get(ip, {})
            
            return {
                "ip": ip,
                "is_blocked": False,
                "message": "차단되지 않은 IP입니다",
                "request_history_count": len(request_history),
                "stats": ip_stats,
                "timestamp": time.time()
            }
        
        return {
            "ip": ip,
            "is_blocked": True,
            "block_info": blocked_info.to_dict(),
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IP 정보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="IP 정보 조회에 실패했습니다")


@router.post("/block-ip")
async def block_ip_manually(request: ManualBlockRequest) -> Dict[str, Any]:
    """
    수동으로 IP 차단
    """
    try:
        # IP 주소 유효성 검증
        try:
            ipaddress.ip_address(request.ip)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 IP 주소입니다")
        
        # 화이트리스트 확인
        if ip_blocker_middleware.is_whitelisted(request.ip):
            raise HTTPException(status_code=400, detail="화이트리스트에 있는 IP는 차단할 수 없습니다")
        
        # 이미 차단된 IP 확인
        is_blocked, existing_block = await ip_blocker_middleware.storage.is_blocked(request.ip)
        if is_blocked:
            return {
                "success": False,
                "message": "이미 차단된 IP입니다",
                "existing_block": existing_block.to_dict(),
                "timestamp": time.time()
            }
        
        # 수동 차단 실행
        success = await ip_blocker_middleware.block_ip_manually(
            request.ip, 
            request.reason, 
            request.duration_hours
        )
        
        if success:
            logger.info(f"🔨 수동 IP 차단: {request.ip} | 이유: {request.reason} | 시간: {request.duration_hours}시간")
            return {
                "success": True,
                "message": f"IP {request.ip}이(가) {request.duration_hours}시간 동안 차단되었습니다",
                "ip": request.ip,
                "duration_hours": request.duration_hours,
                "reason": request.reason,
                "timestamp": time.time()
            }
        else:
            raise HTTPException(status_code=500, detail="IP 차단에 실패했습니다")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"수동 IP 차단 중 오류: {e}")
        raise HTTPException(status_code=500, detail="IP 차단 처리에 실패했습니다")


@router.delete("/unblock-ip/{ip}")
async def unblock_ip_manually(ip: str) -> Dict[str, Any]:
    """
    수동으로 IP 차단 해제
    """
    try:
        # IP 주소 유효성 검증
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 IP 주소입니다")
        
        # 차단 여부 확인
        is_blocked, blocked_info = await ip_blocker_middleware.storage.is_blocked(ip)
        if not is_blocked:
            return {
                "success": False,
                "message": "차단되지 않은 IP입니다",
                "ip": ip,
                "timestamp": time.time()
            }
        
        # 차단 해제 실행
        success = await ip_blocker_middleware.unblock_ip_manually(ip)
        
        if success:
            logger.info(f"🔓 수동 IP 차단 해제: {ip}")
            return {
                "success": True,
                "message": f"IP {ip}의 차단이 해제되었습니다",
                "ip": ip,
                "previous_block": blocked_info.to_dict() if blocked_info else None,
                "timestamp": time.time()
            }
        else:
            raise HTTPException(status_code=500, detail="IP 차단 해제에 실패했습니다")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"수동 IP 차단 해제 중 오류: {e}")
        raise HTTPException(status_code=500, detail="IP 차단 해제 처리에 실패했습니다")


@router.get("/stats")
async def get_ip_blocker_stats() -> Dict[str, Any]:
    """
    IP 차단 시스템 통계 정보
    """
    try:
        stats = await ip_blocker_middleware.get_stats()
        
        # 추가 통계 계산
        analyzer = ip_blocker_middleware.analyzer
        current_time = time.time()
        
        # 활성 IP 수
        active_ips = len(analyzer.ip_stats)
        
        # 최근 활동 IP들 (지난 1시간)
        recent_active_ips = 0
        for ip, stat in analyzer.ip_stats.items():
            if current_time - stat.get("last_request", 0) < 3600:
                recent_active_ips += 1
        
        # 위협 분포
        threat_distribution = {level.value: 0 for level in ThreatLevel}
        reason_distribution = {reason.value: 0 for reason in BlockReason}
        
        blocked_ips = await ip_blocker_middleware.storage.get_blocked_ips()
        for blocked_ip in blocked_ips:
            threat_distribution[blocked_ip.threat_level.value] += 1
            reason_distribution[blocked_ip.reason.value] += 1
        
        return {
            **stats,
            "active_ips": active_ips,
            "recent_active_ips": recent_active_ips,
            "threat_distribution": threat_distribution,
            "reason_distribution": reason_distribution,
            "config": {
                "redis_enabled": ip_blocker_middleware.config.redis_enabled,
                "analysis_window_minutes": ip_blocker_middleware.config.analysis_window_minutes,
                "suspicious_request_count": ip_blocker_middleware.config.suspicious_request_count,
                "failed_auth_threshold": ip_blocker_middleware.config.failed_auth_threshold,
            }
        }
        
    except Exception as e:
        logger.error(f"IP 차단 통계 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="통계 정보 조회에 실패했습니다")


@router.post("/analyze-ip")
async def analyze_ip(request: IPAnalysisRequest) -> Dict[str, Any]:
    """
    특정 IP의 위험도 분석
    """
    try:
        ip = request.ip
        
        # IP 주소 유효성 검증
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise HTTPException(status_code=400, detail="유효하지 않은 IP 주소입니다")
        
        # IP 통계 가져오기
        ip_stats = ip_blocker_middleware.analyzer.ip_stats.get(ip, {})
        request_history = list(ip_blocker_middleware.analyzer.request_history.get(ip, []))
        
        # 차단 여부 확인
        is_blocked, blocked_info = await ip_blocker_middleware.storage.is_blocked(ip)
        
        # 위험도 점수 계산
        risk_score = 0
        risk_factors = []
        
        if ip_stats:
            # 요청 빈도
            total_requests = ip_stats.get("total_requests", 0)
            if total_requests > 1000:
                risk_score += 30
                risk_factors.append(f"과도한 요청 수: {total_requests}")
            elif total_requests > 500:
                risk_score += 15
                risk_factors.append(f"많은 요청 수: {total_requests}")
            
            # 인증 실패
            failed_auths = ip_stats.get("failed_auths", 0)
            if failed_auths > 10:
                risk_score += 25
                risk_factors.append(f"인증 실패 과다: {failed_auths}회")
            elif failed_auths > 5:
                risk_score += 10
                risk_factors.append(f"인증 실패: {failed_auths}회")
            
            # User-Agent 다양성
            user_agents = len(ip_stats.get("user_agents", set()))
            if user_agents > 10:
                risk_score += 20
                risk_factors.append(f"다양한 User-Agent: {user_agents}개")
            
            # 엔드포인트 다양성
            endpoints = len(ip_stats.get("endpoints", set()))
            if endpoints > 20:
                risk_score += 15
                risk_factors.append(f"다양한 엔드포인트 접근: {endpoints}개")
        
        # 최근 요청 패턴 분석
        if request_history:
            recent_requests = [req for req in request_history if time.time() - req.timestamp < 3600]
            if len(recent_requests) > 100:
                risk_score += 20
                risk_factors.append(f"최근 1시간 과도한 요청: {len(recent_requests)}회")
        
        # 위험도 레벨 결정
        if risk_score >= 70:
            risk_level = "CRITICAL"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 30:
            risk_level = "MEDIUM"
        elif risk_score >= 10:
            risk_level = "LOW"
        else:
            risk_level = "SAFE"
        
        return {
            "ip": ip,
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "is_blocked": is_blocked,
            "blocked_info": blocked_info.to_dict() if blocked_info else None,
            "stats": ip_stats,
            "request_history_count": len(request_history),
            "recent_requests_count": len([req for req in request_history if time.time() - req.timestamp < 3600]),
            "analysis_timestamp": time.time(),
            "recommendation": {
                "SAFE": "안전한 IP입니다",
                "LOW": "주의 관찰이 필요합니다",
                "MEDIUM": "의심스러운 활동이 감지되었습니다",
                "HIGH": "위험한 IP로 판단되며 차단을 고려하세요",
                "CRITICAL": "즉시 차단이 필요한 위험한 IP입니다"
            }.get(risk_level, "알 수 없는 위험도")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IP 분석 중 오류: {e}")
        raise HTTPException(status_code=500, detail="IP 분석에 실패했습니다")


@router.get("/whitelist")
async def get_whitelist() -> Dict[str, Any]:
    """
    화이트리스트 조회
    """
    try:
        return {
            "whitelist_ips": list(ip_blocker_middleware.config.whitelist_ips),
            "count": len(ip_blocker_middleware.config.whitelist_ips),
            "description": "화이트리스트에 있는 IP는 차단되지 않습니다",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"화이트리스트 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="화이트리스트 조회에 실패했습니다")


@router.get("/config")
async def get_ip_blocker_config() -> Dict[str, Any]:
    """
    IP 차단 시스템 설정 정보
    """
    try:
        config = ip_blocker_middleware.config
        
        return {
            "enabled": config.enabled,
            "redis_enabled": config.redis_enabled,
            "redis_host": config.redis_host,
            "redis_port": config.redis_port,
            "analysis_window_minutes": config.analysis_window_minutes,
            "thresholds": {
                "suspicious_request_count": config.suspicious_request_count,
                "rapid_request_threshold": config.rapid_request_threshold,
                "failed_auth_threshold": config.failed_auth_threshold,
                "captcha_failure_threshold": config.captcha_failure_threshold,
                "endpoint_scan_threshold": config.endpoint_scan_threshold,
                "different_ua_threshold": config.different_ua_threshold
            },
            "block_durations": {
                "low_threat_minutes": config.low_threat_block_time // 60,
                "medium_threat_minutes": config.medium_threat_block_time // 60,
                "high_threat_minutes": config.high_threat_block_time // 60,
                "critical_threat_minutes": config.critical_threat_block_time // 60
            },
            "protected_endpoints": config.protected_endpoints,
            "whitelist_count": len(config.whitelist_ips),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"설정 정보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="설정 정보 조회에 실패했습니다")


@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = Query(50, ge=1, le=200, description="조회할 항목 수"),
    ip_filter: Optional[str] = Query(None, description="특정 IP 필터링")
) -> Dict[str, Any]:
    """
    최근 활동 조회
    """
    try:
        analyzer = ip_blocker_middleware.analyzer
        current_time = time.time()
        recent_activity = []
        
        # 모든 IP의 최근 요청 수집
        for ip, history in analyzer.request_history.items():
            if ip_filter and ip != ip_filter:
                continue
                
            for request in history:
                if current_time - request.timestamp < 3600:  # 최근 1시간
                    recent_activity.append({
                        "ip": ip,
                        "timestamp": request.timestamp,
                        "endpoint": request.endpoint,
                        "method": request.method,
                        "status_code": request.status_code,
                        "user_agent": request.user_agent[:100] + "..." if len(request.user_agent) > 100 else request.user_agent,
                        "response_time": request.response_time,
                        "threat_score": request.threat_score
                    })
        
        # 시간순 정렬
        recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "recent_activity": recent_activity[:limit],
            "total_recent_requests": len(recent_activity),
            "time_window": "최근 1시간",
            "ip_filter": ip_filter,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"최근 활동 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="최근 활동 조회에 실패했습니다")


@router.get("/info")
async def get_ip_blocker_info() -> Dict[str, Any]:
    """
    IP 차단 시스템 정보
    """
    return {
        "system": {
            "name": "글바구니 IP 차단 시스템",
            "version": "1.0.0",
            "description": "비정상적인 요청 패턴을 감지하여 자동으로 IP를 차단하는 시스템"
        },
        "features": {
            "automatic_detection": "비정상적인 요청 패턴 자동 감지",
            "threat_levels": "4단계 위험도 분류 (LOW/MEDIUM/HIGH/CRITICAL)",
            "storage_options": "메모리 + Redis 저장소 지원",
            "manual_management": "수동 차단/해제 기능",
            "whitelist_support": "화이트리스트 IP 보호",
            "real_time_analysis": "실시간 요청 패턴 분석"
        },
        "detection_criteria": {
            "rate_limit_abuse": "짧은 시간 내 과도한 요청",
            "failed_auth_attempts": "연속적인 인증 실패",
            "captcha_failures": "CAPTCHA 반복 실패",
            "endpoint_scanning": "다양한 엔드포인트 스캔",
            "user_agent_violations": "의심스러운 User-Agent 패턴",
            "suspicious_patterns": "기타 비정상적인 행동 패턴"
        },
        "block_durations": {
            "LOW": "15분 차단",
            "MEDIUM": "1시간 차단",
            "HIGH": "2시간 차단",
            "CRITICAL": "24시간 차단"
        },
        "api_endpoints": {
            "GET /ip-management/blocked-ips": "차단된 IP 목록 조회",
            "GET /ip-management/blocked-ips/{ip}": "특정 IP 차단 정보",
            "POST /ip-management/block-ip": "수동 IP 차단",
            "DELETE /ip-management/unblock-ip/{ip}": "수동 IP 차단 해제",
            "GET /ip-management/stats": "시스템 통계",
            "POST /ip-management/analyze-ip": "IP 위험도 분석",
            "GET /ip-management/recent-activity": "최근 활동 조회"
        }
    } 