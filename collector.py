import pyupbit

price = pyupbit.get_current_price("KRW-BTC")

print(f"비트코인 현재가 :  {int(price):,}원")


