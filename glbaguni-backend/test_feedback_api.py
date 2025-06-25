#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
피드백 API 테스트 스크립트
"""

import requests
import json
import uuid

# API Base URL
API_BASE = "http://localhost:8003"

def test_feedback_submission():
    """피드백 제출 테스트"""
    print("📝 피드백 제출 테스트 시작...")
    
    # 테스트 데이터
    feedback_data = {
        "user_id": str(uuid.uuid4()),
        "article_url": "https://example.com/test-article",
        "article_title": "테스트 기사 제목",
        "feedback_type": "positive",
        "rating": 5,
        "comment": "정말 유용한 요약이었습니다!",
        "summary_language": "ko"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/feedback",
            json=feedback_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 피드백 제출 성공: {result}")
            return result.get("feedback_id")
        else:
            print(f"❌ 피드백 제출 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 피드백 제출 중 오류: {e}")
        return None

def test_feedback_stats():
    """피드백 통계 조회 테스트"""
    print("\n📊 피드백 통계 조회 테스트 시작...")
    
    try:
        response = requests.get(
            f"{API_BASE}/feedback/stats?days=30",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 피드백 통계 조회 성공:")
            print(f"  - 총 피드백: {result['total_feedback']}개")
            print(f"  - 긍정 피드백: {result['positive_count']}개")
            print(f"  - 부정 피드백: {result['negative_count']}개")
            print(f"  - 평균 평점: {result['average_rating']}")
            print(f"  - 긍정 비율: {result['positive_percentage']}%")
            return True
        else:
            print(f"❌ 피드백 통계 조회 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 피드백 통계 조회 중 오류: {e}")
        return False

def test_multiple_feedbacks():
    """여러 피드백 제출 테스트"""
    print("\n🔄 여러 피드백 제출 테스트 시작...")
    
    test_cases = [
        {
            "user_id": str(uuid.uuid4()),
            "article_url": "https://example.com/article-1",
            "article_title": "AI 발전 소식",
            "feedback_type": "positive",
            "rating": 4,
            "summary_language": "ko"
        },
        {
            "user_id": str(uuid.uuid4()),
            "article_url": "https://example.com/article-2", 
            "article_title": "경제 뉴스",
            "feedback_type": "negative",
            "rating": 2,
            "summary_language": "ko"
        },
        {
            "user_id": str(uuid.uuid4()),
            "article_url": "https://example.com/article-3",
            "article_title": "스포츠 소식",
            "feedback_type": "positive",
            "rating": 5,
            "summary_language": "en"
        }
    ]
    
    success_count = 0
    for i, feedback in enumerate(test_cases, 1):
        print(f"  {i}. {feedback['article_title']} - {feedback['feedback_type']}")
        
        try:
            response = requests.post(
                f"{API_BASE}/feedback",
                json=feedback,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                success_count += 1
                print(f"     ✅ 성공")
            else:
                print(f"     ❌ 실패: {response.status_code}")
                
        except Exception as e:
            print(f"     ❌ 오류: {e}")
    
    print(f"\n총 {len(test_cases)}개 중 {success_count}개 성공")
    return success_count == len(test_cases)

def main():
    """메인 테스트 함수"""
    print("🧪 피드백 API 테스트 시작")
    print("=" * 50)
    
    # 1. 단일 피드백 제출 테스트
    feedback_id = test_feedback_submission()
    
    # 2. 여러 피드백 제출 테스트  
    test_multiple_feedbacks()
    
    # 3. 피드백 통계 조회 테스트
    test_feedback_stats()
    
    print("\n" + "=" * 50)
    print("🎉 피드백 API 테스트 완료")

if __name__ == "__main__":
    main() 