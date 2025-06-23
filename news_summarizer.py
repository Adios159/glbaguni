#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
뉴스 요약 시스템
사용자가 자연어로 뉴스 주제를 입력하면, 키워드를 추출하고 관련 뉴스를 찾아 요약하는 시스템
"""

import requests
import feedparser
import json
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import logging
from dataclasses import dataclass

try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    # Create a dummy BeautifulSoup import to avoid errors
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        BeautifulSoup = None

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    LEGACY_OPENAI = False
except ImportError:
    try:
        import openai
        OPENAI_AVAILABLE = True
        LEGACY_OPENAI = True
    except ImportError:
        OPENAI_AVAILABLE = False
        LEGACY_OPENAI = False
        # Create dummy openai module to avoid import errors
        openai = None

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    title: str
    link: str
    summary: str
    content: str = ""
    published_date: Optional[str] = None
    source: str = ""

class NewsKeywordExtractor:
    """키워드 추출 클래스"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self.openai_client = None
        if openai_api_key and OPENAI_AVAILABLE:
            if LEGACY_OPENAI:
                import openai
                openai.api_key = openai_api_key
            else:
                self.openai_client = OpenAI(api_key=openai_api_key)
    
    def extract_keywords_with_gpt(self, text: str) -> List[str]:
        """GPT를 사용한 키워드 추출"""
        if not self.openai_api_key or not OPENAI_AVAILABLE:
            logger.warning("OpenAI API key not provided or openai package not installed. Using simple keyword extraction.")
            return self.extract_keywords_simple(text)
        
        try:
            prompt = f"""
다음 텍스트에서 뉴스 검색에 유용한 핵심 키워드를 추출해주세요.
- 고유명사(회사명, 인물명, 지역명, 기술명 등)를 우선 추출
- 핵심 주제어를 포함
- 최대 10개까지
- 각 키워드는 따옴표 없이 콤마로 구분
- 키워드만 출력하고 다른 설명은 하지 마세요

텍스트: "{text}"

키워드:"""

            if LEGACY_OPENAI:
                import openai
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "당신은 뉴스 키워드 추출 전문가입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.3
                )
                keywords_text = response.choices[0].message.content.strip()
            else:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "당신은 뉴스 키워드 추출 전문가입니다."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.3
                )
                keywords_text = response.choices[0].message.content.strip()
            
            keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
            logger.info(f"GPT로 추출된 키워드: {keywords}")
            return keywords[:10]  # 최대 10개
            
        except Exception as e:
            logger.error(f"GPT 키워드 추출 실패: {e}")
            return self.extract_keywords_simple(text)
    
    def extract_keywords_simple(self, text: str) -> List[str]:
        """간단한 키워드 추출 (GPT 사용 불가시 대안)"""
        # 한국어 키워드 패턴 매칭
        keywords = []
        
        # 기본적인 키워드 패턴들
        patterns = {
            '회사명': r'(삼성|LG|SK|현대|기아|네이버|카카오|쿠팡|배달의민족|토스|TSMC|애플|구글|마이크로소프트|테슬라)',
            '기술': r'(반도체|AI|인공지능|5G|6G|블록체인|메타버스|NFT|클라우드|빅데이터)',
            '경제': r'(주가|증시|코스피|나스닥|달러|원화|금리|인플레이션|경기침체)',
            '정치': r'(대통령|국회|정부|여당|야당|선거|정책|법안)',
            '사회': r'(코로나|백신|기후|환경|교육|의료|복지)'
        }
        
        for category, pattern in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)
        
        # 중복 제거 및 정리
        keywords = list(set(keywords))
        logger.info(f"간단 추출된 키워드: {keywords}")
        return keywords[:10]

