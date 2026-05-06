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
    전체 코인 스캔 → 매수 후보 선별
    - 5% 이내 코인만 watchlist 등록
    - 1차/추가 매수 통합 관리
    """

    def __init__(self, strategies: dict,
                 market_ticker: str = "KRW-BTC",
                 scan_interval: int = 300):
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
        """
        전체 코인 스캔 → 매수 후보 선별
        1. 보유 코인 추가 매수 후보 (5% 이내)
        2. 새 코인 1차 매수 후보 (5% 이내)
        """
        watchlist = {}
        market_df = self.get_market_df()
        positions = self.load_positions()
        pending_orders = self.load_pending_orders()

        # 주문 중인 코인 제외
        exclude_tickers = set(pending_orders.keys())
        # exclude_tickers = set()

        for strategy_name, config in self.strategies.items():
            strategy = config['strategy']
            tickers = config.get('tickers') or pyupbit.get_tickers(fiat="KRW")
            watchlist[strategy_name] = []

            logger.info(f"[{strategy_name}] 스캔 시작 ({len(tickers)}개 코인)")

            # 1. 보유 코인 추가 매수 후보 체크
            for ticker, pos in positions.items():
                try:
                    if ticker in exclude_tickers:
                        continue

                    if pos.get('strategy') != strategy_name:
                        continue

                    buy_stage = pos.get('buy_stage', 1)
                    if buy_stage >= len(strategy.buy_stages):
                        continue

                    df = pyupbit.get_ohlcv(ticker, interval="day", count=200)
                    if df is None:
                        continue

                    df = strategy.prepare(df)

                    try:
                        current_price = pyupbit.get_current_price(ticker)
                    except:
                        continue

                    if current_price is None:
                        continue

                    prev_buy_price = pos.get('prev_buy_price')
                    buy_price = strategy.get_buy_price(
                        df=df,
                        stage=buy_stage,
                        prev_buy_price=prev_buy_price
                    )

                    if not buy_price:
                        continue

                    diff = (current_price - buy_price) / buy_price * 100

                    # 5% 이내일 때만 watchlist 등록!
                    if diff > 5.0:
                        continue

                    watchlist[strategy_name].append({
                        'ticker': ticker,
                        'buy_stage': buy_stage,
                        'buy_price': round(buy_price, 0),
                        'prev_buy_price': prev_buy_price,
                        'current_price': current_price,
                        'diff': round(diff, 2),
                        'is_additional': True
                    })

                    logger.info(f"  ✅ {ticker} | "
                               f"{buy_stage+1}차 추가 매수 | "
                               f"목표가: {int(buy_price):,}원 | "
                               f"차이: {round(diff, 2)}%")

                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"[{ticker}] 추가 매수 스캔 오류: {e}")

            # 2. 새 코인 1차 매수 후보 체크
            for ticker in tickers:
                try:
                    if ticker in positions:
                        continue
                    if ticker in exclude_tickers:
                        continue

                    df = pyupbit.get_ohlcv(ticker, interval="day", count=200)
                    if df is None:
                        continue

                    df = strategy.prepare(df)

                    # 전제조건 확인 (BTC 조건)
                    if not strategy.check_precondition(df, market_df):
                        continue

                    try:
                        current_price = pyupbit.get_current_price(ticker)
                    except:
                        continue

                    if current_price is None:
                        continue

                    # 1차 매수가 계산
                    buy_price = strategy.get_buy_price(df=df, stage=0)
                    if not buy_price:
                        continue

                    diff = (current_price - buy_price) / buy_price * 100

                    # 5% 이내일 때만 watchlist 등록!
                    if diff > 5.0:
                        continue

                    watchlist[strategy_name].append({
                        'ticker': ticker,
                        'buy_stage': 0,
                        'buy_price': round(buy_price, 0),
                        'prev_buy_price': None,
                        'current_price': current_price,
                        'diff': round(diff, 2),
                        'is_additional': False
                    })

                    logger.info(f"  ✅ {ticker} | "
                               f"1차 신규 | "
                               f"목표가: {int(buy_price):,}원 | "
                               f"차이: {round(diff, 2)}%")

                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"[{ticker}] 스캔 오류: {e}")

            logger.info(f"[{strategy_name}] 스캔 완료 "
                       f"({len(watchlist[strategy_name])}개 발견)")

            # 텔레그램 알림
            if watchlist[strategy_name]:
                additional = [i for i in watchlist[strategy_name]
                             if i.get('is_additional')]
                new_coins = [i for i in watchlist[strategy_name]
                            if not i.get('is_additional')]

                msg = f"📌 [{strategy_name}] 매수 후보 {len(watchlist[strategy_name])}개\n"

                if additional:
                    msg += f"\n🔄 추가 매수 ({len(additional)}개)\n"
                    for item in additional:
                        msg += (f"  {item['ticker']} | "
                               f"{item['buy_stage']+1}차 | "
                               f"목표가: {int(item['buy_price']):,}원 | "
                               f"차이: {item['diff']}%\n")

                if new_coins:
                    msg += f"\n🆕 신규 매수 ({len(new_coins)}개)\n"
                    for item in new_coins:
                        msg += (f"  {item['ticker']} | "
                               f"목표가: {int(item['buy_price']):,}원 | "
                               f"차이: {item['diff']}%\n")

                notifier.send(msg)

        watchlist['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_watchlist(watchlist)
        return watchlist

    def run(self):
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
        scan_interval=300
    )
    scanner.run()