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
        self.positions_file = "positions.json"
        self.pending_orders_file = "pending_orders.json"

        self.positions = {}       # 보유 중인 코인
        self.pending_orders = {}  # 미체결 주문
        self.initial_capital = None
        self.start_date = date.today()

    # ========== 파일 저장/로드 ==========

    def save_positions(self):
        """포지션 저장"""
        with open(self.positions_file, 'w') as f:
            json.dump(self.positions, f, ensure_ascii=False, indent=2)

    def save_pending_orders(self):
        """미체결 주문 저장"""
        with open(self.pending_orders_file, 'w') as f:
            json.dump(self.pending_orders, f, ensure_ascii=False, indent=2)

    def load_positions(self):
        """포지션 로드"""
        if os.path.exists(self.positions_file):
            with open(self.positions_file, 'r') as f:
                self.positions = json.load(f)
            logger.info(f"포지션 로드: {list(self.positions.keys())}")
            self._verify_positions()
        else:
            logger.info("positions.json 없음 → API에서 초기 로드")
            self.load_existing_positions()
            self.save_positions()

    def load_pending_orders(self):
        """
        미체결 주문 로드 + 재시작 시 체결 여부 확인
        """
        if os.path.exists(self.pending_orders_file):
            with open(self.pending_orders_file, 'r') as f:
                self.pending_orders = json.load(f)
            logger.info(f"미체결 주문 로드: {list(self.pending_orders.keys())}")

            # 재시작 시 각 주문 상태 확인
            for ticker in list(self.pending_orders.keys()):
                try:
                    uuid = self.pending_orders[ticker]['uuid']
                    order_info = self.upbit.get_order(uuid)

                    if order_info is None:
                        continue

                    state = order_info.get('state', '')

                    # 체결 완료 → positions로 이동
                    if state == 'done':
                        logger.info(f"재시작 시 체결 확인 | {ticker}")
                        self._on_order_filled(
                            ticker,
                            self.pending_orders[ticker],
                            order_info
                        )
                        del self.pending_orders[ticker]

                    # 취소됨 → 제거
                    elif state == 'cancel':
                        logger.info(f"재시작 시 취소 확인 | {ticker}")
                        del self.pending_orders[ticker]

                    # 미체결 → 유지
                    elif state == 'wait':
                        logger.info(f"미체결 유지 | {ticker} | "
                                f"목표가: {int(self.pending_orders[ticker]['buy_price']):,}원")

                except Exception as e:
                    logger.error(f"[{ticker}] 주문 상태 확인 오류: {e}")

            self.save_pending_orders()

        else:
            # pending_orders.json 없으면 전체 취소!
            logger.info("pending_orders.json 없음 → 미체결 주문 전체 취소")
            self.pending_orders = {}
            self.order_manager.cancel_all_orders()  # 전체 취소!
            self.save_pending_orders()

    def load_watchlist(self) -> dict:
        """관심종목 로드"""
        if os.path.exists(self.watchlist_file):
            with open(self.watchlist_file, 'r') as f:
                return json.load(f)
        return {}

    # ========== 초기화 ==========

    def load_existing_positions(self):
        """API에서 기존 보유 코인 로드"""
        balances = self.upbit.get_balances()
        for b in balances:
            if not isinstance(b, dict):
                continue
            if b['currency'] == 'KRW':
                continue
            if float(b['balance']) <= 0:
                continue

            ticker = f"KRW-{b['currency']}"
            avg_buy_price = float(b['avg_buy_price'])
            qty = float(b['balance'])

            if avg_buy_price == 0:
                continue

            # 시세 조회 불가 코인 스킵
            try:
                price = pyupbit.get_current_price(ticker)
                if price is None:
                    continue
            except:
                continue

            strategy_name = list(self.strategies.keys())[0]
            strategy = self.strategies[strategy_name]
            stage_amount = self.get_buy_amount(strategy)
            invested = avg_buy_price * qty
            buy_stage = round(invested / stage_amount)
            buy_stage = max(1, min(buy_stage, len(strategy.buy_stages)))

            self.positions[ticker] = {
                'strategy': strategy_name,
                'avg_buy_price': avg_buy_price,
                'total_qty': qty,
                'invested': invested,
                'sell_stage': 0,
                'sell_base_qty': qty,
                'stage_amount': stage_amount,
                'prev_buy_price': avg_buy_price,
                'buy_stage': buy_stage
            }
            logger.info(f"기존 보유 | {ticker} | "
                       f"평단가: {int(avg_buy_price):,}원 | "
                       f"{buy_stage}차 매수 상태로 등록")

    def _verify_positions(self):
        """API 잔고 vs positions.json 비교"""
        try:
            balances = self.upbit.get_balances()
            api_tickers = set()

            for b in balances:
                if not isinstance(b, dict):
                    continue
                currency = b.get('currency', '')
                if currency == 'KRW':
                    continue
                if float(b.get('balance', 0)) <= 0:
                    continue
                api_tickers.add(f"KRW-{currency}")

            file_tickers = set(self.positions.keys())

            # 파일에는 있는데 실제로는 없는 코인
            sold_externally = file_tickers - api_tickers
            if sold_externally:
                msg = f"⚠️ 외부 매도 감지: {sold_externally}"
                logger.warning(msg)
                notifier.send(msg)
                for ticker in sold_externally:
                    del self.positions[ticker]
                self.save_positions()

            # API에는 있는데 파일에는 없는 코인
            bought_externally = api_tickers - file_tickers
            if bought_externally:
                msg = f"⚠️ 외부 매수 감지: {bought_externally}"
                logger.warning(msg)
                notifier.send(msg)

                for b in balances:
                    if not isinstance(b, dict):
                        continue
                    currency = b.get('currency', '')
                    ticker = f"KRW-{currency}"

                    # bought_externally에 있는 코인만!
                    if ticker not in bought_externally:
                        continue

                    avg_buy_price = float(b.get('avg_buy_price', 0))
                    qty = float(b.get('balance', 0))

                    if avg_buy_price == 0 or qty <= 0:
                        continue

                    try:
                        price = pyupbit.get_current_price(ticker)
                        if price is None:
                            continue
                    except:
                        continue

                    strategy_name = list(self.strategies.keys())[0]
                    strategy = self.strategies[strategy_name]
                    stage_amount = self.get_buy_amount(strategy)
                    invested = avg_buy_price * qty
                    buy_stage = round(invested / stage_amount)
                    buy_stage = max(1, min(buy_stage, len(strategy.buy_stages)))

                    self.positions[ticker] = {
                        'strategy': strategy_name,
                        'avg_buy_price': avg_buy_price,
                        'total_qty': qty,
                        'invested': invested,
                        'sell_stage': 0,
                        'sell_base_qty': qty,
                        'stage_amount': stage_amount,
                        'prev_buy_price': avg_buy_price,
                        'buy_stage': buy_stage
                    }
                    logger.info(f"외부 매수 코인 등록 | {ticker} | "
                            f"평단가: {int(avg_buy_price):,}원 | "
                            f"{buy_stage}차 매수 상태로 등록")

                self.save_positions()

        except Exception as e:
            logger.error(f"포지션 검증 오류: {e}")

    # ========== 자산 계산 ==========

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
        return krw >= buy_amount * total_stages

    def get_total_asset(self) -> float:
        """총 자산 계산"""
        total = self.order_manager.get_balance_krw()
        for ticker, pos in self.positions.items():
            try:
                price = pyupbit.get_current_price(ticker)
                if price:
                    total += price * pos['total_qty']
            except:
                pass
        return total

    def get_daily_profit(self) -> float:
        """오늘 수익률 계산"""
        if not self.initial_capital:
            return 0.0
        return (self.get_total_asset() - self.initial_capital) / self.initial_capital * 100

    # ========== 주문 체결 처리 ==========

    def _on_order_filled(self, ticker: str, order: dict, order_info: dict):
        """
        주문 체결 시 처리
        → positions에 등록 또는 업데이트
        """
        strategy_name = order['strategy']
        buy_price = float(order_info['price'])
        qty = float(order_info['executed_volume'])
        buy_amount = order['buy_amount']
        buy_stage = order['buy_stage']

        if ticker not in self.positions:
            # 1차 매수 체결
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
        else:
            # 추가 매수 체결
            pos = self.positions[ticker]
            pos['total_qty'] += qty
            pos['invested'] += buy_amount
            pos['avg_buy_price'] = pos['invested'] / pos['total_qty']
            pos['buy_stage'] += 1
            pos['prev_buy_price'] = buy_price
            pos['sell_base_qty'] = pos['total_qty']
            pos['sell_stage'] = 0

        self.save_positions()
        logger.info(f"✅ 체결 완료 | {ticker} | "
                   f"{int(buy_price):,}원 | {buy_stage+1}차")
        notifier.send_buy(ticker, buy_price, buy_amount, buy_stage + 1)

    # ========== 스캔 함수 ==========

    def scan_orders(self, watchlist: dict):
        """
        미체결 주문 모니터링
        1. 체결됐으면 positions 등록
        2. watchlist에서 사라졌으면 주문 취소
        """
        # watchlist에 있는 티커 목록
        watchlist_tickers = []
        for key, items in watchlist.items():
            if key == 'updated_at':
                continue
            if isinstance(items, list):
                watchlist_tickers += [i['ticker'] for i in items]

        for ticker in list(self.pending_orders.keys()):
            try:
                order = self.pending_orders[ticker]
                uuid = order['uuid']

                # 업비트 주문 상태 확인
                order_info = self.upbit.get_order(uuid)
                if order_info is None:
                    continue

                state = order_info.get('state', '')

                # 체결 완료
                if state == 'done':
                    self._on_order_filled(ticker, order, order_info)
                    del self.pending_orders[ticker]
                    self.save_pending_orders()
                    logger.info(f"✅ 주문 체결 | {ticker}")

                # 취소됨
                elif state == 'cancel':
                    del self.pending_orders[ticker]
                    self.save_pending_orders()
                    logger.info(f"주문 취소됨 | {ticker}")

                # 미체결 → watchlist 체크
                elif state == 'wait':
                    # positions에 있는 코인 (추가 매수 주문)
                    # → watchlist 상관없이 유지
                    if ticker in self.positions:
                        continue

                    # 새 코인 (1차 매수 주문)
                    # → watchlist에서 사라지면 취소
                    if ticker not in watchlist_tickers:
                        self.order_manager.cancel_order(uuid)
                        del self.pending_orders[ticker]
                        self.save_pending_orders()
                        logger.info(f"주문 취소 | {ticker} | "
                                   f"바운더리 이탈")

            except Exception as e:
                logger.error(f"[{ticker}] 주문 체크 오류: {e}")

    def scan_buy(self, watchlist: dict):
        """매수 스캔"""
        krw = self.order_manager.get_balance_krw()

        # 1부: 보유 코인 추가 매수 (watchlist 무관!)
        for ticker, pos in list(self.positions.items()):
            try:
                # 이미 주문 걸린 코인 스킵
                if ticker in self.pending_orders:
                    continue

                strategy = self.strategies.get(pos['strategy'])
                if not strategy:
                    continue

                buy_stage = pos['buy_stage']
                if buy_stage >= len(strategy.buy_stages):
                    continue

                buy_amount = pos['stage_amount']
                if krw < buy_amount:
                    continue

                df = pyupbit.get_ohlcv(ticker, interval="day", count=50)
                buy_target = strategy.get_buy_price(
                    df=df,
                    stage=buy_stage,
                    prev_buy_price=pos['prev_buy_price']
                )
                if not buy_target:
                    continue

                try:
                    current_price = pyupbit.get_current_price(ticker)
                except:
                    continue

                # 매수 목표가 5% 이내면 주문
                diff = (current_price - buy_target) / buy_target * 100
                if diff <= 5.0:
                    result = self.order_manager.buy_limit_order(
                        ticker, buy_target, buy_amount)

                    if result:
                        self.pending_orders[ticker] = {
                            'uuid': result['uuid'],
                            'buy_price': buy_target,
                            'buy_amount': buy_amount,
                            'strategy': pos['strategy'],
                            'buy_stage': buy_stage,
                            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        self.save_pending_orders()
                        logger.info(f"📈 {buy_stage+1}차 매수 주문 | "
                                   f"{ticker} | {int(buy_target):,}원")

            except Exception as e:
                logger.error(f"[{ticker}] 추가 매수 오류: {e}")

        # 2부: 새 코인 1차 매수 (watchlist 기반)
        for strategy_name, items in watchlist.items():
            if strategy_name == 'updated_at':
                continue

            strategy = self.strategies.get(strategy_name)
            if not strategy:
                continue

            for item in items:
                ticker = item['ticker']

                # 이미 보유 or 주문 중인 코인 스킵
                if ticker in self.positions:
                    continue
                if ticker in self.pending_orders:
                    continue

                if not self.can_buy(strategy):
                    continue

                buy_amount = self.get_buy_amount(strategy)
                buy_price = item['buy_price']

                try:
                    current_price = pyupbit.get_current_price(ticker)
                except:
                    continue

                # ready True → 즉시 주문
                if item.get('ready', False):
                    result = self.order_manager.buy_limit_order(
                        ticker, buy_price, buy_amount)

                    if result:
                        self.pending_orders[ticker] = {
                            'uuid': result['uuid'],
                            'buy_price': buy_price,
                            'buy_amount': buy_amount,
                            'strategy': strategy_name,
                            'buy_stage': 0,
                            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        self.save_pending_orders()
                        logger.info(f"✅ 1차 매수 주문 | {ticker} | "
                                   f"{int(buy_price):,}원")

                # ready False → 실시간 조건 체크
                else:
                    df = pyupbit.get_ohlcv(ticker, interval="day", count=50)
                    if not strategy.is_ready_to_buy(df, current_price):
                        continue

                    buy_price = strategy.get_buy_price(
                        df=df, stage=0, current_price=current_price)
                    if not buy_price:
                        continue

                    result = self.order_manager.buy_limit_order(
                        ticker, buy_price, buy_amount)

                    if result:
                        self.pending_orders[ticker] = {
                            'uuid': result['uuid'],
                            'buy_price': buy_price,
                            'buy_amount': buy_amount,
                            'strategy': strategy_name,
                            'buy_stage': 0,
                            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        self.save_pending_orders()
                        logger.info(f"📌 1차 매수 주문 | {ticker} | "
                                   f"{int(buy_price):,}원")

    def scan_sell(self):
        """매도 스캔"""
        for ticker in list(self.positions.keys()):
            try:
                pos = self.positions[ticker]
                strategy = self.strategies.get(pos['strategy'])
                if not strategy:
                    continue

                try:
                    current_price = pyupbit.get_current_price(ticker)
                except:
                    logger.info(f"스킵 | {ticker} | 시세 조회 불가")
                    del self.positions[ticker]
                    self.save_positions()
                    continue

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
                    logger.info(f"✅ {sell_stage+1}차 익절 | "
                               f"{ticker} | {int(sell_target):,}원")

                    pos['total_qty'] -= sell_qty
                    pos['invested'] = pos['total_qty'] * avg_price
                    pos['sell_stage'] += 1

                    if pos['sell_stage'] >= len(strategy.sell_stages):
                        if pos['total_qty'] > 0:
                            self.order_manager.sell_limit_order(
                                ticker, current_price, pos['total_qty'])
                        del self.positions[ticker]

                    self.save_positions()

                # 손절
                elif current_price <= stop_target:
                    self.order_manager.sell_limit_order(
                        ticker, stop_target, pos['total_qty'])
                    notifier.send_sell(ticker, stop_target, profit, "손절")
                    logger.info(f"🛑 손절 | {ticker} | "
                               f"{int(stop_target):,}원")
                    del self.positions[ticker]
                    self.save_positions()

            except Exception as e:
                logger.error(f"[{ticker}] 매도 스캔 오류: {e}")

    def run(self, daily_loss_limit: float = -100.0):
        """자동매매 메인 루프"""
        self.load_positions()
        self.load_pending_orders()
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
                    msg = f"🛑 일일 손실 한도 ({round(daily_profit, 2)}%)"
                    logger.info(msg)
                    notifier.send(msg)
                    break

                total_asset = self.get_total_asset()
                logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] "
                           f"총자산: {int(total_asset):,}원 | "
                           f"수익률: {round(daily_profit, 2)}%")

                watchlist = self.load_watchlist()

                self.scan_orders(watchlist)  # 1. 미체결 주문 체크
                self.scan_sell()             # 2. 매도 체크
                self.scan_buy(watchlist)     # 3. 매수 체크

                if datetime.now().hour == 9 and datetime.now().minute == 0:
                    notifier.send_daily_report(
                        total_asset, daily_profit, self.positions)

                logger.info(f"⏳ {self.scan_interval}초 대기 중...\n")
                time.sleep(self.scan_interval)

            except Exception as e:
                logger.error(f"[ERROR] {e}")
                notifier.send_error(str(e))
                time.sleep(60)