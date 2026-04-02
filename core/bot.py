# core/bot.py - 자동매매 봇 프레임워크

import pyupbit
import time
from datetime import datetime, date
from core.order import OrderManager
from strategies.base import BaseStrategy
from utils.logger import Logger

logger = Logger("bot")

class TradingBot:
    """
    전략을 주입받아서 자동매매 실행
    strategy만 바꾸면 다른 전략으로 매매 가능!
    """

    def __init__(self, upbit: pyupbit.Upbit,
                 strategy: BaseStrategy,
                 tickers: list,
                 budget: float = 100000,        # 1회 매수 예산
                 max_holding: int = 3,          # 최대 보유 코인 수
                 scan_interval: int = 300):     # 스캔 주기 (초)
        self.upbit = upbit
        self.strategy = strategy
        self.tickers = tickers
        self.budget = budget
        self.max_holding = max_holding
        self.scan_interval = scan_interval
        self.order_manager = OrderManager(upbit)

        # 포지션 관리
        self.positions = {}  # {'KRW-BTC': {'buy_price': 100000, 'qty': 0.001}}
        self.initial_capital = None
        self.start_date = date.today()

    def get_total_asset(self) -> float:
        """총 자산 계산 (원화 + 보유 코인 평가금액)"""
        total = self.order_manager.get_balance_krw()
        for ticker in self.positions:
            try:
                price = pyupbit.get_current_price(ticker)
                qty = self.positions[ticker]['total_qty']
                total += price * qty
            except:
                pass
        return total

    def get_daily_profit(self) -> float:
        """오늘 수익률 계산"""
        if self.initial_capital is None or self.initial_capital == 0:
            return 0.0
        total = self.get_total_asset()
        return (total - self.initial_capital) / self.initial_capital * 100

    def scan_buy(self):
        """전략 스캔 → 매수 신호 있으면 지정가 주문"""
        import pyupbit
        krw = self.order_manager.get_balance_krw()

        # 최대 보유 코인 수 초과 시 스킵
        if len(self.positions) >= self.max_holding:
            return

        # 예산 부족 시 스킵
        if krw < self.budget:
            return

        for ticker in self.tickers:
            if ticker in self.positions:
                continue

            try:
                df = pyupbit.get_ohlcv(ticker, interval="day", count=50)
                if df is None:
                    continue

                df = self.strategy.prepare(df)
                buy_price = self.strategy.get_buy_price(df)

                if buy_price:
                    # 지정가 매수 주문
                    result = self.order_manager.buy_limit_order(
                        ticker, buy_price, self.budget)

                    if result:
                        qty = self.budget / buy_price
                        self.positions[ticker] = {
                            'avg_buy_price': buy_price,
                            'total_qty': qty,
                            'invested': self.budget,
                            'sell_stage': 0,
                            'buy_stage': 1
                        }
                        logger.info(f"📈 매수 주문 | {ticker} | {int(buy_price):,}원")

                time.sleep(0.1)

            except Exception as e:
                logger.error(f"[{ticker}] 스캔 오류: {e}")

    def scan_sell(self):
        """보유 코인 수익률 확인 → 매도/손절 주문"""
        for ticker in list(self.positions.keys()):
            try:
                current_price = pyupbit.get_current_price(ticker)
                pos = self.positions[ticker]
                avg_price = pos['avg_buy_price']
                sell_stage = pos['sell_stage']

                # 매도 목표가
                sell_target = self.strategy.get_sell_price(avg_price, sell_stage)
                # 손절가
                stop_target = self.strategy.get_stop_loss_price(
                    avg_price,
                    current_price=current_price,
                    sell_stage=sell_stage
                )

                profit = (current_price - avg_price) / avg_price * 100
                logger.info(f"📊 {ticker} | 현재가: {int(current_price):,}원 | 수익률: {round(profit, 2)}%")

                # 익절 조건
                if current_price >= sell_target:
                    sell_ratio = self.strategy.get_stage_sell_ratio(sell_stage)
                    sell_qty = pos['total_qty'] * sell_ratio
                    self.order_manager.sell_limit_order(ticker, sell_target, sell_qty)
                    logger.info(f"✅ 익절 주문 | {ticker} | {int(sell_target):,}원")

                    pos['sell_stage'] += 1
                    pos['total_qty'] -= sell_qty

                    # 모든 매도 완료
                    if pos['sell_stage'] >= len(self.strategy.sell_stages):
                        del self.positions[ticker]

                # 손절 조건
                elif current_price <= stop_target:
                    self.order_manager.sell_limit_order(
                        ticker, stop_target, pos['total_qty'])
                    logger.info(f"🛑 손절 주문 | {ticker} | {int(stop_target):,}원")
                    del self.positions[ticker]

            except Exception as e:
                logger.error(f"[{ticker}] 매도 스캔 오류: {e}")

    def run(self, daily_loss_limit: float = -10.0):
        """자동매매 메인 루프"""
        self.initial_capital = self.get_total_asset()
        logger.info(f"=== 자동매매 봇 시작 ===")
        logger.info(f"전략: {self.strategy.name}")
        logger.info(f"초기자산: {int(self.initial_capital):,}원")
        logger.info(f"매수 예산: {int(self.budget):,}원")
        logger.info(f"최대 보유 코인: {self.max_holding}개")

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
                    logger.info(f"🛑 일일 손실 한도 초과 ({round(daily_profit, 2)}%) 봇 중지")
                    break

                total_asset = self.get_total_asset()
                logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] "
                           f"총자산: {int(total_asset):,}원 | "
                           f"오늘 수익률: {round(daily_profit, 2)}%")

                # 매도 스캔
                self.scan_sell()

                # 매수 스캔
                self.scan_buy()

                logger.info(f"⏳ {self.scan_interval}초 대기 중...\n")
                time.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"[ERROR] {e}")
                time.sleep(60)