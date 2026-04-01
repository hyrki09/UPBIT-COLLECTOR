# utils/logger.py - 로그 관리

import logging
import os
from datetime import datetime

class Logger:
    """
    파일 + 터미널 동시 로그 출력
    날짜별로 로그 파일 자동 생성
    """

    def __init__(self, name: str, log_dir: str = "logs"):
        self.name = name
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)  # logs 폴더 생성

        # 오늘 날짜로 로그 파일 생성
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = f"{log_dir}/{name}_{today}.log"

        # 로거 설정
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # 중복 핸들러 방지
        if not self.logger.handlers:
            # 파일 핸들러
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s'
            ))

            # 터미널 핸들러
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s'
            ))

            self.logger.addHandler(file_handler)
            self.logger.addHandler(stream_handler)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg):
        self.logger.error(msg)

    def warning(self, msg):
        self.logger.warning(msg)


if __name__ == "__main__":
    # 테스트
    logger = Logger("test")
    logger.info("로거 테스트!")
    logger.error("에러 테스트!")
    logger.warning("경고 테스트!")
