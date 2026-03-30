# strategies/base.py - 모든 전략의 기본 클래스

from abc import ABC, abstractmethod
import pandas as pd

#* 모든 전략이 상속받는 기본 클래스
class BaseStrategy(ABC):

    def __init__(self, name):
        self.name = name  # 전략 이름
    
    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 전처리 - 필요하면 자식 클래스에서 오버라이드"""
        return df

    @abstractmethod
    def get_buy_price(self, df) -> float:     
        """매수 목표가 반환 (None이면 매수 안 함)"""
        pass

    @abstractmethod
    def get_sell_price(self, buy_price: float) -> float:
        """매도 목표가 반환"""
        pass

    @abstractmethod
    def get_stop_loss_price(self, buy_price: float) -> float:
        """손절가 반환"""
        pass