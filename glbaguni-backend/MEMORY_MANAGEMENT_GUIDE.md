# 📚 메모리 관리 시스템 가이드

## 🧠 개요

글바구니 백엔드 서버에는 주기적으로 메모리를 모니터링하고 자동으로 정리하는 고급 메모리 관리 시스템이 통합되어 있습니다. 이 시스템은 서버의 안정성을 보장하고 메모리 누수를 방지합니다.

## ✨ 주요 기능

### 1. **실시간 메모리 모니터링**
- 시스템 메모리 사용률 실시간 추적
- 프로세스별 메모리 사용량 모니터링  
- 스왑 메모리 사용률 감시
- 가비지 컬렉션 통계 수집

### 2. **자동 메모리 정리**
- 임계값 기반 자동 정리 실행
- 가비지 컬렉션 강제 실행
- 캐시 자동 정리 (LRU 방식)
- 약한 참조(weak reference) 정리

### 3. **지능형 알림 시스템**
- 메모리 사용률 경고 (기본값: 70%)
- 심각한 상황 알림 (기본값: 85%)
- 쿨다운 기능으로 스팸 방지 (기본값: 15분)

### 4. **REST API 제공**
- 메모리 상태 조회
- 수동 정리 실행
- 설정 변경
- 히스토리 조회

## 🚀 시작하기

메모리 관리 시스템은 서버 시작 시 자동으로 활성화됩니다.

```python
# 서버 시작 시 자동 실행됨
await initialize_memory_manager()
```

## 📊 API 사용법

### 메모리 상태 확인

```bash
# 현재 메모리 상태 조회
curl -X GET "http://localhost:8003/memory/status"
```

**응답 예시:**
```json
{
  "status": "healthy",
  "message": "메모리 상태가 양호합니다 (45.2%)",
  "memory_percent": 45.2,
  "process_memory_mb": 256.8,
  "cache_size": 150,
  "timestamp": "2024-01-01T12:00:00"
}
```

### 상세 통계 조회

```bash
# 상세한 메모리 통계 및 트렌드
curl -X GET "http://localhost:8003/memory/stats"
```

**응답 예시:**
```json
{
  "current": {
    "timestamp": "2024-01-01T12:00:00",
    "total_memory_mb": 8192.0,
    "available_memory_mb": 4096.0,
    "used_memory_mb": 4096.0,
    "memory_percent": 50.0,
    "process_memory_mb": 256.8,
    "process_memory_percent": 3.1,
    "swap_memory_mb": 0.0,
    "swap_percent": 0.0,
    "gc_collections": {"0": 10, "1": 2, "2": 0},
    "cache_size": 150
  },
  "trend": {
    "trend": "stable",
    "avg_usage": 48.5,
    "peak_usage": 52.3,
    "sample_count": 30
  },
  "history_size": 288,
  "optimization_count": 5,
  "cache_size": 150,
  "is_running": true
}
```

### 수동 메모리 정리

```bash
# 즉시 메모리 정리 실행
curl -X POST "http://localhost:8003/memory/cleanup"
```

**응답 예시:**
```json
{
  "success": true,
  "optimization_time": 0.25,
  "gc_collected": 42,
  "cache_cleaned": 30,
  "memory_freed_mb": 15.2,
  "message": "메모리 정리가 성공적으로 완료되었습니다."
}
```

### 백그라운드 정리

```bash
# 백그라운드에서 메모리 정리 (즉시 응답)
curl -X POST "http://localhost:8003/memory/cleanup/background"
```

### 메모리 히스토리 조회

```bash
# 최근 6시간 메모리 사용 히스토리
curl -X GET "http://localhost:8003/memory/history?hours=6"
```

### 설정 조회 및 변경

```bash
# 현재 설정 조회
curl -X GET "http://localhost:8003/memory/config"

# 설정 변경
curl -X POST "http://localhost:8003/memory/config" \
  -H "Content-Type: application/json" \
  -d '{
    "monitoring_interval_seconds": 30,
    "cleanup_interval_seconds": 180,
    "warning_threshold": 75.0,
    "critical_threshold": 90.0,
    "cleanup_threshold": 85.0,
    "max_cache_size": 2000,
    "enable_alerts": true
  }'
```

## ⚙️ 설정 옵션

### 기본 설정

```python
class MemoryConfig:
    # 모니터링 설정
    monitoring_interval_seconds: int = 60    # 1분마다 모니터링
    cleanup_interval_seconds: int = 300      # 5분마다 정리
    
    # 임계값 설정 (백분율)
    warning_threshold: float = 70.0          # 경고 임계값
    critical_threshold: float = 85.0         # 심각 임계값  
    cleanup_threshold: float = 80.0          # 정리 시작 임계값
    
    # 캐시 관리
    max_cache_size: int = 1000               # 최대 캐시 크기
    cache_cleanup_ratio: float = 0.3         # 30% 정리
    
    # 히스토리 관리
    max_history_size: int = 288              # 24시간 (5분 간격)
    
    # 알림 설정
    enable_alerts: bool = True               # 알림 활성화
    alert_cooldown_minutes: int = 15         # 15분간 동일 알림 방지
```

### 임계값 설명

