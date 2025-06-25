#!/usr/bin/env python3
"""
Test script for new User History and Recommendation features.
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_summarize_with_history():
    """Test summarization with user history tracking."""
    print("\n📝 Testing summarization with history tracking...")
    
    payload = {
        "rss_urls": ["https://feeds.bbci.co.uk/news/world/rss.xml"],
        "recipient_email": "test@example.com",
        "language": "ko",
        "max_articles": 2,
        "user_id": "test-user-123"
    }
    
    response = requests.post(f"{BASE_URL}/summarize", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data['success']}")
        print(f"User ID: {data.get('user_id')}")
        print(f"Summaries: {len(data.get('summaries', []))}")
        return data.get('user_id')
    else:
        print(f"Error: {response.text}")
        return None

def test_direct_text_summarization():
    """Test direct text summarization with history."""
    print("\n📄 Testing direct text summarization...")
    
    payload = {
        "text": "This is a test article about artificial intelligence. AI technology is rapidly advancing and changing various industries.",
        "language": "ko",
        "user_id": "test-user-123"
    }
    
    response = requests.post(f"{BASE_URL}/summarize-text", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Summary: {data.get('summary', 'No summary')}")
        print(f"Language: {data.get('language')}")
    else:
        print(f"Error: {response.text}")

def test_user_history(user_id):
    """Test user history retrieval."""
    print("\n📖 Testing user history retrieval...")
    
    params = {
        "user_id": user_id,
        "page": 1,
        "per_page": 10
    }
    
    response = requests.get(f"{BASE_URL}/history", params=params)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data['success']}")
        print(f"Total items: {data['total_items']}")
        print(f"History items: {len(data['history'])}")
        
        for i, item in enumerate(data['history'][:2], 1):  # Show first 2
            print(f"  {i}. {item['article_title']} ({item['summary_language']})")
    else:
        print(f"Error: {response.text}")

def test_recommendations(user_id):
    """Test recommendation generation."""
    print("\n🎯 Testing recommendation generation...")
    
    params = {
        "user_id": user_id,
        "max_recommendations": 5
    }
    
    response = requests.get(f"{BASE_URL}/recommendations", params=params)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data['success']}")
        print(f"Recommendations: {len(data['recommendations'])}")
        print(f"Types: {data['recommendation_types']}")
        
        for i, rec in enumerate(data['recommendations'][:3], 1):  # Show first 3
            print(f"  {i}. {rec['article_title']} (Type: {rec['recommendation_type']}, Score: {rec['recommendation_score']:.2f})")
    else:
        print(f"Error: {response.text}")

def test_user_stats(user_id):
    """Test user statistics."""
    print("\n📊 Testing user statistics...")
    
    params = {"user_id": user_id}
    
    response = requests.get(f"{BASE_URL}/user-stats", params=params)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data['success']}")
        print(f"Total summaries: {data['total_summaries']}")
        print(f"Preferred language: {data['preferred_language']}")
        print(f"Favorite categories: {data['favorite_categories']}")
        print(f"Recent activity items: {len(data['recent_activity'])}")
    else:
        print(f"Error: {response.text}")

def main():
    """Main test function."""
    print("🚀 Testing User History and Recommendation Features")
    print("=" * 60)
    
    # Test health first
    if not test_health():
        print("❌ Health check failed. Make sure the server is running.")
        return
    
    # Test summarization with history
    user_id = test_summarize_with_history()
    if not user_id:
        print("❌ Summarization test failed. Skipping dependent tests.")
        return
    
    # Test direct text summarization
    test_direct_text_summarization()
    
    # Wait a moment for database operations to complete
    print("\n⏳ Waiting 2 seconds for database operations...")
    time.sleep(2)
    
    # Test history retrieval
    test_user_history(user_id)
    
    # Test recommendations
    test_recommendations(user_id)
    
    # Test user stats
    test_user_stats(user_id)
    
    print("\n✅ All tests completed!")
    print("\nNow you can test the frontend by:")
    print("1. Starting the frontend: cd ../glbaguni-frontend && npm run dev")
    print("2. Opening browser to: http://localhost:5173")
    print("3. Testing the new History and Recommendations tabs")

if __name__ == "__main__":
    main()