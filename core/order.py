# core/order.py - 주문 처리

import pyupbit
import time
from utils.logger import Logger

logger = Logger("order")

class OrderManager:
    """
    실제 매수/매도 주문 처리
    잔고 확인, 주문 실행, 체결 확인
    """

    def __init__(self, upbit: pyupbit.Upbit):
        self.upbit = upbit

    def get_balance_krw(self) -> float:
        """원화 잔고 조회"""
        try:
            balance = self.upbit.get_balance("KRW")
            return balance if balance is not None else 0.0
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return 0.0

    def get_balance_coin(self, ticker: str) -> float:
        """코인 잔고 조회"""
        try:
            currency = ticker.split('-')[1]  # KRW-BTC → BTC
            balance = self.upbit.get_balance(currency)
            return balance if balance is not None else 0.0
        except Exception as e:
            logger.error(f"{ticker} 잔고 조회 실패: {e}")
            return 0.0

    def get_avg_buy_price(self, ticker: str) -> float:
        """평균 매수가 조회"""
        try:
            currency = ticker.split('-')[1]
            balances = self.upbit.get_balances()
            for b in balances:
                if b['currency'] == currency:
                    return float(b['avg_buy_price'])
            return 0.0
        except Exception as e:
            logger.error(f"{ticker} 평균매수가 조회 실패: {e}")
            return 0.0

    def buy_limit_order(self, ticker: str, price: float, amount: float):
        """
        지정가 매수 주문
        price: 매수 가격
        amount: 매수 금액 (원화)
        """
        try:
            qty = amount / price  # 매수 수량
            result = self.upbit.buy_limit_order(ticker, price, qty)
            logger.info(f"지정가 매수 주문 | {ticker} | {int(price):,}원 | {round(qty, 4)}개")
            return result
        except Exception as e:
            logger.error(f"매수 주문 실패 | {ticker} | {e}")
            return None

    def sell_limit_order(self, ticker: str, price: float, qty: float = None):
        """
        지정가 매도 주문
        price: 매도 가격
        qty: 매도 수량 (None이면 전량 매도)
        """
        try:
            if qty is None:
                qty = self.get_balance_coin(ticker)  # 전량 매도

            if qty <= 0:
                logger.warning(f"{ticker} 보유 수량 없음")
                return None

            result = self.upbit.sell_limit_order(ticker, price, qty)
            logger.info(f"지정가 매도 주문 | {ticker} | {int(price):,}원 | {round(qty, 4)}개")
            return result
        except Exception as e:
            logger.error(f"매도 주문 실패 | {ticker} | {e}")
            return None

    def cancel_order(self, uuid: str):
        """주문 취소"""
        try:
            result = self.upbit.cancel_order(uuid)
            logger.info(f"주문 취소 | {uuid}")
            return result
        except Exception as e:
            logger.error(f"주문 취소 실패 | {uuid} | {e}")
            return None

    def get_open_orders(self, ticker: str = None):
        """미체결 주문 조회"""
        try:
            orders = self.upbit.get_order(ticker, state="wait")
            return orders if orders else []
        except Exception as e:
            logger.error(f"미체결 주문 조회 실패: {e}")
            return []

    def cancel_all_orders(self, ticker: str = None):
        """미체결 주문 전체 취소"""
        orders = self.get_open_orders(ticker)
        for order in orders:
            self.cancel_order(order['uuid'])
            time.sleep(0.1)
        logger.info(f"미체결 주문 {len(orders)}개 취소 완료")