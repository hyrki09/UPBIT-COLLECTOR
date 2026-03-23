import pyupbit
import time
import pandas as pd
from config import ACCESS_KEY, SECRET_KEY

#* 업비트 연결
def connect_upbit():
    try:
        upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)
        print("업비트 연결성공")
        return upbit
    except Exception as e:
        print(f"X 연결 실패!: {e}")
        return None
    
#* 잔고 조회
def get_balance(upbit):
    krw = upbit.get_balance("KRW")
    print(f"\n 원화 잔고: {int(krw):,} 원")

    # 보유 코인 조회
    balances = upbit.get_balances()
    for b in balances:
        print(b)
        if b['currency'] != 'KRW' and float(b['balance']) > 0:
            try:
                ticker = f"KRW-{b['currency']}"
                price = pyupbit.get_current_price(ticker)
                value = float(b['balance']) * price
                print(f"{ticker}: {float(b['balance'])}개 | 평가금액: {int(value):,}원")
            except Exception as e:
                pass
                # print(f"[ERROR]  {b['currency']}: {e}")

#* 과거 데이터 가져오기
def get_ohlcv(ticker, interval='day', count=30):
    try:
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
        return df
    except Exception as e:
        print(f"[ERROR] {ticker} 데이터 조회 실패 : {e}")
        return None

#* 전략 확인 - 골든크로스 발생여부    
def check_strategy(ticker, short=5, long=20):
    df = get_ohlcv(ticker)
    if df is None:
        return False
    
    # 이동평균선
    df['ma_short'] = df['close'].rolling(short).mean()
    df['ma_long'] = df['close'].rolling(long).mean()

    today = df.iloc[-1]
    yesterday = df.iloc[-2]

    golden_cross = (today['ma_short'] > today['ma_long'] and yesterday['ma_short'] <= yesterday['ma_long'])

    return golden_cross

if __name__ == "__main__":
    upbit = connect_upbit()
    if upbit:
        get_balance(upbit)

        # 주요 코인 전략 확인
        print("\n=== 전략 스캔 ===")
        watchlist = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
        for ticker in watchlist:
            result = check_strategy(ticker)
            print(f"{ticker} : {'골든크로스!' if result else '대기중'}")
            time.sleep(0.1)