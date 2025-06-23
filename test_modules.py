#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""모듈 임포트 테스트"""

def test_imports():
    try:
        print("=== 모듈 임포트 테스트 ===")
        
        # 라우터 테스트
        from glbaguni.backend.routers.summarize import router
        print("✓ Summarize 라우터 임포트 성공")
        print(f"  - 라우터 prefix: {router.prefix}")
        print(f"  - 라우터 tags: {router.tags}")
        
        # GPT 서비스 테스트
        from glbaguni.backend.services.gpt import GPTService
        print("✓ GPT 서비스 임포트 성공")
        
        # Validator 테스트
        from glbaguni.backend.utils.validator import validate_and_sanitize_text
        print("✓ Validator 유틸리티 임포트 성공")
        
        print("\n모든 모듈이 성공적으로 로드되었습니다!")
        return True
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_imports() 