import pyupbit
import time
import logging

from datetime import datetime, date
from config import ACCESS_KEY, SECRET_KEY

#* 로그 설정
logging.basicConfig(
    filename='trading.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    encoding='utf-8'
)

#* 터미널 출력 + 파일 저장
def log(msg):
    print(msg)
    logging.info(msg)

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
        # print(b)
        if b['currency'] != 'KRW' and float(b['balance']) > 0:
            try:
                ticker = f"KRW-{b['currency']}"
                price = pyupbit.get_current_price(ticker)
                value = float(b['balance']) * price
                print(f"{ticker}: {float(b['balance'])}개 | 평가금액: {int(value):,}원")
            except Exception as e:
                pass
                # print(f"[ERROR]  {b['currency']}: {e}")

#* 과거 데이터 가져오기
def get_ohlcv(ticker, interval='day', count=30):
    try:
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
        return df
    except Exception as e:
        print(f"[ERROR] {ticker} 데이터 조회 실패 : {e}")
        return None

#* 전략 확인 - 골든크로스 발생여부    
def check_strategy(ticker, short=5, long=20):
    df = get_ohlcv(ticker)
    if df is None:
        return False
    
    # 이동평균선
    df['ma_short'] = df['close'].rolling(short).mean()
    df['ma_long'] = df['close'].rolling(long).mean()

    today = df.iloc[-1]
    yesterday = df.iloc[-2]

    golden_cross = (today['ma_short'] > today['ma_long'] and yesterday['ma_short'] <= yesterday['ma_long'])

    return golden_cross

#* 시장가 매수
def buy_market_order(upbit, ticker, amount):
    try:
        result = upbit.buy_market_order(ticker, amount)
        print(f"✅ 매수 완료 | {ticker} | {amount:,}원")
        return result
    except Exception as e:
        print(f"❌ 매수 실패 | {ticker} | {e}")
        return None

#* 시장가 매도 (전량)
def sell_market_order(upbit, ticker):
    try:
        balance = upbit.get_balance(ticker.split('-')[1])
        if balance > 0:
            result = upbit.sell_market_order(ticker, balance)
            print(f"매도 완료 | {ticker} | {balance}개")
            return result
        else:
            print(f"보유 수량 없음 | {ticker}")
            return None
    except Exception as e:
        print(f"매도 실패 | {ticker} | {e}")
        return None

#* 현재 수익률 조회
def get_current_profit(upbit, ticker):
    try:
        balances = upbit.get_balances()
        print(balances)
        for b in balances:
            if b['currency'] == ticker.split('-')[1]:
                avg_buy_price = float(b['avg_buy_price']) # 평균 매수가

                if avg_buy_price == 0:
                    print(f"{ticker} 평균 매수가 없음 (에어드랍 또는 입금된 코인)")
                    return 0
                current_price = pyupbit.get_current_price(ticker)
                profit = (current_price - avg_buy_price) / avg_buy_price * 100
                print(f"{ticker} 수익률 : {round(profit, 2)}")
                return profit
    except Exception as e:
        print(f"[ERROR] {e}")
    return 0

#* 자동매매 메인루프
# budget : 1회 매수 금액 (원)
# profit_target: 목표 수익률 (%)
# stop_loss: 손절 기준 (%)
# daily_loss_limit: 하루 최대 손실 한도 (%)
def run_bot(upbit, budget=10000, profit_target=5.0, stop_loss=-5.0, daily_loss_limit=-10.0):
    # 시작 자본 기록
    initial_krw = upbit.get_balance("KRW")
    log(f"💰 시작 자본: {int(initial_krw):,}원")

    holding = {}
    start_date = date.today()

    while True:
        try:
            # 날짜 바뀌면 시작 자본 초기화
            if date.today() != start_date:
                initial_krw = upbit.get_balance("KRW")
                start_date = date.today()
                log("📅 날짜 변경 - 시작 자본 초기화")

            # 현재 총 자산 계산 (원화 + 보유 코인 평가금액)
            krw = upbit.get_balance("KRW")
            total_asset = krw  # 원화 잔고

            for ticker in holding.keys():
                current_price = pyupbit.get_current_price(ticker)
                amount = holding[ticker]['amount']
                total_asset += current_price * amount  # 코인 평가금액 추가

            # 하루 수익률 = (현재 총자산 - 시작 자본) / 시작 자본 * 100
            daily_profit = (total_asset - initial_krw) / initial_krw * 100

            log(f"[{datetime.now().strftime('%H:%M:%S')}] 💰 총자산: {int(total_asset):,}원 | 오늘 수익률: {round(daily_profit, 2)}%")

            # 하루 최대 손실 한도 초과 시 봇 중지
            if daily_profit <= daily_loss_limit:
                log(f"🛑 하루 최대 손실 한도 초과! ({round(daily_profit, 2)}%) 봇 중지")
                break

            # 보유 코인 수익률 확인 → 매도
            for ticker in list(holding.keys()):
                current_price = pyupbit.get_current_price(ticker)
                buy_price = holding[ticker]['buy_price']
                amount = holding[ticker]['amount']
                profit = (current_price - buy_price) / buy_price * 100

                log(f"  📊 {ticker} 수익률: {round(profit, 2)}%")

                if profit >= profit_target:
                    sell_market_order(upbit, ticker)
                    del holding[ticker]
                    log(f"  ✅ {ticker} 익절! 수익률: {round(profit, 2)}%")

                elif profit <= stop_loss:
                    sell_market_order(upbit, ticker)
                    del holding[ticker]
                    log(f"  🛑 {ticker} 손절! 수익률: {round(profit, 2)}%")

            # 전략 스캔 → 매수
            if krw >= budget:
                tickers = pyupbit.get_tickers(fiat="KRW")
                for ticker in tickers:
                    if ticker in holding:
                        continue
                    if check_strategy(ticker):
                        log(f"\n  📈 골든크로스 발생! {ticker}")
                        result = buy_market_order(upbit, ticker, budget)
                        if result:
                            current_price = pyupbit.get_current_price(ticker)
                            amount = budget / current_price  # 매수 수량
                            holding[ticker] = {
                                'buy_price': current_price,
                                'amount': amount  # 수량도 기록!
                            }
                    time.sleep(0.1)

            log(f"  ⏳ 5분 대기 중...\n")
            time.sleep(300)

        except Exception as e:
            log(f"[ERROR] {e}")
            time.sleep(60)


if __name__ == "__main__":
    upbit = connect_upbit()
    if upbit:
        get_balance(upbit)

        # 주요 코인 전략 확인
        # print("\n=== 전략 스캔 ===")
        # watchlist = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
        # for ticker in watchlist:
        #     result = check_strategy(ticker)
        #     print(f"{ticker} : {'골든크로스!' if result else '대기중'}")
        #     time.sleep(0.1)

        # print("\n === 수익률 확인 ===")
        # get_current_profit(upbit, "KRW-VTHO")

        
        # ⚠️ 실제 매매 전 잔고 확인 필수!
        print("\n⚠️ 자동매매를 시작합니다. 잔고를 확인하세요.")
        print("시작하려면 Enter, 취소하려면 Ctrl+C")
        input()
        
        
        run_bot(
            upbit,
            budget=10000,        # 1회 매수 10,000원
            profit_target=5.0,   # 5% 익절
            stop_loss=-5.0,      # -5% 손절
            daily_loss_limit=-10.0  # 하루 -10% 시 봇 중지
        )
