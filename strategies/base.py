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
        """데이터 전처리"""
        return df

    def check_precondition(self, df: pd.DataFrame,
                            market_df: pd.DataFrame = None) -> bool:
        """
        전제조건 확인
        df: 현재 종목 데이터
        market_df: 시장 기준 데이터 (예: BTC 데이터)
        기본: 항상 True (전제조건 없음)
        자식 클래스에서 오버라이드해서 사용
        """
        return True

    @abstractmethod
    def get_buy_price(self, df: pd.DataFrame,
                    current_price: float = None):
        """
        매수 목표가 반환
        current_price 없으면 → 종가 기준 (백테스트)
        current_price 있으면 → 현재가 기준 (실시간 봇)
        None 반환 시 매수 안 함
        """
        pass

    def get_stage_buy_price(self, prev_buy_price: float, stage: int = 0) -> float:
        """직전 매수가 기준으로 stage번째 매수 목표가 반환"""
        offset = self.buy_stages[stage]['price_offset']
        return prev_buy_price * (1 + offset)

    def get_stage_buy_ratio(self, stage: int = 0) -> float:
        """stage번째 매수 비율 반환"""
        return self.buy_stages[stage]['ratio']

    def get_sell_price(self, avg_buy_price: float, stage: int = 0) -> float:
        """stage번째 매도 목표가 반환"""
        profit = self.sell_stages[stage]['profit']
        return avg_buy_price * (1 + profit)

    def get_stage_sell_ratio(self, stage: int = 0) -> float:
        """stage번째 매도 비율 반환"""
        return self.sell_stages[stage]['ratio']

    def get_stop_loss_price(self, buy_price: float,
                             current_price: float = None,
                             sell_stage: int = 0) -> float:
        """손절가 반환"""
        return buy_price * (1 - self.stop_loss_ratio)
    
    # base.py에 추가
    def is_watchable(self, df: pd.DataFrame,
                    current_price: float) -> bool:
        """
        관심종목 등록 조건
        기본: 매수 목표가 10% 이내
        전략마다 오버라이드 가능
        """
        buy_price = self.get_buy_price(df)
        if buy_price is None:
            return False
        diff = (current_price - buy_price) / buy_price * 100
        return diff <= 10.0  # 기본 10% 이내