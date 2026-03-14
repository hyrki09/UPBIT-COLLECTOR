import pyupbit

# 업비트 원화 마켓 전체 코인 가져오기
TICKERS = pyupbit.get_tickers(fiat="KRW")

# 저장 파일명
OUTPUT_FILE = "price_data.csv"