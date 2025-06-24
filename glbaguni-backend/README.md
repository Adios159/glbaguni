# 글바구니 (Glbaguni) - AI-Powered News Aggregation & Summarization Platform v3.0.0

한국어와 영어를 지원하는 AI 기반 뉴스 수집 및 요약 플랫폼입니다. RSS 피드 수집, 자연어 뉴스 검색, 개인화된 추천 시스템, 사용자 히스토리 관리를 제공합니다.

## 🚀 주요 기능

### ✅ **완전 리팩토링된 모듈화 아키텍처 (v3.0.0)**
- **클린 아키텍처**: 각 기능별로 완전히 분리된 모듈 구조
- **라우터 분리**: FastAPI 라우터를 기능별로 완전 분리 (`/summarize`, `/core`, `/health`)
- **서비스 레이어**: GPT, 뉴스, RSS 서비스를 독립적인 서비스로 분리
- **유틸리티 모듈**: 로깅, 예외처리, 환경설정, 검증 등 유틸리티 완전 분리
- **컴포넌트 관리**: 의존성 주입 패턴으로 컴포넌트 생명주기 관리

### ✅ **다국어 뉴스 요약 시스템**
- **다국어 지원**: 한국어(`ko`) 및 영어(`en`) 요약 제공
- **지능형 언어 감지**: 자동 언어 인식 및 적절한 요약 언어 선택
- **GPT-4 통합**: OpenAI GPT-4를 활용한 고품질 요약
- **커스텀 프롬프트**: 사용자 정의 요약 스타일 지원
- **보안 검증**: 입력/출력 데이터 검증 및 정화 시스템

### ✅ **한국 RSS 피드 호환성**
- **자동 인코딩 감지**: chardet을 사용한 UTF-8, EUC-KR, CP949 자동 감지
- **주요 한국 언론사 지원**: JTBC, 한겨레, MBC, SBS, 연합뉴스, 조선일보 등
- **차단 방지 헤더**: 403/404 오류 방지를 위한 최적화된 User-Agent
- **한국어 콘텐츠 추출**: 한국 뉴스 기사 형식에 맞춘 강력한 HTML 파싱
- **비동기 처리**: 대량 RSS 처리를 위한 비동기 fetcher 구현

### ✅ **자연어 뉴스 검색**
- **자연어 쿼리**: "요즘 반도체 뉴스 알려줘" 형태의 자연스러운 검색
- **키워드 자동 추출**: GPT를 활용한 지능적 키워드 추출
- **관련 뉴스 필터링**: 키워드 기반 관련도 높은 기사 선별
- **실시간 RSS 수집**: 주요 언론사 RSS 피드에서 최신 뉴스 수집
- **다양한 RSS 소스**: SBS, JTBC, 연합뉴스, 매일경제, 정부기관 등 35개 소스

### ✅ **사용자 히스토리 및 추천 시스템**
- **개인 히스토리**: 사용자별 요약 기록 저장 및 관리
- **개인화된 추천**: 사용자의 관심사 기반 맞춤 뉴스 추천
  - 키워드 기반 추천
  - 카테고리 기반 추천
  - 혼합 추천 알고리즘
- **다국어 히스토리**: 언어별 분류 및 검색 지원
- **통계 대시보드**: 사용자 활동 분석 및 선호도 통계
- **자동 카테고리 분류**: 정치, 경제, 기술, 건강, 스포츠, 문화 등

### ✅ **모던 React 프론트엔드**
- **언어 토글**: 한국어/영어 요약 언어 선택 UI (🇰🇷/🇺🇸)
- **다크 모드**: 완전한 다크/라이트 테마 지원
- **반응형 디자인**: Tailwind CSS 기반 모바일 친화적 인터페이스
- **실시간 피드백**: 처리 상태 및 언어 선택 시각적 표시
- **5개 주요 페이지**: 홈, 요약, 히스토리, 추천, 연락처

### ✅ **고급 기능**
- **이메일 전송**: 아름답게 포맷된 요약 이메일 전송
- **보안 시스템**: 입력 검증, 출력 정화, SQL 인젝션 방지
- **로깅 시스템**: 구조화된 로깅과 모니터링
- **예외 처리**: 포괄적인 에러 핸들링 및 사용자 친화적 에러 메시지
- **성능 최적화**: 비동기 처리, 컴포넌트 캐싱, 배치 처리

