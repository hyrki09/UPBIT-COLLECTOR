import pyupbit
from dotenv import load_dotenv
import os

load_dotenv()

#API 키
ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY")
SECRET_KEY = os.getenv("UPBIT_SECRET_KEY")

# 업비트 원화 마켓 전체 코인 가져오기
TICKERS = pyupbit.get_tickers(fiat="KRW")
# 저장 파일명
OUTPUT_FILE = "price_data.csv"
INTERVAL = 60 