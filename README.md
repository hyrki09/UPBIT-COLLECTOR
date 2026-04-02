# 업비트 자동매매 프레임워크

업비트 코인 자동매매 프레임워크
시세 수집 → 시각화 → 백테스트 → 자동매매까지 한 번에!

## 실행 환경
- Python 3.9.9
- 업비트 API (pyupbit)

## 설치 방법
```bash
pip install -r requirements.txt
```

## 프로젝트 구조
```
upbit-collector/
├── core/
│   ├── backtest.py  # 백테스터 (분할매수/매도, 시가체결)
│   ├── bot.py       # 자동매매 봇
│   ├── order.py     # 주문 처리
│   └── updater.py   # 데이터 업데이터
├── strategies/
│   ├── base.py         # 전략 기본 클래스
│   └── golden_cross.py # 골든크로스 전략
├── utils/
│   └── logger.py    # 로그 관리
├── data/
│   └── day/         # 코인별 일봉 데이터
├── logs/            # 거래 로그
├── main.py          # 실행 진입점
└── config.py        # 설정값
```

## 실행 방법
```bash
# 1. 데이터 업데이트
python core/updater.py

# 2. 백테스트
python main.py

# 3. 자동매매 봇
python bot.py
```

## 백테스트 결과 (골든크로스 MA5/MA20 기준 2025-01-01 ~ 2026-03-15)
| 티커 | 전략 수익률 | Buy&Hold | 승률 |
|------|------------|----------|------|
| KRW-SOL | 9.61% | -55.15% | 65.0% |
| KRW-DOGE | 7.34% | -70.76% | 70.59% |
| KRW-ADA | 6.86% | -71.82% | 65.22% |
| KRW-BTC | 5.77% | -25.61% | 73.68% |
| KRW-ETH | 2.04% | -38.32% | 65.0% |
| KRW-XRP | 0.19% | -40.33% | 58.33% |

## 전략 추가 방법
```python
# strategies/my_strategy.py 생성
from strategies.base import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("내 전략")
        self.buy_stages = [...]
        self.sell_stages = [...]

    def get_buy_price(self, df):
        # 매수 조건 구현
        ...
```