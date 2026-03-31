# main.py - 실행 진입점

import sys
import pyupbit
from core.updater import DataUpdater
from core.backtest import Backtest
from strategies.golden_cross import GoldenCrossStrategy

def update_data(tickers=None, intervals=["day"]):
    """데이터 업데이트"""
    updater = DataUpdater()
    if tickers is None:
        tickers = pyupbit.get_tickers(fiat="KRW")
    updater.update_all(tickers, intervals)

def run_backtest(ticker, strategy, interval="day",
                 initial_capital=1000000,
                 start_date=None, end_date=None):
    """백테스트 실행"""
    bt = Backtest(
        strategy=strategy,
        ticker=ticker,
        interval=interval,
        initial_capital=initial_capital,
        start_date=start_date,
        end_date=end_date
    )
    result = bt.run()
    bt.print_result(result)
    return result

def compare_tickers(tickers, strategy, interval="day",
                    initial_capital=1000000,
                    start_date=None, end_date=None):
    """여러 코인 백테스트 비교"""
    results = []

    for ticker in tickers:
        try:
            bt = Backtest(
                strategy=strategy,
                ticker=ticker,
                interval=interval,
                initial_capital=initial_capital,
                start_date=start_date,
                end_date=end_date
            )
            result = bt.run()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] {ticker}: {e}")

    # 수익률 기준 정렬
    results.sort(key=lambda x: x['total_return'], reverse=True)

    print(f"\n=== 전체 코인 백테스트 결과 ===")
    print(f"{'코인':<15} {'수익률':>8} {'Buy&Hold':>10} {'승률':>8}")
    print("-" * 45)
    for r in results:
        print(f"{r['ticker']:<15} {r['total_return']:>7}% {r['bnh_return']:>9}% {r['win_rate']:>7}%")

    return results


if __name__ == "__main__":
    # 전략 설정
    strategy = GoldenCrossStrategy(short=5, long=20)

    # 1. 단일 코인 백테스트
    print("=== 단일 코인 백테스트 ===")
    run_backtest(
        ticker="KRW-BTC",
        strategy=strategy,
        initial_capital=1000000,
        start_date="2025-01-01",
        end_date="2026-03-15"
    )

    # 2. 여러 코인 비교
    print("\n=== 여러 코인 비교 ===")
    tickers = ["KRW-BTC", "KRW-ETH", "KRW-XRP",
               "KRW-SOL", "KRW-ADA", "KRW-DOGE"]
    compare_tickers(
        tickers=tickers,
        strategy=strategy,
        initial_capital=1000000,
        start_date="2025-01-01",
        end_date="2026-03-15"
    )