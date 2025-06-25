#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP 차단 시스템 테스트
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from fastapi.testclient import TestClient

try:
    from backend.utils.ip_blocker import (
        IPBlockerMiddleware,
        IPBlockerConfig,
        RequestPattern,
        RequestAnalyzer,
        BlockedIP,
        BlockReason,
        ThreatLevel,
        IPBlockerStorage
    )
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend.utils.ip_blocker import (
        IPBlockerMiddleware,
        IPBlockerConfig,
        RequestPattern,
        RequestAnalyzer,
        BlockedIP,
        BlockReason,
        ThreatLevel,
        IPBlockerStorage
    )


class TestIPBlockerConfig:
    """IP 차단 설정 테스트"""
    
    def test_default_config(self):
        """기본 설정 테스트"""
        config = IPBlockerConfig()
        
        assert config.enabled is True
        assert config.failed_auth_threshold == 10
        assert config.captcha_failure_threshold == 5
        assert config.redis_enabled is False
        assert "127.0.0.1" in config.whitelist_ips
    
    def test_custom_config(self):
        """사용자 정의 설정 테스트"""
        custom_ips = {"192.168.1.1", "10.0.0.1"}
        config = IPBlockerConfig(
            failed_auth_threshold=5,
            redis_enabled=True,
            whitelist_ips=custom_ips
        )
        
        assert config.failed_auth_threshold == 5
        assert config.redis_enabled is True
        assert config.whitelist_ips == custom_ips


class TestRequestPattern:
    """요청 패턴 테스트"""
    
    def test_request_pattern_creation(self):
        """요청 패턴 생성 테스트"""
        pattern = RequestPattern(
            ip="192.168.1.100",
            timestamp=time.time(),
            endpoint="/auth/login",
            method="POST",
            user_agent="Mozilla/5.0",
            status_code=401,
            response_time=0.5
        )
        
        assert pattern.ip == "192.168.1.100"
        assert pattern.endpoint == "/auth/login"
        assert pattern.status_code == 401
    
    def test_pattern_to_dict(self):
        """패턴 딕셔너리 변환 테스트"""
        pattern = RequestPattern(
            ip="192.168.1.100",
            timestamp=1703123456.789,
            endpoint="/test",
            method="GET",
            user_agent="TestAgent",
            status_code=200,
            response_time=0.1
        )
        
        data = pattern.to_dict()
        assert data["ip"] == "192.168.1.100"
        assert data["timestamp"] == 1703123456.789
        assert data["endpoint"] == "/test"


class TestBlockedIP:
    """차단된 IP 테스트"""
    
    def test_blocked_ip_creation(self):
        """차단 IP 생성 테스트"""
        now = time.time()
        blocked_ip = BlockedIP(
            ip="192.168.1.100",
            reason=BlockReason.FAILED_AUTH_ATTEMPTS,
            threat_level=ThreatLevel.HIGH,
            blocked_at=now,
            blocked_until=now + 3600
        )
        
        assert blocked_ip.ip == "192.168.1.100"
        assert blocked_ip.reason == BlockReason.FAILED_AUTH_ATTEMPTS
        assert blocked_ip.threat_level == ThreatLevel.HIGH
        assert blocked_ip.block_count == 1
    
    def test_blocked_ip_serialization(self):
        """차단 IP 직렬화 테스트"""
        now = time.time()
        blocked_ip = BlockedIP(
            ip="192.168.1.100",
            reason=BlockReason.MANUAL_BLOCK,
            threat_level=ThreatLevel.MEDIUM,
            blocked_at=now,
            blocked_until=now + 1800,
            user_agents={"TestAgent"},
            endpoints_accessed={"/test"}
        )
        
        data = blocked_ip.to_dict()
        assert data["ip"] == "192.168.1.100"
        assert data["reason"] == "manual_block"
        assert data["threat_level"] == "medium"
        assert "TestAgent" in data["user_agents"]
        assert "/test" in data["endpoints_accessed"]
    
    def test_blocked_ip_deserialization(self):
        """차단 IP 역직렬화 테스트"""
        now = time.time()
        data = {
            "ip": "192.168.1.100",
            "reason": "failed_auth_attempts",
            "threat_level": "high",
            "blocked_at": now,
            "blocked_until": now + 3600,
            "block_count": 2,
            "request_count": 50,
            "user_agents": ["TestAgent1", "TestAgent2"],
            "endpoints_accessed": ["/auth/login", "/auth/register"]
        }
        
        blocked_ip = BlockedIP.from_dict(data)
        assert blocked_ip.ip == "192.168.1.100"
        assert blocked_ip.reason == BlockReason.FAILED_AUTH_ATTEMPTS
        assert blocked_ip.threat_level == ThreatLevel.HIGH
        assert blocked_ip.block_count == 2
        assert len(blocked_ip.user_agents) == 2


