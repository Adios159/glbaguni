# 글바구니 프론트엔드 (Glbaguni Frontend)

React와 Tailwind CSS로 구축된 AI 기반 뉴스 요약 서비스의 프론트엔드입니다.

## 🎨 주요 기능

### ✅ **모던 사용자 인터페이스**
- **반응형 디자인**: 모바일, 태블릿, 데스크톱 완벽 지원
- **다크/라이트 테마**: 사용자 선호에 따른 테마 전환
- **직관적인 네비게이션**: 명확하고 사용하기 쉬운 메뉴 구조
- **아름다운 그라데이션**: 현대적이고 세련된 디자인

### ✅ **5개 핵심 페이지**
1. **홈페이지** (`/`): 서비스 소개 및 주요 기능 안내
2. **요약 페이지** (`/summarize`): RSS 피드 및 기사 URL 요약
3. **히스토리 페이지** (`/history`): 개인 요약 기록 관리
4. **추천 페이지** (`/recommendations`): AI 기반 개인화 뉴스 추천
5. **연락처 페이지** (`/contact`): 문의 및 지원 정보

### ✅ **고급 UI 컴포넌트**
- **언어 토글**: 한국어/영어 요약 선택 (🇰🇷/🇺🇸)
- **테마 토글**: 다크/라이트 모드 즉시 전환
- **로딩 스피너**: 요약 처리 중 시각적 피드백
- **에러 핸들링**: 사용자 친화적 에러 메시지
- **성공 알림**: 작업 완료 시 명확한 피드백

## 🛠️ 기술 스택

- **React 18**: 최신 React 기능 활용
- **Vite**: 빠른 개발 서버 및 빌드 도구
- **Tailwind CSS**: 유틸리티 기반 CSS 프레임워크
- **React Router**: SPA 라우팅 관리
- **커스텀 훅**: 재사용 가능한 로직 분리

## 📁 프로젝트 구조

```
src/
├── App.jsx                    # 메인 애플리케이션 컴포넌트
├── main.jsx                   # React 앱 진입점
├── index.css                  # 전역 스타일
├── pages/                     # 페이지 컴포넌트
│   ├── HomePage.jsx           # 홈페이지 - 서비스 소개
│   ├── SummarizePage.jsx      # 요약 페이지 - 주요 기능
│   ├── HistoryPage.jsx        # 히스토리 - 과거 요약 기록
│   ├── RecommendationPage.jsx # 추천 - 개인화 뉴스
│   └── ContactPage.jsx        # 연락처 - 지원 정보
├── components/                # 재사용 가능한 컴포넌트
│   ├── Navbar.jsx            # 네비게이션 바
│   └── ThemeToggle.jsx       # 테마 전환 버튼
└── hooks/                     # 커스텀 React 훅
    ├── useTheme.js           # 테마 상태 관리
    └── useFormValidation.js  # 폼 검증 로직
```

## 🚀 설치 및 실행

### 필수 조건
- Node.js 16 이상
- npm 또는 yarn

### 1. 의존성 설치

```bash
# npm 사용
npm install

# 또는 yarn 사용
yarn install
```

### 2. 개발 서버 시작

```bash
# npm 사용
npm run dev

# 또는 yarn 사용
yarn dev
```

개발 서버가 `http://localhost:5173`에서 실행됩니다.

### 3. 프로덕션 빌드

```bash
# npm 사용
npm run build

# 또는 yarn 사용
yarn build
```

빌드된 파일은 `dist/` 디렉토리에 생성됩니다.

### 4. 프로덕션 서버 미리보기

```bash
# npm 사용
npm run preview

# 또는 yarn 사용
yarn preview
```

## 🎯 주요 기능별 상세 설명

### 홈페이지 (HomePage.jsx)
- **히어로 섹션**: 서비스 소개와 주요 CTA 버튼
- **기능 카드**: 6개 핵심 기능을 시각적으로 표현
- **사용 방법**: 3단계 간단한 사용법 안내
- **최종 액션**: 서비스 시작 유도

### 요약 페이지 (SummarizePage.jsx)
- **URL 입력**: RSS 피드 또는 기사 URL 입력
- **언어 선택**: 한국어/영어 요약 선택
- **이메일 옵션**: 요약 결과 이메일 발송
- **실시간 처리**: 요약 진행 상황 표시

