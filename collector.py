import pyupbit
import pandas as pd
from datetime import datetime
import time
from config import TICKERS


#* 특정 코인의 과거 데이터 가져오기
def get_ohlcv(ticker, interval="day", count=365):
    try:
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
        print(df)
        df['ticker'] = ticker
        return df
    except Exception as e:
        print(f"[ERROR] {ticker} 데이터 수집 실패 : {e}")
        return None

#* 코인별로 CSV 저장
def save_ohlcv(ticker, df):
    if df is not None:
        df.to_csv(f"data/{ticker}.csv")
        print(f"{ticker} 저장완료 ({len(df)}행)")

if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok="True")

    print("=====과거 데이터 수집 시작=====")
    for ticker in TICKERS:
        df = get_ohlcv(ticker)
        save_ohlcv(ticker, df)
        time.sleep(0.1)
    print("\n 전체수집완료")   