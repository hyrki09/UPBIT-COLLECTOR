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
        # print(b)
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

#* 시장가 매수
def buy_market_order(upbit, ticker, amount):
    try:
        result = upbit.buy_market_order(ticker, amount)
        print(f"✅ 매수 완료 | {ticker} | {amount:,}원")
        return result
    except Exception as e:
        print(f"❌ 매수 실패 | {ticker} | {e}")
        return None

#* 시장가 매도 (전량)
def sell_market_order(upbit, ticker):
    try:
        balance = upbit.get_balance(ticker.split('-')[1])
        if balance > 0:
            result = upbit.sell_market_order(ticker, balance)
            print(f"매도 완료 | {ticker} | {balance}개")
            return result
        else:
            print(f"보유 수량 없음 | {ticker}")
            return None
    except Exception as e:
        print(f"매도 실패 | {ticker} | {e}")
        return None

#* 현재 수익률 조회
def get_current_profit(upbit, ticker):
    try:
        balances = upbit.get_balances()
        print(balances)
        for b in balances:
            if b['currency'] == ticker.split('-')[1]:
                avg_buy_price = float(b['avg_buy_price']) # 평균 매수가

                if avg_buy_price == 0:
                    print(f"{ticker} 평균 매수가 없음 (에어드랍 또는 입금된 코인)")
                    return 0
                current_price = pyupbit.get_current_price(ticker)
                profit = (current_price - avg_buy_price) / avg_buy_price * 100
                print(f"{ticker} 수익률 : {round(profit, 2)}")
                return profit
    except Exception as e:
        print(f"[ERROR] {e}")
    return 0

if __name__ == "__main__":
    upbit = connect_upbit()
    if upbit:
        get_balance(upbit)

        # 주요 코인 전략 확인
        # print("\n=== 전략 스캔 ===")
        # watchlist = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
        # for ticker in watchlist:
        #     result = check_strategy(ticker)
        #     print(f"{ticker} : {'골든크로스!' if result else '대기중'}")
        #     time.sleep(0.1)

        print("\n === 수익률 확인 ===")
        get_current_profit(upbit, "KRW-VTHO")