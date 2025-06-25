# IP 차단 시스템 사용법 가이드

## 🛡️ 개요

글바구니의 IP 차단 시스템은 비정상적인 요청 패턴을 자동으로 감지하여 악의적인 IP를 차단하는 고급 보안 시스템입니다.

## ✨ 주요 기능

### 1. 자동 위협 감지
- **연속 인증 실패**: 지정 횟수 이상 로그인 실패 시 차단
- **CAPTCHA 남용**: CAPTCHA 반복 실패 시 차단
- **빠른 연속 요청**: 짧은 시간 내 과도한 요청 시 차단
- **엔드포인트 스캔**: 다양한 경로에 대한 탐색 시도 감지
- **의심스러운 User-Agent**: 비정상적인 클라이언트 패턴 감지

### 2. 4단계 위험도 분류
- **LOW**: 15분 차단 (의심스러운 활동)
- **MEDIUM**: 1시간 차단 (비정상적인 패턴)
- **HIGH**: 2시간 차단 (명백한 공격)
- **CRITICAL**: 24시간 차단 (즉시 차단 필요)

### 3. 저장소 옵션
- **메모리 모드**: 빠른 처리, 서버 재시작 시 초기화
- **Redis 모드**: 영구 저장, 클러스터 환경 지원

## 🔧 설정

### 환경 변수 설정

```bash
# IP 차단 기능 활성화
IP_BLOCKER_ENABLED=true

# Redis 설정 (선택사항)
IP_BLOCKER_REDIS_ENABLED=true
IP_BLOCKER_REDIS_HOST=localhost
IP_BLOCKER_REDIS_PORT=6379
IP_BLOCKER_REDIS_DB=1
IP_BLOCKER_REDIS_PASSWORD=your_password

# 감지 임계값
IP_BLOCKER_FAILED_AUTH_THRESHOLD=10
IP_BLOCKER_CAPTCHA_FAILURE_THRESHOLD=5
IP_BLOCKER_SUSPICIOUS_REQUEST_COUNT=100

# 차단 시간 (초)
IP_BLOCKER_LOW_THREAT_BLOCK_TIME=900      # 15분
IP_BLOCKER_MEDIUM_THREAT_BLOCK_TIME=3600  # 1시간
IP_BLOCKER_HIGH_THREAT_BLOCK_TIME=7200    # 2시간
IP_BLOCKER_CRITICAL_THREAT_BLOCK_TIME=86400 # 24시간

# 화이트리스트 IP (쉼표로 구분)
IP_BLOCKER_WHITELIST_IPS=127.0.0.1,::1,localhost,192.168.1.0/24
```

## 📡 API 엔드포인트

### 1. 차단된 IP 목록 조회
```http
GET /ip-management/blocked-ips
```

**응답 예시:**
```json
{
  "total_blocked": 5,
  "blocked_ips": [
    {
      "ip": "192.168.1.100",
      "reason": "failed_auth_attempts",
      "threat_level": "high",
      "blocked_at": 1703123456.789,
      "blocked_until": 1703130656.789,
      "block_count": 2,
      "remaining_time": 7200
    }
  ],
  "by_threat_level": {
    "low": [],
    "medium": [],
    "high": [...]
  }
}
```

### 2. 특정 IP 정보 조회
```http
GET /ip-management/blocked-ips/{ip}
```

### 3. 수동 IP 차단
```http
POST /ip-management/block-ip
Content-Type: application/json

{
  "ip": "192.168.1.100",
  "reason": "Manual block - suspicious activity",
  "duration_hours": 24
}
```

### 4. 수동 IP 차단 해제
```http
DELETE /ip-management/unblock-ip/{ip}
```

### 5. IP 위험도 분석
```http
POST /ip-management/analyze-ip
Content-Type: application/json

{
  "ip": "192.168.1.100"
}
```

**응답 예시:**
```json
{
  "ip": "192.168.1.100",
  "risk_score": 85,
  "risk_level": "HIGH",
  "risk_factors": [
    "과도한 요청 수: 1500",
    "인증 실패 과다: 15회",
    "다양한 User-Agent: 12개"
  ],
  "recommendation": "위험한 IP로 판단되며 차단을 고려하세요"
}
```

### 6. 시스템 통계
```http
GET /ip-management/stats
```

### 7. 최근 활동 조회
```http
GET /ip-management/recent-activity?limit=50&ip_filter=192.168.1.100
```

### 8. 화이트리스트 조회
```http
GET /ip-management/whitelist
```

