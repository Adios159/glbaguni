#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import requests
import feedparser
import chardet
from glbaguni.backend.fetcher import ArticleFetcher
from glbaguni.backend.summarizer import ArticleSummarizer

def test_korean_rss_comprehensive():
    """Test Korean RSS feeds with encoding fixes and comprehensive diagnostics."""
    
    # Target RSS feeds for testing
    rss_feeds = [
        "https://news-ex.jtbc.co.kr/v1/get/rss/newsflesh",
        "https://www.hani.co.kr/rss/",
        "https://imnews.imbc.com/rss/google_news/narrativeNews.rss"
    ]
    
    print("🔬 KOREAN RSS COMPREHENSIVE TESTING")
    print("=" * 80)
    print()
    
    fetcher = ArticleFetcher()
    summarizer = ArticleSummarizer()
    
    all_results = {}
    
    for i, feed_url in enumerate(rss_feeds, 1):
        print(f"📰 TESTING FEED {i}/3: {feed_url}")
        print("=" * 80)
        
        # Step 1: Manual RSS parsing with encoding detection
        print("🔍 STEP 1: Manual RSS Parsing with Encoding Detection")
        print("-" * 60)
        
        try:
            # Fetch with proper headers
            response = requests.get(feed_url, headers={
                'User-Agent': 'Mozilla/5.0 (Glbaguni RSS Bot)',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'
            }, timeout=15)
            
            print(f"✅ HTTP Status: {response.status_code}")
            print(f"📄 Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            print(f"📊 Content Length: {len(response.content)} bytes")
            
            # Detect encoding
            detected = chardet.detect(response.content)
            encoding = detected.get('encoding', 'utf-8') if detected else 'utf-8'
            confidence = detected.get('confidence', 0) if detected else 0
            
            print(f"🔍 Detected Encoding: {encoding} (confidence: {confidence:.2f})")
            
            # Decode content
            try:
                decoded_content = response.content.decode(encoding, errors='ignore')
                print(f"✅ Successfully decoded {len(decoded_content)} characters")
            except Exception as e:
                print(f"⚠️  Decode error, falling back to utf-8: {e}")
                decoded_content = response.content.decode('utf-8', errors='ignore')
            
            # Parse with feedparser
            feed = feedparser.parse(decoded_content)
            
            print(f"🚨 Bozo Flag: {feed.bozo} ({'Parsing issues detected' if feed.bozo else 'No issues'})")
            if feed.bozo and hasattr(feed, 'bozo_exception'):
                print(f"⚠️  Bozo Exception: {feed.bozo_exception}")
            
            print(f"📄 Total Entries: {len(feed.entries)}")
            
            if hasattr(feed, 'feed'):
                print(f"📰 Feed Title: {getattr(feed.feed, 'title', 'Unknown')}")
                print(f"🔗 Feed Link: {getattr(feed.feed, 'link', 'Unknown')}")
            
            # Show first 3 entries
            if len(feed.entries) > 0:
                print(f"📋 First 3 Entries:")
                for j, entry in enumerate(feed.entries[:3]):
                    print(f"  {j+1}. Title: {getattr(entry, 'title', 'No title')}")
                    print(f"     Link: {getattr(entry, 'link', 'No link')}")
                    print()
            else:
                print("❌ No entries found")
                
        except Exception as e:
            print(f"❌ Error in manual parsing: {e}")
            feed = feedparser.parse(feed_url)  # Fallback
        
        print()
        
        # Step 2: Article fetching with our enhanced fetcher
        print("🔧 STEP 2: Enhanced Article Fetching")
        print("-" * 60)
        
        articles = fetcher.fetch_rss_articles(feed_url, max_articles=5)
        
        print(f"📊 Articles Fetched: {len(articles)}")
        
        if articles:
            print("📋 Article Details:")
            for j, article in enumerate(articles, 1):
                print(f"  {j}. Title: {article.title}")
                print(f"     URL: {article.url}")
                print(f"     Content Length: {len(article.content)} characters")
                print(f"     Content Preview: {article.content[:200]}...")
                
                # Check for extraction failure marker
                if "본문 추출 실패" in article.content:
                    print(f"     ⚠️  Contains '본문 추출 실패'")
                else:
                    print(f"     ✅ Content extraction successful")
                print()
        else:
            print("❌ No articles fetched")
        
        print()
        
        # Step 3: Summarization test (if articles available)
        if articles:
            print("📝 STEP 3: Summarization Testing")
            print("-" * 60)
            
            try:
                # Test with first 2 articles
                test_articles = articles[:2]
                summaries = summarizer.summarize_articles(test_articles)
                
                print(f"📊 Articles Sent for Summarization: {len(test_articles)}")
                print(f"📋 Summaries Generated: {len(summaries)}")
                
                if summaries:
                    for j, summary in enumerate(summaries, 1):
                        print(f"  {j}. Title: {summary.get('title', 'Unknown')}")
                        print(f"     Summary Length: {len(summary.get('summary', ''))} characters")
                        print(f"     Summary Preview: {summary.get('summary', '')[:150]}...")
                        print()
                else:
                    print("❌ No summaries generated")
                    
            except Exception as e:
                print(f"❌ Summarization error: {e}")
        else:
            print("⏭️  STEP 3: Skipped (no articles to summarize)")
        
        # Store results
        all_results[feed_url] = {
            'articles_fetched': len(articles),
            'articles': articles,
            'feed_parseable': len(feed.entries) > 0 if 'feed' in locals() else False,
            'bozo_flag': feed.bozo if 'feed' in locals() else True
        }
        
        print("=" * 80)
        print()
    
    # Final summary
    print("🎯 FINAL RESULTS SUMMARY")
    print("=" * 80)
    
    total_articles = 0
    successful_feeds = 0
    
    for feed_url, results in all_results.items():
        articles_count = results['articles_fetched']
        total_articles += articles_count
        
        if articles_count >= 2:
            successful_feeds += 1
            status = "✅ SUCCESS"
        elif articles_count > 0:
            status = "⚠️  PARTIAL"
        else:
            status = "❌ FAILED"
        
        print(f"{status} - {feed_url}")
        print(f"   📊 Articles: {articles_count}")
        print(f"   🚨 Bozo: {results['bozo_flag']}")
        print()
    
    print(f"📈 OVERALL STATISTICS:")
    print(f"   🎯 Target: At least 2 articles per feed")
    print(f"   ✅ Successful Feeds: {successful_feeds}/3")
    print(f"   📊 Total Articles Fetched: {total_articles}")
    print(f"   📋 Average per Feed: {total_articles/3:.1f}")
    
    if successful_feeds >= 2:
        print(f"🎉 GOAL ACHIEVED: {successful_feeds} feeds successfully providing 2+ articles each!")
    else:
        print(f"⚠️  GOAL NOT MET: Only {successful_feeds} feeds met the 2+ article requirement")
    
    print("=" * 80)

if __name__ == "__main__":
    test_korean_rss_comprehensive() 