### 히스토리 페이지 (HistoryPage.jsx)
- **요약 기록**: 사용자별 과거 요약 내역
- **필터링**: 언어별, 날짜별 필터 기능
- **페이지네이션**: 대량 데이터 효율적 표시
- **상세 보기**: 개별 요약 내용 확장 표시

### 추천 페이지 (RecommendationPage.jsx)
- **개인화 추천**: 사용자 관심사 기반 뉴스
- **카테고리별 분류**: 정치, 경제, 기술 등
- **추천 점수**: 관련도 기반 점수 표시
- **즉시 요약**: 추천 기사 바로 요약 가능

### 연락처 페이지 (ContactPage.jsx)
- **개발자 정보**: 프로젝트 개발자 연락처
- **GitHub 링크**: 소스코드 및 이슈 트래커
- **기술 지원**: 문의 방법 안내
- **FAQ**: 자주 묻는 질문 답변

## 🎨 디자인 시스템

### 색상 팔레트
- **Primary**: Blue (파란색) - 신뢰성과 안정성
- **Background**: White/Gray-900 - 라이트/다크 테마
- **Text**: Gray-900/White - 명확한 가독성
- **Accent**: 각 기능별 구분 색상

### 타이포그래피
- **제목**: 큰 폰트 크기, 굵은 두께
- **본문**: 적절한 행 간격과 읽기 쉬운 크기
- **버튼**: 명확하고 클릭 가능한 스타일

### 반응형 디자인
- **모바일**: 320px 이상
- **태블릿**: 768px 이상
- **데스크톱**: 1024px 이상

## 🔧 커스텀 훅

### useTheme
테마 상태를 관리하는 훅입니다.

```javascript
const { theme, toggleTheme } = useTheme();
```

- `theme`: 현재 테마 ('light' 또는 'dark')
- `toggleTheme`: 테마 전환 함수

### useFormValidation
폼 검증 로직을 처리하는 훅입니다.

```javascript
const { isValid, errors, validate } = useFormValidation(rules);
```

- `isValid`: 폼 유효성 상태
- `errors`: 검증 오류 메시지
- `validate`: 검증 실행 함수

## 🚀 성능 최적화

### 최적화 기법
- **Lazy Loading**: 페이지별 코드 분할
- **이미지 최적화**: 적절한 포맷과 크기
- **CSS 최적화**: Tailwind CSS Purge 활용
- **번들 최적화**: Vite의 최적화 기능 활용

### 빌드 최적화
- **Tree Shaking**: 사용하지 않는 코드 제거
- **압축**: 프로덕션 빌드 시 코드 압축
- **캐싱**: 정적 자산 브라우저 캐싱 활용

## 🔗 백엔드 연동

### API 엔드포인트
프론트엔드는 다음 백엔드 API와 연동됩니다:

- `POST /summarize/text` - 텍스트 요약
- `POST /news-search` - 자연어 뉴스 검색
- `GET /history` - 사용자 히스토리 조회
- `GET /recommendations` - 개인화 추천
- `GET /user-stats` - 사용자 통계

### 환경 설정
백엔드 서버 URL을 환경 변수로 설정:

```bash
VITE_API_URL=http://localhost:8000
```

## 🐛 문제 해결

### 자주 발생하는 문제

1. **포트 충돌**
   - 해결: `npm run dev -- --port 3000`으로 다른 포트 사용

2. **빌드 실패**
   - 해결: `node_modules` 삭제 후 재설치

3. **Tailwind CSS 적용 안됨**
   - 해결: `tailwind.config.js` 설정 확인

4. **라우팅 문제**
   - 해결: React Router 설정 및 경로 확인

## 📱 모바일 지원

### 반응형 기능
- **터치 최적화**: 모바일 터치 인터페이스 지원
- **스와이프 제스처**: 자연스러운 모바일 제스처
- **적응형 레이아웃**: 화면 크기별 최적화된 레이아웃
- **PWA 준비**: Progressive Web App 구조

## 🔮 향후 계획

### v2.0.0 (예정)
- **PWA 지원**: 오프라인 기능 및 푸시 알림
- **실시간 업데이트**: WebSocket을 통한 실시간 요약 상태
- **고급 필터**: 더 세밀한 검색 및 필터 기능

### v2.1.0 (예정)
- **소셜 로그인**: Google, GitHub 로그인 지원
- **공유 기능**: 요약 결과 SNS 공유
- **즐겨찾기**: 중요한 요약 북마크 기능

---

**글바구니 프론트엔드** - 아름답고 직관적인 뉴스 요약 경험 ✨ 