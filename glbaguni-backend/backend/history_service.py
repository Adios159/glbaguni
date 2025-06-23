"""
History and recommendation service for tracking user activity and generating personalized recommendations.
"""
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter
import re
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

try:
    from .models import UserHistory, RecommendationLog, UserPreferences, Article
    from .database import get_or_create_user_preferences
except ImportError:
    from models import UserHistory, RecommendationLog, UserPreferences, Article
    from database import get_or_create_user_preferences

logger = logging.getLogger(__name__)

class HistoryService:
    """Service for managing user history and generating recommendations."""
    
    def __init__(self):
        self.stopwords_ko = {
            '이', '그', '저', '것', '들', '수', '있', '하', '되', '된', '될', '에', '의', '을', '를', 
            '이다', '있다', '하다', '되다', '같다', '대한', '위한', '통해', '따라', '위해', '대해',
            '그러나', '그리고', '하지만', '또한', '또는', '만약', '따라서', '그래서', '즉', '예를'
        }
        self.stopwords_en = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
    
    def generate_user_id(self) -> str:
        """Generate a unique user ID."""
        return str(uuid.uuid4())
    
    def extract_keywords(self, text: str, language: str = "en", max_keywords: int = 10) -> List[str]:
        """
        Extract meaningful keywords from text based on language.
        Simple keyword extraction using word frequency.
        """
        if not text:
            return []
        
        # Clean and normalize text
        text = text.lower()
        # Remove special characters and numbers
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        # Split into words
        words = text.split()
        
        # Remove stopwords based on language
        stopwords = self.stopwords_ko if language == "ko" else self.stopwords_en
        words = [word for word in words if word not in stopwords and len(word) > 2]
        
        # Count word frequency
        word_freq = Counter(words)
        
        # Return top keywords
        return [word for word, freq in word_freq.most_common(max_keywords)]
    
    def categorize_article(self, title: str, content: str, url: str) -> Optional[str]:
        """
        Basic article categorization based on keywords and URL patterns.
        Returns category string or None.
        """
        title_lower = title.lower()
        content_lower = content.lower()
        url_lower = url.lower()
        
        # Define category keywords (both Korean and English)
        categories = {
            "정치/Politics": [
                "정치", "대통령", "국회", "의원", "선거", "정당", "정부", "국정", "여당", "야당",
                "politics", "president", "congress", "election", "government", "parliament", "senator"
            ],
            "경제/Economy": [
                "경제", "금융", "주식", "시장", "기업", "투자", "부동산", "GDP", "인플레이션", "금리",
                "economy", "finance", "stock", "market", "business", "investment", "real estate", "inflation"
            ],
            "기술/Technology": [
                "기술", "IT", "인공지능", "AI", "컴퓨터", "소프트웨어", "하드웨어", "디지털", "스마트폰", "앱",
                "technology", "artificial intelligence", "computer", "software", "digital", "smartphone", "app"
            ],
            "건강/Health": [
                "건강", "의료", "병원", "질병", "치료", "백신", "코로나", "의사", "간호사", "약",
                "health", "medical", "hospital", "disease", "treatment", "vaccine", "doctor", "medicine"
            ],
            "스포츠/Sports": [
                "스포츠", "축구", "야구", "농구", "올림픽", "월드컵", "선수", "팀", "경기", "우승",
                "sports", "football", "soccer", "baseball", "basketball", "olympics", "player", "team", "game"
            ],
            "문화/Culture": [
                "문화", "영화", "드라마", "음악", "예술", "책", "소설", "전시", "공연", "축제",
                "culture", "movie", "film", "drama", "music", "art", "book", "exhibition", "performance", "festival"
            ]
        }
        
        # Check for category matches
        text_to_check = f"{title_lower} {content_lower[:500]}"  # First 500 chars of content
        
        category_scores = {}
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in text_to_check)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        return None
    
    def save_summary_history(
        self, 
        db: Session, 
        user_id: str, 
        article: Article, 
        summary: str, 
        language: str,
        original_length: int,
        summary_length: int
    ) -> UserHistory:
        """
        Save a summary to user history.
        """
        try:
            # Extract content excerpt (first 500 characters)
            content_excerpt = article.content[:500] + "..." if len(article.content) > 500 else article.content
            
            # Extract keywords from title and content
            full_text = f"{article.title} {article.content}"
            keywords = self.extract_keywords(full_text, language)
            
            # Categorize article
            category = self.categorize_article(article.title, article.content, str(article.url))
            
            # Create history entry
            history_entry = UserHistory(
                user_id=user_id,
                article_title=article.title,
                article_url=str(article.url),
                article_source=article.source,
                content_excerpt=content_excerpt,
                summary_text=summary,
                summary_language=language,
                original_length=original_length,
                summary_length=summary_length,
                keywords=json.dumps(keywords),
                category=category,
                created_at=datetime.utcnow()
            )
            
            db.add(history_entry)
            db.commit()
            db.refresh(history_entry)
            
            logger.info(f"📝 [HISTORY] Saved summary history for user {user_id}: {article.title}")
            return history_entry
            
        except Exception as e:
            logger.error(f"❌ [HISTORY] Failed to save summary history: {e}")
            db.rollback()
            raise
    
    def save_news_search_history(
        self, 
        db: Session, 
        user_id: str, 
        article_title: str,
        article_url: str,
        article_source: str,
        content_excerpt: str,
        summary_text: str,
        language: str,
        original_length: int,
        summary_length: int,
        keywords: List[str]
    ) -> UserHistory:
        """
        Save a news search result to user history.
        This is a specialized method for news search results.
        """
        try:
            # Categorize article based on title and content excerpt
            category = self.categorize_article(article_title, content_excerpt, article_url)
            
            # Create history entry
            history_entry = UserHistory(
                user_id=user_id,
                article_title=article_title,
                article_url=article_url,
                article_source=article_source,
                content_excerpt=content_excerpt,
                summary_text=summary_text,
                summary_language=language,
                original_length=original_length,
                summary_length=summary_length,
                keywords=json.dumps(keywords),
                category=category,
                created_at=datetime.utcnow()
            )
            
            db.add(history_entry)
            db.commit()
            db.refresh(history_entry)
            
            logger.info(f"📝 [HISTORY] Saved news search history for user {user_id}: {article_title}")
            return history_entry
            
        except Exception as e:
            logger.error(f"❌ [HISTORY] Failed to save news search history: {e}")
            db.rollback()
            raise
    
    def get_user_history(
        self, 
        db: Session, 
        user_id: str, 
        page: int = 1, 
        per_page: int = 20,
        language_filter: Optional[str] = None
    ) -> Tuple[List[UserHistory], int]:
        """
        Get user's summary history with pagination and optional language filtering.
        """
        try:
            query = db.query(UserHistory).filter(UserHistory.user_id == user_id)
            
            # Apply language filter if specified
            if language_filter:
                query = query.filter(UserHistory.summary_language == language_filter)
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination and ordering
            offset = (page - 1) * per_page
            history_items = query.order_by(desc(UserHistory.created_at)).offset(offset).limit(per_page).all()
            
            logger.info(f"📖 [HISTORY] Retrieved {len(history_items)} history items for user {user_id}")
            return history_items, total_count
            
        except Exception as e:
            logger.error(f"❌ [HISTORY] Failed to get user history: {e}")
            return [], 0
    
    def get_user_keywords(self, db: Session, user_id: str, limit_days: int = 30) -> List[str]:
        """
        Get frequently used keywords from user's recent history.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=limit_days)
            
            history_items = db.query(UserHistory).filter(
                and_(
                    UserHistory.user_id == user_id,
                    UserHistory.created_at >= cutoff_date
                )
            ).all()
            
            # Aggregate all keywords
            all_keywords = []
            for item in history_items:
                if item.keywords:
                    try:
                        keywords = json.loads(item.keywords)
                        all_keywords.extend(keywords)
                    except (json.JSONDecodeError, TypeError):
                        continue
            
            # Count keyword frequency
            keyword_freq = Counter(all_keywords)
            
            # Return top 20 most frequent keywords
            top_keywords = [keyword for keyword, freq in keyword_freq.most_common(20)]
            
            logger.info(f"🔍 [HISTORY] Found {len(top_keywords)} frequent keywords for user {user_id}")
            return top_keywords
            
        except Exception as e:
            logger.error(f"❌ [HISTORY] Failed to get user keywords: {e}")
            return []
    
    def get_user_categories(self, db: Session, user_id: str, limit_days: int = 30) -> List[str]:
        """
        Get frequently accessed categories from user's recent history.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=limit_days)
            
            history_items = db.query(UserHistory).filter(
                and_(
                    UserHistory.user_id == user_id,
                    UserHistory.created_at >= cutoff_date,
                    UserHistory.category.isnot(None)
                )
            ).all()
            
            # Count category frequency
            categories = [item.category for item in history_items if item.category]
            category_freq = Counter(categories)
            
            # Return top categories
            top_categories = [category for category, freq in category_freq.most_common(10)]
            
            logger.info(f"📂 [HISTORY] Found {len(top_categories)} frequent categories for user {user_id}")
            return top_categories
            
        except Exception as e:
            logger.error(f"❌ [HISTORY] Failed to get user categories: {e}")
            return []
    
    def generate_keyword_based_recommendations(
        self, 
        db: Session, 
        user_id: str, 
        available_articles: List[Article],
        max_recommendations: int = 5
    ) -> List[Dict]:
        """
        Generate recommendations based on user's frequent keywords.
        """
        try:
            user_keywords = self.get_user_keywords(db, user_id)
            if not user_keywords:
                return []
            
            recommendations = []
            
            for article in available_articles:
                # Extract keywords from article
                article_text = f"{article.title} {article.content[:1000]}"  # First 1000 chars
                article_keywords = self.extract_keywords(article_text, "en")  # Assuming mixed content
                
                # Calculate similarity score (intersection of keywords)
                common_keywords = set(user_keywords) & set(article_keywords)
                if common_keywords:
                    score = len(common_keywords) / len(set(user_keywords) | set(article_keywords))  # Jaccard similarity
                    
                    recommendations.append({
                        "article_title": article.title,
                        "article_url": str(article.url),
                        "article_source": article.source,
                        "recommendation_type": "keyword",
                        "recommendation_score": score,
                        "keywords": list(common_keywords),
                        "category": self.categorize_article(article.title, article.content, str(article.url))
                    })
            
            # Sort by score and limit results
            recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
            return recommendations[:max_recommendations]
            
        except Exception as e:
            logger.error(f"❌ [HISTORY] Failed to generate keyword-based recommendations: {e}")
            return []
    
    def generate_category_based_recommendations(
        self, 
        db: Session, 
        user_id: str, 
        available_articles: List[Article],
        max_recommendations: int = 5
    ) -> List[Dict]:
        """
        Generate recommendations based on user's frequent categories.
        """
        try:
            user_categories = self.get_user_categories(db, user_id)
            if not user_categories:
                return []
            
            recommendations = []
            
            for article in available_articles:
                article_category = self.categorize_article(article.title, article.content, str(article.url))
                
                if article_category and article_category in user_categories:
                    # Score based on category preference frequency
                    category_rank = user_categories.index(article_category) + 1
                    score = 1.0 / category_rank  # Higher score for more frequent categories
                    
                    recommendations.append({
                        "article_title": article.title,
                        "article_url": str(article.url),
                        "article_source": article.source,
                        "recommendation_type": "category",
                        "recommendation_score": score,
                        "keywords": [],
                        "category": article_category
                    })
            
            # Sort by score and limit results
            recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
            return recommendations[:max_recommendations]
            
        except Exception as e:
            logger.error(f"❌ [HISTORY] Failed to generate category-based recommendations: {e}")
            return []
    
    def generate_recommendations(
        self, 
        db: Session, 
        user_id: str, 
        available_articles: List[Article],
        max_total: int = 10
    ) -> List[Dict]:
        """
        Generate combined recommendations using multiple strategies.
        """
        try:
            all_recommendations = []
            
            # Get keyword-based recommendations
            keyword_recs = self.generate_keyword_based_recommendations(db, user_id, available_articles, max_total // 2)
            all_recommendations.extend(keyword_recs)
            
            # Get category-based recommendations
            category_recs = self.generate_category_based_recommendations(db, user_id, available_articles, max_total // 2)
            all_recommendations.extend(category_recs)
            
            # Remove duplicates (by URL) and sort by score
            seen_urls = set()
            unique_recommendations = []
            
            for rec in sorted(all_recommendations, key=lambda x: x["recommendation_score"], reverse=True):
                if rec["article_url"] not in seen_urls:
                    seen_urls.add(rec["article_url"])
                    unique_recommendations.append(rec)
            
            result = unique_recommendations[:max_total]
            
            logger.info(f"🎯 [HISTORY] Generated {len(result)} recommendations for user {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ [HISTORY] Failed to generate recommendations: {e}")
            return []
    
    def log_recommendation_click(self, db: Session, user_id: str, article_url: str):
        """
        Log when a user clicks on a recommended article.
        """
        try:
            # Find the recommendation log entry
            rec_log = db.query(RecommendationLog).filter(
                and_(
                    RecommendationLog.user_id == user_id,
                    RecommendationLog.recommended_article_url == article_url,
                    RecommendationLog.clicked == False
                )
            ).first()
            
            if rec_log:
                rec_log.clicked = True
                db.commit()
                logger.info(f"👆 [HISTORY] Logged recommendation click for user {user_id}: {article_url}")
            
        except Exception as e:
            logger.error(f"❌ [HISTORY] Failed to log recommendation click: {e}")
    
    def get_user_stats(self, db: Session, user_id: str) -> Dict:
        """
        Get comprehensive user statistics.
        """
        try:
            # Get total summaries
            total_summaries = db.query(UserHistory).filter(UserHistory.user_id == user_id).count()
            
            # Get user preferences
            preferences = get_or_create_user_preferences(db, user_id)
            
            # Get favorite categories
            favorite_categories = self.get_user_categories(db, user_id)[:5]  # Top 5
            
            # Get recent activity (last 10 items)
            recent_history, _ = self.get_user_history(db, user_id, page=1, per_page=10)
            
            # Get recommendations count
            recommendations_count = db.query(RecommendationLog).filter(RecommendationLog.user_id == user_id).count()
            
            return {
                "user_id": user_id,
                "total_summaries": total_summaries,
                "preferred_language": preferences.preferred_language,
                "favorite_categories": favorite_categories,
                "recent_activity": recent_history,
                "recommendations_count": recommendations_count
            }
            
        except Exception as e:
            logger.error(f"❌ [HISTORY] Failed to get user stats: {e}")
            return {
                "user_id": user_id,
                "total_summaries": 0,
                "preferred_language": "en",
                "favorite_categories": [],
                "recent_activity": [],
                "recommendations_count": 0
            }