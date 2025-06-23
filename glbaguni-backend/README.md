# 글바구니 (Glbaguni) - AI-Powered News Aggregation & Summarization Platform

한국어와 영어를 지원하는 AI 기반 뉴스 수집 및 요약 플랫폼입니다. RSS 피드 수집, 자연어 뉴스 검색, 개인화된 추천 시스템을 제공합니다.

## 🚀 주요 기능

### ✅ **다국어 뉴스 요약 시스템**
- **다국어 지원**: 한국어(`ko`) 및 영어(`en`) 요약 제공
- **지능형 언어 감지**: 자동 언어 인식 및 적절한 요약 언어 선택
- **GPT-4 통합**: OpenAI GPT-4를 활용한 고품질 요약
- **커스텀 프롬프트**: 사용자 정의 요약 스타일 지원

### ✅ **한국 RSS 피드 호환성**
- **자동 인코딩 감지**: chardet을 사용한 UTF-8, EUC-KR, CP949 자동 감지
- **주요 한국 언론사 지원**: JTBC, 한겨레, MBC, SBS, 연합뉴스, 조선일보 등
- **차단 방지 헤더**: 403/404 오류 방지를 위한 최적화된 User-Agent
- **한국어 콘텐츠 추출**: 한국 뉴스 기사 형식에 맞춘 강력한 HTML 파싱

### ✅ **자연어 뉴스 검색 (신규)**
- **자연어 쿼리**: "요즘 반도체 뉴스 알려줘" 형태의 자연스러운 검색
- **키워드 자동 추출**: GPT를 활용한 지능적 키워드 추출
- **관련 뉴스 필터링**: 키워드 기반 관련도 높은 기사 선별
- **실시간 RSS 수집**: 주요 언론사 RSS 피드에서 최신 뉴스 수집

### ✅ **사용자 히스토리 및 추천 시스템 (신규)**
- **개인 히스토리**: 사용자별 요약 기록 저장 및 관리
- **개인화된 추천**: 사용자의 관심사 기반 맞춤 뉴스 추천
- **다국어 히스토리**: 언어별 분류 및 검색 지원
- **통계 대시보드**: 사용자 활동 분석 및 선호도 통계

### ✅ **모던 React 프론트엔드**
- **언어 토글**: 한국어/영어 요약 언어 선택 UI (🇰🇷/🇺🇸)
- **다크 모드**: 완전한 다크/라이트 테마 지원
- **반응형 디자인**: Tailwind CSS 기반 모바일 친화적 인터페이스
- **실시간 피드백**: 처리 상태 및 언어 선택 시각적 표시

### ✅ **핵심 기능**
- **RSS 피드 처리**: RSS 피드에서 자동 기사 수집
- **직접 URL 지원**: 개별 기사 URL에서 콘텐츠 추출
- **이메일 전송**: 아름답게 포맷된 요약 이메일 전송
- **모듈화 아키텍처**: 유지보수가 쉬운 클린 코드 구조

## 📁 프로젝트 구조

```
gulbaguni-backend/
├── glbaguni/
│   ├── backend/
│   │   ├── main.py                # FastAPI 앱 (v2.0.0) - 다국어 엔드포인트
│   │   ├── news_aggregator.py     # 자연어 뉴스 검색 시스템
│   │   ├── fetcher.py            # 한국어 지원 RSS 및 HTML 수집
│   │   ├── summarizer.py         # 다국어 GPT 요약 로직
│   │   ├── history_service.py    # 사용자 히스토리 관리
│   │   ├── notifier.py           # 이메일 알림 시스템
│   │   ├── models.py             # 다국어 지원 Pydantic 모델
│   │   ├── database.py           # SQLAlchemy 데이터베이스 설정
│   │   └── config.py             # 환경 설정
│   ├── glbaguni.db              # SQLite 데이터베이스
│   ├── requirements.txt         # Python 의존성
│   ├── env_template.txt         # 환경변수 템플릿
│   └── README.md               # 메인 문서
├── glbaguni-frontend/          # React 프론트엔드
│   ├── src/
│   │   ├── App.jsx            # 메인 앱 컴포넌트
│   │   ├── pages/
│   │   │   ├── HomePage.jsx        # 홈페이지
│   │   │   ├── SummarizePage.jsx   # 요약 페이지
│   │   │   ├── HistoryPage.jsx     # 히스토리 페이지
│   │   │   ├── RecommendationPage.jsx # 추천 페이지
│   │   │   └── ContactPage.jsx     # 연락처 페이지
│   │   ├── components/        # 재사용 가능한 UI 컴포넌트
│   │   └── hooks/             # 커스텀 React 훅
│   ├── package.json           # 프론트엔드 의존성
│   └── vite.config.js         # Vite 설정
├── README_news.md             # 뉴스 검색 시스템 문서
└── news_summarizer.py         # 독립 실행형 뉴스 요약 스크립트
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
cd gulbaguni-backend/glbaguni

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
```

