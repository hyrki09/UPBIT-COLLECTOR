# core/backtest.py - 프레임워크 백테스터
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
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
                 end_date: str = None,
                 market_ticker: str = "KRW-BTC"):  # ← BTC 추가
        self.strategy = strategy
        self.ticker = ticker
        self.interval = interval
        self.initial_capital = initial_capital
        self.start_date = start_date
        self.end_date = end_date
        self.market_ticker = market_ticker

    def load_data(self) -> pd.DataFrame:
        """CSV에서 데이터 불러오기 + 날짜 필터링"""
        df = pd.read_csv(f"data/{self.interval}/{self.ticker}.csv",
                        index_col=0, parse_dates=True)
        if self.start_date:
            df = df[df.index >= self.start_date]
        if self.end_date:
            df = df[df.index <= self.end_date]
        return df

    def load_market_data(self) -> pd.DataFrame:
        """BTC 데이터 로드 (check_precondition용)"""
        path = f"data/{self.interval}/{self.market_ticker}.csv"
        if os.path.exists(path):
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            if self.start_date:
                df = df[df.index >= self.start_date]
            if self.end_date:
                df = df[df.index <= self.end_date]
            return df
        return None

    def calc_mdd(self, capital_history: list) -> float:
        """
        MDD (최대 낙폭) 계산
        전략 쓰다가 최대 얼마나 잃었나?
        """
        if not capital_history:
            return 0.0

        peak = capital_history[0]
        mdd = 0.0

        for capital in capital_history:
            if capital > peak:
                peak = capital
            drawdown = (peak - capital) / peak * 100
            if drawdown > mdd:
                mdd = drawdown

        return round(mdd, 2)

    def calc_sharpe(self, capital_history: list) -> float:
        """
        샤프지수 계산
        리스크 대비 수익이 얼마나 좋나?
        샤프지수 = 수익률 / 변동성
        """
        if len(capital_history) < 2:
            return 0.0

        # 일별 수익률 계산
        returns = []
        for i in range(1, len(capital_history)):
            daily_return = (capital_history[i] - capital_history[i-1]) / capital_history[i-1]
            returns.append(daily_return)

        if not returns:
            return 0.0

        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # 연환산 샤프지수 (365일 기준)
        sharpe = (avg_return / std_return) * np.sqrt(365)
        return round(sharpe, 2)

    def run(self):
        df = self.load_data()
        df = self.strategy.prepare(df)
        market_df = self.load_market_data()  # ← BTC 데이터

        capital = self.initial_capital
        position = None
        buy_stage = 0
        prev_buy_price = None
        trades = []
        capital_history = [capital]  # ← 자산 히스토리

        for i in range(1, len(df)):
            current_df = df.iloc[:i+1]
            candle = df.iloc[i]

            # BTC 전제조건 확인
            if market_df is not None:
                current_market_df = market_df.iloc[:i+1]
                if not self.strategy.check_precondition(
                    current_df, current_market_df):
                    # BTC 조건 안 맞으면 신규 매수 스킵
                    # (보유 중인 코인 매도는 계속)
                    if position is None:
                        capital_history.append(capital)
                        continue

            is_bullish = candle['close'] >= candle['open']

            if is_bullish:
                price_sequence = [
                    ('open', candle['open']),
                    ('low',  candle['low']),
                    ('high', candle['high']),
                ]
            else:
                price_sequence = [
                    ('open', candle['open']),
                    ('high', candle['high']),
                    ('low',  candle['low']),
                ]

            for price_type, current_price in price_sequence:
                just_bought = False

                # 매수 체크
                while buy_stage < len(self.strategy.buy_stages):

                    buy_target = self.strategy.get_buy_price(
                        df=current_df,
                        stage=buy_stage,
                        prev_buy_price=prev_buy_price
                    )

                    if position is None:
                        buy_ratio = self.strategy.get_stage_buy_ratio(buy_stage)
                        buy_amount = capital * buy_ratio
                    else:
                        buy_amount = position['stage_amount']

                    if current_price <= buy_target and capital >= buy_amount:
                        actual_buy = buy_target
                        if price_type == 'open':
                            actual_buy = candle['open']

                        qty = buy_amount / actual_buy
                        capital -= buy_amount
                        prev_buy_price = actual_buy
                        just_bought = True

                        if position is None:
                            position = {
                                'total_qty': qty,
                                'invested': buy_amount,
                                'avg_buy_price': actual_buy,
                                'sell_stage': 0,
                                'sell_base_qty': qty,
                                'stage_amount': buy_amount
                            }
                        else:
                            position['total_qty'] += qty
                            position['invested'] += buy_amount
                            position['avg_buy_price'] = (
                                position['invested'] / position['total_qty'])
                            position['sell_base_qty'] = position['total_qty']
                            position['sell_stage'] = 0

                        buy_stage += 1
                        trades.append({
                            'date': df.index[i],
                            'action': f'{buy_stage}차 매수',
                            'price': int(actual_buy),
                            'profit': None
                        })
                    else:
                        break

                # 매도 체크
                if position and not just_bought:
                    sell_stage = position['sell_stage']

                    while sell_stage < len(self.strategy.sell_stages):
                        avg_price = position['avg_buy_price']
                        sell_target = self.strategy.get_sell_price(
                            avg_price, sell_stage)
                        stop_target = self.strategy.get_stop_loss_price(
                            avg_price,
                            current_price=current_price,
                            sell_stage=sell_stage
                        )
                        sell_ratio = self.strategy.get_stage_sell_ratio(sell_stage)

                        actual_sell = None
                        action = None

                        if price_type in ['open', 'high']:
                            if current_price >= sell_target:
                                actual_sell = sell_target
                                if price_type == 'open':
                                    actual_sell = candle['open']
                                action = '익절'

                        if price_type in ['open', 'low'] and not actual_sell:
                            if current_price <= stop_target:
                                actual_sell = stop_target
                                if price_type == 'open':
                                    actual_sell = candle['open']
                                action = '손절'

                        if actual_sell:
                            if action == '손절':
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
                                prev_buy_price = None
                                buy_stage = 0
                                break

                            else:
                                sell_qty = position['sell_base_qty'] * sell_ratio
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
                                    position['total_qty'] * avg_price)
                                position['sell_stage'] += 1
                                sell_stage += 1

                                if position['sell_stage'] >= len(self.strategy.sell_stages):
                                    if position['total_qty'] > 0:
                                        capital += position['total_qty'] * actual_sell
                                    position = None
                                    prev_buy_price = None
                                    buy_stage = 0
                                    break
                        else:
                            break

            # 하루 끝 자산 기록
            total = capital
            if position:
                total += position['total_qty'] * candle['close']
            capital_history.append(total)

        if position:
            capital += position['total_qty'] * df['close'].iloc[-1]

        total_return = (capital - self.initial_capital) / self.initial_capital * 100
        bnh = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100

        sold_trades = [t for t in trades if '익절' in t['action'] or '손절' in t['action']]
        win_trades = [t for t in sold_trades if t['profit'] > 0]
        win_rate = len(win_trades) / len(sold_trades) * 100 if sold_trades else 0

        # MDD, 샤프지수 계산
        mdd = self.calc_mdd(capital_history)
        sharpe = self.calc_sharpe(capital_history)

        return {
            'strategy': self.strategy.name,
            'ticker': self.ticker,
            'start_date': df.index[0].date(),
            'end_date': df.index[-1].date(),
            'total_return': round(total_return, 2),
            'bnh_return': round(bnh, 2),
            'win_rate': round(win_rate, 2),
            'mdd': mdd,          # ← 추가
            'sharpe': sharpe,    # ← 추가
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
        print(f"📉 MDD: {result['mdd']}%")         # ← 추가
        print(f"⚡ 샤프지수: {result['sharpe']}")   # ← 추가

    def plot_result(self, result):
        """백테스트 결과 차트 (Plotly)"""
        from chart_analysis import draw_envelope_chart

        draw_envelope_chart(
            ticker=self.ticker,
            ma_period=self.strategy.ma_period if hasattr(self.strategy, 'ma_period') else 10,
            envelope=self.strategy.envelope if hasattr(self.strategy, 'envelope') else 0.10,
            interval=self.interval,
            start_date=str(self.start_date) if self.start_date else None,
            end_date=str(self.end_date) if self.end_date else None,
            trades=result['trades']
        )


# 멀티코인 백테스트
class MultiBacktest:
    """
    여러 코인 동시 백테스트
    결과 비교 및 랭킹 출력
    """

    def __init__(self, strategy: BaseStrategy,
                 tickers: list,
                 interval: str = "day",
                 initial_capital: float = 1000000,
                 start_date: str = None,
                 end_date: str = None,
                 market_ticker: str = "KRW-BTC"):
        self.strategy = strategy
        self.tickers = tickers
        self.interval = interval
        self.initial_capital = initial_capital
        self.start_date = start_date
        self.end_date = end_date
        self.market_ticker = market_ticker

    def run(self) -> list:
        """전체 코인 백테스트 실행"""
        results = []

        for ticker in self.tickers:
            try:
                bt = Backtest(
                    strategy=self.strategy,
                    ticker=ticker,
                    interval=self.interval,
                    initial_capital=self.initial_capital,
                    start_date=self.start_date,
                    end_date=self.end_date,
                    market_ticker=self.market_ticker
                )
                result = bt.run()
                results.append(result)
                print(f"✅ {ticker} 완료")
            except Exception as e:
                print(f"❌ {ticker} 오류: {e}")

        # 수익률 기준 정렬
        results.sort(key=lambda x: x['total_return'], reverse=True)
        return results

    def print_results(self, results: list):
        """결과 비교 출력"""
        print(f"\n=== 전체 코인 백테스트 결과 ===")
        print(f"{'티커':<15} {'수익률':>8} {'B&H':>8} "
              f"{'승률':>8} {'MDD':>8} {'샤프':>8}")
        print("-" * 60)

        for r in results:
            print(f"{r['ticker']:<15} "
                  f"{r['total_return']:>7}% "
                  f"{r['bnh_return']:>7}% "
                  f"{r['win_rate']:>7}% "
                  f"{r['mdd']:>7}% "
                  f"{r['sharpe']:>8}")


if __name__ == "__main__":
    from strategies.down_coin import DownCoinStrategy

    strategy = DownCoinStrategy(ma_period=10, envelope=0.10, stage_ratio=0.05)

    # 단일 코인 백테스트
    bt = Backtest(
        strategy=strategy,
        ticker="KRW-XRP",
        interval="day",
        initial_capital=1000000,
        start_date="2025-01-01",
        end_date="2026-04-05"
    )
    result = bt.run()
    bt.print_result(result)
    bt.plot_result(result)

    # 멀티코인 백테스트
    tickers = ["KRW-XRP", "KRW-ETH", "KRW-ADA",
               "KRW-LINK", "KRW-SOL", "KRW-DOGE"]

    multi = MultiBacktest(
        strategy=strategy,
        tickers=tickers,
        interval="day",
        initial_capital=1000000,
        start_date="2025-01-01",
        end_date="2026-04-05"
    )
    results = multi.run()
    multi.print_results(results)