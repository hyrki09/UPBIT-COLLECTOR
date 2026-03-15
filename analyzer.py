import pandas as pd

#* CSV에서 데이터 가져오기
def load_data(ticker):
    df = pd.read_csv(f"data/{ticker}.csv", index_col=0, parse_dates=True)
    return df

#* 기본 분석
def analyze(ticker):
    df = load_data(ticker)
    
    print(f"\n=== {ticker} 분석 ===")
    print(f"기간 : {df.index[0].date()} ~ {df.index[-1].date()}")
    print(f"현재가 : {int(df['close'].iloc[-1]):,}원")
    print(f"최고가 : {int(df['high'].max()):,}원")
    print(f"최저가 : {int(df['low'].min()):,}원")
    print(f"평균가 : {int(df['close'].mean()):,}원")
    print(f"최근 7일 평균 : {int(df['close'].tail(7).mean()):,}원")
    print(f"최근 30일 평균 : {int(df['close'].tail(30).mean()):,}원")

if __name__ == "__main__":
    for ticker in ["KRW-BTC", "KRW-ETH", "KRW-XRP"]:
        analyze(ticker)
    