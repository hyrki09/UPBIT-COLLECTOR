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

    print(df)

    fig, ax = plt.subplots(figsize=(12, 5)) 

    ax.plot(df.index, df['close'], label='종가', color='blue')
    ax.plot(df.index, df['ma7'], label='7일 이동 평균선', color='orange')
    ax.plot(df.index, df['ma30'], label='30일 이동 평균선', color='red')
    ax.set_title(f"{ticker} 가격차트")
    ax.set_xlabel("날짜")
    ax.set_ylabel("가격 (원)")
    ax.legend()
    ax.grid(True) # 격자 표시

    print(fig)

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    draw_char("KRW-BTC")