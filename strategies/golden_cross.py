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

        # 분할매수 설정 (직전 매수가 기준)
        self.buy_stages = [
            {'ratio': 0.3, 'price_offset': 0.0},    # 1차: 기준가에 30%
            {'ratio': 0.3, 'price_offset': -0.03},  # 2차: 직전 매수가 -3%에 30%
            {'ratio': 0.3, 'price_offset': -0.03},  # 3차: 직전 매수가 -3%에 30%
        ]

        # 분할매도 설정
        self.sell_stages = [
            {'ratio': 0.5, 'profit': 0.03},  # 1차: 평균매수가 +3% 시 50%
            {'ratio': 0.5, 'profit': 0.05},  # 2차: 평균매수가 +5% 시 나머지
        ]

        # 손절 설정
        self.stop_loss_ratio = 0.05  # 기본 -5% 손절

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """이동평균선 계산"""
        df=df.copy()
        df[f'ma{self.short}'] = df['close'].rolling(self.short).mean()
        df[f'ma{self.long}'] = df['close'].rolling(self.long).mean()
        return df

    def get_buy_price(self, df: pd.DataFrame):
        """골든크로스 발생 시 단기 이동평균선 가격 반환"""
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
        """
        익절 차수에 따라 손절가 변경
        0차 익절 전: 매수가 -5%
        1차 익절 후: 본전 보호 (매수가)
        2차 익절 후: 없음 (전량 매도 완료)
        """
        if sell_stage == 0:
            return buy_price * (1 - self.stop_loss_ratio)  # -5%
        elif sell_stage >= 1:
            return buy_price  # 본전 보호