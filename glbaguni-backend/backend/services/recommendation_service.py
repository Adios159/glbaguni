#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recommendation Service
사용자 추천 시스템
"""

import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

try:
    from ..models import Article, RecommendationLog, UserHistory
except ImportError:
    from models import Article, RecommendationLog, UserHistory

logger = logging.getLogger(__name__)


class RecommendationService:
    """사용자 추천 서비스"""

    def __init__(self):
        self.min_history_for_recommendations = 3
        self.max_recommendations = 20

    def generate_keyword_based_recommendations(
        self,
        db: Session,
        user_id: str,
        available_articles: List[Article],
        max_recommendations: int = 5,
    ) -> List[Dict]:
        """키워드 기반 추천 생성"""
        try:
            # 사용자의 최근 30일 키워드 분석
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            user_keywords = (
                db.query(UserHistory)
                .filter(
                    UserHistory.user_id == user_id,
                    UserHistory.created_at >= thirty_days_ago,
                )
                .all()
            )

            if len(user_keywords) < self.min_history_for_recommendations:
                logger.info(
                    f"사용자 {user_id}의 히스토리가 부족합니다 ({len(user_keywords)}개)"
                )
                return []

            # 키워드 빈도 계산
            all_keywords = []
            for history in user_keywords:
                if history.keywords:
                    try:
                        keywords = json.loads(history.keywords)
                        all_keywords.extend(keywords)
                    except json.JSONDecodeError:
                        continue

            if not all_keywords:
                return []

            keyword_counts = Counter(all_keywords)
            top_keywords = [kw for kw, count in keyword_counts.most_common(10)]

            # 키워드 기반 기사 추천
            recommendations = []
            for article in available_articles[:50]:  # 성능을 위해 제한
                score = self._calculate_keyword_similarity(article, top_keywords)
                if score > 0.3:  # 임계값
                    recommendations.append(
                        {
                            "article_title": article.title,
                            "article_url": str(article.url),
                            "article_source": article.source,
                            "recommendation_type": "keyword",
                            "recommendation_score": score,
                            "matched_keywords": self._get_matched_keywords(
                                article, top_keywords
                            ),
                            "created_at": datetime.utcnow(),
                        }
                    )

            # 점수 순으로 정렬
            recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)

            logger.info(
                f"키워드 기반 추천 {len(recommendations[:max_recommendations])}개 생성"
            )
            return recommendations[:max_recommendations]

        except Exception as e:
            logger.error(f"키워드 기반 추천 생성 실패: {e}")
            return []

    def generate_category_based_recommendations(
        self,
        db: Session,
        user_id: str,
        available_articles: List[Article],
        max_recommendations: int = 5,
    ) -> List[Dict]:
        """카테고리 기반 추천 생성"""
        try:
            # 사용자의 선호 카테고리 분석
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            user_history = (
                db.query(UserHistory)
                .filter(
                    UserHistory.user_id == user_id,
                    UserHistory.created_at >= thirty_days_ago,
                    UserHistory.category.isnot(None),
                )
                .all()
            )

            if not user_history:
                return []

            # 카테고리 선호도 계산
            category_counts = Counter([h.category for h in user_history if h.category])
            if not category_counts:
                return []

            top_categories = [cat for cat, count in category_counts.most_common(5)]

            # 카테고리 기반 기사 추천
            recommendations = []
            for article in available_articles[:50]:
                category = self._categorize_article(
                    article.title, article.content, str(article.url)
                )
                if category in top_categories:
                    score = category_counts[category] / sum(category_counts.values())
                    recommendations.append(
                        {
                            "article_title": article.title,
                            "article_url": str(article.url),
                            "article_source": article.source,
                            "recommendation_type": "category",
                            "recommendation_score": score,
                            "category": category,
                            "created_at": datetime.utcnow(),
                        }
                    )

            # 점수 순으로 정렬
            recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)

            logger.info(
                f"카테고리 기반 추천 {len(recommendations[:max_recommendations])}개 생성"
            )
            return recommendations[:max_recommendations]

        except Exception as e:
            logger.error(f"카테고리 기반 추천 생성 실패: {e}")
            return []

    def generate_recommendations(
        self,
        db: Session,
        user_id: str,
        available_articles: List[Article],
        max_total: int = 10,
    ) -> List[Dict]:
        """통합 추천 생성"""
        try:
            # 키워드 기반 추천 (60%)
            keyword_recommendations = self.generate_keyword_based_recommendations(
                db, user_id, available_articles, max_total // 2 + 2
            )

            # 카테고리 기반 추천 (40%)
            category_recommendations = self.generate_category_based_recommendations(
                db, user_id, available_articles, max_total // 2
            )

            # 추천 결합 (중복 제거)
            all_recommendations = []
            seen_urls = set()

            # 키워드 추천 우선 추가
            for rec in keyword_recommendations:
                if rec["article_url"] not in seen_urls:
                    all_recommendations.append(rec)
                    seen_urls.add(rec["article_url"])

            # 카테고리 추천 추가
            for rec in category_recommendations:
                if (
                    rec["article_url"] not in seen_urls
                    and len(all_recommendations) < max_total
                ):
                    all_recommendations.append(rec)
                    seen_urls.add(rec["article_url"])

            logger.info(f"통합 추천 {len(all_recommendations)}개 생성")
            return all_recommendations[:max_total]

        except Exception as e:
            logger.error(f"통합 추천 생성 실패: {e}")
            return []

    def _calculate_keyword_similarity(
        self, article: Article, user_keywords: List[str]
    ) -> float:
        """기사와 사용자 키워드 간 유사도 계산"""
        article_text = f"{article.title} {article.content}".lower()

        matches = 0
        for keyword in user_keywords:
            if keyword.lower() in article_text:
                matches += 1

        return matches / len(user_keywords) if user_keywords else 0

    def _get_matched_keywords(
        self, article: Article, user_keywords: List[str]
    ) -> List[str]:
        """매칭된 키워드 목록 반환"""
        article_text = f"{article.title} {article.content}".lower()
        matched = []

        for keyword in user_keywords:
            if keyword.lower() in article_text:
                matched.append(keyword)

        return matched

    def _categorize_article(self, title: str, content: str, url: str) -> Optional[str]:
        """기사 카테고리 분류"""
        title_lower = title.lower()
        content_lower = content.lower()

        categories = {
            "정치/Politics": [
                "정치",
                "대통령",
                "국회",
                "의원",
                "선거",
                "정당",
                "정부",
                "politics",
                "president",
                "congress",
                "election",
            ],
            "경제/Economy": [
                "경제",
                "금융",
                "주식",
                "시장",
                "기업",
                "투자",
                "economy",
                "finance",
                "stock",
                "market",
                "business",
            ],
            "기술/Technology": [
                "기술",
                "IT",
                "인공지능",
                "AI",
                "컴퓨터",
                "소프트웨어",
                "technology",
                "artificial intelligence",
                "computer",
            ],
            "스포츠/Sports": [
                "스포츠",
                "축구",
                "야구",
                "농구",
                "올림픽",
                "sports",
                "football",
                "soccer",
                "baseball",
            ],
        }

        text_to_check = f"{title_lower} {content_lower[:500]}"

        for category, keywords in categories.items():
            if any(keyword in text_to_check for keyword in keywords):
                return category

        return None

    def log_recommendation_click(self, db: Session, user_id: str, article_url: str):
        """추천 클릭 로그 기록"""
        try:
            log_entry = RecommendationLog(
                user_id=user_id,
                article_url=article_url,
                clicked_at=datetime.utcnow(),
                recommendation_type="mixed",
            )

            db.add(log_entry)
            db.commit()

            logger.info(f"추천 클릭 로그 기록: {user_id} -> {article_url}")

        except Exception as e:
            logger.error(f"추천 클릭 로그 기록 실패: {e}")
            db.rollback()
