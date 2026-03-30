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
                 start_date: str = None,   # 시작 날짜 "2025-01-01"
                 end_date: str = None):    # 마감 날짜 "2026-01-01"
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

        # 시작 날짜 필터링
        if self.start_date:
            df = df[df.index >= self.start_date]

        # 마감 날짜 필터링
        if self.end_date:
            df = df[df.index <= self.end_date]

        return df

    def run(self):
        """백테스트 실행"""
        df = self.load_data()
        df = self.strategy.prepare(df)

        capital = self.initial_capital
        position = 0
        buy_price = 0
        buy_target = None
        sell_target = None
        stop_target = None
        trades = []

        for i in range(1, len(df)):
            current_df = df.iloc[:i+1]
            candle = df.iloc[i]  # 오늘 캔들

            if position == 0:
                buy_target = self.strategy.get_buy_price(current_df)

                if buy_target:
                    # 시가가 이미 매수목표가 이하면 시가에 체결
                    if candle['open'] <= buy_target:
                        actual_buy = candle['open']
                    # 저가 <= 매수목표가 <= 고가면 목표가에 체결
                    elif candle['low'] <= buy_target <= candle['high']:
                        actual_buy = buy_target
                    else:
                        actual_buy = None

                    if actual_buy:
                        position = capital / actual_buy
                        buy_price = actual_buy
                        capital = 0
                        sell_target = self.strategy.get_sell_price(buy_price)
                        stop_target = self.strategy.get_stop_loss_price(buy_price)

                        trades.append({
                            'date': df.index[i],
                            'action': '매수',
                            'price': int(buy_price),
                            'profit': None
                        })

            elif position > 0:
                # 시가가 이미 매도목표가 이상 → 시가에 체결 (갭 상승)
                if candle['open'] >= sell_target:
                    actual_sell = candle['open']

                # 저가 <= 매도목표가 <= 고가 → 목표가에 체결
                elif candle['low'] <= sell_target <= candle['high']:
                    actual_sell = sell_target

                else:
                    actual_sell = None

                # 손절: 저가가 손절가 이하 → 손절가에 체결
                if candle['low'] <= stop_target and actual_sell is None:
                    actual_sell = stop_target

                if actual_sell:
                    capital = position * actual_sell
                    profit = (actual_sell - buy_price) / buy_price * 100
                    action = '익절' if actual_sell >= buy_price else '손절'
                    trades.append({
                        'date': df.index[i],
                        'action': action,
                        'price': int(actual_sell),
                        'profit': round(profit, 2)
                    })
                    position = 0
                    sell_target = None
                    stop_target = None

            # 현재 보유 중이면 현재가로 평가
        if position > 0:
            capital = position * df['close'].iloc[-1]

        total_return = (capital - self.initial_capital) / self.initial_capital * 100
        bnh = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100

        sold_trades = [t for t in trades if t['action'] in ['익절', '손절']]
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
            if t['action'] == '매수':
                print(f"{t['date'].date()} 매수 | {t['price']:,}원")
            else:
                print(f"{t['date'].date()} {t['action']} | {t['price']:,}원 | 수익률: {t['profit']}%")

        final_capital = self.initial_capital * (1 + result['total_return'] / 100)
        profit_amount = final_capital - self.initial_capital

        print(f"\n💰 최종자산: {int(final_capital):,}원")
        print(f"📈 수익금: {int(profit_amount):,}원")
        print(f"📊 전략 수익률: {result['total_return']}%")
        print(f"📊 Buy & Hold:  {result['bnh_return']}%")
        print(f"🎯 승률: {result['win_rate']}%")


if __name__ == "__main__":
    from strategies.golden_cross import GoldenCrossStrategy

    strategy = GoldenCrossStrategy(short=5, long=20,
                                    profit_target=5.0, stop_loss=5.0)
    bt = Backtest(
        strategy=strategy,
        ticker="KRW-BTC",
        interval="day",
        initial_capital=1000000,    # 초기자산 100만원
        start_date="2025-01-01",    # 시작 날짜
        end_date="2026-03-15"       # 마감 날짜
    )
    result = bt.run()
    bt.print_result(result)