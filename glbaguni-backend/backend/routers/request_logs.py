#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
요청 로그 관리 라우터
요청 로그 조회, 분석, 통계 등을 관리하는 엔드포인트를 제공합니다.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import csv
import io
import json
from pathlib import Path

try:
    from utils.logging_config import get_logger
    from utils.request_logger import (
        RequestLoggerMiddleware,
        RequestLoggerConfig,
        LogAnalyzer,
        get_request_logger_middleware
    )
except ImportError:
    from backend.utils.logging_config import get_logger
    from backend.utils.request_logger import (
        RequestLoggerMiddleware,
        RequestLoggerConfig,
        LogAnalyzer,
        get_request_logger_middleware
    )
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("request_logs")

router = APIRouter(prefix="/request-logs", tags=["Request Logs"])


class LogQueryRequest(BaseModel):
    """로그 쿼리 요청 모델"""
    start_time: Optional[float] = Field(None, description="시작 시간 (Unix timestamp)")
    end_time: Optional[float] = Field(None, description="종료 시간 (Unix timestamp)")
    client_ip: Optional[str] = Field(None, description="클라이언트 IP")
    endpoint: Optional[str] = Field(None, description="엔드포인트 경로")
    status_code: Optional[int] = Field(None, description="HTTP 상태 코드")
    is_blocked: Optional[bool] = Field(None, description="차단 여부")
    method: Optional[str] = Field(None, description="HTTP 메소드")
    user_agent: Optional[str] = Field(None, description="User-Agent")
    limit: int = Field(1000, ge=1, le=10000, description="최대 결과 수")


class PatternAnalysisRequest(BaseModel):
    """패턴 분석 요청 모델"""
    hours: int = Field(24, ge=1, le=168, description="분석할 시간 범위 (시간)")
    include_whitelisted: bool = Field(False, description="화이트리스트 IP 포함")
    min_requests: int = Field(10, ge=1, description="최소 요청 수")


