#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로깅 설정 모듈
전체 프로젝트의 로깅을 중앙에서 관리
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional


def setup_comprehensive_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    console_output: bool = True,
    file_output: bool = True,
) -> logging.Logger:
    """
    포괄적인 로깅 시스템 설정 (main.py와 호환)

    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 로그 파일 저장 디렉토리
        console_output: 콘솔 출력 여부
        file_output: 파일 출력 여부

    Returns:
        설정된 메인 로거
    """
    # 로그 디렉토리 생성
    if file_output:
        os.makedirs(log_dir, exist_ok=True)

    # 로그 포맷 설정 (main.py와 동일)
    log_format = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # 로깅 설정 (main.py 방식과 동일)
    handlers = []

    if console_output:
        handlers.append(logging.StreamHandler(sys.stdout))

    if file_output:
        handlers.extend(
            [
                logging.FileHandler(
                    os.path.join(log_dir, "glbaguni_main.log"), encoding="utf-8"
                ),
                logging.FileHandler(
                    os.path.join(log_dir, "glbaguni_errors.log"),
                    encoding="utf-8",
                    mode="a",
                ),
            ]
        )

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )

    # 외부 라이브러리 로깅 레벨 조정
    external_loggers = ["httpx", "httpcore", "urllib3", "requests"]
    for logger_name in external_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # uvicorn 로깅 조정
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.setLevel(logging.INFO)

    # 메인 로거 반환 (main.py와 동일)
    logger = logging.getLogger("glbaguni.main")
    logger.info("=" * 80)
    logger.info("🚀 글바구니 백엔드 서버 v3.0.0 시작")
    logger.info("=" * 80)
    return logger


def get_logger(name: str) -> logging.Logger:
    """모듈별 로거 생성"""
    return logging.getLogger(name)


def configure_external_loggers():
    """외부 라이브러리 로거 설정"""
    external_loggers = [
        "httpx",
        "httpcore",
        "urllib3",
        "requests",
        "openai",
        "uvicorn.access",
        "sqlalchemy.engine",
    ]

    for logger_name in external_loggers:
        external_logger = logging.getLogger(logger_name)
        external_logger.setLevel(logging.WARNING)


def log_api_request(method: str, path: str, client_ip: str = "unknown") -> None:
    """API 요청 로깅"""
    logger = get_logger("api.requests")
    logger.info(f"📥 {method} {path} from {client_ip}")


def log_performance(
    operation: str, duration: float, details: Optional[dict] = None
) -> None:
    """성능 로깅"""
    logger = get_logger("performance")

    details_str = ""
    if details:
        details_str = " | " + " | ".join(f"{k}: {v}" for k, v in details.items())

    logger.info(f"⏱️ {operation}: {duration:.3f}초{details_str}")


def log_external_call(
    service: str, endpoint: str, duration: float, success: bool = True
) -> None:
    """외부 서비스 호출 로깅"""
    logger = get_logger("external.calls")
    status = "✅" if success else "❌"
    logger.info(f"{status} {service} -> {endpoint}: {duration:.3f}초")


class ContextLogger:
    """컨텍스트 매니저를 사용한 로깅"""

    def __init__(self, operation: str, logger_name: str = "context"):
        self.operation = operation
        self.logger = get_logger(logger_name)
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"🔄 시작: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.info(f"✅ 완료: {self.operation} ({duration:.3f}초)")
        else:
            self.logger.error(
                f"❌ 실패: {self.operation} ({duration:.3f}초) - {exc_val}"
            )

        return False  # 예외 재발생


def setup_rotating_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """회전 로그 파일 설정"""
    os.makedirs(log_dir, exist_ok=True)

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)

    # 회전 파일 핸들러
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "glbaguni.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

    configure_external_loggers()
    return get_logger("glbaguni.main")


# 하위 호환성을 위한 별칭
setup_logging = setup_comprehensive_logging
