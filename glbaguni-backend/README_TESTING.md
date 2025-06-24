# 글바구니 백엔드 테스트 가이드

## 테스트 실행 방법

### 기본 테스트 실행
```bash
cd backend
python -m pytest ../tests/ -v
```

### 특정 모듈 테스트
```bash
# 모델 테스트
python -m pytest ../tests/test_models.py -v

# 보안 테스트  
python -m pytest ../tests/test_security.py -v
```

### 코드 형식화
```bash
# Black으로 형식화
black backend/ --line-length 88

# Import 정리
isort backend/ --profile black
```

### 코드 품질 검사
```bash
# 스타일 검사
flake8 backend/ --max-line-length=88 --ignore=E203,W503,E501,F401,F841
```

## 테스트 구조
- test_models.py: 데이터 모델 테스트
- test_fetcher.py: RSS/HTML 가져오기 테스트  
- test_security.py: 보안 기능 테스트
- test_summarizer.py: 요약 기능 테스트

## 개발 도구
- pytest: 테스트 프레임워크
- black: 코드 형식화
- isort: Import 정리
- flake8: 스타일 검사
- pylint: 코드 분석

