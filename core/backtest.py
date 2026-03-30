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
                 interval: str = "day", initial_capital: float = 1000000):
        self.strategy = strategy
        self.ticker = ticker
        self.interval = interval
        self.initial_capital = initial_capital

    def load_data(self) -> pd.DataFrame:
        """CSV에서 데이터 불러오기"""
        df = pd.read_csv(f"data/{self.interval}/{self.ticker}.csv",
                        index_col=0, parse_dates=True)
        return df

    def run(self):
        """백테스트 실행"""
        df = self.load_data()
        df = self.strategy.prepare(df)

        capital = self.initial_capital
        position = 0
        buy_price = 0
        buy_target = None   # 매수 목표가
        sell_target = None  # 매도 목표가
        stop_target = None  # 손절가
        trades = []

        for i in range(1, len(df)):
            current_df = df.iloc[:i+1]
            candle = df.iloc[i]  # 오늘 캔들 (시가/고가/저가/종가)

            if position == 0:
                # 매수 목표가 계산
                buy_target = self.strategy.get_buy_price(current_df)

                if buy_target:
                    # 오늘 캔들 안에서 체결 가능한지 확인
                    # 저가 <= 매수목표가 <= 고가 이면 체결!
                    if candle['low'] <= buy_target <= candle['high']:
                        position = capital / buy_target
                        buy_price = buy_target
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
                # 매도 확인 (고가 >= 매도목표가)
                if candle['high'] >= sell_target:
                    capital = position * sell_target
                    profit = (sell_target - buy_price) / buy_price * 100
                    trades.append({
                        'date': df.index[i],
                        'action': '익절',
                        'price': int(sell_target),
                        'profit': round(profit, 2)
                    })
                    position = 0
                    sell_target = None
                    stop_target = None

                # 손절 확인 (저가 <= 손절가)
                elif candle['low'] <= stop_target:
                    capital = position * stop_target
                    profit = (stop_target - buy_price) / buy_price * 100
                    trades.append({
                        'date': df.index[i],
                        'action': '손절',
                        'price': int(stop_target),
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

        # 승률 계산
        sold_trades = [t for t in trades if t['action'] in ['익절', '손절']]
        win_trades = [t for t in sold_trades if t['profit'] > 0]
        win_rate = len(win_trades) / len(sold_trades) * 100 if sold_trades else 0

        return {
            'strategy': self.strategy.name,
            'ticker': self.ticker,
            'total_return': round(total_return, 2),
            'bnh_return': round(bnh, 2),
            'win_rate': round(win_rate, 2),
            'trades': trades
        }

    def print_result(self, result):
        """결과 출력"""
        print(f"\n=== {result['ticker']} {result['strategy']} 백테스트 결과 ===")
        for t in result['trades']:
            if t['action'] == '매수':
                print(f"{t['date'].date()} 매수 | {t['price']:,}원")
            else:
                print(f"{t['date'].date()} {t['action']} | {t['price']:,}원 | 수익률: {t['profit']}%")

        print(f"\n💰 전략 수익률: {result['total_return']}%")
        print(f"📊 Buy & Hold:  {result['bnh_return']}%")
        print(f"🎯 승률: {result['win_rate']}%")


if __name__ == "__main__":
    from strategies.golden_cross import GoldenCrossStrategy

    strategy = GoldenCrossStrategy(short=5, long=20, 
                                    profit_target=5.0, stop_loss=5.0)
    bt = Backtest(strategy=strategy, ticker="KRW-BTC", interval="day")
    result = bt.run()
    bt.print_result(result)