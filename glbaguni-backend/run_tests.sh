#!/bin/bash

# 글바구니 백엔드 테스트 실행 스크립트

echo "��� 글바구니 백엔드 테스트 및 코드 품질 검사 시작..."

# 1. 환경 설정
echo "��� 의존성 확인 중..."
pip install -r requirements-dev.txt > /dev/null 2>&1

# 2. 코드 형식화
echo "��� 코드 형식화 중..."
black backend/ --line-length 88 --quiet
isort backend/ --profile black --quiet

# 3. 테스트 실행
echo "✅ 단위 테스트 실행 중..."
cd backend
python -m pytest ../tests/ -v --tb=short

# 4. 코드 품질 검사 (주요 오류만)
echo "��� 코드 품질 검사 중..."
flake8 . --max-line-length=88 --ignore=E203,W503,E501,F401,F841,W291 --exclude=logs,__pycache__ --statistics || true

echo "��� 테스트 및 품질 검사 완료!"

