#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
요약 관련 엔드포인트들
"""

import json
import logging
import traceback
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

# Import dependencies with type: ignore to avoid linter conflicts
import sys
import os

# Add the backend directory to the path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from models import ArticleSummary, SummaryRequest, SummaryResponse, SummaryFeedbackRequest, SummaryFeedbackResponse, FeedbackStatsResponse  # type: ignore
    from models.models import SummaryFeedback  # type: ignore
    from services.background_tasks import save_to_history, send_summary_email  # type: ignore
    from utils.executors import SafeExecutor  # type: ignore
    from utils.responses import ResponseBuilder  # type: ignore
    from utils.validators import InputSanitizer  # type: ignore
except ImportError:
    try:
        # Fallback for package import
        from ..models import ArticleSummary, SummaryRequest, SummaryResponse, SummaryFeedbackRequest, SummaryFeedbackResponse, FeedbackStatsResponse  # type: ignore
        from ..models.models import SummaryFeedback  # type: ignore
        from ..services.background_tasks import save_to_history, send_summary_email  # type: ignore
        from ..utils.executors import SafeExecutor  # type: ignore
        from ..utils.responses import ResponseBuilder  # type: ignore
        from ..utils.validators import InputSanitizer  # type: ignore
    except ImportError:
        # Final fallback with minimal imports
        from models import ArticleSummary, SummaryRequest, SummaryResponse, SummaryFeedbackRequest, SummaryFeedbackResponse, FeedbackStatsResponse  # type: ignore
        
        # Simple mock implementations for missing dependencies
        class SafeExecutor:  # type: ignore
            @staticmethod
            async def safe_call(func, *args, **kwargs):  # type: ignore
                if callable(func):
                    try:
                        result = func(*args, **kwargs)
                        return await result if hasattr(result, '__await__') else result
                    except Exception:
                        return None
                return None
        
        class ResponseBuilder:  # type: ignore
            @staticmethod
            def success(data=None, message=""):  # type: ignore
                return {"success": True, "data": data, "message": message}
        
        class InputSanitizer:  # type: ignore
            @staticmethod
            def sanitize_text(text, max_length, field_name):  # type: ignore
                return str(text)[:max_length] if text else ""
        
        async def save_to_history(*args, **kwargs):  # type: ignore
            pass
        
        async def send_summary_email(*args, **kwargs):  # type: ignore
            pass


def create_summarize_router(app_state, importer):
    """요약 라우터 생성"""
    router = APIRouter()

    @router.post("/summarize", response_model=SummaryResponse)
    async def summarize_articles(
        request: SummaryRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(importer.services["get_db"]),
    ):
        """RSS 피드 요약 API"""
        request_id = str(uuid.uuid4())[:8]
        logger = logging.getLogger("glbaguni")
        logger.info(f"🚀 [{request_id}] RSS 요약 요청 시작")

        try:
            # 입력 검증
            validated_urls = []
            if request.rss_urls:
                for url in request.rss_urls:
                    validated_url = InputSanitizer.sanitize_text(str(url), 500, "RSS URL")
                    validated_urls.append(validated_url)

            user_id = (
                InputSanitizer.sanitize_text(request.user_id, 100, "사용자 ID")
                if request.user_id
                else "anonymous"
            )
            language = request.language or "ko"

            # 기사 수집
            if not app_state.fetcher:
                raise HTTPException(500, "RSS 수집 서비스가 초기화되지 않았습니다")

            articles = await SafeExecutor.safe_call(
                app_state.fetcher.fetch_multiple_sources,
                description="RSS 피드 수집",
                rss_urls=validated_urls or None,
                max_articles_per_source=request.max_articles or 5,
            )

            if not articles:
                raise HTTPException(404, "수집된 기사가 없습니다")

            logger.info(f"📰 [{request_id}] {len(articles)}개 기사 수집 완료")

            # 기사 요약
            if not app_state.summarizer:
                raise HTTPException(500, "요약 서비스가 초기화되지 않았습니다")

            summaries = []
            for i, article in enumerate(articles, 1):
                try:
                    logger.info(f"📝 [{request_id}] 요약 {i}/{len(articles)}")

                    content = f"제목: {article.title}\n내용: {article.content}"
                    result = await SafeExecutor.safe_call(
                        app_state.summarizer.summarize,
                        content,
                        language,
                        description=f"기사 {i} 요약",
                    )

                    if isinstance(result, dict) and "summary" in result:
                        summary = ArticleSummary(
                            title=article.title,
                            url=article.url,
                            summary=result["summary"],
                            source=article.source,
                            original_length=len(article.content),
                            summary_length=len(result["summary"]),
                        )
                        summaries.append(summary)

                except Exception as e:
                    logger.error(f"기사 {i} 요약 실패: {e}")
                    continue

            if not summaries:
                raise HTTPException(500, "요약된 기사가 없습니다")

            logger.info(f"✅ [{request_id}] {len(summaries)}개 기사 요약 완료")

            # 백그라운드 작업들
            if request.recipient_email and app_state.notifier:
                background_tasks.add_task(
                    send_summary_email, request.recipient_email, summaries, request_id, app_state
                )

            if user_id != "anonymous":
                background_tasks.add_task(
                    save_to_history, user_id, summaries, db, request_id, app_state
                )

            # SummaryResponse에 맞는 형식으로 변환
            summaries_dict = [
                {
                    "title": summary.title,
                    "url": str(summary.url),
                    "summary": summary.summary,
                    "source": summary.source,
                    "original_length": summary.original_length,
                    "summary_length": summary.summary_length,
                }
                for summary in summaries
            ]

            return SummaryResponse(
                success=True,
                message=f"{len(summaries)}개 기사 요약 완료",
                summaries=summaries_dict,
                total_articles=len(summaries),
                processed_at=datetime.now(),
                user_id=user_id,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ [{request_id}] 요약 처리 중 오류: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(500, "요약 처리 중 내부 오류가 발생했습니다")

    @router.post("/summarize-text")
    async def summarize_text_endpoint(request: Request):
        """텍스트 직접 요약 API"""
        request_id = str(uuid.uuid4())[:8]
        logger = logging.getLogger("glbaguni")
        logger.info(f"📝 [{request_id}] 텍스트 요약 요청")

        try:
            body = await request.json()
            text = body.get("text", "")
            language = body.get("language", "ko")

            # 입력 검증
            validated_text = InputSanitizer.sanitize_text(text, 10000, "요약할 텍스트")
            logger.info(f"📝 [{request_id}] 텍스트 길이: {len(validated_text)}자")

            if not app_state.summarizer:
                raise HTTPException(500, "요약 서비스가 초기화되지 않았습니다")

            # 요약 처리
            result = await SafeExecutor.safe_call(
                app_state.summarizer.summarize,
                validated_text,
                language,
                description="텍스트 요약",
            )

            if isinstance(result, dict) and "summary" in result:
                response_data = {
                    "summary": result["summary"],
                    "original_length": len(validated_text),
                    "summary_length": len(result["summary"]),
                    "language": language,
                    "compression_ratio": round(
                        len(result["summary"]) / len(validated_text), 3
                    ),
                }

                logger.info(f"✅ [{request_id}] 텍스트 요약 완료")
                return ResponseBuilder.success(
                    data=response_data, message="텍스트 요약 완료"
                )
            else:
                raise HTTPException(500, "요약 결과가 올바르지 않습니다")

        except HTTPException:
            raise
        except json.JSONDecodeError:
            raise HTTPException(400, "JSON 형식이 올바르지 않습니다")
        except Exception as e:
            logger.error(f"❌ [{request_id}] 텍스트 요약 중 오류: {e}")
            raise HTTPException(500, "텍스트 요약 중 내부 오류가 발생했습니다")

    @router.get("/status")
    async def summarize_status():
        """요약 서비스 상태 확인 API"""
        return {"status": "요약 서비스가 정상 작동 중입니다 📝"}

    @router.post("/feedback", response_model=SummaryFeedbackResponse)
    async def submit_feedback(
        feedback: SummaryFeedbackRequest,
        db: Session = Depends(importer.services["get_db"]),
    ):
        """요약 결과에 대한 피드백 제출 API"""
        logger = logging.getLogger("glbaguni")
        
        try:
            # 입력 검증
            user_id = feedback.user_id or "anonymous"
            
            # 새로운 피드백 생성
            db_feedback = SummaryFeedback(
                user_id=user_id,
                history_item_id=feedback.history_item_id,
                article_url=feedback.article_url,
                article_title=feedback.article_title,
                feedback_type=feedback.feedback_type,
                rating=feedback.rating,
                comment=feedback.comment,
                summary_language=feedback.summary_language or "ko",
            )
            
            db.add(db_feedback)
            db.commit()
            db.refresh(db_feedback)
            
            logger.info(f"📝 피드백 저장 완료: {feedback.feedback_type} (rating: {feedback.rating})")
            
            return SummaryFeedbackResponse(
                success=True,
                message="피드백이 성공적으로 저장되었습니다. 감사합니다!",
                feedback_id=db_feedback.id
            )
            
        except Exception as e:
            logger.error(f"❌ 피드백 저장 중 오류: {e}")
            db.rollback()
            raise HTTPException(500, "피드백 저장 중 오류가 발생했습니다")

    @router.get("/feedback/stats", response_model=FeedbackStatsResponse)
    async def get_feedback_stats(
        db: Session = Depends(importer.services["get_db"]),
        days: int = 30  # 최근 N일간의 통계
    ):
        """피드백 통계 조회 API"""
        logger = logging.getLogger("glbaguni")
        
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            
            # 기간 설정
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 전체 피드백 수
            total_feedback = db.query(SummaryFeedback).filter(
                SummaryFeedback.created_at >= start_date
            ).count()
            
            if total_feedback == 0:
                return FeedbackStatsResponse(
                    success=True,
                    total_feedback=0,
                    positive_count=0,
                    negative_count=0,
                    average_rating=0.0,
                    positive_percentage=0.0,
                    recent_feedback=[],
                    feedback_by_language={}
                )
            
            # 긍정/부정 피드백 수
            positive_count = db.query(SummaryFeedback).filter(
                SummaryFeedback.created_at >= start_date,
                SummaryFeedback.feedback_type == "positive"
            ).count()
            
            negative_count = db.query(SummaryFeedback).filter(
                SummaryFeedback.created_at >= start_date,
                SummaryFeedback.feedback_type == "negative"
            ).count()
            
            # 평균 평점
            avg_rating_result = db.query(func.avg(SummaryFeedback.rating)).filter(
                SummaryFeedback.created_at >= start_date
            ).scalar()
            average_rating = float(avg_rating_result) if avg_rating_result else 0.0
            
            # 긍정 비율
            positive_percentage = (positive_count / total_feedback * 100) if total_feedback > 0 else 0.0
            
            # 최근 피드백 (최대 10개)
            recent_feedback_items = db.query(SummaryFeedback).filter(
                SummaryFeedback.created_at >= start_date
            ).order_by(SummaryFeedback.created_at.desc()).limit(10).all()
            
            recent_feedback = [
                {
                    "article_title": item.article_title,
                    "feedback_type": item.feedback_type,
                    "rating": item.rating,
                    "comment": item.comment,
                    "created_at": item.created_at.isoformat(),
                }
                for item in recent_feedback_items
            ]
            
            # 언어별 피드백 통계
            language_stats = db.query(
                SummaryFeedback.summary_language,
                func.count(SummaryFeedback.id).label('count')
            ).filter(
                SummaryFeedback.created_at >= start_date
            ).group_by(SummaryFeedback.summary_language).all()
            
            feedback_by_language = {lang: count for lang, count in language_stats}
            
            logger.info(f"📊 피드백 통계 조회 완료: 총 {total_feedback}개")
            
            return FeedbackStatsResponse(
                success=True,
                total_feedback=total_feedback,
                positive_count=positive_count,
                negative_count=negative_count,
                average_rating=round(average_rating, 2),
                positive_percentage=round(positive_percentage, 1),
                recent_feedback=recent_feedback,
                feedback_by_language=feedback_by_language
            )
            
        except Exception as e:
            logger.error(f"❌ 피드백 통계 조회 중 오류: {e}")
            raise HTTPException(500, "피드백 통계 조회 중 오류가 발생했습니다")

    return router


# Export a router instance for main.py to use
# This is a simplified version that doesn't require app_state for basic functionality
router = APIRouter(prefix="/summarize", tags=["summarize"])

@router.get("/status")
async def summarize_status():
    """요약 서비스 상태 확인"""
    return {
        "status": "ready",
        "service": "summarize",
        "message": "요약 서비스가 준비되었습니다"
    }
