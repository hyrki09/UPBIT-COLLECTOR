# strategies/golden_cross.py - 골든크로스 전략

from strategies.base import BaseStrategy
import pandas as pd

class GoldenCrossStrategy(BaseStrategy):
    """
    골든크로스 전략
    단기 이동평균이 장기 이동평균을 위로 돌파하면 매수
    """

    def __init__(self, short=5, long=20):
        super().__init__("골든크로스")
        self.short = short
        self.long = long

        # 분할매수 설정
        self.buy_stages = [
            {'ratio': 0.3, 'price_offset': 0.0},
            {'ratio': 0.3, 'price_offset': -0.03},
            {'ratio': 0.3, 'price_offset': -0.03},
        ]

        # 분할매도 설정
        self.sell_stages = [
            {'ratio': 0.5, 'profit': 0.03},
            {'ratio': 0.5, 'profit': 0.05},
        ]

        self.stop_loss_ratio = 0.05

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """이동평균선 계산"""
        df = df.copy()
        df[f'ma{self.short}'] = df['close'].rolling(self.short).mean()
        df[f'ma{self.long}'] = df['close'].rolling(self.long).mean()
        return df

    def get_buy_price(self, df: pd.DataFrame,
                      current_price: float = None):
        """
        골든크로스 발생 시 단기 이동평균선 가격 반환
        골든크로스 아니면 None 반환
        """
        df = self.prepare(df)
        today = df.iloc[-1]
        yesterday = df.iloc[-2]

        golden_cross = (
            today[f'ma{self.short}'] > today[f'ma{self.long}'] and
            yesterday[f'ma{self.short}'] <= yesterday[f'ma{self.long}']
        )

        if golden_cross:
            return today[f'ma{self.short}']

        return None

    def get_stop_loss_price(self, buy_price: float,
                             current_price: float = None,
                             sell_stage: int = 0) -> float:
        if sell_stage == 0:
            return buy_price * (1 - self.stop_loss_ratio)
        else:
            return buy_price