# 업비트 자동매매 프로젝트

업비트 코인 시세 수집, 시각화, 백테스팅 프로그램

## 실행 환경
- Python 3.9.9
- 업비트 API (pyupbit)

## 설치 방법
```bash
pip install -r requirements.txt
```

## 파일 구조
- `collector.py` - 과거 시세 데이터 수집
- `analyzer.py`  - 데이터 분석 (평균가, 최고가 등)
- `chart.py`     - 차트 시각화 (이동평균선)
- `backtest.py`  - 백테스터 (전략 검증 + 수익률 계산)
- `config.py`    - 설정값
- `data/`        - 수집된 코인별 CSV (로컬 생성)

## 실행 순서
```bash
# 1. 과거 데이터 수집
python collector.py

# 2. 데이터 분석
python analyzer.py

# 3. 차트 보기
python chart.py

# 4. 백테스트
python backtest.py
```

## 백테스트 결과 (KRW-BTC 기준)
| 전략 | 수익률 | 거래횟수 |
|------|--------|--------|
| MA5 vs MA20 | 15.63% | 19번 |
| MA7 vs MA30 | 10.79% | 13번 |
| MA10 vs MA60 | -3.73% | 6번 |
| Buy & Hold | -13.3% | - |