class NewsContentParser:
    """뉴스 본문 파싱 클래스"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def parse_article_content(self, url: str) -> str:
        """기사 본문 파싱"""
        try:
            if NEWSPAPER_AVAILABLE:
                return self._parse_with_newspaper(url)
            else:
                return self._parse_with_beautifulsoup(url)
        except Exception as e:
            logger.error(f"기사 파싱 실패 ({url}): {e}")
            return ""
    
    def _parse_with_newspaper(self, url: str) -> str:
        """newspaper3k를 사용한 파싱"""
        try:
            article = Article(url, language='ko')
            article.download()
            article.parse()
            return article.text
        except Exception as e:
            logger.error(f"Newspaper 파싱 실패: {e}")
            return self._parse_with_beautifulsoup(url)
    
    def _parse_with_beautifulsoup(self, url: str) -> str:
        """BeautifulSoup을 사용한 파싱"""
        if not BeautifulSoup:
            logger.error("BeautifulSoup not available. Please install beautifulsoup4.")
            return ""
            
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 일반적인 기사 본문 선택자들
            selectors = [
                'article',
                '.article-content',
                '.news-content',
                '.post-content',
                '#articleText',
                '.article_view',
                '.read_body'
            ]
            
            content = ""
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text().strip() for elem in elements])
                    break
            
            # 선택자로 찾지 못한 경우 p 태그들을 수집
            if not content:
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
            
            return content
        except Exception as e:
            logger.error(f"BeautifulSoup 파싱 실패: {e}")
            return ""

class NewsSummarizer:
    """뉴스 요약 클래스"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.openai_api_key = openai_api_key
        self.openai_client = None
        if openai_api_key and OPENAI_AVAILABLE:
            if LEGACY_OPENAI:
                import openai
                openai.api_key = openai_api_key
            else:
                self.openai_client = OpenAI(api_key=openai_api_key)
    
    def summarize_article(self, content: str, title: str = "") -> str:
        """기사 요약"""
        if not content.strip():
            return "본문을 가져올 수 없어 요약할 수 없습니다."
        
        if not self.openai_api_key or not OPENAI_AVAILABLE:
            return self._simple_summarize(content)
        
        try:
            prompt = f"""
다음 뉴스 기사를 3-4문장으로 간결하게 요약해주세요:

제목: {title}
본문: {content[:2000]}  # 토큰 제한을 위해 앞부분만

요약:"""

            if LEGACY_OPENAI:
                import openai
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "당신은 뉴스 요약 전문가입니다. 핵심 내용을 간결하고 정확하게 요약해주세요."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.3
                )
                summary = response.choices[0].message.content.strip()
            else:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "당신은 뉴스 요약 전문가입니다. 핵심 내용을 간결하고 정확하게 요약해주세요."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.3
                )
                summary = response.choices[0].message.content.strip()
            
            return summary
            
        except Exception as e:
            logger.error(f"GPT 요약 실패: {e}")
            return self._simple_summarize(content)
    
    def _simple_summarize(self, content: str) -> str:
        """간단한 요약 (GPT 사용 불가시)"""
        sentences = re.split(r'[.!?]', content)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # 앞의 3문장 정도를 요약으로 사용
        summary_sentences = sentences[:3]
        return ' '.join(summary_sentences) + '.'

