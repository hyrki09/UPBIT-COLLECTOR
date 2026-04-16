# chart_analysis.py

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def draw_envelope_chart(ticker, ma_period=10, envelope=0.10,
                        interval="day", start_date=None, end_date=None,
                        trades=None):  # ← trades 파라미터 추가
    """
    캔들차트 + 이평선 + 엔벨로프 + 백테스트 매수/매도 시점
    """
    path = f"data/{interval}/{ticker}.csv"
    if not os.path.exists(path):
        print(f"[ERROR] {path} 파일 없음")
        return

    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.columns = [c.lower() for c in df.columns]

    if start_date:
        df = df[df.index >= start_date]
    if end_date:
        df = df[df.index <= end_date]

    # 이평선 + 엔벨로프 계산
    df['ma'] = df['close'].rolling(ma_period).mean()
    df['upper'] = df['ma'] * (1 + envelope)
    df['lower'] = df['ma'] * (1 - envelope)
    df['buy_target'] = df['lower'] * (1 - envelope)

    # 서브플롯
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.8, 0.2]
    )

    # 캔들차트
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='캔들',
            increasing_line_color='red',
            decreasing_line_color='blue',
        ),
        row=1, col=1
    )

    # 이평선
    fig.add_trace(
        go.Scatter(x=df.index, y=df['ma'],
                  name=f'MA{ma_period}',
                  line=dict(color='orange', width=1.5)),
        row=1, col=1
    )

    # 상단선
    fig.add_trace(
        go.Scatter(x=df.index, y=df['upper'],
                  name=f'상단선(+{int(envelope*100)}%)',
                  line=dict(color='blue', width=1)),
        row=1, col=1
    )

    # 하단선
    fig.add_trace(
        go.Scatter(x=df.index, y=df['lower'],
                  name=f'하단선(-{int(envelope*100)}%)',
                  line=dict(color='red', width=1)),
        row=1, col=1
    )

    # 매수 목표가
    fig.add_trace(
        go.Scatter(x=df.index, y=df['buy_target'],
                  name='매수목표가',
                  line=dict(color='purple', width=1, dash='dash')),
        row=1, col=1
    )

    # 거래량
    colors = ['red' if c >= o else 'blue'
              for c, o in zip(df['close'], df['open'])]
    fig.add_trace(
        go.Bar(x=df.index, y=df['volume'],
               name='거래량',
               marker_color=colors),
        row=2, col=1
    )

    # 백테스트 거래 내역 표시
    if trades:
        buy_dates, buy_prices, buy_texts = [], [], []
        sell_dates, sell_prices, sell_texts = [], [], []
        stop_dates, stop_prices, stop_texts = [], [], []

        for t in trades:
            date = pd.Timestamp(t['date'])
            print(date, type(date))
            if '매수' in t['action']:
                buy_dates.append(date)
                buy_prices.append(t['price'])
                buy_texts.append(f"{t['action']}<br>{t['price']:,}원")
            elif '익절' in t['action']:
                sell_dates.append(date)
                sell_prices.append(t['price'])
                sell_texts.append(
                    f"{t['action']}<br>{t['price']:,}원<br>{t['profit']}%")
            elif '손절' in t['action']:
                stop_dates.append(date)
                stop_prices.append(t['price'])
                stop_texts.append(
                    f"{t['action']}<br>{t['price']:,}원<br>{t['profit']}%")

        # 매수 표시 (초록 삼각형 위)
        if buy_dates:
            fig.add_trace(
                go.Scatter(
                    x=buy_dates,
                    y=[p * 0.97 for p in buy_prices],  # 캔들 아래
                    mode='markers+text',
                    marker=dict(symbol='triangle-up', size=12, color='green'),
                    text=buy_texts,
                    textposition='bottom center',
                    name='매수',
                    hovertext=buy_texts
                ),
                row=1, col=1
            )

        # 익절 표시 (빨간 삼각형 아래)
        if sell_dates:
            fig.add_trace(
                go.Scatter(
                    x=sell_dates,
                    y=[p * 1.03 for p in sell_prices],  # 캔들 위
                    mode='markers+text',
                    marker=dict(symbol='triangle-down', size=12, color='red'),
                    text=sell_texts,
                    textposition='top center',
                    name='익절',
                    hovertext=sell_texts
                ),
                row=1, col=1
            )

        # 손절 표시 (검정 삼각형)
        if stop_dates:
            fig.add_trace(
                go.Scatter(
                    x=stop_dates,
                    y=[p * 1.03 for p in stop_prices],
                    mode='markers+text',
                    marker=dict(symbol='triangle-down', size=12, color='black'),
                    text=stop_texts,
                    textposition='top center',
                    name='손절',
                    hovertext=stop_texts
                ),
                row=1, col=1
            )

    # 레이아웃
    fig.update_layout(
        title=f'{ticker} {ma_period}일 엔벨로프 ({int(envelope*100)}%)',
        xaxis_rangeslider_visible=False,
        height=800,
        template='plotly_dark',
        xaxis2=dict(
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1M", step="month"),
                    dict(count=3, label="3M", step="month"),
                    dict(count=6, label="6M", step="month"),
                    dict(step="all", label="전체")
                ]
            )
        )
    )

    # fig.update_xaxes(type='category', tickangle=45)
    fig.update_xaxes(
        tickangle=45,
        tickformat="%Y-%m-%d",  # 날짜 형식
        type='date'
    )
    fig.show()


if __name__ == "__main__":
    # 백테스트 결과와 함께 차트 보기
    from core.backtest import Backtest
    from strategies.down_coin import DownCoinStrategy

    strategy = DownCoinStrategy(ma_period=10, envelope=0.10, stage_ratio=0.05)
    bt = Backtest(
        strategy=strategy,
        ticker="KRW-XRP",
        interval="day",
        initial_capital=1000000,
        start_date="2025-01-01",
        end_date="2026-04-05"
    )
    result = bt.run()
    bt.print_result(result)

    # 차트에 매수/매도 시점 표시
    draw_envelope_chart(
        ticker="KRW-XRP",
        ma_period=10,
        envelope=0.10,
        interval="day",
        start_date="2025-01-01",
        end_date="2026-04-05",
        trades=result['trades']  # ← 거래 내역 전달
    )