#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Router
JWT 기반 인증 및 사용자 관리 엔드포인트
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# 내부 모듈 임포트
from backend.database import get_db
from backend.models import User, UserCreate, UserRead
from backend.security import (
    authenticate_user,
    create_access_token,
    create_user,
    decode_access_token,
)

logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/auth", tags=["authentication"])

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    JWT 토큰으로부터 현재 사용자를 가져옵니다.
    
    Args:
        token: JWT 액세스 토큰
        db: 데이터베이스 세션
        
    Returns:
        User: 현재 사용자 객체
        
    Raises:
        HTTPException: 인증 실패 시
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # JWT 토큰 검증
    user_id = decode_access_token(token)
    if user_id is None:
        logger.warning("JWT 토큰 검증 실패")
        raise credentials_exception
    
    # 사용자 조회 (SQLAlchemy filter 사용으로 SQL 인젝션 방어)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.warning(f"사용자를 찾을 수 없음: user_id={user_id}")
        raise credentials_exception
    
    return user


@router.post("/register", response_model=dict)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    새로운 사용자를 등록합니다.
    
    Args:
        user_data: 사용자 생성 데이터 (username, password)
        db: 데이터베이스 세션
        
    Returns:
        dict: 등록 결과
        
    Example:
        POST /auth/register
        {
            "username": "testuser",
            "password": "password123"
        }
    """
    logger.info(f"회원가입 요청: username={user_data.username}")
    
    # 사용자 생성 (내부적으로 SQLAlchemy filter 사용)
    result = create_user(db, user_data.username, user_data.password)
    
    if not result["success"]:
        logger.warning(f"회원가입 실패: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    logger.info(f"회원가입 성공: username={user_data.username}, user_id={result['user']['id']}")
    
    return {
        "success": True,
        "message": "회원가입이 완료되었습니다.",
        "user": {
            "id": result["user"]["id"],
            "username": result["user"]["username"]
        }
    }


@router.post("/login", response_model=dict)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    사용자 로그인을 처리하고 JWT 토큰을 반환합니다.
    
    Args:
        form_data: OAuth2 표준 로그인 폼 (username, password)
        db: 데이터베이스 세션
        
    Returns:
        dict: JWT 액세스 토큰과 토큰 타입
        
    Example:
        POST /auth/login
        Content-Type: application/x-www-form-urlencoded
        
        username=testuser&password=password123
    """
    logger.info(f"로그인 요청: username={form_data.username}")
    
    # 사용자 인증 (내부적으로 SQLAlchemy filter 사용)
    auth_result = authenticate_user(db, form_data.username, form_data.password)
    
    if not auth_result["success"]:
        logger.warning(f"로그인 실패: username={form_data.username}, error={auth_result['error']}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth_result["error"],
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # JWT 토큰 생성
    access_token = create_access_token(data={"user_id": auth_result["user"]["id"]})
    
    logger.info(f"로그인 성공: username={form_data.username}, user_id={auth_result['user']['id']}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": auth_result["user"]["id"],
            "username": auth_result["user"]["username"]
        }
    }


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    현재 로그인한 사용자의 정보를 조회합니다.
    
    Args:
        current_user: 현재 인증된 사용자 (Dependency Injection)
        
    Returns:
        UserRead: 사용자 정보
        
    Example:
        GET /auth/me
        Authorization: Bearer <jwt_token>
    """
    logger.info(f"사용자 정보 조회: user_id={current_user.id}, username={current_user.username}")
    
    return UserRead(
        id=current_user.id,
        username=current_user.username
    )


@router.get("/health")
async def auth_health_check():
    """
    인증 라우터 헬스체크 엔드포인트
    
    Returns:
        dict: 상태 정보
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "endpoints": {
            "register": "POST /auth/register",
            "login": "POST /auth/login", 
            "me": "GET /auth/me"
        }
    }
