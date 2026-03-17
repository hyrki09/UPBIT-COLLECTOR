import pandas as pd

#* CSV에서 데이터 불러오기
def load_data(ticker):
    df = pd.read_csv(f"data/{ticker}.csv", index_col=0, parse_dates=True)
    return df

#* 이동평균선 추가
def add_moving_averages(df, short=7, long=30):
    df[f'ma{short}'] = df['close'].rolling(short).mean()
    df[f'ma{long}'] = df['close'].rolling(long).mean()
    return df

#* 매수/매도 신호 생성
def generate_signals(df, short=7, long=30):
    df['signal'] = 0
    
    for i in range(1, len(df)):
        # 골든 크로스 : 단기선이 장기선을 위로 돌파 -> 매수
        if df[f'ma{short}'].iloc[i] > df[f'ma{long}'].iloc[i] and \
            df[f'ma{short}'].iloc[i-1] <= df[f'ma{long}'].iloc[i-1]:
            df.iloc[i, df.columns.get_loc('signal')] = 1
        # 데드크로스 : 단기선이 장기선아래로 돌파 -> 매도    
        elif df[f'ma{short}'].iloc[i] < df[f'ma{long}'].iloc[i] and \
            df[f'ma{short}'].iloc[i-1] >= df[f'ma{long}'].iloc[i-1]:
             df.iloc[i, df.columns.get_loc('signal')] = -1

    return df

if __name__ == "__main__":
    ticker = "KRW-BTC"
    df = load_data(ticker)
    df = add_moving_averages(df)
    df = generate_signals(df)

    # 매수/매도 신호만 출력
    signals = df[df['signal'] != 0][['close', 'signal']]
    signals['action'] = signals['signal'].map({1: '📈 매수', -1: '📉 매도'})
    print(f"\n=== {ticker} 골든크로스 신호 ===")
    print(signals[['close', 'action']])
    print(f"\n총 {len(signals)}번 신호 발생")

            



# df = load_data("KRW-BTC")

# print(df)