# core/updater.py - 데이터 최신화

import pyupbit
import pandas as pd
import os
from datetime import datetime

#*  일봉/분봉 데이터를 CSV로 저장하고 최신화
#*  매번 전체 데이터를 새로 받지 않고
#*  마지막 저장 시점 이후 데이터만 추가!
class DataUpdater:

    # interval별 설정
    INTERVAL_CONFIG = {
        "day":     {"count": 200, "folder": "data/day"},
        "minute1": {"count": 10080, "folder": "data/minute1"},  # 7일치
        "minute3": {"count": 14400, "folder": "data/minute3"},  # 30일치
        "minute5": {"count": 8640,  "folder": "data/minute5"},  # 30일치
    }

    def __init__(self):
        # 폴더 자동 생성
        for config in self.INTERVAL_CONFIG.values():
            os.makedirs(config["folder"], exist_ok=True)

    # CSV 파일 경로 반환
    def get_file_path(self, ticker, interval):
        folder = self.INTERVAL_CONFIG[interval]["folder"]
        return f"{folder}/{ticker}.csv"

    # 기존 CSV 데이터 불러오기
    def load_existing(self, ticker, interval):
        path = self.get_file_path(ticker, interval)
        if os.path.exists(path):
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            return df
        return None
    
    # 전체 과거 데이터 가져오기 (200개 제한 우회)
    def get_all_ohlcv(self, ticker, interval="day"):
        import time

        all_df = pd.DataFrame()
        to = None

        while True:
            if to:
                df = pyupbit.get_ohlcv(ticker, interval=interval,
                                        count=200, to=to)
            else:
                df = pyupbit.get_ohlcv(ticker, interval=interval, count=200)

            if df is None or len(df) == 0:
                break

            all_df = pd.concat([df, all_df])
            to = df.index[0]

            print(f"  {df.index[0].date()} ~ {df.index[-1].date()} ({len(all_df)}개)")

            # 200개 미만이면 더 이상 데이터 없음
            if len(df) < 200:
                break

            time.sleep(0.1)

        return all_df
    
    # 특정 날짜 이후 데이터 가져오기 (200개 제한 우회)
    def get_range_ohlcv(self, ticker, interval, from_date):
        import time

        all_df = pd.DataFrame()
        to = None

        while True:
            if to:
                df = pyupbit.get_ohlcv(ticker, interval=interval,
                                        count=200, to=to)
            else:
                df = pyupbit.get_ohlcv(ticker, interval=interval, count=200)

            if df is None or len(df) == 0:
                break

            # from_date 이후 데이터만 필터링
            filtered = df[df.index > from_date]
            all_df = pd.concat([filtered, all_df])

            # from_date보다 이전 데이터가 나오면 stop
            if df.index[0] <= from_date:
                break

            to = df.index[0]
            time.sleep(0.1)

        return all_df

    # 데이터 최신화
    def update(self, ticker, interval="day"):
        existing_df = self.load_existing(ticker, interval)

        if existing_df is not None:
            last_date = existing_df.index[-1]
            days_diff = (datetime.now() - last_date).days + 10

            if days_diff <= 200:
                # 200개 이하면 한 번에 가져오기
                new_df = pyupbit.get_ohlcv(ticker, interval=interval, 
                                            count=days_diff)
                new_df = new_df[new_df.index > last_date]
            else:
                # 200개 초과면 반복 호출로 가져오기
                new_df = self.get_range_ohlcv(ticker, interval, last_date)

            if new_df is None or len(new_df) == 0:
                print(f"[{ticker}] {interval} 이미 최신 상태")
                return existing_df

            updated_df = pd.concat([existing_df, new_df])

        else:
            # 처음이면 전체 데이터
            print(f"[{ticker}] 최초 수집 중...")
            updated_df = self.get_all_ohlcv(ticker, interval)

            if updated_df is None:
                return None

        path = self.get_file_path(ticker, interval)
        updated_df.to_csv(path)
        print(f"✅ [{ticker}] {interval} 완료 (총 {len(updated_df)}개)")
        return updated_df

    # 여러 코인 한 번에 업데이트
    def update_all(self, tickers, intervals=["day", "minute3"]):
        import time
        print(f"=== 데이터 업데이트 시작 ({len(tickers)}개 코인) ===\n")

        for ticker in tickers:
            for interval in intervals:
                self.update(ticker, interval)
                time.sleep(0.1)  # Rate Limit 방지

        print("\n✅ 전체 업데이트 완료!")


if __name__ == "__main__":
    updater = DataUpdater()

    # # 주요 코인 업데이트 테스트
    # tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
    # updater.update_all(tickers, intervals=["day", "minute3"])

    # 업비트 전체 코인 가져오기
    tickers = pyupbit.get_tickers(fiat="KRW")
    print(f"총 {len(tickers)}개 코인 업데이트 시작")

    # # 일봉만 먼저
    updater.update_all(tickers, intervals=["day"])



    # 테스트용 2개 코인만
    # tickers = ["KRW-BTC", "KRW-XRP"]
    # updater.update_all(tickers, intervals=["day"])