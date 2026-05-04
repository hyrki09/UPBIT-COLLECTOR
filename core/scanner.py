# core/scanner.py - 관심종목 스캐너

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyupbit
import pandas as pd
import json
import time
from datetime import datetime
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
                 scan_interval: int = 300):  # 기본 5분
        self.strategies = strategies
        self.market_ticker = market_ticker
        self.scan_interval = scan_interval
        self.watchlist_file = "watchlist.json"
        self.positions_file = "positions.json"
        self.pending_orders_file = "pending_orders.json"

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

    def load_positions(self) -> dict:
        """봇의 보유 코인 로드"""
        if os.path.exists(self.positions_file):
            with open(self.positions_file, 'r') as f:
                return json.load(f)
        return {}

    def load_pending_orders(self) -> dict:
        """봇의 미체결 주문 로드"""
        if os.path.exists(self.pending_orders_file):
            with open(self.pending_orders_file, 'r') as f:
                return json.load(f)
        return {}

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

        # 보유 코인 + 미체결 주문 코인 제외 목록
        positions = self.load_positions()
        pending_orders = self.load_pending_orders()
        exclude_tickers = set(positions.keys()) | set(pending_orders.keys())

        # 시장 기준 데이터 (BTC)
        market_df = self.get_market_df()

        for strategy_name, config in self.strategies.items():
            strategy = config['strategy']
            tickers = config.get('tickers') or pyupbit.get_tickers(fiat="KRW")
            watchlist[strategy_name] = []

            logger.info(f"[{strategy_name}] 스캔 시작 ({len(tickers)}개 코인)")

            for ticker in tickers:
                try:
                    # 보유 중이거나 주문 중인 코인 제외
                    if ticker in exclude_tickers:
                        continue

                    df = pyupbit.get_ohlcv(ticker, interval="day", count=200)
                    if df is None:
                        continue

                    df = strategy.prepare(df)

                    # 전제조건 확인 (BTC 조건)
                    if not strategy.check_precondition(df, market_df):
                        continue

                    current_price = pyupbit.get_current_price(ticker)
                    if current_price is None:
                        continue

                    # 관심종목 조건 확인
                    if not strategy.is_watchable(df, current_price):
                        continue

                    # 매수 목표가 계산
                    buy_price = strategy.get_buy_price(df)
                    if not buy_price:
                        continue

                    # 즉시 주문 조건 확인
                    ready = strategy.is_ready_to_buy(df, current_price)
                    diff = (current_price - buy_price) / buy_price * 100

                    watchlist[strategy_name].append({
                        'ticker': ticker,
                        'buy_price': round(buy_price, 0),
                        'current_price': current_price,
                        'diff': round(diff, 2),
                        'ready': ready
                    })

                    status = "✅ 즉시 주문" if ready else "📌 모니터링"
                    logger.info(f"  {status} | {ticker} | "
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
                ready_list = [i for i in watchlist[strategy_name] if i['ready']]
                watch_list = [i for i in watchlist[strategy_name] if not i['ready']]

                msg = f"📌 [{strategy_name}] 관심종목 {len(watchlist[strategy_name])}개\n"

                if ready_list:
                    msg += f"\n✅ 즉시 주문 가능 ({len(ready_list)}개)\n"
                    for item in ready_list:
                        msg += (f"  {item['ticker']} | "
                               f"목표가: {int(item['buy_price']):,}원 | "
                               f"차이: {item['diff']}%\n")

                if watch_list:
                    msg += f"\n👀 모니터링 ({len(watch_list)}개)\n"
                    for item in watch_list:
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
    from strategies.down_coin import DownCoinStrategy

    strategies = {
        'down_coin': {
            'strategy': DownCoinStrategy(
                ma_period=10,
                envelope=0.10,
                stage_ratio=0.05
            ),
            'tickers': pyupbit.get_tickers(fiat='KRW')
        }
    }

    scanner = ScannerBot(
        strategies=strategies,
        market_ticker="KRW-BTC",
        scan_interval=300  # 5분마다
    )
    scanner.run()