# core/backtest.py - 프레임워크 백테스터
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 현재 파일(core/backtest.py)의 부모 폴더(upbit-collector)를 경로에 추가
# 그래야 strategies 폴더를 찾을 수 있음

import pandas as pd
import matplotlib.pyplot as plt
from strategies.base import BaseStrategy

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

class Backtest:
    """
    어떤 전략이든 받아서 백테스트 실행
    시가/고가/저가 기반으로 실제 체결 시뮬레이션
    """

    def __init__(self, strategy: BaseStrategy, ticker: str,
                 interval: str = "day",
                 initial_capital: float = 1000000,
                 start_date: str = None,
                 end_date: str = None):
        self.strategy = strategy
        self.ticker = ticker
        self.interval = interval
        self.initial_capital = initial_capital
        self.start_date = start_date
        self.end_date = end_date

    def load_data(self) -> pd.DataFrame:
        """CSV에서 데이터 불러오기 + 날짜 필터링"""
        df = pd.read_csv(f"data/{self.interval}/{self.ticker}.csv",
                        index_col=0, parse_dates=True)
        if self.start_date:
            df = df[df.index >= self.start_date]
        if self.end_date:
            df = df[df.index <= self.end_date]
        return df

    def run(self):
        """백테스트 실행"""
        df = self.load_data()
        df = self.strategy.prepare(df)

        capital = self.initial_capital
        position = None
        buy_stage = 0
        base_buy_price = None
        prev_buy_price = None
        trades = []

        for i in range(1, len(df)):
            current_df = df.iloc[:i+1]
            candle = df.iloc[i]

            # 매수 단계
            if buy_stage < len(self.strategy.buy_stages):

                if buy_stage == 0:
                    base_price = self.strategy.get_buy_price(current_df)
                    if base_price:
                        base_buy_price = base_price
                        prev_buy_price = base_price

                if base_buy_price:
                    buy_target = self.strategy.get_stage_buy_price(
                        prev_buy_price, buy_stage)
                    buy_ratio = self.strategy.get_stage_buy_ratio(buy_stage)

                    if position is None:
                        buy_amount = capital * buy_ratio
                    else:
                        buy_amount = position['stage_amount']

                    actual_buy = None
                    if candle['open'] <= buy_target:
                        actual_buy = candle['open']
                    elif candle['low'] <= buy_target <= candle['high']:
                        actual_buy = buy_target

                    if actual_buy and capital >= buy_amount:
                        qty = buy_amount / actual_buy
                        capital -= buy_amount
                        prev_buy_price = actual_buy

                        if position is None:
                            # 1차 매수
                            position = {
                                'total_qty': qty,
                                'invested': buy_amount,
                                'avg_buy_price': actual_buy,
                                'sell_stage': 0,
                                'stage_amount': buy_amount,
                                'sell_base_qty': qty,  # ← 매도 기준 수량
                            }
                        else:
                            # 2차, 3차 추가 매수
                            position['total_qty'] += qty
                            position['invested'] += buy_amount
                            position['avg_buy_price'] = (
                                position['invested'] / position['total_qty']
                            )
                            # 추가 매수 시 매도 기준 수량 + 매도 차수 초기화!
                            position['sell_base_qty'] = position['total_qty']
                            position['sell_stage'] = 0

                        buy_stage += 1
                        trades.append({
                            'date': df.index[i],
                            'action': f'{buy_stage}차 매수',
                            'price': int(actual_buy),
                            'profit': None
                        })

            # 매도 단계
            if position:
                sell_stage = position['sell_stage']

                if sell_stage < len(self.strategy.sell_stages):
                    avg_price = position['avg_buy_price']

                    stop_target = self.strategy.get_stop_loss_price(
                        avg_price,
                        current_price=candle['close'],
                        sell_stage=sell_stage
                    )
                    sell_target = self.strategy.get_sell_price(avg_price, sell_stage)
                    sell_ratio = self.strategy.get_stage_sell_ratio(sell_stage)

                    actual_sell = None
                    action = None

                    if candle['open'] >= sell_target:
                        actual_sell = candle['open']
                        action = '익절'
                    elif candle['open'] <= stop_target:
                        actual_sell = candle['open']
                        action = '손절'
                    elif candle['low'] <= sell_target <= candle['high']:
                        actual_sell = sell_target
                        action = '익절'
                    elif candle['low'] <= stop_target:
                        actual_sell = stop_target
                        action = '손절'

                    if actual_sell:
                        if action == '손절':
                            # 전량 손절
                            sell_qty = position['total_qty']
                            capital += sell_qty * actual_sell
                            profit = (actual_sell - avg_price) / avg_price * 100
                            trades.append({
                                'date': df.index[i],
                                'action': f'{sell_stage + 1}차 손절',
                                'price': int(actual_sell),
                                'profit': round(profit, 2)
                            })
                            position = None
                            base_buy_price = None
                            prev_buy_price = None
                            buy_stage = 0

                        else:
                            # 분할 익절 (sell_base_qty 기준으로 계산!)
                            sell_qty = position['sell_base_qty'] * sell_ratio
                            
                            # 실제 보유량보다 많으면 보유량만큼만
                            sell_qty = min(sell_qty, position['total_qty'])
                            
                            capital += sell_qty * actual_sell
                            profit = (actual_sell - avg_price) / avg_price * 100
                            trades.append({
                                'date': df.index[i],
                                'action': f'{sell_stage + 1}차 익절',
                                'price': int(actual_sell),
                                'profit': round(profit, 2)
                            })
                            position['total_qty'] -= sell_qty
                            position['invested'] = (
                                position['total_qty'] * avg_price
                            )
                            position['sell_stage'] += 1

                            # 모든 매도 완료
                            if position['sell_stage'] >= len(self.strategy.sell_stages):
                                if position['total_qty'] > 0:
                                    capital += position['total_qty'] * actual_sell
                                position = None
                                base_buy_price = None
                                prev_buy_price = None
                                buy_stage = 0

        # 보유 중인 포지션 현재가로 평가
        if position:
            capital += position['total_qty'] * df['close'].iloc[-1]

        total_return = (capital - self.initial_capital) / self.initial_capital * 100
        bnh = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100

        sold_trades = [t for t in trades if '익절' in t['action'] or '손절' in t['action']]
        win_trades = [t for t in sold_trades if t['profit'] > 0]
        win_rate = len(win_trades) / len(sold_trades) * 100 if sold_trades else 0

        return {
            'strategy': self.strategy.name,
            'ticker': self.ticker,
            'start_date': df.index[0].date(),
            'end_date': df.index[-1].date(),
            'total_return': round(total_return, 2),
            'bnh_return': round(bnh, 2),
            'win_rate': round(win_rate, 2),
            'trades': trades
        }

    def print_result(self, result):
        """결과 출력"""
        print(f"\n=== {result['ticker']} {result['strategy']} 백테스트 결과 ===")
        print(f"📅 기간: {result['start_date']} ~ {result['end_date']}")
        print(f"💵 초기자산: {int(self.initial_capital):,}원")

        for t in result['trades']:
            if '매수' in t['action']:
                print(f"{t['date'].date()} {t['action']} | {t['price']:,}원")
            else:
                print(f"{t['date'].date()} {t['action']} | "
                      f"{t['price']:,}원 | 수익률: {t['profit']}%")

        final_capital = self.initial_capital * (1 + result['total_return'] / 100)
        profit_amount = final_capital - self.initial_capital

        print(f"\n💰 최종자산: {int(final_capital):,}원")
        print(f"📈 수익금: {int(profit_amount):,}원")
        print(f"📊 전략 수익률: {result['total_return']}%")
        print(f"📊 Buy & Hold:  {result['bnh_return']}%")
        print(f"🎯 승률: {result['win_rate']}%")


if __name__ == "__main__":
    from strategies.golden_cross import GoldenCrossStrategy

    strategy = GoldenCrossStrategy(short=5, long=20)
    bt = Backtest(
        strategy=strategy,
        ticker="KRW-BTC",
        interval="day",
        initial_capital=1000000,
        start_date="2025-01-01",
        end_date="2026-03-15"
    )
    result = bt.run()
    bt.print_result(result)