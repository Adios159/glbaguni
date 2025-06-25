#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
글바구니 (Glbaguni) 문제 예방 스크립트
=================================

이 스크립트는 다음과 같은 문제들을 예방합니다:
1. 포트 충돌 문제
2. import 에러
3. 환경변수 누락
4. 컴포넌트 초기화 실패
5. 라우터 등록 오류
"""

import os
import sys
import subprocess
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

class ProblemPrevention:
    """문제 예방을 위한 종합 검증 도구"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.project_root = Path(__file__).parent
        self.results = {
            "timestamp": time.time(),
            "checks": {},
            "recommendations": [],
            "critical_issues": [],
            "warnings": []
        }
    
    def _setup_logging(self) -> logging.Logger:
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('problem_prevention.log')
            ]
        )
        return logging.getLogger("problem_prevention")
    
    def run_all_checks(self) -> Dict[str, Any]:
        """모든 검증 실행"""
        self.logger.info("🔍 글바구니 문제 예방 검증 시작...")
        
        checks = [
            ("포트 검증", self.check_ports),
            ("환경변수 검증", self.check_environment_variables),
            ("Python 의존성 검증", self.check_python_dependencies),
            ("파일 구조 검증", self.check_file_structure),
            ("import 경로 검증", self.check_import_paths),
            ("설정 파일 검증", self.check_config_files),
            ("라우터 파일 검증", self.check_router_files),
            ("컴포넌트 초기화 검증", self.check_component_initialization)
        ]
        
        for check_name, check_func in checks:
            try:
                self.logger.info(f"  ⏳ {check_name} 진행 중...")
                result = check_func()
                self.results["checks"][check_name] = result
                
                if result.get("status") == "success":
                    self.logger.info(f"  ✅ {check_name} 완료")
                elif result.get("status") == "warning":
                    self.logger.warning(f"  ⚠️ {check_name} 경고: {result.get('message', '')}")
                    self.results["warnings"].append(f"{check_name}: {result.get('message', '')}")
                else:
                    self.logger.error(f"  ❌ {check_name} 실패: {result.get('message', '')}")
                    self.results["critical_issues"].append(f"{check_name}: {result.get('message', '')}")
                    
            except Exception as e:
                self.logger.error(f"  💥 {check_name} 검증 중 오류: {e}")
                self.results["critical_issues"].append(f"{check_name}: 검증 중 오류 - {str(e)}")
        
        # 권장사항 생성
        self._generate_recommendations()
        
        # 결과 저장
        self._save_results()
        
        self.logger.info("🎉 문제 예방 검증 완료!")
        return self.results
    
    def check_ports(self) -> Dict[str, Any]:
        """포트 사용 현황 검증"""
        try:
            import socket
            
            ports_to_check = [8000, 8001, 8002, 8003, 5173, 5174, 5175, 5176, 5177, 5178]
            port_status = {}
            
            for port in ports_to_check:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                port_status[port] = "사용중" if result == 0 else "사용가능"
            
            used_ports = [p for p, status in port_status.items() if status == "사용중"]
            
            return {
                "status": "warning" if used_ports else "success",
                "message": f"사용 중인 포트: {used_ports}" if used_ports else "모든 포트 사용 가능",
                "data": port_status,
                "recommendations": [
                    "백엔드는 8003 포트 사용 권장",
                    "프론트엔드는 Vite 자동 할당 포트 사용",
                    "포트 충돌 시 다른 포트로 변경 필요"
                ] if used_ports else []
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"포트 검증 실패: {str(e)}",
                "recommendations": ["포트 검증을 수동으로 수행하세요"]
            }
    
    def check_environment_variables(self) -> Dict[str, Any]:
        """환경변수 설정 검증"""
        required_vars = {
            "OPENAI_API_KEY": "OpenAI API 키 (요약 기능용)",
            "SMTP_USERNAME": "이메일 SMTP 사용자명",
            "SMTP_PASSWORD": "이메일 SMTP 비밀번호"
        }
        
        optional_vars = {
            "DATABASE_URL": "데이터베이스 연결 URL",
            "REDIS_URL": "Redis 연결 URL",
            "LOG_LEVEL": "로그 레벨 설정"
        }
        
        missing_required = []
        missing_optional = []
        configured = []
        
        for var, desc in required_vars.items():
            if os.getenv(var):
                configured.append(f"{var}: {desc}")
            else:
                missing_required.append(f"{var}: {desc}")
        
        for var, desc in optional_vars.items():
            if os.getenv(var):
                configured.append(f"{var}: {desc}")
            else:
                missing_optional.append(f"{var}: {desc}")
        
        # 프론트엔드 환경변수 검증
        frontend_env_file = self.project_root.parent / "glbaguni-frontend" / ".env.local"
        frontend_env_exists = frontend_env_file.exists()
        
        status = "error" if missing_required else ("warning" if missing_optional else "success")
        
        return {
            "status": status,
            "message": f"필수 환경변수 {len(missing_required)}개 누락, 선택적 {len(missing_optional)}개 누락",
            "data": {
                "configured": configured,
                "missing_required": missing_required,
                "missing_optional": missing_optional,
                "frontend_env_exists": frontend_env_exists
            },
            "recommendations": [
                "누락된 필수 환경변수를 .env 파일에 설정하세요",
                "프론트엔드 .env.local 파일을 생성하여 VITE_API_BASE를 설정하세요" if not frontend_env_exists else None
            ]
        }
    
    def check_python_dependencies(self) -> Dict[str, Any]:
        """Python 의존성 검증"""
        try:
            requirements_file = self.project_root / "requirements.txt"
            
            if not requirements_file.exists():
                return {
                    "status": "warning",
                    "message": "requirements.txt 파일이 존재하지 않습니다",
                    "recommendations": ["requirements.txt 파일을 생성하세요"]
                }
            
            # 설치된 패키지 확인
            result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=json"], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                return {
                    "status": "error",
                    "message": "pip list 실행 실패",
                    "recommendations": ["Python 환경을 확인하세요"]
                }
            
            installed_packages = {pkg["name"].lower(): pkg["version"] for pkg in json.loads(result.stdout)}
            
            # 핵심 의존성 확인
            critical_deps = ["fastapi", "uvicorn", "openai", "requests", "sqlalchemy"]
            missing_deps = [dep for dep in critical_deps if dep not in installed_packages]
            
            return {
                "status": "error" if missing_deps else "success",
                "message": f"누락된 핵심 의존성: {missing_deps}" if missing_deps else "모든 핵심 의존성 설치됨",
                "data": {
                    "installed_count": len(installed_packages),
                    "missing_critical": missing_deps,
                    "critical_installed": [dep for dep in critical_deps if dep in installed_packages]
                },
                "recommendations": [
                    "pip install -r requirements.txt 실행하여 의존성 설치" if missing_deps else None
                ]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"의존성 검증 실패: {str(e)}",
                "recommendations": ["수동으로 의존성을 확인하세요"]
            }
    
    def check_file_structure(self) -> Dict[str, Any]:
        """파일 구조 검증"""
        critical_files = [
            "backend/main.py",
            "backend/routers/health.py",
            "backend/routers/core.py",
            "backend/routers/summarize.py",
            "backend/utils/component_manager.py",
            "backend/utils/logging_config.py"
        ]
        
        optional_files = [
            "backend/routers/auth.py",
            "backend/routers/news.py",
            "backend/routers/fetch.py",
            "backend/routers/history_router.py",
            "backend/routers/sources.py"
        ]
        
        missing_critical = []
        missing_optional = []
        existing_files = []
        
        for file_path in critical_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                missing_critical.append(file_path)
        
        for file_path in optional_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                missing_optional.append(file_path)
        
        return {
            "status": "error" if missing_critical else ("warning" if missing_optional else "success"),
            "message": f"필수 파일 {len(missing_critical)}개 누락, 선택적 파일 {len(missing_optional)}개 누락",
            "data": {
                "existing_files": existing_files,
                "missing_critical": missing_critical,
                "missing_optional": missing_optional
            },
            "recommendations": [
                "누락된 필수 파일들을 생성하거나 복원하세요" if missing_critical else None
            ]
        }
    
    def check_import_paths(self) -> Dict[str, Any]:
        """import 경로 검증"""
        try:
            # 주요 모듈들의 import 테스트
            import_tests = [
                ("backend.main", "메인 애플리케이션"),
                ("backend.utils.component_manager", "컴포넌트 매니저"),
                ("backend.utils.logging_config", "로깅 설정"),
                ("backend.routers.health", "헬스체크 라우터")
            ]
            
            successful_imports = []
            failed_imports = []
            
            for module_name, description in import_tests:
                try:
                    __import__(module_name)
                    successful_imports.append(f"{module_name}: {description}")
                except ImportError as e:
                    failed_imports.append(f"{module_name}: {description} - {str(e)}")
            
            return {
                "status": "error" if failed_imports else "success",
                "message": f"import 실패: {len(failed_imports)}개",
                "data": {
                    "successful": successful_imports,
                    "failed": failed_imports
                },
                "recommendations": [
                    "실패한 import들의 경로와 의존성을 확인하세요" if failed_imports else None
                ]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"import 검증 실패: {str(e)}",
                "recommendations": ["Python 경로 설정을 확인하세요"]
            }
    
    def check_config_files(self) -> Dict[str, Any]:
        """설정 파일 검증"""
        config_files = {
            "pyproject.toml": "Python 프로젝트 설정",
            "requirements.txt": "Python 의존성",
            "../glbaguni-frontend/package.json": "프론트엔드 의존성",
            "../glbaguni-frontend/vite.config.js": "Vite 설정"
        }
        
        existing_configs = []
        missing_configs = []
        
        for file_path, description in config_files.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                existing_configs.append(f"{file_path}: {description}")
            else:
                missing_configs.append(f"{file_path}: {description}")
        
        return {
            "status": "warning" if missing_configs else "success",
            "message": f"설정 파일 {len(missing_configs)}개 누락",
            "data": {
                "existing": existing_configs,
                "missing": missing_configs
            },
            "recommendations": [
                "누락된 설정 파일들을 생성하세요" if missing_configs else None
            ]
        }
    
    def check_router_files(self) -> Dict[str, Any]:
        """라우터 파일들의 구조 검증"""
        router_dir = self.project_root / "backend" / "routers"
        
        if not router_dir.exists():
            return {
                "status": "error",
                "message": "routers 디렉토리가 존재하지 않습니다",
                "recommendations": ["routers 디렉토리를 생성하세요"]
            }
        
        router_files = list(router_dir.glob("*.py"))
        router_info = []
        
        for router_file in router_files:
            if router_file.name == "__init__.py":
                continue
                
            try:
                content = router_file.read_text(encoding='utf-8')
                has_router = "router" in content and "APIRouter" in content
                has_fastapi_import = "fastapi" in content or "APIRouter" in content
                
                router_info.append({
                    "file": router_file.name,
                    "has_router": has_router,
                    "has_fastapi_import": has_fastapi_import,
                    "status": "ok" if has_router and has_fastapi_import else "needs_review"
                })
                
            except Exception as e:
                router_info.append({
                    "file": router_file.name,
                    "error": str(e),
                    "status": "error"
                })
        
        problematic_routers = [r for r in router_info if r.get("status") != "ok"]
        
        return {
            "status": "warning" if problematic_routers else "success",
            "message": f"문제가 있는 라우터 파일: {len(problematic_routers)}개",
            "data": {
                "all_routers": router_info,
                "problematic": problematic_routers
            },
            "recommendations": [
                "문제가 있는 라우터 파일들을 검토하고 수정하세요" if problematic_routers else None
            ]
        }
    
    def check_component_initialization(self) -> Dict[str, Any]:
        """컴포넌트 초기화 로직 검증"""
        try:
            component_manager_file = self.project_root / "backend" / "utils" / "component_manager.py"
            
            if not component_manager_file.exists():
                return {
                    "status": "error",
                    "message": "component_manager.py 파일이 존재하지 않습니다",
                    "recommendations": ["컴포넌트 매니저 파일을 생성하세요"]
                }
            
            content = component_manager_file.read_text(encoding='utf-8')
            
            # 중요한 함수들 존재 여부 확인
            important_functions = [
                "initialize_all_components",
                "get_component_status",
                "safe_initialize_component",
                "cleanup_components"
            ]
            
            missing_functions = []
            existing_functions = []
            
            for func in important_functions:
                if f"def {func}" in content or f"async def {func}" in content:
                    existing_functions.append(func)
                else:
                    missing_functions.append(func)
            
            return {
                "status": "warning" if missing_functions else "success",
                "message": f"누락된 중요 함수: {len(missing_functions)}개",
                "data": {
                    "existing_functions": existing_functions,
                    "missing_functions": missing_functions
                },
                "recommendations": [
                    "누락된 컴포넌트 관리 함수들을 구현하세요" if missing_functions else None
                ]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"컴포넌트 초기화 검증 실패: {str(e)}",
                "recommendations": ["컴포넌트 매니저 파일을 수동으로 확인하세요"]
            }
    
    def _generate_recommendations(self):
        """검증 결과를 바탕으로 권장사항 생성"""
        recommendations = []
        
        # 환경변수 설정 가이드
        if any("환경변수" in issue for issue in self.results["critical_issues"]):
            recommendations.append({
                "priority": "high",
                "category": "환경설정",
                "title": "환경변수 설정 완료",
                "description": ".env 파일에 필수 환경변수들을 설정하세요",
                "commands": [
                    "cp env_template.txt .env",
                    "# .env 파일을 편집하여 실제 값들을 입력하세요"
                ]
            })
        
        # 프론트엔드 환경변수 설정
        if not (self.project_root.parent / "glbaguni-frontend" / ".env.local").exists():
            recommendations.append({
                "priority": "medium",
                "category": "프론트엔드",
                "title": "프론트엔드 환경변수 설정",
                "description": "프론트엔드 API 주소를 환경변수로 설정하세요",
                "commands": [
                    "cd ../glbaguni-frontend",
                    "echo 'VITE_API_BASE=http://127.0.0.1:8003' > .env.local"
                ]
            })
        
        # 서버 실행 가이드
        recommendations.append({
            "priority": "low",
            "category": "운영",
            "title": "안정적인 서버 실행 방법",
            "description": "권장되는 서버 실행 순서를 따르세요",
            "commands": [
                "# 1. 백엔드 실행",
                "cd glbaguni-backend",
                "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8003 --reload",
                "",
                "# 2. 프론트엔드 실행 (새 터미널)",
                "cd glbaguni-frontend",
                "npm run dev"
            ]
        })
        
        self.results["recommendations"] = recommendations
    
    def _save_results(self):
        """검증 결과를 파일에 저장"""
        results_file = self.project_root / "problem_prevention_results.json"
        
        try:
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"📄 검증 결과가 {results_file}에 저장되었습니다")
            
        except Exception as e:
            self.logger.error(f"결과 저장 실패: {e}")
    
    def print_summary(self):
        """검증 결과 요약 출력"""
        print("\n" + "="*80)
        print("🛡️  글바구니 문제 예방 검증 결과 요약")
        print("="*80)
        
        total_checks = len(self.results["checks"])
        successful_checks = sum(1 for check in self.results["checks"].values() if check.get("status") == "success")
        warning_checks = sum(1 for check in self.results["checks"].values() if check.get("status") == "warning")
        error_checks = sum(1 for check in self.results["checks"].values() if check.get("status") == "error")
        
        print(f"📊 총 검증 항목: {total_checks}")
        print(f"✅ 성공: {successful_checks}")
        print(f"⚠️  경고: {warning_checks}")
        print(f"❌ 오류: {error_checks}")
        
        if self.results["critical_issues"]:
            print(f"\n❌ 심각한 문제 ({len(self.results['critical_issues'])}개):")
            for issue in self.results["critical_issues"]:
                print(f"   • {issue}")
        
        if self.results["warnings"]:
            print(f"\n⚠️  경고 사항 ({len(self.results['warnings'])}개):")
            for warning in self.results["warnings"]:
                print(f"   • {warning}")
        
        if self.results["recommendations"]:
            print(f"\n💡 권장사항 ({len(self.results['recommendations'])}개):")
            for rec in self.results["recommendations"]:
                print(f"   📌 [{rec['priority'].upper()}] {rec['title']}")
                print(f"      {rec['description']}")
        
        print("\n" + "="*80)


def main():
    """메인 실행 함수"""
    prevention = ProblemPrevention()
    
    try:
        results = prevention.run_all_checks()
        prevention.print_summary()
        
        # 자동 수정 제안
        if results["critical_issues"]:
            print("\n🔧 자동 수정을 시도하시겠습니까? (y/n): ", end="")
            if input().lower() == 'y':
                prevention.auto_fix_issues()
        
        return 0 if not results["critical_issues"] else 1
        
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        return 1
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        return 1


if __name__ == "__main__":
    exit(main()) 