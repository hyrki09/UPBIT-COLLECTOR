# strategies/base.py

from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):

    def __init__(self, name):
        self.name = name
        
        # 분할매수 설정
        self.buy_stages = [
            {'ratio': 1.0, 'price_offset': 0.0}
        ]

        # 분할매도 설정
        self.sell_stages = [
            {'ratio': 1.0, 'profit': 0.05}
        ]

        # 손절 설정
        self.stop_loss_ratio = 0.05

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    @abstractmethod
    def get_buy_price(self, df: pd.DataFrame):
        """1차 매수 기준가 반환 (None이면 매수 안 함)"""
        pass

    def get_stage_buy_price(self, prev_buy_price: float, stage: int = 0) -> float:
        """
        stage번째 매수 목표가 반환
        방식 2: 직전 매수가 기준으로 계산
        prev_buy_price: 직전 매수가
        """
        offset = self.buy_stages[stage]['price_offset']
        return prev_buy_price * (1 + offset)

    def get_stage_buy_ratio(self, stage: int = 0) -> float:
        """stage번째 매수 비율 반환"""
        return self.buy_stages[stage]['ratio']

    def get_sell_price(self, avg_buy_price: float, stage: int = 0) -> float:
        """stage번째 매도 목표가 반환 (평균 매수가 기준)"""
        profit = self.sell_stages[stage]['profit']
        return avg_buy_price * (1 + profit)

    def get_stage_sell_ratio(self, stage: int = 0) -> float:
        """stage번째 매도 비율 반환"""
        return self.sell_stages[stage]['ratio']

    def get_stop_loss_price(self, buy_price: float,
                             current_price: float = None,
                             sell_stage: int = 0) -> float:
        """
        손절가 반환
        sell_stage: 몇 차 익절했는지에 따라 손절가 변경
        current_price: 현재가 (트레일링 스탑용)
        기본: 매수가 기준 -stop_loss_ratio%
        """
        return buy_price * (1 - self.stop_loss_ratio)