class NewsAggregator:
    """뉴스 수집 및 통합 클래스"""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.keyword_extractor = NewsKeywordExtractor(openai_api_key)
        self.content_parser = NewsContentParser()
        self.summarizer = NewsSummarizer(openai_api_key)
        self.rss_feeds = self._get_rss_feeds()
    
    def _get_rss_feeds(self) -> Dict[str, List[str]]:
        """RSS 피드 목록"""
        rss_feeds = {
            "SBS": [
                "https://news.sbs.co.kr/news/headlineRssFeed.do?plink=RSSREADER",
                "https://news.sbs.co.kr/news/newsflashRssFeed.do?plink=RSSREADER",
                "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01",  # 정치
                "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=02",  # 경제
                "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=03",  # 사회
                "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=07",  # 문화
                "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=08",  # 국제
                "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=14",  # 연예
                "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=09",  # 스포츠
            ],
            "JTBC": [
                "https://news-ex.jtbc.co.kr/v1/get/rss/newsflesh",
                "https://news-ex.jtbc.co.kr/v1/get/rss/issue",
                "https://news-ex.jtbc.co.kr/v1/get/rss/section/10",  # 정치
                "https://news-ex.jtbc.co.kr/v1/get/rss/section/20",  # 경제
                "https://news-ex.jtbc.co.kr/v1/get/rss/section/30",  # 사회
                "https://news-ex.jtbc.co.kr/v1/get/rss/section/40",  # 문화
                "https://news-ex.jtbc.co.kr/v1/get/rss/section/50",  # 국제
                "https://news-ex.jtbc.co.kr/v1/get/rss/section/60",  # 스포츠
            ],
            "Yonhap": [
                "https://www.yna.co.kr/rss/news.xml",
                "https://www.yna.co.kr/rss/politics.xml",
                "https://www.yna.co.kr/rss/economy.xml",
                "https://www.yna.co.kr/rss/industry.xml",
                "https://www.yna.co.kr/rss/society.xml",
                "https://www.yna.co.kr/rss/international.xml",
                "https://www.yna.co.kr/rss/culture.xml",
                "https://www.yna.co.kr/rss/entertainment.xml",
                "https://www.yna.co.kr/rss/sports.xml",
            ],
            "MaeilEconomy": [
                "https://www.mk.co.kr/rss/30000001/",
                "https://www.mk.co.kr/rss/40300001/",
                "https://www.mk.co.kr/rss/30200030/",
                "https://www.mk.co.kr/rss/30100041/",
                "https://www.mk.co.kr/rss/30800011/",
                "https://www.mk.co.kr/rss/30300018/",
                "https://www.mk.co.kr/rss/50400012/",
                "https://www.mk.co.kr/rss/50700001/",
            ],
            "Korean_Government": {
                "국무조정실": "https://www.korea.kr/rss/dept_opm.xml",
                "기획재정부": "https://www.korea.kr/rss/dept_moef.xml",
                "교육부": "https://www.korea.kr/rss/dept_moe.xml",
                "과학기술정보통신부": "https://www.korea.kr/rss/dept_msit.xml",
                "외교부": "https://www.korea.kr/rss/dept_mofa.xml",
                "통일부": "https://www.korea.kr/rss/dept_unikorea.xml",
                "법무부": "https://www.korea.kr/rss/dept_moj.xml",
                "국방부": "https://www.korea.kr/rss/dept_mnd.xml",
                "행정안전부": "https://www.korea.kr/rss/dept_mois.xml",
                "보훈처": "https://www.korea.kr/rss/dept_mpva.xml",
                "문화체육관광부": "https://www.korea.kr/rss/dept_mcst.xml",
                "농림축산식품부": "https://www.korea.kr/rss/dept_mafra.xml",
                "산업통상자원부": "https://www.korea.kr/rss/dept_motie.xml",
                "보건복지부": "https://www.korea.kr/rss/dept_mw.xml",
                "환경부": "https://www.korea.kr/rss/dept_me.xml",
                "고용노동부": "https://www.korea.kr/rss/dept_moel.xml",
                "여성가족부": "https://www.korea.kr/rss/dept_mogef.xml",
                "국토교통부": "https://www.korea.kr/rss/dept_molit.xml",
                "해양수산부": "https://www.korea.kr/rss/dept_mof.xml",
                "중소벤처기업부": "https://www.korea.kr/rss/dept_mss.xml",
                "인사혁신처": "https://www.korea.kr/rss/dept_mpm.xml",
                "법제처": "https://www.korea.kr/rss/dept_moleg.xml",
                "식품의약품안전처": "https://www.korea.kr/rss/dept_mfds.xml",
                "국세청": "https://www.korea.kr/rss/dept_nts.xml",
                "관세청": "https://www.korea.kr/rss/dept_customs.xml",
                "조달청": "https://www.korea.kr/rss/dept_pps.xml",
                "통계청": "https://www.korea.kr/rss/dept_kostat.xml",
                "항공우주연구원": "https://www.korea.kr/rss/dept_kasa.xml",
                "정부법무공단": "https://www.korea.kr/rss/dept_oka.xml",
                "스포츠윤리센터": "https://www.korea.kr/rss/dept_spo.xml",
                "병무청": "https://www.korea.kr/rss/dept_mma.xml",
                "방위사업청": "https://www.korea.kr/rss/dept_dapa.xml",
                "경찰청": "https://www.korea.kr/rss/dept_npa.xml",
                "소방청": "https://www.korea.kr/rss/dept_nfa.xml",
                "해양경찰청": "https://www.korea.kr/rss/dept_kcg.xml",
                "한국보훈복지의료공단": "https://www.korea.kr/rss/dept_khs.xml",
                "농촌진흥청": "https://www.korea.kr/rss/dept_rda.xml",
                "산림청": "https://www.korea.kr/rss/dept_forest.xml",
                "특허청": "https://www.korea.kr/rss/dept_kipo.xml",
                "질병관리청": "https://www.korea.kr/rss/dept_kdca.xml",
                "기상청": "https://www.korea.kr/rss/dept_kma.xml",
                "아시아문화전당": "https://www.korea.kr/rss/dept_macc.xml",
                "사행산업통합감독위원회": "https://www.korea.kr/rss/dept_sda.xml"
            }
        }
        return rss_feeds
    
    def fetch_rss_articles(self, rss_url: str, source: str) -> List[Dict]:
        """RSS에서 기사 목록 가져오기"""
        try:
            feed = feedparser.parse(rss_url)
            articles = []
            
            for entry in feed.entries:
                article = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'summary': entry.get('summary', ''),
                    'published': entry.get('published', ''),
                    'source': source
                }
                articles.append(article)
            
            logger.info(f"RSS에서 {len(articles)}개 기사 수집: {source}")
            return articles
            
        except Exception as e:
            logger.error(f"RSS 수집 실패 ({rss_url}): {e}")
            return []
    
    def filter_articles_by_keywords(self, articles: List[Dict], keywords: List[str]) -> List[Dict]:
        """키워드로 기사 필터링"""
        if not keywords:
            return articles
        
        filtered_articles = []
        
        for article in articles:
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            
            # 키워드 중 하나라도 제목이나 요약에 포함되면 선택
            for keyword in keywords:
                if keyword.lower() in title or keyword.lower() in summary:
                    filtered_articles.append(article)
                    break
        
        logger.info(f"키워드 필터링 결과: {len(filtered_articles)}개 기사")
        return filtered_articles
    
    def process_news_query(self, query: str, max_articles: int = 10) -> List[NewsArticle]:
        """뉴스 쿼리 처리 (메인 함수)"""
        logger.info(f"뉴스 검색 시작: '{query}'")
        
        # 1. 키워드 추출
        keywords = self.keyword_extractor.extract_keywords_with_gpt(query)
        if not keywords:
            logger.warning("키워드를 추출할 수 없습니다.")
            return []
        
        # 2. RSS 피드에서 기사 수집
        all_articles = []
        
        for source, feeds in self.rss_feeds.items():
            if isinstance(feeds, dict):  # 정부 RSS의 경우
                for dept_name, feed_url in feeds.items():
                    articles = self.fetch_rss_articles(feed_url, f"{source}_{dept_name}")
                    all_articles.extend(articles)
            else:  # 일반 언론사 RSS의 경우
                for feed_url in feeds:
                    articles = self.fetch_rss_articles(feed_url, source)
                    all_articles.extend(articles)
                    time.sleep(0.5)  # API 호출 제한 고려
        
        # 3. 키워드로 필터링
        filtered_articles = self.filter_articles_by_keywords(all_articles, keywords)
        
        # 4. 중복 제거 (URL 기준)
        unique_articles = {}
        for article in filtered_articles:
            url = article['link']
            if url not in unique_articles:
                unique_articles[url] = article
        
        filtered_articles = list(unique_articles.values())[:max_articles]
        
        # 5. 본문 크롤링 및 요약
        result_articles = []
        
        for i, article in enumerate(filtered_articles):
            logger.info(f"기사 처리 중 ({i+1}/{len(filtered_articles)}): {article['title']}")
            
            # 본문 크롤링
            content = self.content_parser.parse_article_content(article['link'])
            
            # 요약 생성
            summary = self.summarizer.summarize_article(content, article['title'])
            
            news_article = NewsArticle(
                title=article['title'],
                link=article['link'],
                summary=summary,
                content=content[:500] + "..." if len(content) > 500 else content,
                published_date=article.get('published'),
                source=article['source']
            )
            
            result_articles.append(news_article)
            time.sleep(1)  # API 호출 제한 고려
        
        logger.info(f"뉴스 검색 완료: {len(result_articles)}개 기사 처리")
        return result_articles

