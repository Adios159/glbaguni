#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
개선된 FastAPI 요약 서비스 예시
사용자 제공 코드를 기반으로 실제 운영 환경에 적합하게 개선
"""

import os
import re
import time
import uuid
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

app = FastAPI(
    title="Improved Summarization API",
    description="보안과 로깅이 강화된 요약 서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 보안 설정
API_KEY = os.getenv("API_KEY", "demo_secret_key_123")
security = HTTPBearer()

# 요청/응답 모델
class SummarizeRequest(BaseModel):
    content: str
    language: str = "ko"
    max_length: Optional[int] = 500

class SummarizeResponse(BaseModel):
    success: bool
    summary: str
    request_id: str
    processed_at: str
    metadata: dict

# 의존성 함수
async def verify_api_key(request: Request) -> str:
    """API 키 검증 의존성"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    print(f"🔐 [보안] API 키 인증 시작 - ID: {request_id}")
    
    api_key = request.headers.get("x-api-key")
    if not api_key or api_key != API_KEY:
        print(f"❌ [보안 오류] API 키가 누락되었거나 유효하지 않음 - ID: {request_id}")
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    
    print(f"✅ [보안] API 키 인증 성공 - ID: {request_id}")
    return api_key

def validate_content(content: str, request_id: str) -> str:
    """콘텐츠 검증 함수"""
    print(f"🔎 [검증] 사용자 입력 검증 시작 - ID: {request_id}")
    
    # 빈 콘텐츠 체크
    if not content or not content.strip():
        print(f"❌ [검증 오류] 입력된 콘텐츠가 없음 - ID: {request_id}")
        raise HTTPException(status_code=400, detail="Content is required")
    
    # 길이 제한
    if len(content) > 10000:
        print(f"❌ [검증 오류] 콘텐츠가 너무 김: {len(content)}자 - ID: {request_id}")
        raise HTTPException(status_code=400, detail="Content too long (max 10000 characters)")
    
    # 악성 콘텐츠 검사
    if re.search(r'<script|javascript:|data:|vbscript:', content, re.IGNORECASE):
        print(f"❌ [검증 오류] 잠재적 악성 콘텐츠 감지 - ID: {request_id}")
        raise HTTPException(status_code=400, detail="Potentially malicious content detected")
    
    print(f"🔎 [검증] 사용자 입력 검증 완료 - ID: {request_id}, 길이: {len(content)}자")
    return content.strip()

async def generate_summary(content: str, language: str, request_id: str) -> str:
    """실제 요약 생성 함수 (GPT 서비스 연동 예시)"""
    print(f"⚙️ [처리] 요약 모델 실행 시작 - ID: {request_id}")
    
    try:
        # 실제 환경에서는 OpenAI API나 다른 요약 서비스 호출
        # 여기서는 데모용 로직
        
        # 간단한 요약 로직 (실제로는 GPT API 호출)
        words = content.split()
        if language == "ko":
            summary = f"요약: {' '.join(words[:20])}..." if len(words) > 20 else f"요약: {content}"
        else:
            summary = f"Summary: {' '.join(words[:20])}..." if len(words) > 20 else f"Summary: {content}"
        
        # 처리 시간 시뮬레이션
        await asyncio.sleep(0.5)
        
        print(f"✅ [완료] 요약 결과 생성 완료 - ID: {request_id}")
        return summary
        
    except Exception as e:
        print(f"❌ [처리 오류] 요약 생성 실패 - ID: {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """모든 요청에 고유 ID 추가"""
    request.state.request_id = str(uuid.uuid4())[:8]
    response = await call_next(request)
    return response

@app.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    request: Request,
    data: SummarizeRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    📋 향상된 요약 엔드포인트
    
    - API 키 인증 필수
    - 단계별 로깅
    - 강화된 입력 검증
    - 구조화된 응답
    """
    request_id = request.state.request_id
    start_time = time.time()
    
    try:
        # 1. 요청 수신
        print(f"📥 [요약요청] 사용자 입력 수신 완료 - ID: {request_id}")
        
        # 2. 입력 검증
        validated_content = validate_content(data.content, request_id)
        
        # 3. 요약 처리
        summary = await generate_summary(validated_content, data.language, request_id)
        
        # 4. 응답 생성
        processing_time = time.time() - start_time
        
        response_data = SummarizeResponse(
            success=True,
            summary=summary,
            request_id=request_id,
            processed_at=datetime.now().isoformat(),
            metadata={
                "original_length": len(validated_content),
                "summary_length": len(summary),
                "processing_time_seconds": round(processing_time, 3),
                "language": data.language,
                "compression_ratio": round((1 - len(summary) / len(validated_content)) * 100, 2) if validated_content else 0
            }
        )
        
        # 5. 응답 전송
        print(f"📤 [응답] 클라이언트에 응답 전송 - ID: {request_id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [오류] 요약 처리 중 예상치 못한 오류 발생 - ID: {request_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """서비스 상태 확인"""
    return {
        "status": "healthy",
        "service": "summarization-api",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "api_key_authentication",
            "step_by_step_logging", 
            "enhanced_input_validation",
            "structured_responses",
            "request_tracking"
        ]
    }

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Improved Summarization API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 