@router.get("/stats")
async def get_request_log_stats() -> Dict[str, Any]:
    """
    요청 로그 시스템 통계 정보
    """
    try:
        logger_middleware = get_request_logger_middleware()
        
        # 기본 통계
        basic_stats = logger_middleware.get_stats()
        
        # 데이터베이스 통계 (가능한 경우)
        db_stats = logger_middleware.get_database_stats(24)
        
        return {
            "basic_stats": basic_stats,
            "database_stats": db_stats,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"요청 로그 통계 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="통계 정보 조회에 실패했습니다")


@router.post("/query")
async def query_request_logs(request: LogQueryRequest) -> Dict[str, Any]:
    """
    요청 로그 쿼리
    """
    try:
        logger_middleware = get_request_logger_middleware()
        
        # 쿼리 파라미터 준비
        query_params = {}
        
        if request.start_time:
            query_params['start_time'] = request.start_time
        
        if request.end_time:
            query_params['end_time'] = request.end_time
        
        if request.client_ip:
            query_params['client_ip'] = request.client_ip
        
        if request.endpoint:
            query_params['endpoint'] = request.endpoint
        
        if request.status_code:
            query_params['status_code'] = request.status_code
        
        if request.is_blocked is not None:
            query_params['is_blocked'] = request.is_blocked
        
        query_params['limit'] = request.limit
        
        # 로그 쿼리 실행
        logs = logger_middleware.query_logs(**query_params)
        
        return {
            "logs": logs,
            "total_results": len(logs),
            "query_params": query_params,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"로그 쿼리 중 오류: {e}")
        raise HTTPException(status_code=500, detail="로그 쿼리에 실패했습니다")


@router.get("/recent")
async def get_recent_logs(
    hours: int = Query(1, ge=1, le=24, description="최근 시간 범위"),
    limit: int = Query(100, ge=1, le=1000, description="최대 결과 수"),
    status_filter: Optional[str] = Query(None, description="상태 필터 (success/error/blocked)")
) -> Dict[str, Any]:
    """
    최근 요청 로그 조회
    """
    try:
        logger_middleware = get_request_logger_middleware()
        
        start_time = time.time() - (hours * 3600)
        query_params = {
            'start_time': start_time,
            'limit': limit
        }
        
        # 상태 필터 적용
        if status_filter == "error":
            # 4xx, 5xx 상태 코드만
            pass  # 여러 상태 코드는 별도 쿼리 필요
        elif status_filter == "blocked":
            query_params['is_blocked'] = True
        elif status_filter == "success":
            # 2xx, 3xx 상태 코드만
            pass
        
        logs = logger_middleware.query_logs(**query_params)
        
        # 상태 필터 후처리
        if status_filter == "error":
            logs = [log for log in logs if log.get('status_code', 0) >= 400]
        elif status_filter == "success":
            logs = [log for log in logs if 200 <= log.get('status_code', 0) < 400]
        
        return {
            "logs": logs[:limit],
            "time_range_hours": hours,
            "filter": status_filter,
            "total_results": len(logs),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"최근 로그 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="최근 로그 조회에 실패했습니다")


@router.get("/analyze/suspicious-patterns")
async def analyze_suspicious_patterns(
    hours: int = Query(24, ge=1, le=168, description="분석할 시간 범위"),
    threshold_requests: int = Query(100, ge=10, description="의심 임계값 (시간당 요청 수)")
) -> Dict[str, Any]:
    """
    의심스러운 패턴 분석
    """
    try:
        logger_middleware = get_request_logger_middleware()
        
        if not logger_middleware.db_logger:
            raise HTTPException(status_code=400, detail="데이터베이스 로깅이 활성화되지 않았습니다")
        
        analyzer = LogAnalyzer(logger_middleware.db_logger)
        patterns = analyzer.detect_suspicious_patterns(hours)
        
        # 추가 분석
        start_time = time.time() - (hours * 3600)
        
        # 고빈도 IP 분석
        recent_logs = logger_middleware.query_logs(start_time=start_time, limit=10000)
        
        ip_analysis = {}
        endpoint_analysis = {}
        user_agent_analysis = {}
        
        for log in recent_logs:
            ip = log.get('client_ip', '')
            endpoint = log.get('endpoint', '')
            user_agent = log.get('user_agent', '')
            
            # IP별 분석
            if ip not in ip_analysis:
                ip_analysis[ip] = {
                    'request_count': 0,
                    'unique_endpoints': set(),
                    'status_codes': {},
                    'user_agents': set(),
                    'first_seen': log.get('timestamp', 0),
                    'last_seen': log.get('timestamp', 0)
                }
            
            ip_stats = ip_analysis[ip]
            ip_stats['request_count'] += 1
            ip_stats['unique_endpoints'].add(endpoint)
            ip_stats['user_agents'].add(user_agent)
            ip_stats['last_seen'] = max(ip_stats['last_seen'], log.get('timestamp', 0))
            
            status_code = log.get('status_code', 0)
            ip_stats['status_codes'][status_code] = ip_stats['status_codes'].get(status_code, 0) + 1
            
            # 엔드포인트별 분석
            endpoint_analysis[endpoint] = endpoint_analysis.get(endpoint, 0) + 1
            
            # User-Agent별 분석
            user_agent_analysis[user_agent] = user_agent_analysis.get(user_agent, 0) + 1
        
        # 의심스러운 IP 식별
        suspicious_ips = []
        for ip, stats in ip_analysis.items():
            risk_score = 0
            risk_factors = []
            
            # 요청 빈도
            requests_per_hour = stats['request_count'] / hours
            if requests_per_hour > threshold_requests:
                risk_score += 30
                risk_factors.append(f"고빈도 요청: {requests_per_hour:.1f}/시간")
            
            # 엔드포인트 다양성
            unique_endpoints = len(stats['unique_endpoints'])
            if unique_endpoints > 20:
                risk_score += 20
                risk_factors.append(f"다양한 엔드포인트: {unique_endpoints}개")
            
            # User-Agent 다양성
            unique_uas = len(stats['user_agents'])
            if unique_uas > 5:
                risk_score += 15
                risk_factors.append(f"다양한 User-Agent: {unique_uas}개")
            
            # 4xx 에러율
            total_requests = stats['request_count']
            error_4xx = sum(count for code, count in stats['status_codes'].items() if 400 <= code < 500)
            error_rate = (error_4xx / total_requests) * 100 if total_requests > 0 else 0
            
            if error_rate > 50:
                risk_score += 25
                risk_factors.append(f"높은 4xx 에러율: {error_rate:.1f}%")
            
            if risk_score > 30:
                suspicious_ips.append({
                    'ip': ip,
                    'risk_score': risk_score,
                    'risk_factors': risk_factors,
                    'stats': {
                        'request_count': stats['request_count'],
                        'requests_per_hour': requests_per_hour,
                        'unique_endpoints': unique_endpoints,
                        'unique_user_agents': unique_uas,
                        'error_rate': error_rate,
                        'duration_hours': (stats['last_seen'] - stats['first_seen']) / 3600
                    }
                })
        
        # 위험도순 정렬
        suspicious_ips.sort(key=lambda x: x['risk_score'], reverse=True)
        
        # 상위 엔드포인트
        top_endpoints = sorted(endpoint_analysis.items(), key=lambda x: x[1], reverse=True)[:20]
        
        # 상위 User-Agent
        top_user_agents = sorted(user_agent_analysis.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return {
            "analysis_period_hours": hours,
            "threshold_requests_per_hour": threshold_requests,
            "suspicious_ips": suspicious_ips[:50],  # 상위 50개
            "detected_patterns": patterns,
            "top_endpoints": [{"endpoint": ep, "count": count} for ep, count in top_endpoints],
            "top_user_agents": [{"user_agent": ua, "count": count} for ua, count in top_user_agents],
            "summary": {
                "total_ips_analyzed": len(ip_analysis),
                "suspicious_ips_count": len(suspicious_ips),
                "total_requests_analyzed": len(recent_logs),
                "unique_endpoints": len(endpoint_analysis),
                "unique_user_agents": len(user_agent_analysis)
            },
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"패턴 분석 중 오류: {e}")
        raise HTTPException(status_code=500, detail="패턴 분석에 실패했습니다")


@router.get("/analyze/ip/{ip}")
async def analyze_ip_activity(
    ip: str,
    hours: int = Query(24, ge=1, le=168, description="분석할 시간 범위")
) -> Dict[str, Any]:
    """
    특정 IP의 활동 분석
    """
    try:
        logger_middleware = get_request_logger_middleware()
        
        start_time = time.time() - (hours * 3600)
        logs = logger_middleware.query_logs(
            start_time=start_time,
            client_ip=ip,
            limit=5000
        )
        
        if not logs:
            return {
                "ip": ip,
                "message": "해당 IP의 로그가 없습니다",
                "analysis_period_hours": hours,
                "timestamp": time.time()
            }
        
        # 활동 분석
        analysis = {
            "ip": ip,
            "total_requests": len(logs),
            "first_seen": min(log.get('timestamp', 0) for log in logs),
            "last_seen": max(log.get('timestamp', 0) for log in logs),
            "unique_endpoints": len(set(log.get('endpoint', '') for log in logs)),
            "unique_user_agents": len(set(log.get('user_agent', '') for log in logs)),
            "methods": {},
            "status_codes": {},
            "endpoints": {},
            "user_agents": {},
            "hourly_distribution": {},
            "response_times": []
        }
        
        for log in logs:
            # 메소드별 집계
            method = log.get('method', '')
            analysis['methods'][method] = analysis['methods'].get(method, 0) + 1
            
            # 상태 코드별 집계
            status_code = log.get('status_code', 0)
            analysis['status_codes'][status_code] = analysis['status_codes'].get(status_code, 0) + 1
            
            # 엔드포인트별 집계
            endpoint = log.get('endpoint', '')
            analysis['endpoints'][endpoint] = analysis['endpoints'].get(endpoint, 0) + 1
            
            # User-Agent별 집계
            user_agent = log.get('user_agent', '')
            analysis['user_agents'][user_agent] = analysis['user_agents'].get(user_agent, 0) + 1
            
            # 시간별 분포
            timestamp = log.get('timestamp', 0)
            hour = datetime.fromtimestamp(timestamp).hour
            analysis['hourly_distribution'][hour] = analysis['hourly_distribution'].get(hour, 0) + 1
            
            # 응답 시간
            response_time = log.get('response_time', 0)
            if response_time > 0:
                analysis['response_times'].append(response_time)
        
        # 통계 계산
        activity_duration = analysis['last_seen'] - analysis['first_seen']
        requests_per_hour = analysis['total_requests'] / max(activity_duration / 3600, 0.01)
        
        # 에러율 계산
        error_count = sum(count for code, count in analysis['status_codes'].items() if code >= 400)
        error_rate = (error_count / analysis['total_requests']) * 100
        
        # 평균 응답 시간
        avg_response_time = sum(analysis['response_times']) / len(analysis['response_times']) if analysis['response_times'] else 0
        
        # 상위 항목들 정렬
        analysis['top_endpoints'] = sorted(analysis['endpoints'].items(), key=lambda x: x[1], reverse=True)[:10]
        analysis['top_user_agents'] = sorted(analysis['user_agents'].items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            **analysis,
            "statistics": {
                "requests_per_hour": requests_per_hour,
                "error_rate": error_rate,
                "avg_response_time": avg_response_time,
                "activity_duration_hours": activity_duration / 3600
            },
            "analysis_period_hours": hours,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"IP 활동 분석 중 오류: {e}")
        raise HTTPException(status_code=500, detail="IP 활동 분석에 실패했습니다")


@router.get("/export/csv")
async def export_logs_csv(
    hours: int = Query(24, ge=1, le=168, description="내보낼 시간 범위"),
    client_ip: Optional[str] = Query(None, description="특정 IP 필터"),
    status_code: Optional[int] = Query(None, description="상태 코드 필터")
):
    """
    로그를 CSV 파일로 내보내기
    """
    try:
        logger_middleware = get_request_logger_middleware()
        
        start_time = time.time() - (hours * 3600)
        query_params = {
            'start_time': start_time,
            'limit': 10000
        }
        
        if client_ip:
            query_params['client_ip'] = client_ip
        
        if status_code:
            query_params['status_code'] = status_code
        
        logs = logger_middleware.query_logs(**query_params)
        
        # CSV 생성
        output = io.StringIO()
        if logs:
            fieldnames = logs[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(logs)
        
        # 파일명 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"request_logs_{timestamp}.csv"
        
        # 임시 파일로 저장
        temp_path = Path(f"/tmp/{filename}")
        temp_path.write_text(output.getvalue(), encoding='utf-8')
        
        return FileResponse(
            path=str(temp_path),
            filename=filename,
            media_type='text/csv'
        )
        
    except Exception as e:
        logger.error(f"CSV 내보내기 중 오류: {e}")
        raise HTTPException(status_code=500, detail="CSV 내보내기에 실패했습니다")


@router.get("/timeline/{ip}")
async def get_ip_timeline(
    ip: str,
    hours: int = Query(24, ge=1, le=168, description="조회할 시간 범위")
) -> Dict[str, Any]:
    """
    특정 IP의 시간별 활동 타임라인
    """
    try:
        logger_middleware = get_request_logger_middleware()
        
        start_time = time.time() - (hours * 3600)
        logs = logger_middleware.query_logs(
            start_time=start_time,
            client_ip=ip,
            limit=5000
        )
        
        # 시간별 그룹화 (10분 단위)
        timeline = {}
        
        for log in logs:
            timestamp = log.get('timestamp', 0)
            # 10분 단위로 그룹화
            time_slot = int(timestamp // 600) * 600
            time_key = datetime.fromtimestamp(time_slot).isoformat()
            
            if time_key not in timeline:
                timeline[time_key] = {
                    'timestamp': time_slot,
                    'request_count': 0,
                    'endpoints': set(),
                    'status_codes': {},
                    'methods': {},
                    'unique_user_agents': set()
                }
            
            slot = timeline[time_key]
            slot['request_count'] += 1
            slot['endpoints'].add(log.get('endpoint', ''))
            slot['unique_user_agents'].add(log.get('user_agent', ''))
            
            status_code = log.get('status_code', 0)
            slot['status_codes'][status_code] = slot['status_codes'].get(status_code, 0) + 1
            
            method = log.get('method', '')
            slot['methods'][method] = slot['methods'].get(method, 0) + 1
        
        # 결과 정리
        timeline_list = []
        for time_key in sorted(timeline.keys()):
            slot = timeline[time_key]
            timeline_list.append({
                'time': time_key,
                'timestamp': slot['timestamp'],
                'request_count': slot['request_count'],
                'unique_endpoints': len(slot['endpoints']),
                'unique_user_agents': len(slot['unique_user_agents']),
                'status_codes': dict(slot['status_codes']),
                'methods': dict(slot['methods']),
                'top_endpoints': list(slot['endpoints'])[:5]
            })
        
        return {
            'ip': ip,
            'timeline': timeline_list,
            'total_requests': len(logs),
            'time_range_hours': hours,
            'granularity_minutes': 10,
            'timestamp': time.time()
        }
        
    except Exception as e:
        logger.error(f"IP 타임라인 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="IP 타임라인 조회에 실패했습니다")


@router.get("/config")
async def get_request_logger_config() -> Dict[str, Any]:
    """
    요청 로거 설정 정보
    """
    try:
        logger_middleware = get_request_logger_middleware()
        config = logger_middleware.config
        
        return {
            "enabled": config.enabled,
            "log_formats": config.log_formats,
            "database_enabled": config.database_enabled,
            "log_directory": str(config.log_dir),
            "max_log_size_mb": config.max_log_size_mb,
            "max_log_files": config.max_log_files,
            "retention_days": config.retention_days,
            "exclude_paths": config.exclude_paths,
            "include_request_body": config.include_request_body,
            "include_response_body": config.include_response_body,
            "compress_old_logs": config.compress_old_logs,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"설정 정보 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail="설정 정보 조회에 실패했습니다")


@router.get("/info")
async def get_request_logger_info() -> Dict[str, Any]:
    """
    요청 로거 시스템 정보
    """
    return {
        "system": {
            "name": "글바구니 요청 로거",
            "version": "1.0.0",
            "description": "모든 HTTP 요청의 상세 정보를 구조화된 로그로 저장하여 보안 분석에 활용"
        },
        "features": {
            "structured_logging": "JSON, CSV 형식의 구조화된 로그",
            "database_storage": "SQLite 데이터베이스 저장 옵션",
            "real_time_analysis": "실시간 요청 패턴 분석",
            "suspicious_detection": "의심스러운 활동 자동 감지",
            "data_export": "CSV 형식으로 데이터 내보내기",
            "log_rotation": "자동 로그 로테이션 및 압축"
        },
        "logged_fields": {
            "basic": ["timestamp", "client_ip", "method", "endpoint", "status_code", "response_time"],
            "network": ["real_ip", "forwarded_for", "user_agent", "referer"],
            "security": ["is_whitelisted", "is_blocked", "block_reason", "threat_level"],
            "user": ["user_id", "session_id", "request_id"],
            "content": ["content_type", "content_length", "response_size"]
        },
        "api_endpoints": {
            "GET /request-logs/stats": "로그 시스템 통계",
            "POST /request-logs/query": "로그 쿼리",
            "GET /request-logs/recent": "최근 로그 조회",
            "GET /request-logs/analyze/suspicious-patterns": "의심 패턴 분석",
            "GET /request-logs/analyze/ip/{ip}": "특정 IP 분석",
            "GET /request-logs/timeline/{ip}": "IP 활동 타임라인",
            "GET /request-logs/export/csv": "CSV 내보내기"
        }
    }