class TestRequestAnalyzer:
    """요청 분석기 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.config = IPBlockerConfig(
            failed_auth_threshold=3,
            captcha_failure_threshold=2,
            rapid_request_threshold=5
        )
        self.analyzer = RequestAnalyzer(self.config)
    
    def test_analyze_normal_request(self):
        """정상 요청 분석 테스트"""
        pattern = RequestPattern(
            ip="192.168.1.100",
            timestamp=time.time(),
            endpoint="/api/test",
            method="GET",
            user_agent="Mozilla/5.0",
            status_code=200,
            response_time=0.1
        )
        
        should_block, reason, threat_level = self.analyzer.analyze_request(pattern)
        assert should_block is False
        assert reason is None
    
    def test_analyze_failed_auth_pattern(self):
        """인증 실패 패턴 분석 테스트"""
        ip = "192.168.1.100"
        
        # 여러 번의 인증 실패 시뮬레이션
        for i in range(4):
            pattern = RequestPattern(
                ip=ip,
                timestamp=time.time(),
                endpoint="/auth/login",
                method="POST",
                user_agent="Mozilla/5.0",
                status_code=401,
                response_time=0.2
            )
            
            should_block, reason, threat_level = self.analyzer.analyze_request(pattern)
            
            if i >= 2:  # 3번째부터 차단
                assert should_block is True
                assert reason == BlockReason.FAILED_AUTH_ATTEMPTS
                assert threat_level == ThreatLevel.HIGH
                break
    
    def test_analyze_rapid_requests(self):
        """빠른 연속 요청 분석 테스트"""
        ip = "192.168.1.100"
        base_time = time.time()
        
        # 빠른 연속 요청 시뮬레이션
        for i in range(6):
            pattern = RequestPattern(
                ip=ip,
                timestamp=base_time + i,
                endpoint=f"/api/test{i}",
                method="GET",
                user_agent="Mozilla/5.0",
                status_code=200,
                response_time=0.1
            )
            
            should_block, reason, threat_level = self.analyzer.analyze_request(pattern)
            
            if i >= 4:  # 5번째부터 차단 가능성
                if should_block:
                    assert reason == BlockReason.RATE_LIMIT_ABUSE
                    assert threat_level == ThreatLevel.HIGH
                    break
    
    def test_analyze_endpoint_scanning(self):
        """엔드포인트 스캔 분석 테스트"""
        ip = "192.168.1.100"
        
        # 다양한 엔드포인트 접근 시뮬레이션
        endpoints = [f"/api/endpoint{i}" for i in range(25)]
        
        for endpoint in endpoints:
            pattern = RequestPattern(
                ip=ip,
                timestamp=time.time(),
                endpoint=endpoint,
                method="GET",
                user_agent="curl/7.68.0",
                status_code=404,
                response_time=0.1
            )
            
            should_block, reason, threat_level = self.analyzer.analyze_request(pattern)
            
            if should_block:
                assert reason in [BlockReason.ENDPOINT_SCANNING, BlockReason.SUSPICIOUS_PATTERNS]
                break


@pytest.mark.asyncio
class TestIPBlockerStorage:
    """IP 차단 저장소 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.config = IPBlockerConfig(redis_enabled=False)
        self.storage = IPBlockerStorage(self.config)
    
    async def test_block_and_check_ip(self):
        """IP 차단 및 확인 테스트"""
        now = time.time()
        blocked_ip = BlockedIP(
            ip="192.168.1.100",
            reason=BlockReason.MANUAL_BLOCK,
            threat_level=ThreatLevel.MEDIUM,
            blocked_at=now,
            blocked_until=now + 1800
        )
        
        # IP 차단
        await self.storage.block_ip(blocked_ip)
        
        # 차단 확인
        is_blocked, blocked_info = await self.storage.is_blocked("192.168.1.100")
        assert is_blocked is True
        assert blocked_info.ip == "192.168.1.100"
        assert blocked_info.reason == BlockReason.MANUAL_BLOCK
    
    async def test_unblock_ip(self):
        """IP 차단 해제 테스트"""
        now = time.time()
        blocked_ip = BlockedIP(
            ip="192.168.1.100",
            reason=BlockReason.MANUAL_BLOCK,
            threat_level=ThreatLevel.LOW,
            blocked_at=now,
            blocked_until=now + 900
        )
        
        # IP 차단
        await self.storage.block_ip(blocked_ip)
        
        # 차단 확인
        is_blocked, _ = await self.storage.is_blocked("192.168.1.100")
        assert is_blocked is True
        
        # 차단 해제
        await self.storage.unblock_ip("192.168.1.100")
        
        # 해제 확인
        is_blocked, _ = await self.storage.is_blocked("192.168.1.100")
        assert is_blocked is False
    
    async def test_expired_block_cleanup(self):
        """만료된 차단 정리 테스트"""
        now = time.time()
        blocked_ip = BlockedIP(
            ip="192.168.1.100",
            reason=BlockReason.MANUAL_BLOCK,
            threat_level=ThreatLevel.LOW,
            blocked_at=now - 100,
            blocked_until=now - 10  # 이미 만료됨
        )
        
        # 만료된 차단 추가
        await self.storage.block_ip(blocked_ip)
        
        # 차단 확인 시 자동으로 만료된 것 제거
        is_blocked, _ = await self.storage.is_blocked("192.168.1.100")
        assert is_blocked is False
    
    async def test_get_blocked_ips(self):
        """차단된 IP 목록 조회 테스트"""
        now = time.time()
        
        # 여러 IP 차단
        ips = ["192.168.1.100", "192.168.1.101", "192.168.1.102"]
        for i, ip in enumerate(ips):
            blocked_ip = BlockedIP(
                ip=ip,
                reason=BlockReason.MANUAL_BLOCK,
                threat_level=ThreatLevel.MEDIUM,
                blocked_at=now,
                blocked_until=now + 1800 + i * 100
            )
            await self.storage.block_ip(blocked_ip)
        
        # 목록 조회
        blocked_ips = await self.storage.get_blocked_ips()
        assert len(blocked_ips) == 3
        
        blocked_ip_addresses = {ip.ip for ip in blocked_ips}
        assert blocked_ip_addresses == set(ips)