### 3. 백엔드 서버 시작

```bash
# 방법 1: 직접 실행
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# 방법 2: 메인 모듈 사용
cd backend && python main.py
```

백엔드 서버: `http://localhost:8000`

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

## 📚 API 문서

### 🆕 새로운 엔드포인트

#### POST `/news-search` - 자연어 뉴스 검색
자연어 쿼리로 관련 뉴스를 검색하고 요약하는 신규 엔드포인트입니다.

**요청 본문:**
```json
{
  "query": "요즘 반도체 뉴스 알려줘",
  "max_articles": 10,
  "language": "ko",
  "recipient_email": "user@example.com",
  "user_id": "optional-user-id"
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
      "source": "SBS"
    }
  ],
  "total_articles": 5,
  "extracted_keywords": ["반도체", "삼성전자", "3나노"],
  "processed_at": "2024-01-01T12:00:00"
}
```

#### GET `/history` - 사용자 히스토리 조회
사용자의 요약 히스토리를 페이지네이션과 언어 필터링으로 조회합니다.

**쿼리 파라미터:**
- `user_id`: 사용자 ID (필수)
- `page`: 페이지 번호 (기본값: 1)
- `per_page`: 페이지당 항목 수 (기본값: 20, 최대: 100)
- `language`: 언어 필터 (선택, ko/en)

#### GET `/recommendations` - 개인화된 추천
사용자의 히스토리 기반 맞춤 뉴스 추천을 제공합니다.

**쿼리 파라미터:**
- `user_id`: 사용자 ID (필수)
- `max_recommendations`: 최대 추천 수 (기본값: 10, 최대: 50)

### 기존 엔드포인트

#### POST `/summarize` - RSS/기사 요약
메인 요약 엔드포인트로 다국어 지원이 강화되었습니다.

**요청 본문:**
```json
{
  "rss_urls": ["https://rss.jtbc.co.kr/Latest.xml"],
  "article_urls": ["https://news.hani.co.kr/sample"],
  "recipient_email": "user@example.com",
  "custom_prompt": "핵심 내용을 간결하게 요약해주세요",
  "max_articles": 5,
  "language": "ko",
  "user_id": "optional-user-id"
}
```

#### POST `/summarize-text` - 텍스트 직접 요약
텍스트를 직접 입력하여 요약하는 엔드포인트입니다.

**요청 본문:**
```json
{
  "text": "요약할 텍스트 내용...",
  "language": "ko",
  "user_id": "optional-user-id"
}
```

## 🎯 사용 시나리오

### 1. RSS 피드 요약
- 여러 RSS 피드를 한 번에 처리
- 언어별 요약 제공
- 이메일로 결과 전송
- 사용자 히스토리에 자동 저장

### 2. 자연어 뉴스 검색
- "AI 관련 뉴스 찾아줘" 형태로 검색
- 키워드 자동 추출 및 관련 뉴스 수집
- 실시간 RSS 피드에서 최신 뉴스 검색

### 3. 개인화된 추천
- 사용자의 과거 관심사 분석
- 유사한 주제의 새로운 뉴스 추천
- 카테고리별 맞춤 추천

## 🔧 고급 설정

### 커스텀 RSS 피드 추가

```python
# backend/news_aggregator.py 수정
def _get_rss_feeds(self):
    rss_feeds = {
        "CustomSource": [
            "https://example.com/rss.xml"
        ]
    }
    return rss_feeds
```

### 요약 프롬프트 커스터마이징

환경변수 또는 API 요청으로 커스텀 프롬프트 사용:

```env
CUSTOM_SUMMARY_PROMPT="다음 기사를 3줄로 요약해주세요:"
```

## 🐛 문제 해결

