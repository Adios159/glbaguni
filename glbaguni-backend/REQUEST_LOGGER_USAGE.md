# 요청 로깅 시스템 사용법 가이드

## 📝 개요

글바구니의 요청 로깅 시스템은 **모든 HTTP 요청의 상세 정보를 구조화된 로그로 저장**하여 의심스러운 패턴 분석과 보안 감사에 활용할 수 있는 포괄적인 로깅 솔루션입니다.

## ✨ 주요 기능

### 1. 포괄적인 요청 정보 수집
- **기본 정보**: IP, 시간, 엔드포인트, HTTP 메소드, 응답 코드, 응답 시간
- **네트워크 정보**: 실제 IP, Forwarded-For, User-Agent, Referer
- **보안 정보**: 화이트리스트 여부, 차단 여부, 차단 이유, 위험 레벨
- **사용자 정보**: 사용자 ID, 세션 ID, 요청 ID
- **콘텐츠 정보**: Content-Type, Content-Length, Response-Size

### 2. 다중 저장 형식
- **JSON 로그**: 구조화된 데이터, 분석 도구 친화적
- **CSV 로그**: 스프레드시트 호환, 통계 분석 용이
- **SQLite 데이터베이스**: 복잡한 쿼리, 실시간 분석

### 3. 지능형 분석 기능
- **의심 패턴 감지**: 고빈도 요청, 스캔 시도, 비정상 User-Agent
- **IP 활동 분석**: 특정 IP의 상세한 행동 패턴 분석
- **시간별 타임라인**: 10분 단위 활동 시각화
- **통계 대시보드**: 실시간 요청 통계 및 트렌드

## 🔧 설정

### 환경 변수 설정

```bash
# 요청 로깅 기본 설정
REQUEST_LOGGER_ENABLED=true
REQUEST_LOGGER_LOG_DIR=logs/requests
REQUEST_LOGGER_LOG_FORMATS=json,csv

# 로그 관리 설정
REQUEST_LOGGER_MAX_LOG_SIZE_MB=100
REQUEST_LOGGER_MAX_LOG_FILES=30
REQUEST_LOGGER_RETENTION_DAYS=30

# 데이터베이스 저장 (선택사항)
REQUEST_LOGGER_DATABASE_ENABLED=true
REQUEST_LOGGER_DATABASE_PATH=logs/requests.db

# 제외 경로 설정
REQUEST_LOGGER_EXCLUDE_PATHS=/docs,/redoc,/openapi.json,/static/,/favicon.ico

# 추가 옵션
REQUEST_LOGGER_INCLUDE_REQUEST_BODY=false
REQUEST_LOGGER_INCLUDE_RESPONSE_BODY=false
REQUEST_LOGGER_COMPRESS_OLD_LOGS=true
```

## 📂 로그 구조

### JSON 로그 예시
```json
{
  "timestamp": 1703123456.789,
  "datetime_iso": "2023-12-21T10:30:56.789000",
  "client_ip": "192.168.1.100",
  "real_ip": "203.0.113.10",
  "forwarded_for": "203.0.113.10, 198.51.100.178",
  "method": "POST",
  "endpoint": "/auth/login",
  "query_params": "redirect=%2Fdashboard",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "referer": "https://gulbaguni.com/login",
  "accept_language": "ko-KR,ko;q=0.9,en;q=0.8",
  "content_type": "application/json",
  "content_length": 156,
  "status_code": 401,
  "response_time": 0.245,
  "response_size": 89,
  "is_whitelisted": false,
  "is_blocked": false,
  "block_reason": null,
  "threat_level": null,
  "user_id": null,
  "session_id": "sess_abc123def456",
  "request_id": "1703123456789-192168100"
}
```

### CSV 로그 헤더
```csv
timestamp,datetime_iso,client_ip,real_ip,forwarded_for,method,endpoint,query_params,user_agent,referer,accept_language,content_type,content_length,status_code,response_time,response_size,is_whitelisted,is_blocked,block_reason,threat_level,user_id,session_id,request_id
```

## 📡 API 엔드포인트

