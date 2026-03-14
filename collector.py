import pyupbit

# 시세화깅ㄴ
# price = pyupbit.get_current_price("KRW-BTC")

# print(f"비트코인 현재가 :  {int(price):,}원")


# 수집할 코인 목록
tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]

for ticker in tickers:
    price = pyupbit.get_current_price(ticker)
    print(f"[{ticker}] {int(price):,}원")