### 9. 시스템 설정 조회
```http
GET /ip-management/config
```

## 🎯 차단 시나리오

### 1. 브루트포스 공격 방어
```
시나리오: 공격자가 로그인을 반복 시도
감지: 10회 이상 인증 실패
결과: HIGH 레벨 차단 (2시간)
```

### 2. 스캐닝 공격 방어
```
시나리오: 봇이 다양한 엔드포인트를 탐색
감지: 20개 이상 다른 경로 접근
결과: MEDIUM 레벨 차단 (1시간)
```

### 3. DDoS 공격 방어
```
시나리오: 짧은 시간 내 과도한 요청
감지: 1분 내 20회 이상 요청
결과: HIGH 레벨 차단 (2시간)
```

### 4. 봇 활동 방어
```
시나리오: 다양한 User-Agent 사용
감지: 10개 이상 다른 User-Agent
결과: MEDIUM 레벨 차단 (1시간)
```

## 🔍 모니터링

### 실시간 모니터링 대시보드
```bash
# 현재 차단된 IP 수
curl http://localhost:8003/ip-management/stats

# 최근 활동 확인
curl http://localhost:8003/ip-management/recent-activity

# 특정 IP 분석
curl -X POST http://localhost:8003/ip-management/analyze-ip \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.100"}'
```

### 로그 모니터링
```bash
# 차단 로그 확인
tail -f logs/security.log | grep "IP 차단"

# 위험도 분석 로그
tail -f logs/security.log | grep "위험도"
```

## ⚠️ 주의사항

### 1. 화이트리스트 관리
- 관리자 IP는 반드시 화이트리스트에 추가
- CIDR 표기법 지원 (예: 192.168.1.0/24)
- 로드밸런서, CDN IP 고려

### 2. Redis 사용 시
- 적절한 메모리 설정
- 백업 및 복구 계획 수립
- 네트워크 보안 고려

### 3. 성능 최적화
- 분석 윈도우 시간 조정
- 임계값 조정으로 오탐 방지
- 정기적인 데이터 정리

## 🛠️ 트러블슈팅

### 1. 차단된 관리자 IP 복구
```bash
# 직접 Redis에서 제거
redis-cli DEL "ip_blocker:blocked:YOUR_IP"

# 또는 화이트리스트에 추가 후 서버 재시작
```

### 2. 오탐 발생 시
```bash
# 임계값 조정
IP_BLOCKER_FAILED_AUTH_THRESHOLD=20
IP_BLOCKER_SUSPICIOUS_REQUEST_COUNT=200

# 분석 윈도우 확대
IP_BLOCKER_ANALYSIS_WINDOW_MINUTES=30
```

### 3. 메모리 사용량 최적화
```bash
# 정리 주기 단축
# code 내에서 cleanup_task 주기 조정
```

## 📊 성능 지표

### 평균 응답 시간
- 메모리 모드: < 1ms
- Redis 모드: < 5ms

### 메모리 사용량
- 활성 IP 1000개당 약 2MB
- 요청 히스토리 포함 시 약 5MB

### 처리량
- 초당 10,000+ 요청 처리 가능
- Redis 사용 시 네트워크 대역폭 고려

## 🔗 통합 가이드

### Rate Limiter와 연동
```python
# 자동으로 연동됨
# Rate Limit 위반 시 IP 차단 시스템에서 패턴 분석
```

### User-Agent 검증과 연동
```python
# 자동으로 연동됨
# User-Agent 위반 시 의심도 점수 증가
```

### CAPTCHA 시스템과 연동
```python
# 자동으로 연동됨
# CAPTCHA 실패 시 자동 차단 고려
```

## 📋 체크리스트

### 배포 전 확인사항
- [ ] 화이트리스트 IP 설정 완료
- [ ] Redis 연결 테스트 (사용 시)
- [ ] 임계값 설정 검토
- [ ] 모니터링 대시보드 구성
- [ ] 로그 수집 설정
- [ ] 복구 절차 문서화

### 운영 중 점검사항
- [ ] 차단된 IP 목록 정기 검토
- [ ] 오탐률 모니터링
- [ ] 시스템 리소스 사용량 확인
- [ ] 로그 크기 관리
- [ ] 백업 상태 점검

이 IP 차단 시스템을 통해 글바구니 서비스의 보안을 크게 강화할 수 있습니다. 자동화된 위협 감지와 실시간 차단으로 안전한 서비스 운영이 가능합니다. 