## 📁 프로젝트 구조 (v3.0.0)

```
gulbaguni/
├── glbaguni-backend/          # 백엔드 애플리케이션
│   ├── backend/
│   │   ├── main.py                    # FastAPI 앱 진입점 (v3.0.0)
│   │   ├── routers/                   # API 라우터 모듈
│   │   │   ├── core.py               # 핵심 라우터 (/, /health, /debug)
│   │   │   ├── summarize.py          # 요약 관련 엔드포인트
│   │   │   └── health.py             # 헬스체크 전용 라우터
│   │   ├── services/                  # 비즈니스 로직 서비스
│   │   │   ├── gpt_service.py        # GPT API 통합 서비스
│   │   │   ├── gpt.py                # GPT 호출 유틸리티
│   │   │   ├── news_service.py       # 뉴스 관련 비즈니스 로직
│   │   │   ├── rss_service.py        # RSS 피드 처리 서비스
│   │   │   └── summarizer.py         # 요약 로직 서비스
│   │   ├── utils/                     # 유틸리티 모듈
│   │   │   ├── logging_config.py     # 로깅 설정
│   │   │   ├── environment.py        # 환경변수 검증
│   │   │   ├── components.py         # 컴포넌트 관리
│   │   │   ├── middleware.py         # 미들웨어
│   │   │   ├── exception_handlers.py # 예외 처리
│   │   │   └── validator.py          # 입력 검증
│   │   ├── models/                    # 데이터 모델
│   │   │   ├── request_schema.py     # 요청 스키마
│   │   │   └── response_schema.py    # 응답 스키마
│   │   ├── config/                    # 설정 모듈
│   │   │   └── settings.py          # 애플리케이션 설정
│   │   ├── news_aggregator.py        # 자연어 뉴스 검색 시스템
│   │   ├── history_service.py        # 히스토리 및 추천 서비스
│   │   ├── fetcher.py               # RSS/HTML 콘텐츠 수집
│   │   ├── async_fetcher.py         # 비동기 콘텐츠 수집
│   │   ├── summarizer.py            # 요약 엔진
│   │   ├── async_summarizer.py      # 비동기 요약 엔진
│   │   ├── database.py              # 데이터베이스 설정
│   │   ├── models.py                # SQLAlchemy 모델
│   │   ├── notifier.py              # 이메일 알림 시스템
│   │   ├── security.py              # 보안 검증 시스템
│   │   └── config.py                # 환경 설정
│   ├── requirements.txt             # Python 의존성
│   ├── env_template.txt            # 환경변수 템플릿
│   └── README.md                   # 메인 문서
├── glbaguni-frontend/              # React 프론트엔드
│   ├── src/
│   │   ├── App.jsx                 # 메인 앱 컴포넌트
│   │   ├── pages/                  # 페이지 컴포넌트
│   │   │   ├── HomePage.jsx        # 홈페이지
│   │   │   ├── SummarizePage.jsx   # 요약 페이지
│   │   │   ├── HistoryPage.jsx     # 히스토리 페이지
│   │   │   ├── RecommendationPage.jsx # 추천 페이지
│   │   │   └── ContactPage.jsx     # 연락처 페이지
│   │   ├── components/             # 재사용 가능한 UI 컴포넌트
│   │   │   ├── Navbar.jsx          # 네비게이션 바
│   │   │   └── ThemeToggle.jsx     # 테마 토글
│   │   └── hooks/                  # 커스텀 React 훅
│   │       ├── useTheme.js         # 테마 관리 훅
│   │       └── useFormValidation.js # 폼 검증 훅
│   ├── package.json                # 프론트엔드 의존성
│   ├── tailwind.config.js         # Tailwind CSS 설정
│   └── vite.config.js             # Vite 빌드 설정
├── README_news.md                  # 뉴스 검색 시스템 문서
├── news_summarizer.py             # 독립 실행형 뉴스 요약 스크립트
├── example_usage.py               # 사용 예제 스크립트
└── test_new_features.py           # 새 기능 테스트 스크립트
```

