#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
뉴스 요약 시스템 사용 예시
"""

import os
from news_summarizer import NewsAggregator

def example_basic_usage():
    """기본 사용 예시"""
    print("=== 기본 사용 예시 ===")
    
    # OpenAI API 키 설정 (선택사항)
    openai_api_key = os.getenv('OPENAI_API_KEY', None)
    
    # 뉴스 수집기 초기화
    aggregator = NewsAggregator(openai_api_key)
    
    # 검색 쿼리
    queries = [
        "요즘 반도체 뉴스 알려줘",
        "삼성전자 최근 소식",
        "인공지능 관련 정부 정책",
        "코로나 백신 최신 뉴스"
    ]
    
    for query in queries:
        print(f"\n🔍 검색: '{query}'")
        print("-" * 50)
        
        try:
            articles = aggregator.process_news_query(query, max_articles=3)
            
            if articles:
                for i, article in enumerate(articles, 1):
                    print(f"{i}. {article.title}")
                    print(f"   출처: {article.source}")
                    print(f"   요약: {article.summary}")
                    print()
            else:
                print("관련 뉴스를 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"오류 발생: {e}")

def example_keyword_extraction():
    """키워드 추출 테스트"""
    print("\n=== 키워드 추출 테스트 ===")
    
    from news_summarizer import NewsKeywordExtractor
    
    extractor = NewsKeywordExtractor()
    
    test_queries = [
        "삼성전자 3나노 반도체 양산 소식 알려줘",
        "테슬라 주가 최근 동향이 궁금해",
        "정부 AI 정책 관련 뉴스 찾아줘",
        "코로나 오미크론 변이 백신 효과"
    ]
    
    for query in test_queries:
        keywords = extractor.extract_keywords_with_gpt(query)
        print(f"쿼리: {query}")
        print(f"키워드: {keywords}")
        print()

def example_custom_rss():
    """커스텀 RSS 피드 사용 예시"""
    print("\n=== 커스텀 RSS 사용 예시 ===")
    
    from news_summarizer import NewsAggregator
    
    class CustomNewsAggregator(NewsAggregator):
        def _get_rss_feeds(self):
            # 원하는 RSS 피드만 사용
            return {
                "TechNews": [
                    "https://feeds.feedburner.com/TechCrunch",
                    "https://www.wired.com/feed/rss"
                ],
                "LocalNews": [
                    "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=02"  # SBS 경제
                ]
            }
    
    aggregator = CustomNewsAggregator()
    articles = aggregator.process_news_query("기술 뉴스", max_articles=2)
    
    for article in articles:
        print(f"제목: {article.title}")
        print(f"요약: {article.summary}")
        print()

def example_json_output():
    """JSON 출력 예시"""
    print("\n=== JSON 출력 예시 ===")
    
    import json
    from news_summarizer import NewsAggregator
    
    aggregator = NewsAggregator()
    articles = aggregator.process_news_query("AI", max_articles=2)
    
    # JSON 형태로 변환
    json_result = []
    for article in articles:
        json_result.append({
            "title": article.title,
            "link": article.link,
            "summary": article.summary,
            "source": article.source,
            "published_date": article.published_date
        })
    
    print(json.dumps(json_result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    # 실행할 예시 선택
    print("뉴스 요약 시스템 사용 예시")
    
    examples = {
        "1": ("기본 사용", example_basic_usage),
        "2": ("키워드 추출 테스트", example_keyword_extraction),
        "3": ("커스텀 RSS", example_custom_rss),
        "4": ("JSON 출력", example_json_output)
    }
    
    print("\n실행할 예시를 선택하세요:")
    for key, (name, _) in examples.items():
        print(f"{key}. {name}")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice in examples:
        examples[choice][1]()
    else:
        print("잘못된 선택입니다.") 