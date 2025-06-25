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
        user_data: 사용자 생성 데이터 (username, email, password, birth_year, gender, interests)
        db: 데이터베이스 세션
        
    Returns:
        dict: 등록 결과
        
    Example:
        POST /auth/register
        {
            "username": "user123",
            "email": "user@email.com",
            "password": "StrongPass123!",
            "birth_year": 1990,
            "gender": "남성",
            "interests": ["음악", "산책"]
        }
    """
    logger.info(f"회원가입 요청: username={user_data.username}")
    
    # 사용자 생성
    result = create_user(
        db, 
        user_data.username,
        user_data.email, 
        user_data.password, 
        user_data.birth_year,
        user_data.gender,
        user_data.interests
    )
    
    if not result["success"]:
        logger.warning(f"회원가입 실패: {result['message']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    logger.info(f"회원가입 성공: username={user_data.username}, user_id={result['user']['id']}")
    
    return {
        "success": True,
        "message": "회원가입이 완료되었습니다.",
        "user": result["user"]
    }


@router.post("/login", response_model=dict)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    사용자 로그인을 처리합니다.
    
    Args:
        form_data: OAuth2 폼 데이터 (username 필드에 이메일 또는 사용자명 입력)
        db: 데이터베이스 세션
        
    Returns:
        dict: 로그인 결과 및 JWT 토큰
        
    Example:
        POST /auth/login (form-data)
        username=user@email.com&password=StrongPass123!
        또는
        username=user123&password=StrongPass123!
    """
    logger.info(f"로그인 요청: email_or_username={form_data.username}")
    
    # 사용자 인증 (form_data.username을 이메일 또는 사용자명으로 처리)
    auth_result = authenticate_user(db, form_data.username, form_data.password)
    
    if not auth_result["success"]:
        logger.warning(f"로그인 실패: {auth_result['message']}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth_result["message"],
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # JWT 토큰 생성
    access_token = create_access_token(data={"sub": str(auth_result["user"]["id"])})
    
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
        username=current_user.username,
        email=current_user.email,
        birth_year=current_user.birth_year,
        gender=current_user.gender,
        interests=current_user.interests
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