### 1. 시스템 통계
```http
GET /request-logs/stats
```

**응답 예시:**
```json
{
  "basic_stats": {
    "total_logged": 15420,
    "total_excluded": 3240,
    "runtime_seconds": 86400,
    "logs_per_minute": 178.5
  },
  "database_stats": {
    "total_requests": 15420,
    "unique_ips": 1245,
    "avg_response_time": 0.156,
    "blocked_requests": 23,
    "error_requests": 145
  }
}
```

### 2. 로그 쿼리
```http
POST /request-logs/query
Content-Type: application/json

{
  "start_time": 1703037056,
  "end_time": 1703123456,
  "client_ip": "192.168.1.100",
  "status_code": 404,
  "limit": 100
}
```

### 3. 최근 로그 조회
```http
GET /request-logs/recent?hours=1&limit=50&status_filter=error
```

### 4. 의심 패턴 분석
```http
GET /request-logs/analyze/suspicious-patterns?hours=24&threshold_requests=100
```

**응답 예시:**
```json
{
  "suspicious_ips": [
    {
      "ip": "192.168.1.100",
      "risk_score": 85,
      "risk_factors": [
        "고빈도 요청: 145.2/시간",
        "다양한 엔드포인트: 23개",
        "높은 4xx 에러율: 67.3%"
      ],
      "stats": {
        "request_count": 3485,
        "requests_per_hour": 145.2,
        "unique_endpoints": 23,
        "error_rate": 67.3
      }
    }
  ]
}
```

### 5. 특정 IP 분석
```http
GET /request-logs/analyze/ip/192.168.1.100?hours=24
```

### 6. IP 활동 타임라인
```http
GET /request-logs/timeline/192.168.1.100?hours=24
```

### 7. CSV 내보내기
```http
GET /request-logs/export/csv?hours=24&client_ip=192.168.1.100
```

## 🔍 의심 패턴 감지

### 자동 감지 기준

#### 1. 고빈도 IP
- **기준**: 시간당 100회 이상 요청
- **위험도**: 30점 추가
- **설명**: DDoS 공격이나 스크래핑 시도

#### 2. 엔드포인트 스캔
- **기준**: 20개 이상 다른 엔드포인트 접근
- **위험도**: 20점 추가
- **설명**: 시스템 탐색 및 취약점 스캔

#### 3. User-Agent 다양성
- **기준**: 5개 이상 다른 User-Agent 사용
- **위험도**: 15점 추가
- **설명**: 봇이 정상 클라이언트로 위장

#### 4. 높은 에러율
- **기준**: 4xx 에러율 50% 이상
- **위험도**: 25점 추가
- **설명**: 무차별 대입 공격이나 스캔 시도

### 위험도 분류
- **0-30점**: 정상 활동
- **31-50점**: 주의 관찰 (LOW)
- **51-70점**: 의심스러운 활동 (MEDIUM)
- **71-90점**: 위험한 활동 (HIGH)
- **91-100점**: 즉시 차단 필요 (CRITICAL)

## 📊 로그 분석 예시

### 1. 브루트포스 공격 탐지
```bash
# 로그인 실패가 많은 IP 찾기
curl -X POST http://localhost:8003/request-logs/query \
  -H "Content-Type: application/json" \
  -d '{
    "endpoint": "/auth/login",
    "status_code": 401,
    "limit": 1000
  }'
```

### 2. 스캔 공격 분석
```bash
# 404 에러가 많은 요청 패턴 분석
curl -X POST http://localhost:8003/request-logs/query \
  -H "Content-Type: application/json" \
  -d '{
    "status_code": 404,
    "limit": 1000
  }'
```

### 3. 특정 IP 상세 분석
```bash
# 의심스러운 IP의 활동 패턴 분석
curl http://localhost:8003/request-logs/analyze/ip/192.168.1.100?hours=24
```

## 🎯 실시간 모니터링

### 1. 실시간 통계 대시보드
```bash
# 현재 시스템 상태 확인
curl http://localhost:8003/request-logs/stats
```

### 2. 의심 활동 감시
```bash
# 지난 1시간 의심 패턴 분석
curl http://localhost:8003/request-logs/analyze/suspicious-patterns?hours=1
```

