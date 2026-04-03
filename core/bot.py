# core/bot.py - 자동매매 봇 프레임워크

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyupbit
import json
import time
from datetime import datetime, date
from core.order import OrderManager
from strategies.base import BaseStrategy
from utils.logger import Logger
from utils.telegram import TelegramNotifier

logger = Logger("bot")
notifier = TelegramNotifier()

class TradingBot:
    """
    watchlist.json 읽어서 관심종목만 집중 매매
    ScannerBot이 관심종목 선별 → TradingBot이 매매
    """

    def __init__(self, upbit: pyupbit.Upbit,
                 strategies: dict,
                 budget: float = 100000,
                 max_holding: int = 3,
                 scan_interval: int = 10):
        """
        strategies: 전략별 설정
        {
            'golden_cross': GoldenCrossStrategy(),
            'envelope': EnvelopeStrategy()
        }
        budget: 1회 매수 예산
        max_holding: 최대 보유 코인 수
        scan_interval: 매매 스캔 주기 (초)
        """
        self.upbit = upbit
        self.strategies = strategies
        self.budget = budget
        self.max_holding = max_holding
        self.scan_interval = scan_interval
        self.order_manager = OrderManager(upbit)
        self.watchlist_file = "watchlist.json"

        # 포지션 관리
        self.positions = {}
        self.initial_capital = None
        self.start_date = date.today()

    def load_watchlist(self) -> dict:
        """관심종목 파일 불러오기"""
        if os.path.exists(self.watchlist_file):
            with open(self.watchlist_file, 'r') as f:
                return json.load(f)
        return {}

    def get_total_asset(self) -> float:
        """총 자산 계산"""
        total = self.order_manager.get_balance_krw()
        for ticker, pos in self.positions.items():
            try:
                price = pyupbit.get_current_price(ticker)
                total += price * pos['total_qty']
            except:
                pass
        return total

    def get_daily_profit(self) -> float:
        """오늘 수익률 계산"""
        if not self.initial_capital:
            return 0.0
        total = self.get_total_asset()
        return (total - self.initial_capital) / self.initial_capital * 100

    def scan_buy(self, watchlist: dict):
        """관심종목 매수 스캔"""
        krw = self.order_manager.get_balance_krw()

        if len(self.positions) >= self.max_holding:
            return
        if krw < self.budget:
            return

        for strategy_name, items in watchlist.items():
            if strategy_name == 'updated_at':
                continue

            strategy = self.strategies.get(strategy_name)
            if not strategy:
                continue

            for item in items:
                ticker = item['ticker']
                buy_price = item['buy_price']

                if ticker in self.positions:
                    continue

                # 지정가 매수 주문
                result = self.order_manager.buy_limit_order(
                    ticker, buy_price, self.budget)

                if result:
                    qty = self.budget / buy_price
                    self.positions[ticker] = {
                        'strategy': strategy_name,
                        'avg_buy_price': buy_price,
                        'total_qty': qty,
                        'invested': self.budget,
                        'sell_stage': 0,
                        'buy_stage': 1
                    }
                    logger.info(f"📈 매수 주문 | {ticker} | {int(buy_price):,}원")
                    notifier.send_buy(ticker, buy_price, self.budget)

    def scan_sell(self):
        """보유 코인 매도 스캔"""
        for ticker in list(self.positions.keys()):
            try:
                pos = self.positions[ticker]
                strategy = self.strategies.get(pos['strategy'])
                if not strategy:
                    continue

                current_price = pyupbit.get_current_price(ticker)
                avg_price = pos['avg_buy_price']
                sell_stage = pos['sell_stage']

                sell_target = strategy.get_sell_price(avg_price, sell_stage)
                stop_target = strategy.get_stop_loss_price(
                    avg_price,
                    current_price=current_price,
                    sell_stage=sell_stage
                )

                profit = (current_price - avg_price) / avg_price * 100
                logger.info(f"📊 {ticker} | "
                           f"현재가: {int(current_price):,}원 | "
                           f"수익률: {round(profit, 2)}%")

                # 익절
                if current_price >= sell_target:
                    sell_ratio = strategy.get_stage_sell_ratio(sell_stage)
                    sell_qty = pos['total_qty'] * sell_ratio
                    self.order_manager.sell_limit_order(
                        ticker, sell_target, sell_qty)
                    notifier.send_sell(ticker, sell_target, profit, "익절")
                    logger.info(f"✅ 익절 주문 | {ticker} | {int(sell_target):,}원")

                    pos['sell_stage'] += 1
                    pos['total_qty'] -= sell_qty

                    if pos['sell_stage'] >= len(strategy.sell_stages):
                        del self.positions[ticker]

                # 손절
                elif current_price <= stop_target:
                    self.order_manager.sell_limit_order(
                        ticker, stop_target, pos['total_qty'])
                    notifier.send_sell(ticker, stop_target, profit, "손절")
                    logger.info(f"🛑 손절 주문 | {ticker} | {int(stop_target):,}원")
                    del self.positions[ticker]

            except Exception as e:
                logger.error(f"[{ticker}] 매도 스캔 오류: {e}")

    def run(self, daily_loss_limit: float = -10.0):
        """자동매매 메인 루프"""
        self.initial_capital = self.get_total_asset()
        logger.info("=== 트레이딩 봇 시작 ===")
        notifier.send(f"🤖 트레이딩 봇 시작!\n"
                     f"초기자산: {int(self.initial_capital):,}원\n"
                     f"매수 예산: {int(self.budget):,}원\n"
                     f"최대 보유: {self.max_holding}개")

        while True:
            try:
                # 날짜 바뀌면 초기자산 초기화
                if date.today() != self.start_date:
                    self.initial_capital = self.get_total_asset()
                    self.start_date = date.today()
                    logger.info("📅 날짜 변경 - 초기자산 초기화")

                # 일일 손실 한도 확인
                daily_profit = self.get_daily_profit()
                if daily_profit <= daily_loss_limit:
                    msg = f"🛑 일일 손실 한도 초과 ({round(daily_profit, 2)}%)"
                    logger.info(msg)
                    notifier.send(msg)
                    break

                total_asset = self.get_total_asset()
                logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] "
                           f"총자산: {int(total_asset):,}원 | "
                           f"수익률: {round(daily_profit, 2)}%")

                # 관심종목 불러오기
                watchlist = self.load_watchlist()

                # 매도 스캔
                self.scan_sell()

                # 매수 스캔
                self.scan_buy(watchlist)

                # 일일 리포트 (오전 9시)
                if datetime.now().hour == 9 and datetime.now().minute == 0:
                    notifier.send_daily_report(
                        total_asset, daily_profit, self.positions)

                logger.info(f"⏳ {self.scan_interval}초 대기 중...\n")
                time.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"[ERROR] {e}")
                notifier.send_error(str(e))
                time.sleep(60)