def main():
    """메인 실행 함수"""
    # OpenAI API 키 설정 (환경변수나 직접 입력)
    import os
    openai_api_key = os.getenv('OPENAI_API_KEY')  # 환경변수에서 가져오기
    
    if not openai_api_key:
        openai_api_key = input("OpenAI API 키를 입력하세요 (선택사항, 엔터로 건너뛰기): ").strip()
        if not openai_api_key:
            openai_api_key = None
    
    # 뉴스 수집기 초기화
    aggregator = NewsAggregator(openai_api_key)
    
    # 사용자 입력
    while True:
        query = input("\n뉴스 검색 쿼리를 입력하세요 (종료: quit): ").strip()
        
        if query.lower() in ['quit', 'exit', '종료']:
            break
        
        if not query:
            continue
        
        try:
            # 뉴스 검색 및 요약
            articles = aggregator.process_news_query(query, max_articles=5)
            
            if not articles:
                print("관련 뉴스를 찾을 수 없습니다.")
                continue
            
            # 결과 출력
            print(f"\n📰 '{query}' 관련 뉴스 요약 ({len(articles)}개)")
            print("=" * 80)
            
            for i, article in enumerate(articles, 1):
                print(f"\n{i}. {article.title}")
                print(f"   출처: {article.source}")
                print(f"   링크: {article.link}")
                print(f"   요약: {article.summary}")
                print("-" * 40)
            
            # JSON 형태로도 출력
            print("\n📄 JSON 형태 결과:")
            result_json = []
            for article in articles:
                result_json.append({
                    "title": article.title,
                    "link": article.link,
                    "summary": article.summary,
                    "source": article.source
                })
            
            print(json.dumps(result_json, ensure_ascii=False, indent=2))
            
        except Exception as e:
            logger.error(f"뉴스 검색 중 오류 발생: {e}")
            print(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main() 