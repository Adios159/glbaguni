# 🤖 CAPTCHA 및 봇 방지 시스템 사용법

## 📋 개요

글바구니 백엔드에 구현된 다중 레이어 봇 방지 시스템입니다:
- **Google reCAPTCHA v2/v3** 지원
- **간단한 수학 문제** 챌린지
- **로직 체크** 문제
- **허니팟** 필드 감지
- **IP 기반 Rate Limiting**
- **User-Agent 검증**

## 🚀 빠른 시작

### 1. 환경 변수 설정

`.env` 파일에 다음 설정을 추가하세요:

```bash
# CAPTCHA 기본 설정
CAPTCHA_ENABLED=true
CAPTCHA_PROTECTION_LEVEL=medium

# Google reCAPTCHA (선택사항)
RECAPTCHA_SITE_KEY=your_site_key_here
RECAPTCHA_SECRET_KEY=your_secret_key_here
RECAPTCHA_VERSION=v2

# 간단한 검증 활성화
SIMPLE_MATH_ENABLED=true
LOGIC_CHECK_ENABLED=true
HONEYPOT_ENABLED=true
```

### 2. 필요한 패키지 설치

```bash
pip install captcha httpx
```

### 3. 서버 시작

```bash
cd glbaguni-backend
python -m backend.main
```

## 🛡️ 보호 레벨

### DISABLED
- 모든 CAPTCHA 검증 비활성화

### LOW
- 기본적인 허니팟 체크만 수행
- 요약 요청 등에 적합

### MEDIUM (기본값)
- 허니팟 + 간단한 수학 문제 또는 reCAPTCHA
- 회원가입, 로그인에 적합

### HIGH
- 모든 검증 방법 조합
- 중요한 API 엔드포인트에 적합

### PARANOID
- 최대 보안, 매우 엄격한 검증
- 관리자 기능 등에 적합

## 🎯 보호 대상 엔드포인트

기본적으로 다음 엔드포인트들이 보호됩니다:

| 엔드포인트 | 보호 레벨 | 설명 |
|-----------|-----------|------|
| `/auth/register` | HIGH | 회원가입 |
| `/auth/login` | MEDIUM | 로그인 (실패 시 강화) |
| `/news-search` | LOW | 뉴스 검색 |
| `/summarize` | LOW | 요약 요청 |
| `/contact` | MEDIUM | 문의하기 |

## 📝 API 사용법

### 1. 수학 문제 챌린지

```javascript
// 1. 수학 문제 받기
const mathResponse = await fetch('/captcha/challenge/math');
const mathChallenge = await mathResponse.json();

console.log(mathChallenge);
// {
//   "challenge_id": "abc123",
//   "question": "15 + 7 = ?",
//   "expires_at": 1234567890,
//   "instructions": "주어진 수학 문제를 풀어서 답을 입력하세요."
// }

// 2. 실제 API 요청 시 답 포함
const registerData = {
  "username": "user123",
  "email": "user@example.com", 
  "password": "password123",
  "math_challenge_id": "abc123",
  "math_answer": 22
};

const response = await fetch('/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(registerData)
});
```

### 2. 로직 체크 챌린지

```javascript
// 1. 로직 문제 받기
const logicResponse = await fetch('/captcha/challenge/logic');
const logicChallenge = await logicResponse.json();

console.log(logicChallenge);
// {
//   "challenge_id": "def456",
//   "question": "다음 중 과일이 아닌 것은?",
//   "options": ["사과", "바나나", "자동차", "딸기"],
//   "expires_at": 1234567890
// }

// 2. 답 포함하여 요청
const requestData = {
  "query": "최신 뉴스",
  "logic_challenge_id": "def456", 
  "logic_answer": "자동차"
};
```

### 3. Google reCAPTCHA

```html
<!-- HTML -->
<script src="https://www.google.com/recaptcha/api.js"></script>
<div class="g-recaptcha" data-sitekey="your_site_key"></div>
```

```javascript
// JavaScript
const recaptchaToken = grecaptcha.getResponse();

const requestData = {
  "username": "user123",
  "password": "password123",
  "recaptcha_token": recaptchaToken
};
```

### 4. 허니팟 필드

```html
<!-- 숨겨진 필드 추가 (봇이 채우면 차단됨) -->
<input type="text" name="website" style="display:none" tabindex="-1">
<input type="text" name="url" style="display:none" tabindex="-1">
```

