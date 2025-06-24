# 백엔드 프로젝트 구조 재정비 계획

## 📋 현재 상황 분석

### 🚨 문제점
1. **파일 크기 초과**: 일부 파일이 200줄을 크게 초과
   - `fetcher.py`: 646줄
   - `news_aggregator.py`: 524줄  
   - `history_service.py`: 508줄
   - `gpt_service.py`: 574줄
   - `routers/health.py`: 305줄

2. **기능 혼재**: 하나의 파일에 여러 기능이 섞여 있음
3. **의존성 복잡**: 모듈 간 의존성이 복잡하게 얽혀 있음

## 🎯 재정비 목표

### ✅ 달성해야 할 기준
1. **파일당 200줄 이하** 유지
2. **기능별 모듈 분리** (단일 책임 원칙)
3. **명확한 디렉토리 구조**
4. **간단한 의존성 관계**

## 🏗️ 새로운 디렉토리 구조

```
backend/
├── main.py                 # FastAPI 앱 진입점 (100줄 이하)
├── routers/                # API 라우터 (각 파일 150줄 이하)
│   ├── __init__.py
│   ├── core.py            # 기본 엔드포인트 (/, /health)
│   ├── summarize.py       # 요약 관련 API
│   ├── news.py            # 뉴스 검색 API
│   ├── fetch.py           # 데이터 수집 API
│   ├── auth.py            # 인증/보안 API
│   ├── history.py         # 히스토리 API
│   └── recommendations.py # 추천 API
├── services/              # 비즈니스 로직 (각 파일 200줄 이하)
│   ├── __init__.py
│   ├── gpt/              # GPT 관련 서비스들
│   │   ├── __init__.py
│   │   ├── client.py     # GPT 클라이언트
│   │   ├── prompts.py    # 프롬프트 관리
│   │   └── summarizer.py # 요약 로직
│   ├── rss/              # RSS 관련 서비스들
│   │   ├── __init__.py
│   │   ├── fetcher.py    # RSS 수집
│   │   └── parser.py     # RSS 파싱
│   ├── content/          # 콘텐츠 처리
│   │   ├── __init__.py
│   │   ├── extractor.py  # 콘텐츠 추출
│   │   └── cleaner.py    # 텍스트 정리
│   ├── news/             # 뉴스 관련
│   │   ├── __init__.py
│   │   ├── search.py     # 뉴스 검색
│   │   └── categorizer.py# 카테고리 분류
│   ├── user/             # 사용자 관련
│   │   ├── __init__.py
│   │   ├── history.py    # 히스토리 관리
│   │   └── recommendations.py # 추천 시스템
│   └── notification/     # 알림 관련
│       ├── __init__.py
│       └── email.py      # 이메일 발송
├── utils/                # 유틸리티 (각 파일 100줄 이하)
│   ├── __init__.py
│   ├── logging_config.py
│   ├── environment.py
│   ├── validator.py
│   ├── security.py
│   └── exceptions.py
├── models/               # 데이터 모델
│   ├── __init__.py
│   ├── database/        # DB 모델
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── article.py
│   │   └── history.py
│   └── schemas/         # API 스키마
│       ├── __init__.py
│       ├── requests.py
│       └── responses.py
└── config/              # 설정 관리
    ├── __init__.py
    ├── settings.py
    └── database.py
```

## 🔄 단계별 리팩토링 계획

### Phase 1: 서비스 분리 (우선순위 1)
1. **GPT 서비스 분리**
   - `gpt_service.py` → `services/gpt/` 디렉토리로 분할
   - `client.py`: API 호출 로직만
   - `prompts.py`: 프롬프트 템플릿 관리
   - `summarizer.py`: 요약 로직

2. **RSS 서비스 분리** 
   - `fetcher.py` → `services/rss/` 디렉토리로 분할
   - `fetcher.py`: RSS 수집 로직
   - `parser.py`: RSS 파싱 로직

3. **콘텐츠 처리 분리**
   - 콘텐츠 추출 로직을 `services/content/`로 이동

### Phase 2: 라우터 정리 (우선순위 2)
1. **새로운 라우터 생성**
   - `routers/news.py`: 뉴스 검색 API
   - `routers/fetch.py`: 데이터 수집 API  
   - `routers/auth.py`: 인증/보안 API

2. **기존 라우터 간소화**
   - `routers/health.py`: 200줄 이하로 축소
   - `routers/summarize.py`: 기능별 분리

### Phase 3: 모델 및 유틸리티 정리 (우선순위 3)
1. **모델 분리**
   - DB 모델과 API 스키마 분리
   - 기능별 모델 그룹화

2. **유틸리티 모듈화**
   - 각 유틸리티 파일을 100줄 이하로 유지

## 🔧 구현 가이드라인

### 파일 크기 관리
- **라우터**: 최대 150줄
- **서비스**: 최대 200줄  
- **유틸리티**: 최대 100줄
- **모델**: 최대 150줄

### 의존성 관리
- **순환 의존성 금지**
- **명확한 계층 구조**: routers → services → utils
- **인터페이스 기반 설계**

### 코드 품질
- **단일 책임 원칙** 준수
- **명확한 함수/클래스 이름**
- **충분한 로깅 및 에러 처리**

## 📊 예상 효과

### ✅ 개선 효과
1. **가독성 향상**: 파일이 작아져 이해하기 쉬움
2. **유지보수성 향상**: 기능별 분리로 수정이 용이
3. **테스트 용이성**: 작은 단위로 테스트 가능
4. **확장성**: 새로운 기능 추가가 쉬움
5. **팀 협업**: 파일 충돌 가능성 감소

### 🎯 성능 영향
- **임포트 시간**: 약간 증가 (미미한 수준)
- **메모리 사용**: 변화 없음
- **실행 속도**: 변화 없음

## 🚀 다음 단계

1. **Phase 1 구현**: GPT, RSS, 콘텐츠 서비스 분리
2. **테스트**: 기능 정상 동작 확인
3. **Phase 2 구현**: 라우터 정리 및 새 라우터 생성
4. **최종 검증**: 전체 시스템 통합 테스트
5. **문서 업데이트**: README 및 API 문서 갱신

---

**목표**: 깔끔하고 유지보수가 쉬운 모듈화된 백엔드 구조 구축 ✨ 