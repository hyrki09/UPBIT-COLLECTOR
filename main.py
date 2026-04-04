# main.py - 실행 진입점

import sys
import pyupbit
from dotenv import load_dotenv
import os

load_dotenv()

from core.updater import DataUpdater
from core.backtest import Backtest
from core.scanner import ScannerBot
from core.bot import TradingBot
from strategies.golden_cross import GoldenCrossStrategy
from strategies.down_coin import DownCoinStrategy
from utils.telegram import TelegramNotifier

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

    results.sort(key=lambda x: x['total_return'], reverse=True)

    print(f"\n=== 전체 코인 백테스트 결과 ===")
    print(f"{'티커':<15} {'수익률':>8} {'Buy&Hold':>10} {'승률':>8}")
    print("-" * 45)
    for r in results:
        print(f"{r['ticker']:<15} {r['total_return']:>7}% "
              f"{r['bnh_return']:>9}% {r['win_rate']:>7}%")

    return results

def run_scanner(strategies, market_ticker="KRW-BTC", scan_interval=3600):
    """스캐너 봇 실행"""
    scanner = ScannerBot(
        strategies=strategies,
        market_ticker=market_ticker,
        scan_interval=scan_interval
    )
    scanner.run()

def run_bot(strategies, budget=100000, max_holding=3, scan_interval=10):
    """트레이딩 봇 실행"""
    access = os.getenv("UPBIT_ACCESS_KEY")
    secret = os.getenv("UPBIT_SECRET_KEY")
    upbit = pyupbit.Upbit(access, secret)

    bot = TradingBot(
        upbit=upbit,
        strategies=strategies,
        budget=budget,
        max_holding=max_holding,
        scan_interval=scan_interval
    )
    bot.run()


if __name__ == "__main__":
    # 전략 설정
    # strategy = GoldenCrossStrategy(short=5, long=20)

    # strategies = {
    #     'golden_cross': {
    #         'strategy': strategy,
    #         'tickers': ["KRW-BTC", "KRW-ETH", "KRW-XRP",
    #                    "KRW-SOL", "KRW-ADA", "KRW-DOGE"]
    #     }
    # }

    # # 실행 모드 선택
    # print("=== 업비트 자동매매 ===")
    # print("1. 데이터 업데이트")
    # print("2. 백테스트")
    # print("3. 스캐너 봇")
    # print("4. 트레이딩 봇")
    # mode = input("선택: ")

    # if mode == "1":
    #     update_data()

    # elif mode == "2":
    #     run_backtest(
    #         ticker="KRW-BTC",
    #         strategy=strategy,
    #         initial_capital=1000000,
    #         start_date="2025-01-01",
    #         end_date="2026-03-15"
    #     )

    # elif mode == "3":
    #     run_scanner(strategies)

    # elif mode == "4":
    #     run_bot(
    #         strategies={'golden_cross': strategy},
    #         budget=10000,
    #         max_holding=3,
    #         scan_interval=10
    #     )

    strategy = DownCoinStrategy(ma_period=10, envelope=0.10, stage_ratio=0.05)

    run_backtest(
        ticker="KRW-XRP",
        strategy=strategy,
        initial_capital=1000000,
        start_date="2025-01-01",
        end_date="2026-03-15"
    )

    tickers = ["KRW-XRP", "KRW-ETH", "KRW-SOL", 
           "KRW-ADA", "KRW-DOGE", "KRW-LINK"]

    compare_tickers(
        tickers=tickers,
        strategy=strategy,
        initial_capital=1000000,
        start_date="2025-01-01",
        end_date="2026-03-15"
    )