# 🗞️ 뉴스 요약 시스템

자연어 입력으로 관련 뉴스를 찾아 AI로 요약하는 Python 시스템

## 📋 개요

사용자가 자연어로 뉴스 주제를 입력하면:
1. **키워드 추출**: GPT를 사용해 핵심 키워드 추출
2. **RSS 수집**: 미리 등록된 RSS 피드에서 뉴스 수집
3. **필터링**: 키워드가 포함된 기사만 선별
4. **본문 크롤링**: 선별된 기사의 전문 수집
5. **AI 요약**: GPT로 각 기사를 간결하게 요약

## 🎯 주요 기능

- **자연어 쿼리**: "요즘 반도체 뉴스 알려줘" → 자동 키워드 추출
- **다양한 RSS 소스**: SBS, JTBC, 연합뉴스, 매일경제, 정부기관 등
- **지능형 필터링**: 키워드 기반 관련도 높은 기사 선별
- **AI 요약**: GPT-3.5를 활용한 고품질 요약
- **모듈화 설계**: 각 기능별 독립적인 클래스 구조

## 🛠️ 설치 및 설정

### 1. 필수 라이브러리 설치

```bash
pip install -r requirements_news.txt
```

### 2. OpenAI API 키 설정 (선택사항)

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

또는 코드 실행 시 직접 입력 가능

### 3. 필요 패키지 설명

- `requests`: HTTP 요청
- `feedparser`: RSS 피드 파싱
- `newspaper3k`: 뉴스 기사 본문 추출
- `beautifulsoup4`: HTML 파싱 (대안)
- `openai`: GPT API 사용
- `lxml`: XML 파싱 지원

## 🚀 사용법

### 기본 사용

```python
from news_summarizer import NewsAggregator

# 초기화
aggregator = NewsAggregator(openai_api_key="your-key")

# 뉴스 검색
articles = aggregator.process_news_query("반도체 뉴스", max_articles=5)

# 결과 출력
for article in articles:
    print(f"제목: {article.title}")
    print(f"요약: {article.summary}")
    print(f"링크: {article.link}")
    print("-" * 40)
```

### 커맨드라인 실행

```bash
python news_summarizer.py
```

### 예시 코드 실행

```bash
python example_usage.py
```

## 📊 입출력 예시

### 입력
```
"요즘 반도체 뉴스 알려줘"
```

### 출력
```json
[
  {
    "title": "삼성전자, 3나노 반도체 상용화 발표",
    "link": "https://news.sbs.co.kr/article123",
    "summary": "삼성전자는 3나노 공정 기반 반도체를 상용화한다고 밝혔다. 이는 TSMC와의 경쟁에서 우위를 점하기 위한 전략으로 해석된다...",
    "source": "SBS"
  }
]
```

## 🏗️ 시스템 구조

```
news_summarizer.py
├── NewsKeywordExtractor     # 키워드 추출
├── NewsContentParser       # 기사 본문 파싱
├── NewsSummarizer          # AI 요약
└── NewsAggregator          # 전체 프로세스 통합
```

### 주요 클래스

#### 1. NewsKeywordExtractor
- GPT 기반 키워드 추출
- 패턴 매칭 대안 제공

#### 2. NewsContentParser
- newspaper3k 우선 사용
- BeautifulSoup 대안 제공

#### 3. NewsSummarizer
- GPT-3.5로 기사 요약
- 간단한 문장 추출 대안

#### 4. NewsAggregator
- 전체 파이프라인 관리
- RSS 피드 설정 및 수집

## 📡 지원 RSS 소스

### 주요 언론사
- **SBS**: 헤드라인, 정치, 경제, 사회, 문화, 국제, 연예, 스포츠
- **JTBC**: 뉴스플래시, 이슈, 각 섹션별
- **연합뉴스**: 전체 뉴스, 정치, 경제, 산업, 사회, 국제, 문화, 연예, 스포츠
- **매일경제**: 경제 전문 뉴스

### 정부기관 (총 35개)
- 국무조정실, 기획재정부, 교육부 등
- 각 부처별 공식 발표 및 정책 뉴스

## ⚙️ 설정 커스터마이징

### RSS 피드 추가/변경

```python
class CustomNewsAggregator(NewsAggregator):
    def _get_rss_feeds(self):
        return {
            "MySource": [
                "https://example.com/rss.xml"
            ]
        }
```

### 키워드 추출 로직 수정

```python
class CustomKeywordExtractor(NewsKeywordExtractor):
    def extract_keywords_simple(self, text):
        # 커스텀 키워드 추출 로직
        return custom_keywords
```

## 🔧 문제 해결

### 1. OpenAI API 에러
- API 키 확인
- 할당량 초과 여부 확인
- 대안: 간단한 키워드 추출 사용

### 2. RSS 피드 접근 불가
- 네트워크 연결 확인
- User-Agent 헤더 문제일 수 있음
- 일부 RSS 피드는 일시적으로 접근 불가할 수 있음

### 3. 기사 본문 파싱 실패
- newspaper3k 설치 확인
- 사이트별 접근 제한 가능성
- BeautifulSoup 대안 사용

## 📈 성능 최적화

### 1. 속도 개선
- RSS 피드 수 조정
- 동시 처리 개수 제한
- 캐싱 시스템 도입

### 2. 정확도 개선
- 키워드 추출 프롬프트 튜닝
- RSS 피드 소스 선별
- 필터링 알고리즘 개선

## 🔒 API 사용량 관리

### OpenAI API 토큰 절약
- 기사 본문 길이 제한 (2000자)
- 배치 처리 고려
- 캐싱으로 중복 요청 방지

### RSS 접근 제한 대응
- 요청 간 지연 시간 추가
- User-Agent 로테이션
- 에러 시 재시도 로직

## 📝 라이선스

MIT License

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 지원

- Issues: GitHub Issues 페이지
- 문서: README 및 코드 주석 참조
- 예시: `example_usage.py` 실행

---

**주의사항**: 
- OpenAI API 사용 시 요금이 발생할 수 있습니다
- RSS 피드 접근 시 해당 사이트의 이용약관을 준수하세요
- 수집된 뉴스의 저작권은 원 출처에 있습니다 