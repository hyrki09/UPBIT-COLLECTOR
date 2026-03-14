import pyupbit
import pandas as pd
from datetime import datetime

#^ 1. 시세확인
# price = pyupbit.get_current_price("KRW-BTC")

# print(f"비트코인 현재가 :  {int(price):,}원")


#^ 2. 수집할 코인 목록 시세 확인
# tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]

# for ticker in tickers:
#     price = pyupbit.get_current_price(ticker)
#     print(f"[{ticker}] {int(price):,}원")

#^ 3. CSV 저장 추가
tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]

# 수집할 코인 목록
records = []
for ticker in tickers:
    price = pyupbit.get_current_price(ticker)

    records.append({
        "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # 현재 시간
        "ticker":ticker,
        "price":int(price)
    })
    print(f"[{ticker}] {int(price):,}원")

# CSV 저장
df = pd.DataFrame(records) # 리스트 -> 표 형태 전환
df.to_csv("price_data.csv", index=False) # CSV 파일로 저장
print("\n price_data.csv 저장완료!")

