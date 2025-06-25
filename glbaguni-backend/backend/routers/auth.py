#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication Router
JWT 기반 인증 및 사용자 관리 엔드포인트
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

# 내부 모듈 임포트
from backend.database import get_db
from backend.models import User, UserCreate, UserRead
from backend.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_access_token,
    decode_refresh_token,
)

# CAPTCHA 검증 임포트
try:
    from utils.captcha_validator import (
        CaptchaRequest, 
        CaptchaResponse, 
        captcha_validator
    )
except ImportError:
    from backend.utils.captcha_validator import (
        CaptchaRequest, 
        CaptchaResponse, 
        captcha_validator
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
async def register(
    request: Request,
    user_data: UserCreate, 
    captcha_data: CaptchaRequest,
    db: Session = Depends(get_db)
):
    """
    새로운 사용자를 등록합니다.
    
    Args:
        request: FastAPI Request 객체
        user_data: 사용자 생성 데이터 (username, email, password, birth_year, gender, interests)
        captcha_data: CAPTCHA 검증 데이터
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
            "interests": ["음악", "산책"],
            "recaptcha_token": "03AGdBq25...",
            "math_challenge_id": "abc123",
            "math_answer": 15
        }
    """
    logger.info(f"회원가입 요청: username={user_data.username}")
    
    # CAPTCHA 검증
    captcha_result = await captcha_validator.validate_request(
        request, 
        captcha_data, 
        "/auth/register"
    )
    
    if not captcha_result.success:
        logger.warning(f"회원가입 CAPTCHA 검증 실패: {captcha_result.message}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"봇 방지 검증 실패: {captcha_result.message}"
        )
    
    logger.info(f"회원가입 CAPTCHA 검증 성공: username={user_data.username}")
    
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
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    captcha_data: CaptchaRequest = CaptchaRequest(),
    db: Session = Depends(get_db)
):
    """
    사용자 로그인을 처리합니다.
    
    Args:
        request: FastAPI Request 객체
        form_data: OAuth2 폼 데이터 (username 필드에 이메일 또는 사용자명 입력)
        captcha_data: CAPTCHA 검증 데이터
        db: 데이터베이스 세션
        
    Returns:
        dict: 로그인 결과 및 JWT 토큰
        
    Example:
        POST /auth/login (form-data)
        username=user@email.com&password=StrongPass123!
        또는
        username=user123&password=StrongPass123!
        
        추가로 CAPTCHA 데이터도 함께 전송:
        {
            "recaptcha_token": "03AGdBq25...",
            "math_challenge_id": "abc123",
            "math_answer": 15
        }
    """
    logger.info(f"로그인 요청: email_or_username={form_data.username}")
    
    # CAPTCHA 검증 (로그인 실패가 많은 경우에만 적용)
    client_id = captcha_validator.get_client_identifier(request)
    client_failures = len(captcha_validator.failure_tracker.get(client_id, []))
    
    # 실패 기록이 3회 이상인 경우 CAPTCHA 검증 강제
    if client_failures >= 3 or captcha_data.recaptcha_token or captcha_data.math_challenge_id:
        captcha_result = await captcha_validator.validate_request(
            request, 
            captcha_data, 
            "/auth/login"
        )
        
        if not captcha_result.success:
            logger.warning(f"로그인 CAPTCHA 검증 실패: {captcha_result.message}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"봇 방지 검증 실패: {captcha_result.message}"
            )
        
        logger.info(f"로그인 CAPTCHA 검증 성공: username={form_data.username}")
    
    # 사용자 인증 (form_data.username을 이메일 또는 사용자명으로 처리)
    auth_result = authenticate_user(db, form_data.username, form_data.password)
    
    if not auth_result["success"]:
        logger.warning(f"로그인 실패: {auth_result['message']}")
        
        # 로그인 실패 기록 (CAPTCHA 검증용)
        captcha_validator.record_failure(client_id)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth_result["message"],
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # JWT 토큰 생성 (액세스 토큰과 리프레시 토큰)
    user_id = str(auth_result["user"]["id"])
    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})
    
    logger.info(f"로그인 성공: username={form_data.username}, user_id={auth_result['user']['id']}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": auth_result["user"]["id"],
            "username": auth_result["user"]["username"]
        }
    }


@router.post("/refresh", response_model=dict)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급받습니다.
    
    Args:
        refresh_token: JWT 리프레시 토큰
        db: 데이터베이스 세션
        
    Returns:
        dict: 새로운 액세스 토큰
        
    Example:
        POST /auth/refresh
        {
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGci..."
        }
    """
    logger.info("토큰 새로고침 요청")
    
    # 리프레시 토큰 검증
    user_id = decode_refresh_token(refresh_token)
    if user_id is None:
        logger.warning("리프레시 토큰 검증 실패")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 리프레시 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 사용자 존재 확인
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logger.warning(f"사용자를 찾을 수 없음: user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 새로운 액세스 토큰 생성
    new_access_token = create_access_token(data={"sub": str(user_id)})
    
    logger.info(f"토큰 새로고침 성공: user_id={user_id}")
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
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
            "refresh": "POST /auth/refresh",
            "me": "GET /auth/me"
        }
    }
