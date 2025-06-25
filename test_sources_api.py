#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sources API 테스트 스크립트
"""

import requests
import json

def test_sources_api():
    """Sources API를 테스트합니다."""
    base_url = "http://localhost:8003"
    
    print("🔍 Sources API 테스트 시작...\n")
    
    # 1. 전체 언론사 목록 조회
    print("1. 전체 언론사 목록 조회")
    print("-" * 50)
    try:
        response = requests.get(f"{base_url}/sources/")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Message: {data['message']}")
            print(f"Total Count: {data['total_count']}")
            print("\n첫 3개 언론사:")
            for i, source in enumerate(data['sources'][:3]):
                print(f"  {i+1}. {source['name']} ({source['category']}) - {source['rss_url']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("\n" + "="*70 + "\n")
    
    # 2. IT 카테고리 필터링
    print("2. IT 카테고리 언론사 조회")
    print("-" * 50)
    try:
        response = requests.get(f"{base_url}/sources/?category=IT")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Message: {data['message']}")
            print(f"Total Count: {data['total_count']}")
            print("\nIT 언론사:")
            for i, source in enumerate(data['sources']):
                print(f"  {i+1}. {source['name']} - {source['rss_url']}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("\n" + "="*70 + "\n")
    
    # 3. 카테고리 목록 조회
    print("3. 카테고리 목록 조회")
    print("-" * 50)
    try:
        response = requests.get(f"{base_url}/sources/categories")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data['success']}")
            print(f"Message: {data['message']}")
            print(f"Total Count: {data['total_count']}")
            print(f"Categories: {', '.join(data['categories'])}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")
    
    print("\n" + "="*70 + "\n")
    
    # 4. 헬스체크
    print("4. Sources 헬스체크")
    print("-" * 50)
    try:
        response = requests.get(f"{base_url}/sources/health")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Status: {data['status']}")
            print(f"Service: {data['service']}")
            print(f"Total Sources: {data['total_sources']}")
            print(f"Available Categories: {', '.join(data['available_categories'])}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_sources_api() 