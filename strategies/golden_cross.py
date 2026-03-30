# strategies/golden_cross.py - 골든크로스 전략

from strategies.base import BaseStrategy
import pandas as pd

class GoldenCrossStrategy(BaseStrategy):
    """
    골든크로스 전략
    단기 이동평균이 장기 이동평균을 위로 돌파하면 매수
    """

    def __init__(self, short=5, long=20, profit_target=5.0, stop_loss=5.0):
        super().__init__("골든크로스")
        self.short = short                  # 단기 이동평균 기간
        self.long = long                    # 장기 이동평균 기간
        self.profit_target = profit_target  # 목표 수익률 (%)
        self.stop_loss = stop_loss          # 손절 기준 (%)

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """이동평균선 계산"""
        df[f'ma{self.short}'] = df['close'].rolling(self.short).mean()
        df[f'ma{self.long}'] = df['close'].rolling(self.long).mean()
        return df

    def get_buy_price(self, df: pd.DataFrame):
        """
        골든크로스 발생 시 다음날 시가 매수
        골든크로스 아니면 None 반환
        """
        df = self.prepare(df)
        today = df.iloc[-1]
        yesterday = df.iloc[-2]

        # 골든크로스 확인
        golden_cross = (
            today[f'ma{self.short}'] > today[f'ma{self.long}'] and
            yesterday[f'ma{self.short}'] <= yesterday[f'ma{self.long}']
        )

        if golden_cross:
            # 단기 이동평균선 가격에 매수 주문
            return today[f'ma{self.short}']
        
        return None  # 골든크로스 아니면 매수 안 함

    def get_sell_price(self, buy_price: float) -> float:
        """목표 수익률 달성 시 매도"""
        return buy_price * (1 + self.profit_target / 100)

    def get_stop_loss_price(self, buy_price: float) -> float:
        """손절가"""
        return buy_price * (1 - self.stop_loss / 100)