#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
요청 로깅 시스템
모든 HTTP 요청의 상세 정보를 구조화된 로그로 저장하여
의심스러운 패턴 분석과 보안 감사에 활용
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Union
import ipaddress
import gzip
import shutil
from pathlib import Path
import csv
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Request, Response
from fastapi.responses import JSONResponse
import uvloop

try:
    from utils.logging_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

logger = get_logger("request_logger")


@dataclass
class RequestLogEntry:
    """요청 로그 엔트리 데이터 구조"""
    timestamp: float
    datetime_iso: str
    client_ip: str
    real_ip: str
    forwarded_for: str
    method: str
    endpoint: str
    query_params: str
    user_agent: str
    referer: str
    accept_language: str
    content_type: str
    content_length: int
    status_code: int
    response_time: float
    response_size: int
    
    # 보안 관련 정보
    is_whitelisted: bool
    is_blocked: bool
    block_reason: Optional[str]
    threat_level: Optional[str]
    
    # 지리적 정보 (선택사항)
    country: Optional[str] = None
    city: Optional[str] = None
    
    # 사용자 정보 (가능한 경우)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # 추가 컨텍스트
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def to_csv_row(self) -> List[str]:
        """CSV 행으로 변환"""
        data = self.to_dict()
        return [str(data.get(field, '')) for field in self.get_csv_headers()]
    
    @classmethod
    def get_csv_headers(cls) -> List[str]:
        """CSV 헤더 반환"""
        return [
            'timestamp', 'datetime_iso', 'client_ip', 'real_ip', 'forwarded_for',
            'method', 'endpoint', 'query_params', 'user_agent', 'referer',
            'accept_language', 'content_type', 'content_length', 'status_code',
            'response_time', 'response_size', 'is_whitelisted', 'is_blocked',
            'block_reason', 'threat_level', 'country', 'city', 'user_id',
            'session_id', 'request_id'
        ]


class RequestLoggerConfig:
    """요청 로거 설정"""
    
    def __init__(
        self,
        enabled: bool = True,
        log_dir: str = "logs/requests",
        max_log_size_mb: int = 100,
        max_log_files: int = 30,
        log_formats: List[str] = None,
        exclude_paths: List[str] = None,
        include_request_body: bool = False,
        include_response_body: bool = False,
        compress_old_logs: bool = True,
        database_enabled: bool = False,
        database_path: str = "logs/requests.db",
        retention_days: int = 30
    ):
        self.enabled = enabled
        self.log_dir = Path(log_dir)
        self.max_log_size_mb = max_log_size_mb
        self.max_log_files = max_log_files
        self.log_formats = log_formats or ['json', 'csv']
        self.exclude_paths = exclude_paths or [
            '/docs', '/redoc', '/openapi.json', '/static/', '/favicon.ico',
            '/health', '/metrics'
        ]
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
        self.compress_old_logs = compress_old_logs
        self.database_enabled = database_enabled
        self.database_path = Path(database_path)
        self.retention_days = retention_days
        
        # 디렉토리 생성
        self.log_dir.mkdir(parents=True, exist_ok=True)
        if self.database_enabled:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)


