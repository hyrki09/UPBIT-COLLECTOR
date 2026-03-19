import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

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

#* 수익률 계산
def calculate_returns(df, initial_capital=1000000):
    capital = initial_capital # 초기 자본
    position = 0 # 보유코인 수량
    buy_price = 0 # 매수가
    trades = [] # 거래 기록

    for i in range(len(df)):
        signal = df['signal'].iloc[i]
        price = df['close'].iloc[i]

        # 매수 신호
        if signal == 1 and position == 0:
            position = capital / price
            buy_price = price
            capital = 0
            trades.append({
                'date' : df.index[i],
                'action': '매수',
                'price' : price,
                'return' : None
            })

        # 매도 신호
        elif signal == -1 and position > 0:
            capital = position * price # 전액 매도
            ret = (price - buy_price) / buy_price * 100  # 수익률
            trades.append({
                'date' : df.index[i],
                'action' : '매도',
                'price' : price,
                'return' : round(ret, 2)
            })
            position = 0

    # 현재 보유 중이면 현재가로 평가
    if position > 0:
        capital = position * df['close'].iloc[-1]

    total_return = (capital - initial_capital) / initial_capital * 100

    return trades, round(total_return, 2)

#* 백테스트 결과 시각화
def plot_backtest(df, trades, initial_capital=1000000):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # 1. 가격 차트 + 매수/매도 시점
    ax1.plot(df.index, df['close'], label='종가', color='blue', alpha=0.5)
    ax1.plot(df.index, df['ma7'], label='5일 이동평균', color='red')
    ax1.plot(df.index, df['ma30'], label='10일 이동평균', color='black')

    for t in trades:
        if t['action'] == '매수':
            ax1.axvline(t['date'], color='green', alpha=0.7, linestyle='--')
            ax1.annotate('매수', xy=(t['date'], t['price']), color='green', fontsize=8)
        else:
            ax1.axvline(t['date'], color='red', alpha=0.7, linestyle='--')
            ax1.annotate('매도', xy=(t['date'], t['price']), color='red', fontsize=8)
    
    ax1.set_title('가격 차트 + 매수/매도 시점')
    ax1.legend() # 차트 오른쪽 위에 있는 범례 표시 , # "종가, 5일 이동평균, 10일 이동평균..."
    ax1.grid(True)

    # 2. 자본금 변화
    capital_history = [initial_capital]
    capital = initial_capital
    position = 0

    for i in range(len(df)):
        signal = df['signal'].iloc[i]
        price = df['close'].iloc[i]

        if signal == 1 and position == 0:
            position = capital / price
            capital = 0
        elif signal == -1 and position > 0:
            capital = price * position
            position = 0

        if position > 0:
            capital_history.append(position * price)
        else:
            capital_history.append(capital)

    ax2.plot(df.index, capital_history[:len(df)], label='자본금', color='green')
    ax2.axhline(initial_capital, color='gray', linestyle='--', label='초기자본')
    ax2.set_title('자본금 변화')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout() # 차트들이 서로 겹치지 않게 자동으로 간격 조정
    plt.show()


if __name__ == "__main__":
    ticker = "KRW-BTC"
    df = load_data(ticker)
    df = add_moving_averages(df)
    df = generate_signals(df)

    trades, total_return =  calculate_returns(df)

    for t in trades:
        if t['action'] == '매도':
            print(f"{t['date'].date()} 매도 | 가격: {int(t['price']):,}원 | 수익률: {t['return']}%")
        else:
            print(f"{t['date'].date()} 매수 | 가격: {int(t['price']):,}원")
    
    print(f"\n💰 최종 수익률: {total_return}%")
    print(f"📊 Buy & Hold 수익률: {round((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100, 2)}%")
            

    plot_backtest(df, trades)

    # # 매수/매도 신호만 출력
    # signals = df[df['signal'] != 0][['close', 'signal']] # True인 행만 필터링해서 가져오기
    # signals['action'] = signals['signal'].map({1: '📈 매수', -1: '📉 매도'})
    # print(f"\n=== {ticker} 골든크로스 신호 ===")
    # print(signals[['close', 'action']])
    # print(f"\n총 {len(signals)}번 신호 발생")



            



# df = load_data("KRW-BTC")

# print(df)