### 3. 최근 차단된 요청
```bash
# 차단된 요청만 조회
curl http://localhost:8003/request-logs/recent?hours=1&status_filter=blocked
```

## 📈 성능 최적화

### 로그 파일 관리
- **자동 로테이션**: 100MB 초과 시 자동 압축
- **보존 기간**: 30일 후 자동 삭제
- **압축**: gzip 압축으로 저장 공간 절약

### 데이터베이스 최적화
- **인덱스**: timestamp, client_ip, endpoint 등 자동 인덱스
- **정리**: 보존 기간 초과 데이터 자동 삭제
- **성능**: 10,000+ 요청/초 처리 가능

### 메모리 사용량
- **기본 로깅**: 요청당 약 2KB 메모리
- **데이터베이스**: 추가 메모리 사용 최소화
- **정리**: 주기적 메모리 정리로 안정성 확보

## 🛠️ 운영 가이드

### 일일 점검 사항
```bash
# 1. 시스템 상태 확인
curl http://localhost:8003/request-logs/stats

# 2. 의심 활동 확인 (지난 24시간)
curl http://localhost:8003/request-logs/analyze/suspicious-patterns?hours=24

# 3. 에러율 높은 요청 확인
curl http://localhost:8003/request-logs/recent?hours=24&status_filter=error
```

### 주간 분석 작업
```bash
# 1. 주간 통계 데이터 내보내기
curl http://localhost:8003/request-logs/export/csv?hours=168 > weekly_logs.csv

# 2. 상위 활동 IP 분석
# (suspicious-patterns API 결과에서 상위 10개 IP 개별 분석)

# 3. 트렌드 분석
# (주간 요청량, 에러율, 차단율 변화 추이)
```

### 로그 백업
```bash
# 로그 디렉토리 백업
tar -czf backup_$(date +%Y%m%d).tar.gz logs/requests/

# 데이터베이스 백업
cp logs/requests.db backup/requests_$(date +%Y%m%d).db
```

## 🔗 다른 시스템과 연동

### IP 차단 시스템 연동
- 요청 로그의 의심 패턴 → IP 차단 시스템 자동 알림
- 차단된 IP 정보 → 요청 로그에 자동 태깅

### SIEM/보안 도구 연동
```bash
# Splunk 연동 예시
tail -f logs/requests/requests_$(date +%Y-%m-%d).json | \
  while read line; do
    curl -X POST https://splunk.company.com/services/collector \
      -H "Authorization: Splunk YOUR_TOKEN" \
      -d "$line"
  done
```

### 모니터링 알림 설정
```python
# 파이썬 스크립트 예시 - 의심 활동 알림
import requests
import time

while True:
    response = requests.get('http://localhost:8003/request-logs/analyze/suspicious-patterns?hours=1')
    data = response.json()
    
    if len(data['suspicious_ips']) > 0:
        # Slack/Discord 알림 발송
        send_alert(f"의심스러운 IP {len(data['suspicious_ips'])}개 감지!")
    
    time.sleep(300)  # 5분마다 체크
```

## 📋 문제 해결

### 로그가 저장되지 않는 경우
1. **디렉토리 권한 확인**: `logs/requests` 디렉토리 쓰기 권한
2. **디스크 공간 확인**: 충분한 저장 공간 여부
3. **설정 확인**: `REQUEST_LOGGER_ENABLED=true`

### 데이터베이스 오류
1. **SQLite 파일 권한**: 데이터베이스 파일 쓰기 권한
2. **동시 접근 제한**: SQLite 동시 쓰기 제한 고려
3. **파일 잠금**: 다른 프로세스의 DB 파일 사용 여부

### 성능 문제
1. **로그 레벨 조정**: 불필요한 경로 제외
2. **압축 설정**: 자동 압축 활성화
3. **정리 주기**: 보존 기간 단축

이 요청 로깅 시스템을 통해 글바구니 서비스의 모든 접근 패턴을 상세히 모니터링하고 보안 위협을 조기에 감지할 수 있습니다! 🚀