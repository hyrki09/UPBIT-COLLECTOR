# 업비트 시세 수집기 + 시각화

업비트 전체 코인 시세를 수집하고 차트로 시각화하는 프로그램

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
- `config.py`    - 설정값
- `data/`        - 수집된 코인별 CSV (로컬 생성)

## 실행 방법
```bash
# 1. 과거 데이터 수집
python collector.py

# 2. 데이터 분석
python analyzer.py

# 3. 차트 보기
python chart.py
```