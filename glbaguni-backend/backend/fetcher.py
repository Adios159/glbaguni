import feedparser
import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from typing import List, Optional, Any, Union
from datetime import datetime
import logging
from urllib.parse import urlparse
import time
import chardet

# Handle relative imports for both module and script execution
try:
    from .models import Article
    from .config import settings
except ImportError:
    try:
        from models import Article
        from config import settings
    except ImportError:
        # Fallback for direct script execution
        from models import Article
        from config import settings

logger = logging.getLogger(__name__)

class ArticleFetcher:
    """Fetches articles from RSS feeds and direct URLs."""
    
    def __init__(self):
        self.session = requests.Session()
        # Updated User-Agent for Korean RSS Bot
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Glbaguni RSS Bot)'
        })
        # Add retry mechanism
        self.session.mount('http://', HTTPAdapter(max_retries=3))
        self.session.mount('https://', HTTPAdapter(max_retries=3))
    
    def fetch_rss_articles(self, rss_url: str, max_articles: int = 10) -> List[Article]:
        """Fetch articles from RSS feed with Korean RSS support."""
        try:
            logger.info(f"Fetching RSS feed: {rss_url}")
            
            # Enhanced RSS fetching with proper headers and encoding detection for Korean sites
            try:
                # Use requests with proper headers for Korean news sites
                response = self.session.get(rss_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Glbaguni RSS Bot)',
                    'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'
                })
                response.raise_for_status()
                
                # Detect encoding using chardet for Korean RSS feeds
                detected_encoding = chardet.detect(response.content)
                encoding = detected_encoding.get('encoding', 'utf-8') if detected_encoding else 'utf-8'
                logger.info(f"🔍 [RSS-ENCODING] Detected encoding: {encoding} (confidence: {detected_encoding.get('confidence', 0):.2f})")
                
                # Decode content with detected encoding
                try:
                    decoded_content = response.content.decode(encoding, errors='ignore')
                    logger.info(f"✅ [RSS-ENCODING] Successfully decoded {len(decoded_content)} characters")
                except Exception as decode_error:
                    logger.warning(f"⚠️  [RSS-ENCODING] Decode error with {encoding}, falling back to utf-8: {decode_error}")
                    decoded_content = response.content.decode('utf-8', errors='ignore')
                
                # Parse the decoded RSS content
                feed = feedparser.parse(decoded_content)
                
            except (requests.RequestException, requests.HTTPError) as e:
                logger.warning(f"HTTP error fetching RSS feed {rss_url}: {e}")
                # Fallback to simple feedparser method
                feed = feedparser.parse(rss_url)
            
            # 🔍 STEP 1: RSS PARSING DEBUGGING
            logger.info(f"🔍 [RSS-PARSE] Analyzing RSS feed structure: {rss_url}")
            logger.info(f"📊 [RSS-PARSE] Feed version: {getattr(feed, 'version', 'Unknown')}")
            logger.info(f"🚨 [RSS-PARSE] Bozo flag: {feed.bozo} (True = parsing issues detected)")
            logger.info(f"📄 [RSS-PARSE] Total entries found: {len(feed.entries) if hasattr(feed, 'entries') else 0}")
            
            # Feed metadata analysis
            if hasattr(feed, 'feed'):
                feed_title = getattr(feed.feed, 'title', 'Unknown')
                feed_link = getattr(feed.feed, 'link', 'Unknown')
                logger.info(f"📰 [RSS-PARSE] Feed title: {feed_title}")
                logger.info(f"🔗 [RSS-PARSE] Feed link: {feed_link}")
                logger.info(f"🌐 [RSS-PARSE] Feed language: {getattr(feed.feed, 'language', 'Unknown')}")
            
            # Bozo flag analysis (critical for Korean RSS feeds)
            if feed.bozo:
                exception_msg = str(feed.bozo_exception) if feed.bozo_exception else "Unknown"
                logger.warning(f"⚠️  [RSS-PARSE] Bozo exception: {exception_msg}")
                logger.warning(f"🔧 [RSS-PARSE] Exception type: {type(feed.bozo_exception).__name__}")
                
                # Korean RSS feeds often have encoding/format issues
                if any(keyword in exception_msg.lower() for keyword in ["not well-formed", "encoding", "xml"]):
                    logger.info(f"✅ [RSS-PARSE] Continuing despite XML issues (common with Korean RSS feeds)")
                else:
                    logger.error(f"❌ [RSS-PARSE] Critical RSS parsing failure: {exception_msg}")
                    return []
            else:
                logger.info(f"✅ [RSS-PARSE] RSS feed parsed successfully without issues")
            
            if not hasattr(feed, 'entries') or not feed.entries:
                logger.error(f"❌ [RSS-PARSE] No entries found in RSS feed")
                logger.info(f"💡 [RSS-PARSE] This could indicate:")
                logger.info(f"   - Invalid RSS URL")
                logger.info(f"   - Server blocking requests")
                logger.info(f"   - Empty or broken RSS feed")
                return []
                
            # 무한로딩 방지: 디버깅 로그 최소화
            logger.info(f"📋 [RSS-ENTRIES] Processing {min(max_articles, len(feed.entries))} entries...")
            
            # 🔍 STEP 3: ARTICLE PROCESSING LOOP - 최적화
            articles = []
            processed_count = 0
            skipped_count = 0
            failed_count = 0
            
            # 처리할 엔트리 수 제한 (무한루프 방지)
            entries_to_process = min(max_articles, len(feed.entries), 15)  # 최대 15개로 제한
            
            for entry_idx, entry in enumerate(feed.entries[:entries_to_process]):
                processed_count += 1
                
                try:
                    # Validate required fields
                    if not hasattr(entry, 'title') or not hasattr(entry, 'link'):
                        skipped_count += 1
                        continue
                    
                    entry_title = str(entry.title).strip()
                    entry_url = str(entry.link)
                    
                    # Extract content from RSS entry
                    content = self._extract_content_from_rss_entry(entry)
                    
                    # 빠른 처리를 위해 RSS 내용이 충분하면 full article fetch 스킵
                    if content and len(content.strip()) >= 200:
                        logger.info(f"✅ [ARTICLE-PROCESS] RSS content sufficient: {len(content)} characters")
                    else:
                        # full article fetch는 시간이 많이 걸리므로 건너뛰기
                        if not content or len(content.strip()) < 50:
                            skipped_count += 1
                            continue
                    
                    # Content validation - 기준을 낮춤
                    if not content or len(content.strip()) < 50:
                        skipped_count += 1
                        continue
                    
                    # Check for extraction failure markers
                    if "본문 추출 실패" in content:
                        skipped_count += 1
                        continue
                    
                    # Parse published date
                    published_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            parsed_date = entry.published_parsed
                            if isinstance(parsed_date, (list, tuple)) and len(parsed_date) >= 6:
                                date_parts = []
                                for i in range(6):
                                    if i < len(parsed_date) and parsed_date[i] is not None:
                                        try:
                                            date_parts.append(int(parsed_date[i]))
                                        except (ValueError, TypeError):
                                            date_parts.append(0)
                                    else:
                                        date_parts.append(0)
                                published_date = datetime(*date_parts)
                        except (ValueError, TypeError, IndexError):
                            pass  # 로그 제거로 속도 향상
                    
                    # Validate URL
                    if not entry_url.startswith(('http://', 'https://')):
                        skipped_count += 1
                        continue
                    
                    # Create Article object
                    try:
                        article = Article(
                            title=entry_title,
                            url=entry_url,
                            content=content,
                            published_date=published_date,
                            author=getattr(entry, 'author', None),
                            source=urlparse(rss_url).netloc or "unknown"
                        )
                        articles.append(article)
                        
                    except Exception:
                        failed_count += 1
                        continue
                    
                except Exception:
                    failed_count += 1
                    continue
            
            # 🔍 STEP 4: FINAL SUMMARY - 로그 최소화
            logger.info(f"📊 [RSS-SUMMARY] {rss_url}: {len(articles)} articles, {skipped_count} skipped, {failed_count} failed")
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {rss_url}: {e}")
            return []
    
    def fetch_html_article(self, url: str) -> Optional[Article]:
        """Fetch article content from direct URL using BeautifulSoup with Korean support."""
        try:
            logger.info(f"Fetching HTML article: {url}")
            
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                logger.error(f"Invalid URL: {url}")
                return None
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                logger.warning(f"Content is not HTML: {content_type}")
                return None
            
            # Handle Korean encoding detection
            encoding = self._detect_encoding(response)
            logger.info(f"Using encoding: {encoding}")
            
            # Parse with detected encoding
            soup = BeautifulSoup(response.content, 'html.parser', from_encoding=encoding)
            
            # Extract title
            title = self._extract_title(soup)
            
            # Extract content with Korean site support
            content = self._extract_content_korean(soup)
            
            if not title or not content:
                logger.warning(f"Could not extract title or content from {url}")
                return None
            
            # Clean and validate content
            title = title.strip()
            content = content.strip()
            
            if len(content) < 30:  # Reduced minimum content length for Korean articles
                logger.warning(f"Content too short from {url}: {len(content)} characters")
                return None
            
            try:
                article = Article(
                    title=title,
                    url=url,  # type: ignore # Pydantic will validate this
                    content=content,
                    source=urlparse(url).netloc or "unknown"
                )
                
                logger.info(f"Successfully fetched article: {title} ({len(content)} characters)")
                return article
            except Exception as e:
                logger.error(f"Error creating Article object: {e}")
                return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching HTML article {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching HTML article {url}: {e}")
            return None

    def _detect_encoding(self, response: requests.Response) -> str:
        """Detect and return appropriate encoding for Korean content."""
        # Try apparent encoding first (good for Korean sites)
        if hasattr(response, 'apparent_encoding') and response.apparent_encoding:
            apparent = response.apparent_encoding.lower()
            # Common Korean encodings
            if any(enc in apparent for enc in ['euc-kr', 'cp949', 'ks_c_5601', 'korean']):
                logger.info(f"Detected Korean encoding: {response.apparent_encoding}")
                return response.apparent_encoding
        
        # Check encoding from headers
        if response.encoding and response.encoding.lower() != 'iso-8859-1':
            return response.encoding
        
        # Check apparent encoding for other cases
        if hasattr(response, 'apparent_encoding') and response.apparent_encoding:
            return response.apparent_encoding
        
        # Default fallback
        return 'utf-8'

    def _extract_content_korean(self, soup: BeautifulSoup) -> str:
        """Extract article content with Korean news site support."""
        # Remove unwanted elements
        for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 
                             'iframe', 'noscript', 'button', 'input', 'select', 'textarea']):
            unwanted.decompose()
        
        # Remove common unwanted elements
        unwanted_selectors = ['.ad', '.advertisement', '.banner', '.social', '.share', '.related', 
                             '.comment', '.sidebar', '.menu', '.navigation', '.breadcrumb']
        for selector in unwanted_selectors:
            for elem in soup.select(selector):
                elem.decompose()
        
        # Enhanced Korean news site content selectors (ordered by priority)
        korean_selectors = [
            # Hani (한겨레)
            {'tag': 'div', 'id': 'article-view-content-div'},
            {'tag': 'div', 'class_': 'article-text'},
            {'tag': 'div', 'id': 'articleBodyContents'},
            {'tag': 'div', 'class_': 'article-text-area'},
            
            # Chosun (조선일보)
            {'tag': 'div', 'class_': 'par'},
            {'tag': 'div', 'id': 'news_body_id'},
            {'tag': 'div', 'class_': 'news_body'},
            
            # JoongAng (중앙일보)
            {'tag': 'div', 'class_': 'article_body'},
            {'tag': 'div', 'id': 'article_body'},
            {'tag': 'div', 'class_': 'article'},
            
            # Yonhap (연합뉴스)
            {'tag': 'div', 'class_': 'story-news-article'},
            {'tag': 'div', 'id': 'articleWrap'},
            {'tag': 'div', 'class_': 'story'},
            {'tag': 'div', 'id': 'articleText'},
            
            # SBS
            {'tag': 'div', 'class_': 'text_area'},
            {'tag': 'div', 'id': 'container'},
            {'tag': 'div', 'class_': 'article_area'},
            
            # KBS
            {'tag': 'div', 'class_': 'detail-body'},
            {'tag': 'div', 'id': 'content'},
            {'tag': 'div', 'class_': 'detail_content'},
            
            # MBC
            {'tag': 'div', 'class_': 'news_txt'},
            {'tag': 'div', 'id': 'content'},
            
            # JTBC
            {'tag': 'div', 'class_': 'article_content'},
            {'tag': 'div', 'id': 'articlebody'},
            
            # Generic Korean patterns
            {'tag': 'div', 'id': 'newsEndContents'},
            {'tag': 'div', 'class_': 'view-content'},
            {'tag': 'div', 'class_': 'article-content'},
            {'tag': 'div', 'class_': 'news-content'},
            {'tag': 'div', 'class_': 'post-content'},
            {'tag': 'div', 'class_': 'entry-content'},
            
            # Generic selectors (lowest priority)
            {'tag': 'article'},
            {'tag': 'div', 'class_': 'article-body'},
            {'tag': 'main'},
        ]
        
        # Try each selector
        for selector in korean_selectors:
            try:
                if 'class_' in selector:
                    content_elem = soup.find(selector['tag'], class_=selector['class_'])
                elif 'id' in selector:
                    content_elem = soup.find(selector['tag'], id=selector['id'])
                else:
                    content_elem = soup.find(selector['tag'])
                
                if content_elem:
                    # Remove nested unwanted elements (only if it's a Tag, not NavigableString)
                    if hasattr(content_elem, 'find_all'):
                        for unwanted in content_elem.find_all(['script', 'style', 'iframe', 'noscript']):
                            unwanted.decompose()
                    
                    text = content_elem.get_text(separator=' ', strip=True)
                    if len(text) > 100:  # Minimum content length
                        logger.info(f"Content extracted using selector: {selector}")
                        return self._clean_korean_text(text)
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # Fallback to generic content extraction
        logger.info("Using fallback content extraction")
        return self._extract_content_fallback(soup)

    def _clean_korean_text(self, text: str) -> str:
        """Clean extracted Korean text."""
        import re
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common Korean site artifacts
        artifacts = [
            r'기자\s*=?\s*\w+@\w+\.\w+',  # Remove reporter email
            r'Copyright\s*©.*',
            r'저작권자\s*©.*',
            r'무단전재.*금지',
            r'배포.*금지',
            r'\[.*?기자\]',
            r'\[.*?특파원\]',
            r'▶.*?◀',
            r'※.*',
            r'☞.*',
            r'■.*',
            r'▲.*',
            r'●.*',
        ]
        
        for pattern in artifacts:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _extract_content_fallback(self, soup: BeautifulSoup) -> str:
        """Fallback content extraction method."""
        try:
            # Try to find content in paragraphs
            paragraphs = soup.find_all('p')
            if paragraphs:
                content_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 20:  # Filter out short paragraphs
                        content_parts.append(text)
                
                if content_parts:
                    combined_text = ' '.join(content_parts)
                    if len(combined_text) > 100:
                        return self._clean_korean_text(combined_text)
            
            # Last resort: body text
            body = soup.find('body')
            if body:
                text = body.get_text(separator=' ', strip=True)
                if len(text) > 100:
                    return self._clean_korean_text(text)
            
            return "본문 추출 실패"
            
        except Exception as e:
            logger.error(f"Fallback content extraction failed: {e}")
            return "본문 추출 실패"
    
    def _extract_content_from_rss_entry(self, entry: Any) -> str:
        """Extract content from RSS entry, trying different fields with Korean support."""
        # Try different content fields (order matters for Korean RSS feeds)
        content_fields = ['content', 'description', 'summary', 'subtitle']
        
        for field in content_fields:
            if hasattr(entry, field):
                content = getattr(entry, field)
                
                # Handle different content types
                if isinstance(content, list) and content:
                    try:
                        # Try to get the value from the first content item
                        if hasattr(content[0], 'value'):
                            extracted = content[0].value
                        elif isinstance(content[0], dict) and 'value' in content[0]:
                            extracted = content[0]['value']
                        else:
                            extracted = str(content[0])
                            
                        if extracted and len(extracted.strip()) > 10:
                            logger.debug(f"Extracted content from {field}: {len(extracted)} characters")
                            return self._clean_rss_content(extracted.strip())
                    except (AttributeError, IndexError, KeyError) as e:
                        logger.debug(f"Failed to extract from {field}: {e}")
                        continue
                        
                elif isinstance(content, str) and content.strip():
                    if len(content.strip()) > 10:
                        logger.debug(f"Extracted content from {field}: {len(content)} characters")
                        return self._clean_rss_content(content.strip())
                        
                elif hasattr(content, 'value'):
                    try:
                        value = getattr(content, 'value')
                        if value:
                            logger.debug(f"Extracted content from {field}.value: {len(str(value))} characters")
                            return self._clean_rss_content(str(value).strip())
                    except AttributeError:
                        continue
        
        return ""

    def _clean_rss_content(self, content: str) -> str:
        """Clean RSS content by removing HTML tags and extra whitespace."""
        import re
        from html import unescape
        
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Unescape HTML entities
        content = unescape(content)
        
        # Remove extra whitespace
        content = ' '.join(content.split())
        
        # Remove common RSS artifacts
        content = re.sub(r'\[CDATA\[|\]\]', '', content)
        content = re.sub(r'^\s*\.\.\.\s*', '', content)
        
        return content.strip()
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title from HTML."""
        # Try different title selectors
        title_selectors = [
            'h1',
            'title',
            '[class*="title"]',
            '[class*="headline"]',
            'h2',
            'h3'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text().strip():
                return title_elem.get_text().strip()
        
        return ""
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract article content from HTML."""
        # Remove unwanted elements
        for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
            unwanted.decompose()
        
        # Try different content selectors
        content_selectors = [
            'article',
            '[class*="content"]',
            '[class*="article"]',
            '[class*="post"]',
            'main',
            '.entry-content',
            '.post-content',
            '.story-content',
            '.article-content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                text = content_elem.get_text(separator=' ', strip=True)
                if len(text) > 100:  # Minimum content length
                    return text
        
        # Fallback to body text
        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)
        
        return ""
    
    def fetch_multiple_sources(self, rss_urls: Optional[List[str]] = None, 
                             article_urls: Optional[List[str]] = None,
                             max_articles: int = 10) -> List[Article]:
        """Fetch articles from multiple sources with timeout protection."""
        import time
        start_time = time.time()
        max_processing_time = 60  # 최대 60초 처리 시간 제한
        
        articles = []
        
        # Fetch from RSS feeds
        if rss_urls:
            processed_feeds = 0
            max_feeds = 5  # 최대 5개 RSS 피드만 처리
            
            for rss_url in rss_urls:
                # 시간 초과 체크
                if time.time() - start_time > max_processing_time:
                    logger.warning(f"Processing timeout reached, stopping RSS fetch at {processed_feeds} feeds")
                    break
                    
                if processed_feeds >= max_feeds:
                    logger.info(f"Maximum RSS feeds reached: {max_feeds}")
                    break
                    
                try:
                    rss_articles = self.fetch_rss_articles(rss_url, min(max_articles, 10))
                    articles.extend(rss_articles)
                    processed_feeds += 1
                    # Add small delay between requests
                    time.sleep(0.3)  # 0.5에서 0.3으로 단축
                except Exception as e:
                    logger.error(f"Error fetching RSS feed {rss_url}: {e}")
                    continue
        
        # Fetch from direct URLs
        if article_urls:
            processed_urls = 0
            max_urls = 10  # 최대 10개 직접 URL만 처리
            
            for url in article_urls:
                # 시간 초과 체크
                if time.time() - start_time > max_processing_time:
                    logger.warning(f"Processing timeout reached, stopping URL fetch at {processed_urls} URLs")
                    break
                    
                if processed_urls >= max_urls:
                    logger.info(f"Maximum URLs reached: {max_urls}")
                    break
                    
                try:
                    article = self.fetch_html_article(url)
                    if article:
                        articles.append(article)
                    processed_urls += 1
                    # Add small delay between requests
                    time.sleep(0.3)  # 0.5에서 0.3으로 단축
                except Exception as e:
                    logger.error(f"Error fetching article {url}: {e}")
                    continue
        
        # Sort by published date (newest first) and limit total
        try:
            articles.sort(key=lambda x: x.published_date or datetime.min, reverse=True)
        except Exception as e:
            logger.warning(f"Error sorting articles: {e}")
        
        # 최종 결과 제한
        final_articles = articles[:max_articles]
        processing_time = time.time() - start_time
        logger.info(f"Fetch completed: {len(final_articles)} articles in {processing_time:.2f}s")
        
        return final_articles