## 🛠️ 설치 및 설정

### 필수 조건
- Python 3.8+
- Node.js 16+
- OpenAI API 키
- SMTP 이메일 자격증명

### 1. 백엔드 설정

```bash
# 프로젝트 클론 및 백엔드 디렉토리 이동
cd glbaguni-backend

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 설정

```bash
# 템플릿 복사 및 설정
cp env_template.txt .env
```

`.env` 파일에 자격증명 입력:

```env
# OpenAI 설정
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# SMTP 설정 (Gmail 예시)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
SMTP_USE_TLS=true

# 앱 설정
DEFAULT_SUMMARY_LENGTH=3
MAX_ARTICLES_PER_REQUEST=15

# 데이터베이스 설정
DATABASE_URL=sqlite:///./glbaguni.db

# 보안 설정
SECRET_KEY=your-secret-key-here
```

### 3. 백엔드 서버 시작

```bash
# 방법 1: 직접 실행 (권장)
cd backend && python main.py

# 방법 2: uvicorn 직접 실행
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

백엔드 서버: `http://localhost:8001`

### 4. 프론트엔드 설정

```bash
# 프론트엔드 디렉토리 이동
cd glbaguni-frontend

# 의존성 설치
npm install

# 개발 서버 시작
npm run dev
```

프론트엔드 서버: `http://localhost:5173`

## 📚 API 문서 (v3.0.0)

### 🔄 **핵심 엔드포인트**

#### GET `/` - 서비스 정보
서비스 기본 정보와 상태를 반환합니다.

#### GET `/health` - 헬스체크
시스템 전반의 건강 상태를 확인합니다.

#### GET `/debug` - 디버그 정보
시스템 구성요소 상태와 환경 정보를 제공합니다.

### 📝 **요약 엔드포인트**

#### POST `/summarize/text` - 텍스트 요약
직접 입력한 텍스트를 요약합니다.

**요청 본문:**
```json
{
  "text": "요약할 텍스트 내용...",
  "language": "ko"
}
```

**응답:**
```json
{
  "success": true,
  "summary": "요약된 내용...",
  "original_length": 1000,
  "summary_length": 200,
  "language": "ko",
  "model": "gpt-3.5-turbo",
  "processed_at": "2024-01-01T12:00:00",
  "request_id": "abc123"
}
```

### 🔍 **뉴스 검색 엔드포인트**

#### POST `/news-search` - 자연어 뉴스 검색
자연어 쿼리로 관련 뉴스를 검색하고 요약합니다.

**요청 본문:**
```json
{
  "query": "요즘 반도체 뉴스 알려줘",
  "max_articles": 10,
  "language": "ko",
  "recipient_email": "user@example.com",
  "user_id": "user-123"
}
```

**응답:**
```json
{
  "success": true,
  "message": "5개의 관련 뉴스를 찾아 요약했습니다.",
  "articles": [
    {
      "title": "삼성전자 3나노 반도체 상용화 발표",
      "summary": "삼성전자가 3나노 공정을 상용화한다고 발표했습니다...",
      "link": "https://news.example.com/samsung-3nm",
      "source": "SBS",
      "category": "기술/Technology"
    }
  ],
  "total_articles": 5,
  "extracted_keywords": ["반도체", "삼성전자", "3나노"],
  "processed_at": "2024-01-01T12:00:00"
}
```

### 📖 **히스토리 엔드포인트**

#### GET `/history` - 사용자 히스토리 조회
사용자의 요약 히스토리를 페이지네이션과 언어 필터링으로 조회합니다.

**쿼리 파라미터:**
- `user_id`: 사용자 ID (필수)
- `page`: 페이지 번호 (기본값: 1)
- `per_page`: 페이지당 항목 수 (기본값: 20, 최대: 100)
- `language`: 언어 필터 (선택, ko/en)

**응답:**
```json
{
  "success": true,
  "history": [
    {
      "id": 1,
      "article_title": "제목",
      "summary_text": "요약",
      "summary_language": "ko",
      "category": "기술/Technology",
      "keywords": ["키워드1", "키워드2"],
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "total_items": 50,
  "page": 1,
  "per_page": 20,
  "total_pages": 3
}
```

