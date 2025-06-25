#!/usr/bin/env python3
"""
간단한 테스트 서버 - 프론트엔드 연결 테스트용
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="Glbaguni Test Server")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용으로 모든 origin 허용
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "message": "서버가 정상적으로 동작하고 있습니다.",
        "version": "test-1.0.0"
    }

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "Glbaguni Test Server is running!"}

if __name__ == "__main__":
    print("🚀 테스트 서버 시작 중...")
    uvicorn.run(
        "simple_server:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    ) 