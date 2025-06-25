# 🚀 글바구니 서버 실행 가이드

## 문제 예방을 위한 권장 실행 순서

### 1. 환경 준비
```bash
# 1-1. 가상환경 활성화
cd glbaguni-backend
source .venv/bin/activate  # Linux/Mac
# 또는
.venv\Scripts\activate     # Windows

# 1-2. 의존성 설치
pip install -r requirements.txt

# 1-3. 환경변수 설정 확인
python -c "
import os
required = ['OPENAI_API_KEY', 'SMTP_USERNAME', 'SMTP_PASSWORD']
for var in required:
    status = '✅' if os.getenv(var) else '❌'
    print(f'{status} {var}')
"
```

### 2. 백엔드 서버 실행
```bash
# 권장 명령어 (포트 8003 사용)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8003 --reload

# 또는 다른 포트 사용
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
```

### 3. 프론트엔드 서버 실행 (새 터미널)
```bash
cd ../glbaguni-frontend

# 환경변수 설정 (백엔드 포트에 맞춰 수정)
echo "VITE_API_BASE=http://127.0.0.1:8003" > .env.local

# 서버 실행
npm run dev
```

### 4. 동작 확인
- 백엔드: http://localhost:8003/health
- 프론트엔드: http://localhost:5173 (또는 Vite가 할당한 포트)

## 🛠️ 문제 해결 가이드

### 포트 충돌 문제
```bash
# 사용 중인 포트 확인
netstat -an | grep :8003

# 다른 포트 사용
python -m uvicorn backend.main:app --port 8004 --reload

# 프론트엔드 환경변수도 수정
echo "VITE_API_BASE=http://127.0.0.1:8004" > ../glbaguni-frontend/.env.local
```

### import 에러 발생 시
```bash
# Python 경로 확인
python -c "import sys; print('\n'.join(sys.path))"

# 모듈 재설치
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### 컴포넌트 초기화 실패 시
```bash
# 문제 진단 스크립트 실행
python problem_prevention.py

# 결과 파일 확인
cat problem_prevention_results.json
```

### 라우터 등록 실패 시
```bash
# 라우터 파일 검증
python -c "
import os
router_dir = 'backend/routers'
for f in os.listdir(router_dir):
    if f.endswith('.py') and f != '__init__.py':
        print(f'✓ {f}')
"
```

## 📊 성능 모니터링

### 서버 상태 확인
```bash
# 상세 헬스체크
curl http://localhost:8003/health/detailed

# 컴포넌트 상태 확인
curl http://localhost:8003/status/services
```

### 로그 모니터링
```bash
# 실시간 로그 확인
tail -f logs/glbaguni.log

# 에러 로그만 확인
grep ERROR logs/glbaguni.log
```

## 🚨 비상 복구 절차

### 1. 서버 재시작
```bash
# 프로세스 종료
pkill -f "uvicorn backend.main"  # Linux/Mac
# Windows에서는 Ctrl+C 또는 터미널 종료

# 깨끗한 재시작
python -m uvicorn backend.main:app --port 8003 --reload
```

### 2. 데이터베이스 초기화
```bash
# 데이터베이스 파일 삭제 (필요한 경우만)
rm glbaguni.db

# 서버 재시작으로 자동 재생성
python -m uvicorn backend.main:app --port 8003 --reload
```

### 3. 캐시 정리
```bash
# Python 캐시 정리
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# 프론트엔드 캐시 정리
cd ../glbaguni-frontend
rm -rf node_modules/.cache
npm run dev
```

## 📋 체크리스트

### 서버 실행 전
- [ ] 가상환경 활성화됨
- [ ] 의존성 설치 완료
- [ ] 환경변수 설정 확인
- [ ] 포트 사용 가능 확인

### 서버 실행 후
- [ ] 백엔드 헬스체크 성공 (200 OK)
- [ ] 프론트엔드 로딩 성공
- [ ] API 연결 확인 (Network 탭)
- [ ] 에러 로그 없음 확인

### 문제 발생 시
- [ ] 문제 예방 스크립트 실행
- [ ] 로그 파일 확인
- [ ] 포트 변경 시도
- [ ] 의존성 재설치

## 🔧 자동화 스크립트

### 전체 시스템 시작
```bash
#!/bin/bash
# start_all.sh

echo "🚀 글바구니 시스템 시작..."

# 백엔드 시작
cd glbaguni-backend
source .venv/bin/activate
python -m uvicorn backend.main:app --port 8003 --reload &

# 프론트엔드 시작 (3초 후)
sleep 3
cd ../glbaguni-frontend
npm run dev &

echo "✅ 시스템 시작 완료!"
echo "백엔드: http://localhost:8003"
echo "프론트엔드: http://localhost:5173"
```

### 문제 진단 및 수정
```bash
#!/bin/bash
# diagnose_and_fix.sh

echo "🔍 문제 진단 시작..."

cd glbaguni-backend
python problem_prevention.py

if [ $? -eq 0 ]; then
    echo "✅ 시스템 정상"
else
    echo "⚠️ 문제 발견, 자동 수정 시도..."
    
    # 포트 변경
    echo "VITE_API_BASE=http://127.0.0.1:8004" > ../glbaguni-frontend/.env.local
    
    # 서버 재시작
    python -m uvicorn backend.main:app --port 8004 --reload
fi
``` 