### 🎯 **추천 엔드포인트**

#### GET `/recommendations` - 개인화된 추천
사용자의 히스토리를 기반으로 개인화된 뉴스를 추천합니다.

**쿼리 파라미터:**
- `user_id`: 사용자 ID (필수)
- `limit`: 추천 개수 (기본값: 5, 최대: 20)

**응답:**
```json
{
  "success": true,
  "recommendations": [
    {
      "article_title": "추천 기사 제목",
      "article_url": "https://example.com/article",
      "article_source": "SBS",
      "recommendation_type": "keyword",
      "recommendation_score": 0.85,
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "total_recommendations": 5,
  "recommendation_types": ["keyword", "category"]
}
```

### 📊 **통계 엔드포인트**

#### GET `/user-stats` - 사용자 통계
사용자의 활동 통계를 제공합니다.

**쿼리 파라미터:**
- `user_id`: 사용자 ID (필수)

**응답:**
```json
{
  "success": true,
  "stats": {
    "total_summaries": 45,
    "summaries_this_month": 12,
    "favorite_categories": ["기술/Technology", "경제/Economy"],
    "most_used_language": "ko",
    "recommendations_count": 3
  }
}
```

## 🔧 고급 기능

### 🛡️ **보안 시스템**
- **입력 검증**: SQL 인젝션, XSS 공격 방지
- **출력 정화**: 응답 데이터 정화 및 검증
- **레이트 리미팅**: API 호출 빈도 제한
- **환경변수 검증**: 필수 설정값 검증

### 📊 **로깅 및 모니터링**
- **구조화된 로깅**: JSON 형태의 구조화된 로그
- **성능 모니터링**: 요청 처리 시간 추적
- **에러 추적**: 상세한 에러 로깅 및 알림
- **사용자 활동 추적**: 사용 패턴 분석

### ⚡ **성능 최적화**
- **비동기 처리**: 대량 데이터 처리를 위한 비동기 아키텍처
- **컴포넌트 캐싱**: 재사용 가능한 컴포넌트 캐싱
- **배치 처리**: 여러 요청을 배치로 처리
- **데이터베이스 최적화**: 인덱싱 및 쿼리 최적화

## 🚨 문제 해결

### 1. OpenAI API 에러
- API 키 유효성 확인
- 할당량 초과 여부 확인
- 네트워크 연결 상태 확인

### 2. 서버 시작 실패
- 포트 충돌 확인 (8001번 포트)
- 환경변수 설정 확인
- 의존성 설치 상태 확인

### 3. RSS 피드 접근 불가
- 네트워크 연결 확인
- RSS URL 유효성 확인
- User-Agent 헤더 문제

### 4. 데이터베이스 오류
- SQLite 파일 권한 확인
- 데이터베이스 마이그레이션 실행
- 디스크 공간 확인

## 📈 성능 벤치마크

### 응답 시간
- 텍스트 요약: 평균 2-5초
- RSS 요약: 평균 10-30초 (기사 수에 따라)
- 히스토리 조회: 평균 100-300ms
- 추천 생성: 평균 500ms-1s

### 처리 용량
- 동시 요청 처리: 최대 50개
- 일일 요약 용량: 최대 1,000건
- RSS 피드 처리: 시간당 최대 500개 기사

## 🔮 향후 계획

### v3.1.0 (예정)
- **실시간 알림**: WebSocket을 통한 실시간 요약 알림
- **고급 추천**: 머신러닝 기반 추천 알고리즘
- **다국어 확장**: 일본어, 중국어 지원

### v3.2.0 (예정)
- **API 키 관리**: 사용자별 API 키 관리 시스템
- **대시보드**: 관리자용 모니터링 대시보드
- **데이터 분석**: 사용 패턴 분석 및 리포트

## 📞 지원 및 문의

- **GitHub Issues**: 버그 신고 및 기능 요청
- **이메일**: 기술 지원 문의
- **문서**: API 문서 및 가이드

---

**글바구니 v3.0.0** - AI가 만드는 더 나은 뉴스 경험 🚀
