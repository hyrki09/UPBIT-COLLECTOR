# core/scanner.py - 관심종목 스캐너

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyupbit
import pandas as pd 
import json
import time
import os
from datetime import datetime
from strategies.base import BaseStrategy
from utils.logger import Logger
from utils.telegram import TelegramNotifier

logger = Logger("scanner")
notifier = TelegramNotifier()

class ScannerBot:
    """
    전체 코인 스캔 → 조건 근접 종목 선별
    watchlist.json에 저장
    TradingBot이 이 파일을 읽어서 매매
    """

    def __init__(self, strategies: dict,
                 market_ticker: str = "KRW-BTC",
                 scan_interval: int = 3600):
        """
        strategies: 전략별 설정
        {
            'golden_cross': {
                'strategy': GoldenCrossStrategy(),
                'tickers': ['KRW-BTC', 'KRW-ETH']  # None이면 전체
            }
        }
        market_ticker: 시장 기준 티커 (글로벌 전제조건용)
        scan_interval: 스캔 주기 (초) 기본 1시간
        """
        self.strategies = strategies
        self.market_ticker = market_ticker
        self.scan_interval = scan_interval
        self.watchlist_file = "watchlist.json"

    def load_watchlist(self) -> dict:
        """관심종목 파일 불러오기"""
        if os.path.exists(self.watchlist_file):
            with open(self.watchlist_file, 'r') as f:
                return json.load(f)
        return {}

    def save_watchlist(self, watchlist: dict):
        """관심종목 파일 저장"""
        with open(self.watchlist_file, 'w') as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=2)

    def get_market_df(self) -> pd.DataFrame:
        """시장 기준 데이터 가져오기 (BTC)"""
        try:
            return pyupbit.get_ohlcv(
                self.market_ticker, interval="day", count=200)
        except:
            return None

    def scan(self) -> dict:
        """전체 코인 스캔 → 관심종목 선별"""
        watchlist = {}

        # 시장 기준 데이터 (BTC) 가져오기
        market_df = self.get_market_df()

        for strategy_name, config in self.strategies.items():
            strategy = config['strategy']
            tickers = config.get('tickers') or pyupbit.get_tickers(fiat="KRW")
            watchlist[strategy_name] = []

            logger.info(f"[{strategy_name}] 스캔 시작 ({len(tickers)}개 코인)")

            for ticker in tickers:
                try:
                    df = pyupbit.get_ohlcv(ticker, interval="day", count=200)
                    if df is None:
                        continue

                    df = strategy.prepare(df)

                    # 전제조건 확인 (글로벌 + 종목별)
                    if not strategy.check_precondition(df, market_df):
                        continue  # 전제조건 불충족 → 스킵

                    # 매수 목표가 계산
                    buy_price = strategy.get_buy_price(df)

                    if buy_price:
                        current_price = pyupbit.get_current_price(ticker)
                        diff = (current_price - buy_price) / buy_price * 100

                        watchlist[strategy_name].append({
                            'ticker': ticker,
                            'buy_price': round(buy_price, 0),
                            'current_price': current_price,
                            'diff': round(diff, 2)
                        })
                        logger.info(f"  📌 {ticker} 발견! "
                                   f"목표가: {int(buy_price):,}원 | "
                                   f"현재가: {int(current_price):,}원 | "
                                   f"차이: {round(diff, 2)}%")

                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"[{ticker}] 스캔 오류: {e}")

            logger.info(f"[{strategy_name}] 스캔 완료 "
                       f"({len(watchlist[strategy_name])}개 발견)")

            # 텔레그램 알림
            if watchlist[strategy_name]:
                msg = f"📌 [{strategy_name}] 관심종목 {len(watchlist[strategy_name])}개 발견!\n"
                for item in watchlist[strategy_name]:
                    msg += (f"  {item['ticker']} | "
                           f"목표가: {int(item['buy_price']):,}원 | "
                           f"차이: {item['diff']}%\n")
                notifier.send(msg)

        watchlist['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_watchlist(watchlist)
        return watchlist

    def run(self):
        """스캐너 메인 루프"""
        logger.info("=== 스캐너 봇 시작 ===")
        notifier.send("🔍 스캐너 봇 시작!")

        while True:
            try:
                logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] 스캔 시작")
                watchlist = self.scan()
                logger.info(f"⏳ {self.scan_interval}초 대기 중...\n")
                time.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"[ERROR] {e}")
                notifier.send_error(str(e))
                time.sleep(60)


if __name__ == "__main__":
    from strategies.golden_cross import GoldenCrossStrategy
    import pandas as pd

    strategies = {
        'golden_cross': {
            'strategy': GoldenCrossStrategy(short=5, long=20),
            'tickers': ["KRW-BTC", "KRW-ETH", "KRW-XRP",
                       "KRW-SOL", "KRW-ADA", "KRW-DOGE"]
        }
    }

    scanner = ScannerBot(
        strategies=strategies,
        market_ticker="KRW-BTC",
        scan_interval=3600
    )
    scanner.run()