### 1. OpenAI API 오류
- API 키 유효성 확인
- 사용량 한도 초과 여부 점검
- 대안: 간단한 텍스트 요약 사용

### 2. RSS 피드 접근 오류
- 네트워크 연결 상태 확인
- User-Agent 헤더 문제 가능성
- 일부 RSS 피드의 일시적 접근 불가

### 3. 한국어 인코딩 문제
- chardet 라이브러리로 자동 감지
- UTF-8, EUC-KR, CP949 지원
- BeautifulSoup 파싱 오류 시 대안 방법 사용

### 4. 데이터베이스 오류
- SQLite 파일 권한 확인
- 테이블 자동 생성 실패 시 수동 초기화
- 히스토리 데이터 백업 권장

## 📊 성능 최적화

### 속도 개선
- RSS 피드 처리 개수 제한 (기본: 6개)
- 기사 처리 시간 제한 (최대: 30초)
- 요청 간 적절한 지연 시간 설정

### 정확도 개선
- GPT 키워드 추출 프롬프트 최적화
- 신뢰할 수 있는 RSS 소스 선별
- 중복 기사 제거 알고리즘

### API 사용량 관리
- 기사 본문 길이 제한 (2000자)
- OpenAI API 토큰 사용량 모니터링
- 캐싱으로 중복 요청 방지

## ✅ 현재 개발 상태 (2024년 1월 기준)

### 완료된 기능
- [x] **기본 RSS 요약**: 다국어 지원 RSS 피드 수집 및 요약
- [x] **자연어 뉴스 검색**: GPT 기반 키워드 추출 및 관련 뉴스 검색
- [x] **사용자 히스토리**: SQLite 기반 개인 요약 기록 관리
- [x] **추천 시스템**: 사용자 관심사 기반 맞춤 뉴스 추천
- [x] **React 프론트엔드**: 5개 페이지 완성 (홈, 요약, 히스토리, 추천, 연락처)
- [x] **다크 모드**: 완전한 테마 전환 지원
- [x] **이메일 알림**: SMTP 기반 요약 결과 전송
- [x] **한국어 언론사 지원**: 주요 RSS 피드 호환성 확보

### 개발 중인 기능
- [ ] **성능 최적화**: news_aggregator.py의 linter 오류 수정 필요
- [ ] **에러 핸들링**: 무한로딩 방지 및 타임아웃 처리 개선
- [ ] **데이터베이스 최적화**: 인덱싱 및 쿼리 성능 개선

### 알려진 이슈
- **Linter 오류**: `news_aggregator.py`에서 OpenAI API 호출 관련 타입 힌트 문제
- **무한로딩**: RSS 피드 처리 시 일부 소스에서 발생 가능
- **메모리 사용량**: 대량 기사 처리 시 메모리 최적화 필요

## 🚀 향후 계획

### 단기 목표 (1-2개월)
- [ ] **버그 수정**: 현재 linter 오류 및 타입 힌트 문제 해결
- [ ] **API 문서 자동화**: Swagger/OpenAPI 자동 문서 생성
- [ ] **테스트 코드**: 단위 테스트 및 통합 테스트 추가
- [ ] **Docker 지원**: 컨테이너화된 배포 환경 구축

### 중기 목표 (3-6개월)
- [ ] **실시간 알림**: WebSocket 기반 실시간 뉴스 알림
- [ ] **소셜 미디어 통합**: Twitter, Facebook 피드 지원
- [ ] **AI 분석**: 감정 분석, 트렌드 예측 기능
- [ ] **성능 모니터링**: 로깅 및 메트릭 수집 시스템

### 장기 목표 (6개월+)
- [ ] **모바일 앱**: React Native 기반 모바일 앱 개발
- [ ] **다국어 확장**: 일본어, 중국어 지원 추가
- [ ] **협업 기능**: 팀 단위 뉴스 공유 및 토론
- [ ] **엔터프라이즈 기능**: 대기업용 커스터마이징 및 온프레미스 배포

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여하기

프로젝트에 기여하고 싶으시다면:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 지원

- 이슈 트래커: GitHub Issues
- 이메일: support@glbaguni.com
- 문서: [GitHub Wiki](https://github.com/your-repo/wiki)

---

**글바구니(Glbaguni)** - AI와 함께하는 스마트한 뉴스 소비 경험 🗞️✨