```javascript
const requestData = {
  "username": "user123",
  "password": "password123",
  "honeypot_fields": {
    "website": "",  // 비어있어야 함
    "url": ""       // 비어있어야 함
  }
};
```

## 🔍 테스트 엔드포인트

### CAPTCHA 테스트

```bash
# 수학 문제 생성
curl -X GET http://localhost:8003/captcha/challenge/math

# 로직 문제 생성  
curl -X GET http://localhost:8003/captcha/challenge/logic

# CAPTCHA 검증
curl -X POST http://localhost:8003/captcha/verify \
  -H "Content-Type: application/json" \
  -d '{"math_challenge_id":"abc123","math_answer":22}'

# 설정 정보 조회
curl -X GET http://localhost:8003/captcha/config

# 통계 정보 조회
curl -X GET http://localhost:8003/captcha/stats
```

### 보안 기능 테스트

```bash
# User-Agent 검증 테스트
curl -H "User-Agent: curl/7.68.0" http://localhost:8003/security/test/user-agent

# Rate Limiting 테스트
curl -X GET http://localhost:8003/rate-limit/test

# 종합 보안 정보
curl -X GET http://localhost:8003/security/info
```

## ⚙️ 고급 설정

### 엔드포인트별 보호 레벨 커스터마이징

```python
from utils.captcha_validator import configure_captcha, ProtectionLevel

# 특정 엔드포인트의 보호 레벨 변경
configure_captcha(
    protection_level=ProtectionLevel.HIGH,
    protected_endpoints={
        "/auth/register": ProtectionLevel.PARANOID,
        "/auth/login": ProtectionLevel.HIGH,
        "/admin/*": ProtectionLevel.PARANOID,
        "/public/*": ProtectionLevel.DISABLED
    }
)
```

### Redis를 사용한 확장

```bash
# Docker로 Redis 실행
docker-compose -f docker-compose.redis.yml up -d

# 환경 변수 설정
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 🚨 오류 응답

### CAPTCHA 검증 실패 (403)

```json
{
  "error": "Forbidden",
  "message": "봇 방지 검증 실패: 수학 문제 답이 틀렸습니다",
  "reason": "수학 문제 답이 틀렸습니다",
  "security_level": "medium",
  "timestamp": 1234567890
}
```

### Rate Limit 초과 (429)

```json
{
  "error": "Too Many Requests",
  "message": "요청 한도를 초과했습니다. 60회/분 제한",
  "limit": 60,
  "reset_time": "2024-01-01T12:00:00",
  "retry_after": 30
}
```

### User-Agent 차단 (403)

```json
{
  "error": "Forbidden", 
  "message": "요청이 차단되었습니다. 올바른 클라이언트를 사용해주세요.",
  "reason": "차단된 User-Agent 패턴: ^curl/.*"
}
```

## 📊 모니터링

### 통계 확인

```bash
# CAPTCHA 통계
curl http://localhost:8003/captcha/stats

# 보안 통계  
curl http://localhost:8003/security/stats

# Rate Limiting 통계
curl http://localhost:8003/rate-limit/status
```

### 로그 모니터링

```bash
# 실시간 로그 확인
tail -f logs/glbaguni.log | grep -E "(CAPTCHA|Rate|User-Agent)"
```

## 🔧 문제 해결

### 일반적인 문제들

1. **CAPTCHA 검증이 항상 실패**
   - `RECAPTCHA_SECRET_KEY` 확인
   - 만료 시간 확인 (수학 문제: 5분, 로직 문제: 3분)

2. **Rate Limiting이 작동하지 않음**
   - `RATE_LIMIT_ENABLED=true` 확인
   - IP 추출 로직 확인 (프록시 환경)

3. **User-Agent 검증 우회**
   - 보안 레벨을 `strict` 또는 `lockdown`으로 변경
   - 커스텀 차단 패턴 추가

### 디버깅 모드

```bash
# 디버그 로그 활성화
LOG_LEVEL=DEBUG python -m backend.main
```

## 🤝 기여하기

새로운 봇 방지 기법이나 개선사항이 있다면:

1. Issue 생성
2. Feature 브랜치 생성  
3. Pull Request 제출

## 📄 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 