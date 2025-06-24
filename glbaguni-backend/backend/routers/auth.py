#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Router
인증 및 보안 관련 엔드포인트
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

# 의존성 임포트
try:
    # Try absolute imports first
    import sys
    import os
    
    # Add the backend directory to the path
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    from config import settings
    from security import sanitize_response, validate_input
    from utils.validator import validate_user_input
except ImportError:
    try:
        # Fallback for package import
        from backend.config import settings
        from backend.security import sanitize_response, validate_input
        from backend.utils.validator import validate_user_input
    except ImportError:
        # Create dummy functions for basic functionality
        from config import settings
        
        def sanitize_response(response):
            return response
        
        def validate_input(text, input_type="general"):
            return str(text) if text else ""
        
        def validate_user_input(text, input_type="general"):
            return str(text) if text else ""

import logging

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/auth", tags=["authentication"])

# API 키 설정 (환경변수에서 가져오기)
API_KEY = os.getenv("API_KEY", "fallback_secret_key")
security = HTTPBearer()

async def verify_api_key(request: Request) -> bool:
    """
    API 키 인증을 수행합니다.
    
    Returns:
        bool: 인증 성공 여부
    """
    request_id = str(uuid.uuid4())[:8]
    
    # 🔐 API 키 인증 시작
    logger.info(f"🔐 [보안] API 키 인증 시작 - ID: {request_id}")
    
    headers = request.headers
    api_key = headers.get("x-api-key")
    
    if not api_key:
        logger.warning(f"❌ [보안 오류] API 키가 누락됨 - ID: {request_id}")
        return False
        
    if api_key != API_KEY:
        logger.warning(f"❌ [보안 오류] 유효하지 않은 API 키 - ID: {request_id}")
        return False
    
    logger.info(f"✅ [보안] API 키 인증 성공 - ID: {request_id}")
    return True

async def get_api_key(request: Request) -> str:
    """
    API 키 의존성 주입 함수
    """
    if not await verify_api_key(request):
        raise HTTPException(
            status_code=403, 
            detail="Invalid or missing API key"
        )
    api_key = request.headers.get("x-api-key")
    if not api_key:
        raise HTTPException(status_code=403, detail="API key is required")
    return api_key

# 요청/응답 모델
class UserRegistrationRequest(BaseModel):
    """사용자 등록 요청"""

    user_id: str
    email: Optional[EmailStr] = None
    preferences: Optional[dict] = None


class TokenValidationRequest(BaseModel):
    """토큰 검증 요청"""

    token: str


class InputValidationRequest(BaseModel):
    """입력 검증 요청"""

    text: str
    input_type: str = "general"


@router.post("/register")
async def register_user(request: UserRegistrationRequest):
    """
    새 사용자를 등록합니다.

    - **user_id**: 고유 사용자 ID
    - **email**: 이메일 주소 (선택사항)
    - **preferences**: 사용자 설정 (선택사항)
    """
    request_id = str(uuid.uuid4())[:8]

    try:
        logger.info(f"👤 [{request_id}] 사용자 등록 요청: {request.user_id}")

        # 사용자 ID 검증
        validated_user_id = validate_user_input(request.user_id, "user_id")

        # 사용자 정보 생성 (여기서는 간단한 구현)
        user_data = {
            "user_id": validated_user_id,
            "email": str(request.email) if request.email else None,
            "preferences": request.preferences or {},
            "created_at": datetime.now().isoformat(),
            "status": "active",
        }

        # 실제로는 데이터베이스에 저장
        logger.info(f"✅ [{request_id}] 사용자 등록 완료: {validated_user_id}")

        return {
            "success": True,
            "message": "사용자가 성공적으로 등록되었습니다.",
            "user_id": validated_user_id,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
        }

    except ValueError as e:
        logger.warning(f"⚠️ [{request_id}] 사용자 등록 실패 - 유효하지 않은 입력: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"💥 [{request_id}] 사용자 등록 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"사용자 등록 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/validate-input")
