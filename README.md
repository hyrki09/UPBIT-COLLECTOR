# 업비트 시세 수집기

업비트 전체 코인 시세를 수집해서 CSV로 저장하는 프로그램

## 실행 환경
- Python 3.9.9
- 업비트 API (pyupbit)

## 설치 방법
```bash
pip install -r requirements.txt
```

## 실행 방법
```bash
python collector.py
```

## 파일 구조
- `collector.py` - 시세 수집 메인 로직
- `config.py` - 설정값 (수집 코인 목록, 저장 파일명)
- `requirements.txt` - 패키지 목록
- `price_data.csv` - 수집된 시세 데이터 (실행 후 생성)

## 수집 데이터 예시
| timestamp | ticker | price |
|-----------|--------|-------|
| 2026-03-14 16:02:09 | KRW-BTC | 104301000 |
| 2026-03-14 16:02:09 | KRW-ETH | 3067000 |