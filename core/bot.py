# core/bot.py - 자동매매 봇 프레임워크

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyupbit
import json
import time
from datetime import datetime, date
from core.order import OrderManager
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
                base_capital: float = 1000000,
                scan_interval: int = 10):
        self.upbit = upbit
        self.strategies = strategies
        self.base_capital = base_capital
        self.scan_interval = scan_interval
        self.order_manager = OrderManager(upbit)
        self.watchlist_file = "watchlist.json"

        self.positions = {}
        self.initial_capital = None
        self.start_date = date.today()

    def get_buy_amount(self, strategy) -> float:
        """매수 금액 계산 (기준 자본금 + 단위 절사)"""
        stage_ratio = strategy.buy_stages[0]['ratio']
        raw_amount = self.base_capital * stage_ratio

        if self.base_capital >= 10000000:
            unit = 100000
        elif self.base_capital >= 1000000:
            unit = 10000
        else:
            unit = 1000

        return (raw_amount // unit) * unit

    def can_buy(self, strategy) -> bool:
        """잔고로 전체 차수 투자 가능한지 확인"""
        krw = self.order_manager.get_balance_krw()
        buy_amount = self.get_buy_amount(strategy)
        total_stages = len(strategy.buy_stages)

        # 전체 차수 투자 가능한지 확인
        max_per_coin = buy_amount * total_stages
        return krw >= max_per_coin

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

        for strategy_name, items in watchlist.items():
            if strategy_name == 'updated_at':
                continue

            strategy = self.strategies.get(strategy_name)
            if not strategy:
                continue

            for item in items:
                ticker = item['ticker']

                # 이미 보유 중인 코인 → 추가 매수 체크
                if ticker in self.positions:
                    pos = self.positions[ticker]
                    buy_stage = pos['buy_stage']

                    if buy_stage >= len(strategy.buy_stages):
                        continue

                    # 추가 매수는 1차 고정 금액 사용
                    buy_amount = pos['stage_amount']
                    if krw < buy_amount:
                        continue

                    # 추가 매수 목표가
                    df = pyupbit.get_ohlcv(ticker, interval="day", count=50)
                    buy_target = strategy.get_buy_price(
                        df=df,
                        stage=buy_stage,
                        prev_buy_price=pos['prev_buy_price']
                    )

                    if not buy_target:
                        continue

                    current_price = pyupbit.get_current_price(ticker)

                    if current_price <= buy_target:
                        result = self.order_manager.buy_limit_order(
                            ticker, buy_target, buy_amount)

                        if result:
                            qty = buy_amount / buy_target
                            pos['total_qty'] += qty
                            pos['invested'] += buy_amount
                            pos['avg_buy_price'] = (
                                pos['invested'] / pos['total_qty'])
                            pos['buy_stage'] += 1
                            pos['prev_buy_price'] = buy_target
                            pos['sell_base_qty'] = pos['total_qty']
                            pos['sell_stage'] = 0

                            logger.info(f"📈 {buy_stage+1}차 매수 주문 | "
                                       f"{ticker} | {int(buy_target):,}원")
                            notifier.send_buy(ticker, buy_target,
                                            buy_amount, buy_stage + 1)
                    continue

                # 새 코인 1차 매수
                if not self.can_buy(strategy):
                    logger.info(f"잔고 부족 | {strategy_name} 매수 불가")
                    continue

                buy_amount = self.get_buy_amount(strategy)
                current_price = pyupbit.get_current_price(ticker)

                # ready True → 즉시 지정가 주문
                if item.get('ready', False):
                    buy_price = item['buy_price']
                    logger.info(f"✅ 즉시 지정가 주문 | {ticker} | "
                               f"{int(buy_price):,}원")

                # ready False → 실시간 조건 체크
                else:
                    df = pyupbit.get_ohlcv(ticker, interval="day", count=50)
                    if not strategy.is_ready_to_buy(df, current_price):
                        continue
                    buy_price = strategy.get_buy_price(df=df, stage=0,
                                                       current_price=current_price)
                    if not buy_price:
                        continue
                    logger.info(f"📌 조건 충족 지정가 주문 | {ticker} | "
                               f"{int(buy_price):,}원")

                result = self.order_manager.buy_limit_order(
                    ticker, buy_price, buy_amount)

                if result:
                    qty = buy_amount / buy_price
                    self.positions[ticker] = {
                        'strategy': strategy_name,
                        'avg_buy_price': buy_price,
                        'total_qty': qty,
                        'invested': buy_amount,
                        'sell_stage': 0,
                        'sell_base_qty': qty,
                        'stage_amount': buy_amount,
                        'prev_buy_price': buy_price,
                        'buy_stage': 1
                    }
                    logger.info(f"📈 1차 매수 주문 | {ticker} | "
                               f"{int(buy_price):,}원 | {int(buy_amount):,}원")
                    notifier.send_buy(ticker, buy_price, buy_amount, 1)

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

                if sell_stage >= len(strategy.sell_stages):
                    continue

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
                    sell_qty = pos['sell_base_qty'] * sell_ratio
                    sell_qty = min(sell_qty, pos['total_qty'])

                    self.order_manager.sell_limit_order(
                        ticker, sell_target, sell_qty)
                    notifier.send_sell(ticker, sell_target, profit, "익절")
                    logger.info(f"✅ {sell_stage+1}차 익절 주문 | "
                               f"{ticker} | {int(sell_target):,}원")

                    pos['total_qty'] -= sell_qty
                    pos['invested'] = pos['total_qty'] * avg_price
                    pos['sell_stage'] += 1

                    if pos['sell_stage'] >= len(strategy.sell_stages):
                        if pos['total_qty'] > 0:
                            self.order_manager.sell_limit_order(
                                ticker, current_price, pos['total_qty'])
                        del self.positions[ticker]

                # 손절
                elif current_price <= stop_target:
                    self.order_manager.sell_limit_order(
                        ticker, stop_target, pos['total_qty'])
                    notifier.send_sell(ticker, stop_target, profit, "손절")
                    logger.info(f"🛑 손절 주문 | {ticker} | "
                               f"{int(stop_target):,}원")
                    del self.positions[ticker]

            except Exception as e:
                logger.error(f"[{ticker}] 매도 스캔 오류: {e}")

    def run(self, daily_loss_limit: float = -10.0):
        """자동매매 메인 루프"""
        self.initial_capital = self.get_total_asset()
        logger.info("=== 트레이딩 봇 시작 ===")
        notifier.send(f"🤖 트레이딩 봇 시작!\n"
                     f"초기자산: {int(self.initial_capital):,}원\n"
                     f"기준자본금: {int(self.base_capital):,}원")

        while True:
            try:
                if date.today() != self.start_date:
                    self.initial_capital = self.get_total_asset()
                    self.start_date = date.today()
                    logger.info("📅 날짜 변경 - 초기자산 초기화")

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

                watchlist = self.load_watchlist()
                self.scan_sell()
                self.scan_buy(watchlist)

                if datetime.now().hour == 9 and datetime.now().minute == 0:
                    notifier.send_daily_report(
                        total_asset, daily_profit, self.positions)

                logger.info(f"⏳ {self.scan_interval}초 대기 중...\n")
                time.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"[ERROR] {e}")
                notifier.send_error(str(e))
                time.sleep(60)