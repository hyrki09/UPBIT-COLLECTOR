import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

#* 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

def load_data(ticker):
    df = pd.read_csv(f"data/{ticker}.csv", index_col=0, parse_dates=True)
    return df

def draw_char(ticker):
    df = load_data(ticker)

    df['ma7'] = df['close'].rolling(7).mean()
    df['ma30'] = df['close'].rolling(30).mean()

    # print(df)

    fig, ax = plt.subplots(figsize=(12, 5)) 

    ax.plot(df.index, df['close'], label='종가', color='blue')
    ax.plot(df.index, df['ma7'], label='7일 이동 평균선', color='orange')
    ax.plot(df.index, df['ma30'], label='30일 이동 평균선', color='red')
    ax.set_title(f"{ticker} 가격차트")
    ax.set_xlabel("날짜")
    ax.set_ylabel("가격 (원)")
    ax.legend()
    ax.grid(True) # 격자 표시

    # print(fig)

    plt.tight_layout()
    plt.show()

#* 여러 코인 차트 한번에 보기
def draw_multiple_charts(tickers):
    fig, axes = plt.subplots(len(tickers), 1, figsize=(12, 5 * len(tickers)))

    for i, ticker in enumerate(tickers):
        df = load_data(ticker)
        

        # 이동평균 계산
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma60'] = df['close'].rolling(60).mean()
        df['ma120'] = df['close'].rolling(120).mean()


        # print(df)
        

        ax = axes[i]
        ax.plot(df.index, df['close'], label='종가', color='blue', alpha=0.5)
        ax.plot(df.index, df['ma5'], label='5일 이동평균', color='green')
        ax.plot(df.index, df['ma10'], label='10일 이동평균', color='black')
        ax.plot(df.index, df['ma20'], label='20일 이동평균', color='cyan')
        ax.plot(df.index, df['ma60'], label='60일 이동평균', color='brown')
        ax.plot(df.index, df['ma120'], label='120일 이동평균', color='midnightblue')

        ax.set_title(f"{ticker} 가격차트")
        ax.set_xlabel("날짜")
        ax.set_ylabel("가격 (원)")
        ax.legend()
        ax.grid(True)
    # print(axes)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    # draw_char("KRW-BTC")
    draw_multiple_charts(["KRW-BTC", "KRW-ETH", "KRW-XRP"])