async def validate_input_endpoint(request: InputValidationRequest):
    """
    사용자 입력을 검증하고 정화합니다.

    - **text**: 검증할 텍스트
    - **input_type**: 입력 유형 (general, url, email, query 등)
    """
    request_id = str(uuid.uuid4())[:8]

    try:
        logger.info(f"🔍 [{request_id}] 입력 검증 요청: {request.input_type}")

        # 입력 검증 및 정화
        validated_text = validate_user_input(request.text, request.input_type)

        # 추가 보안 검사
        is_safe = True
        threats_detected = []

        # 간단한 위협 탐지 (실제로는 더 정교한 검사 필요)
        dangerous_patterns = [
            "<script",
            "javascript:",
            "eval(",
            "document.cookie",
            "DROP TABLE",
            "DELETE FROM",
            "UPDATE SET",
            "--",
            "UNION SELECT",
            "xp_cmdshell",
        ]

        text_lower = request.text.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in text_lower:
                is_safe = False
                threats_detected.append(pattern)

        logger.info(f"✅ [{request_id}] 입력 검증 완료 - 안전: {is_safe}")

        return {
            "success": True,
            "is_safe": is_safe,
            "validated_text": validated_text,
            "original_length": len(request.text),
            "validated_length": len(validated_text),
            "threats_detected": threats_detected,
            "input_type": request.input_type,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
        }

    except ValueError as e:
        logger.warning(f"⚠️ [{request_id}] 입력 검증 실패: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"💥 [{request_id}] 입력 검증 오류: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"입력 검증 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/sanitize-output")
async def sanitize_output_endpoint(request: dict):
    """
    응답 데이터를 정화합니다.

    - **data**: 정화할 데이터 딕셔너리
    """
    request_id = str(uuid.uuid4())[:8]

    try:
        logger.info(f"🧹 [{request_id}] 출력 정화 요청")

        # 응답 데이터 정화
        sanitized_data = sanitize_response(request)

        logger.info(f"✅ [{request_id}] 출력 정화 완료")

        return {
            "success": True,
            "sanitized_data": sanitized_data,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"💥 [{request_id}] 출력 정화 실패: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"출력 정화 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/user/{user_id}")
async def get_user_info(
    user_id: str, credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    사용자 정보를 조회합니다.

    - **user_id**: 조회할 사용자 ID
    """
    request_id = str(uuid.uuid4())[:8]

    try:
        logger.info(f"👤 [{request_id}] 사용자 정보 조회: {user_id}")

        # 사용자 ID 검증
        validated_user_id = validate_user_input(user_id, "user_id")

        # 실제로는 데이터베이스에서 조회
        user_info = {
            "user_id": validated_user_id,
            "status": "active",
            "created_at": "2024-01-01T00:00:00",
            "last_activity": datetime.now().isoformat(),
            "summary_count": 42,
            "preferences": {"language": "ko", "theme": "light"},
        }

        logger.info(f"✅ [{request_id}] 사용자 정보 조회 완료")

        return {
            "success": True,
            "user_info": user_info,
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
        }

    except ValueError as e:
        logger.warning(f"⚠️ [{request_id}] 사용자 조회 실패: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"💥 [{request_id}] 사용자 조회 오류: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"사용자 정보 조회 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/secure-summarize")
async def secure_summarize(
    request: Request,
    api_key: str = Depends(get_api_key)
):
    """
    보안이 강화된 요약 엔드포인트
    """
    request_id = str(uuid.uuid4())[:8]
    
    try:
        # 1. 요청 수신
        logger.info(f"📥 [요약요청] 사용자 입력 수신 완료 - ID: {request_id}")
        
        # 2. 입력 검증 시작
        logger.info(f"🔎 [검증] 사용자 입력 검증 시작 - ID: {request_id}")
        
        body = await request.json()
        content = body.get("content", "").strip()
        
        if not content:
            logger.warning(f"❌ [검증 오류] 입력된 콘텐츠가 없음 - ID: {request_id}")
            raise HTTPException(status_code=400, detail="Content is required")
            
        if len(content) > 10000:  # 길이 제한
            logger.warning(f"❌ [검증 오류] 콘텐츠가 너무 김 - ID: {request_id}")
            raise HTTPException(status_code=400, detail="Content too long")
            
        # 2. 입력 검증 완료
        logger.info(f"🔎 [검증] 사용자 입력 검증 완료 - ID: {request_id}, 길이: {len(content)}자")
        
        # 3. 처리 시작
        logger.info(f"⚙️ [처리] 요약 모델 실행 시작 - ID: {request_id}")
        
        # 실제 요약 로직 (예시)
        summary = f"[{request_id}] 요약 결과: {content[:100]}..."
        
        # 4. 처리 완료
        logger.info(f"✅ [완료] 요약 결과 생성 완료 - ID: {request_id}")
        
        # 5. 응답 전송
        logger.info(f"📤 [응답] 클라이언트에 응답 전송 - ID: {request_id}")
        
        return {
            "success": True,
            "summary": summary,
            "request_id": request_id,
            "processed_at": datetime.now().isoformat(),
            "content_length": len(content),
            "summary_length": len(summary)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [오류] 요약 처리 중 오류 발생 - ID: {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/health")
async def auth_health_check():
    """인증 서비스 헬스체크"""
    return {
        "status": "healthy",
        "service": "auth",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(API_KEY and API_KEY != "fallback_secret_key")
    }