- **warning_threshold (70%)**: 경고 로그 출력
- **cleanup_threshold (80%)**: 자동 정리 시작
- **critical_threshold (85%)**: 심각한 상황 알림

## 🔧 프로그래밍 방식 사용

### 캐시 등록

```python
from utils.memory_manager import get_memory_manager

# 캐시 객체 등록 (자동 관리 대상에 포함)
memory_manager = get_memory_manager()
my_cache = {}
memory_manager.register_cache("my_cache", my_cache)
```

### 수동 제어

```python
from utils.memory_manager import get_memory_manager

memory_manager = get_memory_manager()

# 강제 정리 실행
result = await memory_manager.force_cleanup()

# 현재 상태 조회
stats = memory_manager.get_stats()
health = memory_manager.get_health_status()
```

### 커스텀 캐시 정리

캐시 클래스에 `cleanup` 메서드를 구현하면 자동으로 호출됩니다:

```python
class MyCache:
    def __init__(self):
        self.data = {}
    
    def cleanup(self, cleanup_ratio: float = 0.3):
        """커스텀 정리 로직"""
        items_to_remove = int(len(self.data) * cleanup_ratio)
        # LRU 또는 다른 정리 전략 구현
        pass
```

## 📈 모니터링 및 로깅

### 로그 레벨

```python
# 정상 작동
INFO: "🧠 메모리 관리자 초기화 완료"
INFO: "🚀 메모리 관리 시작"

# 정기 모니터링  
DEBUG: "💾 메모리 상태: 시스템 45.2%, 프로세스 256.8MB, 캐시 150개"

# 경고 상황
WARNING: "⚠️ WARNING: 메모리 사용률 72.5% (경고값: 70.0%)"

# 심각한 상황
CRITICAL: "🚨 CRITICAL: 메모리 사용률 87.1% (임계값: 85.0%)"

# 정리 작업
INFO: "🔧 메모리 최적화 완료: GC 42개 객체, 캐시 30개 항목, 15.2MB 해제"
```

### 대시보드 활용

API를 활용하여 모니터링 대시보드를 구축할 수 있습니다:

```javascript
// 메모리 상태 실시간 조회
const checkMemoryStatus = async () => {
  const response = await fetch('/memory/status');
  const status = await response.json();
  
  if (status.status === 'critical') {
    alert('메모리 사용률이 매우 높습니다!');
  }
};

// 5초마다 상태 확인
setInterval(checkMemoryStatus, 5000);
```

## 🚨 트러블슈팅

### 자주 발생하는 문제

#### 1. 메모리 사용률이 계속 증가하는 경우

```bash
# 강제 정리 실행
curl -X POST "http://localhost:8003/memory/cleanup"

# 임계값 낮추기
curl -X POST "http://localhost:8003/memory/config" \
  -H "Content-Type: application/json" \
  -d '{"cleanup_threshold": 60.0}'
```

#### 2. 정리 효과가 없는 경우

- 애플리케이션 코드에서 메모리 누수 확인
- 큰 객체가 제대로 해제되지 않는지 확인
- 순환 참조 문제 점검

#### 3. 성능 문제

```python
# 모니터링 간격 조정
config = MemoryConfig(
    monitoring_interval_seconds=120,  # 2분으로 늘림
    cleanup_interval_seconds=600      # 10분으로 늘림
)
```

### 로그 분석

```bash
# 메모리 관련 로그만 필터링
grep "memory_manager\|메모리\|Memory" logs/app.log

# 경고/오류만 보기
grep -E "WARNING|ERROR|CRITICAL.*메모리" logs/app.log
```

## 🔐 보안 고려사항

- 메모리 관리 API는 내부 관리용으로 설계됨
- 프로덕션에서는 인증이 필요한 엔드포인트로 보호 권장
- 메모리 정보는 민감한 데이터를 포함할 수 있음

## 📋 베스트 프랙티스

### 1. **적절한 임계값 설정**
```python
# 서버 사양에 맞게 조정
memory_config = MemoryConfig(
    warning_threshold=60.0,      # 메모리가 적은 서버
    critical_threshold=75.0,
    cleanup_threshold=65.0
)
```

### 2. **정기적인 모니터링**
```bash
# 크론잡으로 정기 체크
*/10 * * * * curl -s localhost:8003/memory/status | jq '.memory_percent'
```

### 3. **알림 시스템 통합**
```python
# 슬랙, 이메일 등과 연동
async def send_memory_alert(status):
    if status['memory_percent'] > 80:
        await send_slack_message(f"서버 메모리 사용률 높음: {status['memory_percent']}%")
```

### 4. **캐시 최적화**
```python
# 적절한 캐시 크기 설정
memory_manager.register_cache("summary_cache", summary_cache)
memory_manager.register_cache("article_cache", article_cache)
```

## 📖 추가 리소스

- [Python 메모리 관리 문서](https://docs.python.org/3/library/gc.html)
- [psutil 라이브러리 문서](https://psutil.readthedocs.io/)
- [FastAPI 백그라운드 태스크](https://fastapi.tiangolo.com/tutorial/background-tasks/)

---

이 메모리 관리 시스템을 통해 안정적이고 효율적인 서버 운영이 가능합니다. 문제가 발생하거나 추가 기능이 필요한 경우 언제든지 문의해 주세요! 🚀 