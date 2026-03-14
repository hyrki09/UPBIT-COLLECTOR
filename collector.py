import pyupbit
import pandas as pd
from datetime import datetime
import time
from config import TICKERS, OUTPUT_FILE


# 수집할 코인 목록
records = []
for ticker in TICKERS:
    try:
        price = pyupbit.get_current_price(ticker)

        records.append({
            "timestamp":datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # 현재 시간
            "ticker":ticker,
            "price":int(price)
        })
        print(f"[{ticker}] {int(price):,}원")
    except Exception as e:
        # 에러가 나면 여기서 처리하고 다음 코인으로 패스
        print(f"[ERROR] {ticker} 수집 실패 : {e}")

    time.sleep(0.1)

# records에 값이 있을 때만 CSV 저장
if records:
    df = pd.DataFrame(records) # 리스트 -> 표 형태 전환
    df.to_csv(OUTPUT_FILE, index=False) # CSV 파일로 저장
    print(f"\n {len(records)}개 저장완료!")
else:
    print("\n 저장할 데이터가 없습니다.")
    