class DatabaseLogger:
    """SQLite 데이터베이스 로거"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection_pool = []
        self._init_database()
    
    def _init_database(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS request_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    datetime_iso TEXT NOT NULL,
                    client_ip TEXT NOT NULL,
                    real_ip TEXT,
                    forwarded_for TEXT,
                    method TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    query_params TEXT,
                    user_agent TEXT,
                    referer TEXT,
                    accept_language TEXT,
                    content_type TEXT,
                    content_length INTEGER,
                    status_code INTEGER NOT NULL,
                    response_time REAL NOT NULL,
                    response_size INTEGER,
                    is_whitelisted BOOLEAN,
                    is_blocked BOOLEAN,
                    block_reason TEXT,
                    threat_level TEXT,
                    country TEXT,
                    city TEXT,
                    user_id TEXT,
                    session_id TEXT,
                    request_id TEXT
                )
            ''')
            
            # 인덱스 생성
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_timestamp ON request_logs(timestamp)',
                'CREATE INDEX IF NOT EXISTS idx_client_ip ON request_logs(client_ip)',
                'CREATE INDEX IF NOT EXISTS idx_endpoint ON request_logs(endpoint)',
                'CREATE INDEX IF NOT EXISTS idx_status_code ON request_logs(status_code)',
                'CREATE INDEX IF NOT EXISTS idx_is_blocked ON request_logs(is_blocked)',
                'CREATE INDEX IF NOT EXISTS idx_datetime ON request_logs(datetime_iso)'
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            conn.commit()
            logger.info(f"✅ 요청 로그 데이터베이스 초기화 완료: {self.db_path}")
    
    async def log_entry(self, entry: RequestLogEntry):
        """로그 엔트리를 데이터베이스에 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                data = entry.to_dict()
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data.keys()])
                
                sql = f'INSERT INTO request_logs ({columns}) VALUES ({placeholders})'
                conn.execute(sql, list(data.values()))
                conn.commit()
                
        except Exception as e:
            logger.error(f"데이터베이스 로그 저장 실패: {e}")
    
    def query_logs(
        self, 
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        client_ip: Optional[str] = None,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        is_blocked: Optional[bool] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """로그 쿼리"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                where_clauses = []
                params = []
                
                if start_time:
                    where_clauses.append('timestamp >= ?')
                    params.append(start_time)
                
                if end_time:
                    where_clauses.append('timestamp <= ?')
                    params.append(end_time)
                
                if client_ip:
                    where_clauses.append('client_ip = ?')
                    params.append(client_ip)
                
                if endpoint:
                    where_clauses.append('endpoint LIKE ?')
                    params.append(f'%{endpoint}%')
                
                if status_code:
                    where_clauses.append('status_code = ?')
                    params.append(status_code)
                
                if is_blocked is not None:
                    where_clauses.append('is_blocked = ?')
                    params.append(is_blocked)
                
                where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
                sql = f'''
                    SELECT * FROM request_logs 
                    WHERE {where_sql} 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                '''
                params.append(limit)
                
                cursor = conn.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"로그 쿼리 실패: {e}")
            return []
    
    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """통계 정보 반환"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                start_time = time.time() - (hours * 3600)
                
                # 기본 통계
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total_requests,
                        COUNT(DISTINCT client_ip) as unique_ips,
                        AVG(response_time) as avg_response_time,
                        COUNT(CASE WHEN is_blocked = 1 THEN 1 END) as blocked_requests,
                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_requests
                    FROM request_logs 
                    WHERE timestamp >= ?
                ''', [start_time])
                
                stats = dict(cursor.fetchone())
                
                # 상위 IP
                cursor = conn.execute('''
                    SELECT client_ip, COUNT(*) as request_count
                    FROM request_logs 
                    WHERE timestamp >= ?
                    GROUP BY client_ip
                    ORDER BY request_count DESC
                    LIMIT 10
                ''', [start_time])
                
                stats['top_ips'] = [dict(row) for row in cursor.fetchall()]
                
                # 상위 엔드포인트
                cursor = conn.execute('''
                    SELECT endpoint, COUNT(*) as request_count
                    FROM request_logs 
                    WHERE timestamp >= ?
                    GROUP BY endpoint
                    ORDER BY request_count DESC
                    LIMIT 10
                ''', [start_time])
                
                stats['top_endpoints'] = [dict(row) for row in cursor.fetchall()]
                
                # 시간별 분포
                cursor = conn.execute('''
                    SELECT 
                        strftime('%H', datetime(timestamp, 'unixepoch')) as hour,
                        COUNT(*) as request_count
                    FROM request_logs 
                    WHERE timestamp >= ?
                    GROUP BY hour
                    ORDER BY hour
                ''', [start_time])
                
                stats['hourly_distribution'] = [dict(row) for row in cursor.fetchall()]
                
                return stats
                
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {}


class FileLogger:
    """파일 기반 로거"""
    
    def __init__(self, config: RequestLoggerConfig):
        self.config = config
        self.current_files = {}
        self._init_log_files()
    
    def _init_log_files(self):
        """로그 파일 초기화"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        for format_type in self.config.log_formats:
            file_path = self.config.log_dir / f"requests_{today}.{format_type}"
            self.current_files[format_type] = file_path
            
            if format_type == 'csv' and not file_path.exists():
                # CSV 헤더 작성
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(RequestLogEntry.get_csv_headers())
    
    async def log_entry(self, entry: RequestLogEntry):
        """로그 엔트리를 파일에 저장"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            for format_type in self.config.log_formats:
                file_path = self.config.log_dir / f"requests_{today}.{format_type}"
                
                # 파일이 변경되었으면 업데이트
                if self.current_files.get(format_type) != file_path:
                    self.current_files[format_type] = file_path
                    if format_type == 'csv' and not file_path.exists():
                        with open(file_path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(RequestLogEntry.get_csv_headers())
                
                # 로그 작성
                with open(file_path, 'a', encoding='utf-8') as f:
                    if format_type == 'json':
                        f.write(entry.to_json() + '\n')
                    elif format_type == 'csv':
                        writer = csv.writer(f)
                        writer.writerow(entry.to_csv_row())
                
                # 파일 크기 체크 및 로테이션
                await self._check_file_rotation(file_path)
                
        except Exception as e:
            logger.error(f"파일 로그 저장 실패: {e}")
    
    async def _check_file_rotation(self, file_path: Path):
        """파일 로테이션 체크"""
        try:
            if file_path.stat().st_size > self.config.max_log_size_mb * 1024 * 1024:
                # 파일 크기가 초과되면 압축 후 새 파일 생성
                timestamp = datetime.now().strftime('%H%M%S')
                compressed_path = file_path.with_suffix(f'.{timestamp}{file_path.suffix}.gz')
                
                with open(file_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # 원본 파일 초기화
                if file_path.suffix == '.csv':
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(RequestLogEntry.get_csv_headers())
                else:
                    file_path.write_text('', encoding='utf-8')
                
                logger.info(f"📦 로그 파일 압축 완료: {compressed_path}")
                
        except Exception as e:
            logger.error(f"파일 로테이션 실패: {e}")
    
    async def cleanup_old_logs(self):
        """오래된 로그 파일 정리"""
        try:
            cutoff_time = time.time() - (self.config.retention_days * 24 * 3600)
            
            for file_path in self.config.log_dir.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    logger.info(f"🗑️ 오래된 로그 파일 삭제: {file_path}")
                    
        except Exception as e:
            logger.error(f"로그 정리 실패: {e}")


class RequestLoggerMiddleware:
    """요청 로깅 미들웨어"""
    
    def __init__(self, config: RequestLoggerConfig = None):
        self.config = config or RequestLoggerConfig()
        self.file_logger = FileLogger(self.config) if self.config.log_formats else None
        self.db_logger = DatabaseLogger(self.config.database_path) if self.config.database_enabled else None
        
        # 통계
        self.stats = {
            "total_logged": 0,
            "total_excluded": 0,
            "start_time": time.time(),
            "last_log_time": 0
        }
        
        # 정리 작업 스케줄링
        self._cleanup_task_started = False
        
        logger.info(f"📝 요청 로깅 미들웨어 활성화 (형식: {self.config.log_formats}, DB: {self.config.database_enabled})")
    
    def _should_log_request(self, path: str) -> bool:
        """요청 로깅 여부 판단"""
        if not self.config.enabled:
            return False
        
        for exclude_path in self.config.exclude_paths:
            if path.startswith(exclude_path):
                return False
        
        return True
    
    def _extract_client_ip(self, request: Request) -> tuple[str, str, str]:
        """클라이언트 IP 정보 추출"""
        # X-Forwarded-For 헤더
        forwarded_for = request.headers.get("x-forwarded-for", "")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""
        
        # X-Real-IP 헤더
        real_ip = request.headers.get("x-real-ip", "")
        
        # 직접 연결 IP
        direct_ip = request.client.host if request.client else "unknown"
        
        # 최종 클라이언트 IP 결정
        final_ip = client_ip or real_ip or direct_ip
        
        return final_ip, real_ip, forwarded_for
    
    def _extract_user_info(self, request: Request) -> tuple[Optional[str], Optional[str]]:
        """사용자 정보 추출"""
        # Authorization 헤더에서 사용자 ID 추출 (JWT 등)
        user_id = None
        session_id = None
        
        try:
            # 쿠키에서 세션 ID 추출
            session_id = request.cookies.get("session_id")
            
            # Authorization 헤더 처리 (간단한 예시)
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # JWT 토큰에서 사용자 ID 추출 로직
                # 실제 구현에서는 JWT 라이브러리 사용
                pass
                
        except Exception:
            pass
        
        return user_id, session_id
    
    def _check_security_status(self, request: Request, client_ip: str) -> tuple[bool, bool, Optional[str], Optional[str]]:
        """보안 상태 확인"""
        is_whitelisted = False
        is_blocked = False
        block_reason = None
        threat_level = None
        
        try:
            # IP 차단 시스템과 연동
            from utils.ip_blocker import get_ip_blocker_middleware
            ip_blocker = get_ip_blocker_middleware()
            
            is_whitelisted = ip_blocker.is_whitelisted(client_ip)
            
            # 차단 상태는 비동기이므로 여기서는 기본값 사용
            # 실제 차단 정보는 응답 후 업데이트
            
        except Exception:
            pass
        
        return is_whitelisted, is_blocked, block_reason, threat_level
    
    def _start_cleanup_task(self):
        """정리 작업 시작"""
        if not self._cleanup_task_started and self.file_logger:
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._cleanup_task())
                self._cleanup_task_started = True
                logger.info("🔄 요청 로그 정리 작업 시작")
            except RuntimeError:
                pass
    
    async def _cleanup_task(self):
        """정리 작업"""
        while True:
            try:
                if self.file_logger:
                    await self.file_logger.cleanup_old_logs()
                
                await asyncio.sleep(3600)  # 1시간마다 정리
                
            except Exception as e:
                logger.error(f"로그 정리 작업 오류: {e}")
                await asyncio.sleep(300)
    
    async def __call__(self, request: Request, call_next):
        """미들웨어 실행"""
        start_time = time.time()
        
        # 로깅 대상 확인
        if not self._should_log_request(request.url.path):
            self.stats["total_excluded"] += 1
            return await call_next(request)
        
        # 정리 작업 시작 (한 번만)
        self._start_cleanup_task()
        
        # 요청 정보 수집
        client_ip, real_ip, forwarded_for = self._extract_client_ip(request)
        user_id, session_id = self._extract_user_info(request)
        is_whitelisted, is_blocked, block_reason, threat_level = self._check_security_status(request, client_ip)
        
        # 고유 요청 ID 생성
        request_id = f"{int(start_time * 1000)}-{client_ip.replace('.', '')}"
        
        try:
            # 요청 처리
            response = await call_next(request)
            response_time = time.time() - start_time
            
            # 응답 크기 계산
            response_size = 0
            if hasattr(response, 'body'):
                response_size = len(response.body) if response.body else 0
            
            # 로그 엔트리 생성
            log_entry = RequestLogEntry(
                timestamp=start_time,
                datetime_iso=datetime.fromtimestamp(start_time).isoformat(),
                client_ip=client_ip,
                real_ip=real_ip or "",
                forwarded_for=forwarded_for or "",
                method=request.method,
                endpoint=request.url.path,
                query_params=str(request.url.query),
                user_agent=request.headers.get("user-agent", ""),
                referer=request.headers.get("referer", ""),
                accept_language=request.headers.get("accept-language", ""),
                content_type=request.headers.get("content-type", ""),
                content_length=int(request.headers.get("content-length", 0)),
                status_code=response.status_code,
                response_time=response_time,
                response_size=response_size,
                is_whitelisted=is_whitelisted,
                is_blocked=is_blocked,
                block_reason=block_reason,
                threat_level=threat_level,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id
            )
            
            # 로그 저장
            if self.file_logger:
                await self.file_logger.log_entry(log_entry)
            
            if self.db_logger:
                await self.db_logger.log_entry(log_entry)
            
            # 통계 업데이트
            self.stats["total_logged"] += 1
            self.stats["last_log_time"] = start_time
            
            # 요청 ID를 응답 헤더에 추가
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # 오류 발생 시에도 로그 기록
            response_time = time.time() - start_time
            
            log_entry = RequestLogEntry(
                timestamp=start_time,
                datetime_iso=datetime.fromtimestamp(start_time).isoformat(),
                client_ip=client_ip,
                real_ip=real_ip or "",
                forwarded_for=forwarded_for or "",
                method=request.method,
                endpoint=request.url.path,
                query_params=str(request.url.query),
                user_agent=request.headers.get("user-agent", ""),
                referer=request.headers.get("referer", ""),
                accept_language=request.headers.get("accept-language", ""),
                content_type=request.headers.get("content-type", ""),
                content_length=int(request.headers.get("content-length", 0)),
                status_code=500,
                response_time=response_time,
                response_size=0,
                is_whitelisted=is_whitelisted,
                is_blocked=is_blocked,
                block_reason=f"서버 오류: {str(e)}",
                threat_level=threat_level,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id
            )
            
            if self.file_logger:
                await self.file_logger.log_entry(log_entry)
            
            if self.db_logger:
                await self.db_logger.log_entry(log_entry)
            
            self.stats["total_logged"] += 1
            
            # 오류 재발생
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        runtime = time.time() - self.stats["start_time"]
        
        return {
            **self.stats,
            "runtime_seconds": runtime,
            "logs_per_minute": (self.stats["total_logged"] / max(runtime / 60, 1)),
            "config": {
                "enabled": self.config.enabled,
                "log_formats": self.config.log_formats,
                "database_enabled": self.config.database_enabled,
                "retention_days": self.config.retention_days
            }
        }
    
    def get_database_stats(self, hours: int = 24) -> Dict[str, Any]:
        """데이터베이스 통계 반환"""
        if self.db_logger:
            return self.db_logger.get_statistics(hours)
        return {}
    
    def query_logs(self, **kwargs) -> List[Dict[str, Any]]:
        """로그 쿼리"""
        if self.db_logger:
            return self.db_logger.query_logs(**kwargs)
        return []


# 전역 인스턴스 (지연 생성)
default_request_logger_config = RequestLoggerConfig()
request_logger_middleware = None

def get_request_logger_middleware():
    """요청 로거 미들웨어 인스턴스를 안전하게 가져오기"""
    global request_logger_middleware
    if request_logger_middleware is None:
        request_logger_middleware = RequestLoggerMiddleware(default_request_logger_config)
    return request_logger_middleware

# 설정 함수
def configure_request_logger(
    enabled: bool = True,
    log_dir: str = "logs/requests",
    log_formats: List[str] = None,
    database_enabled: bool = False,
    retention_days: int = 30,
    max_log_size_mb: int = 100
):
    """요청 로거 설정 업데이트"""
    global default_request_logger_config, request_logger_middleware
    
    default_request_logger_config.enabled = enabled
    default_request_logger_config.log_dir = Path(log_dir)
    default_request_logger_config.log_formats = log_formats or ['json', 'csv']
    default_request_logger_config.database_enabled = database_enabled
    default_request_logger_config.retention_days = retention_days
    default_request_logger_config.max_log_size_mb = max_log_size_mb
    
    # 미들웨어 재생성
    request_logger_middleware = RequestLoggerMiddleware(default_request_logger_config)
    
    logger.info(f"✅ 요청 로거 설정 업데이트 완료 (형식: {log_formats}, DB: {database_enabled})")


# 로그 분석 유틸리티
class LogAnalyzer:
    """로그 분석 유틸리티"""
    
    def __init__(self, db_logger: DatabaseLogger):
        self.db_logger = db_logger
    
    def detect_suspicious_patterns(self, hours: int = 24) -> Dict[str, Any]:
        """의심스러운 패턴 감지"""
        start_time = time.time() - (hours * 3600)
        
        patterns = {
            "high_frequency_ips": [],
            "failed_requests": [],
            "scanning_attempts": [],
            "unusual_user_agents": [],
            "geographic_anomalies": []
        }
        
        try:
            # 고빈도 IP 감지
            high_freq = self.db_logger.query_logs(
                start_time=start_time,
                limit=10000
            )
            
            ip_counts = {}
            for log in high_freq:
                ip = log['client_ip']
                ip_counts[ip] = ip_counts.get(ip, 0) + 1
            
            # 임계값 이상의 IP
            threshold = 100  # 시간당 100회 이상
            for ip, count in ip_counts.items():
                if count > threshold:
                    patterns["high_frequency_ips"].append({
                        "ip": ip,
                        "request_count": count,
                        "requests_per_hour": count / hours
                    })
            
            # 실패 요청 패턴
            failed_logs = self.db_logger.query_logs(
                start_time=start_time,
                status_code=404,
                limit=1000
            )
            
            endpoint_404s = {}
            for log in failed_logs:
                endpoint = log['endpoint']
                endpoint_404s[endpoint] = endpoint_404s.get(endpoint, 0) + 1
            
            for endpoint, count in endpoint_404s.items():
                if count > 10:  # 10회 이상 404
                    patterns["failed_requests"].append({
                        "endpoint": endpoint,
                        "count": count
                    })
            
            return patterns
            
        except Exception as e:
            logger.error(f"패턴 감지 실패: {e}")
            return patterns