@pytest.mark.asyncio
class TestIPBlockerMiddleware:
    """IP 차단 미들웨어 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        self.config = IPBlockerConfig(
            enabled=True,
            redis_enabled=False,
            failed_auth_threshold=2
        )
        self.middleware = IPBlockerMiddleware(self.config)
    
    def create_mock_request(self, path: str = "/test", method: str = "GET", 
                          client_ip: str = "192.168.1.100", 
                          user_agent: str = "Mozilla/5.0") -> Request:
        """모킹된 요청 객체 생성"""
        request = MagicMock(spec=Request)
        request.url.path = path
        request.method = method
        request.client.host = client_ip
        request.headers = {"user-agent": user_agent}
        return request
    
    async def test_middleware_normal_request(self):
        """정상 요청 처리 테스트"""
        request = self.create_mock_request()
        
        async def call_next(req):
            from fastapi.responses import JSONResponse
            return JSONResponse({"status": "ok"})
        
        response = await self.middleware(request, call_next)
        assert response.status_code == 200
    
    async def test_middleware_whitelisted_ip(self):
        """화이트리스트 IP 테스트"""
        # 화이트리스트 IP로 요청
        request = self.create_mock_request(client_ip="127.0.0.1")
        
        async def call_next(req):
            from fastapi.responses import JSONResponse
            return JSONResponse({"status": "ok"})
        
        response = await self.middleware(request, call_next)
        assert response.status_code == 200
    
    async def test_middleware_blocked_ip(self):
        """차단된 IP 테스트"""
        ip = "192.168.1.100"
        
        # IP 수동 차단
        await self.middleware.block_ip_manually(ip, "Test block", 1)
        
        # 차단된 IP로 요청
        request = self.create_mock_request(client_ip=ip)
        
        async def call_next(req):
            from fastapi.responses import JSONResponse
            return JSONResponse({"status": "ok"})
        
        response = await self.middleware(request, call_next)
        assert response.status_code == 403
    
    def test_get_client_ip(self):
        """클라이언트 IP 추출 테스트"""
        # X-Forwarded-For 헤더 테스트
        request = MagicMock(spec=Request)
        request.headers = {"x-forwarded-for": "203.0.113.195, 198.51.100.178"}
        request.client.host = "192.168.1.1"
        
        ip = self.middleware.get_client_ip(request)
        assert ip == "203.0.113.195"
        
        # X-Real-IP 헤더 테스트
        request.headers = {"x-real-ip": "203.0.113.200"}
        ip = self.middleware.get_client_ip(request)
        assert ip == "203.0.113.200"
        
        # 직접 연결 테스트
        request.headers = {}
        ip = self.middleware.get_client_ip(request)
        assert ip == "192.168.1.1"
    
    def test_is_whitelisted(self):
        """화이트리스트 확인 테스트"""
        assert self.middleware.is_whitelisted("127.0.0.1") is True
        assert self.middleware.is_whitelisted("localhost") is True
        assert self.middleware.is_whitelisted("192.168.1.100") is False
    
    def test_is_protected_endpoint(self):
        """보호 대상 엔드포인트 확인 테스트"""
        assert self.middleware.is_protected_endpoint("/auth/login") is True
        assert self.middleware.is_protected_endpoint("/admin/users") is True
        assert self.middleware.is_protected_endpoint("/api/data") is True
        assert self.middleware.is_protected_endpoint("/public/info") is False
        assert self.middleware.is_protected_endpoint("/docs") is False
    
    async def test_manual_ip_management(self):
        """수동 IP 관리 테스트"""
        ip = "192.168.1.100"
        
        # 수동 차단
        success = await self.middleware.block_ip_manually(ip, "Test block", 2)
        assert success is True
        
        # 차단 확인
        is_blocked, blocked_info = await self.middleware.storage.is_blocked(ip)
        assert is_blocked is True
        assert blocked_info.reason == BlockReason.MANUAL_BLOCK
        
        # 수동 해제
        success = await self.middleware.unblock_ip_manually(ip)
        assert success is True
        
        # 해제 확인
        is_blocked, _ = await self.middleware.storage.is_blocked(ip)
        assert is_blocked is False
    
    async def test_get_stats(self):
        """통계 정보 테스트"""
        stats = await self.middleware.get_stats()
        
        assert "total_requests" in stats
        assert "blocked_requests" in stats
        assert "currently_blocked_ips" in stats
        assert "runtime_seconds" in stats
        assert "blocked_ips_info" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 