import pyupbit
from config import ACCESS_KEY, SECRET_KEY

#* 업비트 연결
def connect_upbit():
    try:
        upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)
        print("업비트 연결성공")
        return upbit
    except Exception as e:
        print(f"X 연결 실패!: {e}")
        return None
    
#* 잔고 조회
def get_balance(upbit):
    krw = upbit.get_balance("KRW")
    print(f"\n 원화 잔고: {int(krw):,} 원")

    # 보유 코인 조회
    balances = upbit.get_balances()
    for b in balances:
        print(b)
        if b['currency'] != 'KRW' and float(b['balance']) > 0:
            try:
                ticker = f"KRW-{b['currency']}"
                price = pyupbit.get_current_price(ticker)
                value = float(b['balance']) * price
                print(f"{ticker}: {float(b['balance'])}개 | 평가금액: {int(value):,}원")
            except Exception as e:
                pass
                # print(f"[ERROR]  {b['currency']}: {e}")

if __name__ == "__main__":
    upbit = connect_upbit()
    if upbit:
        get_balance(upbit)