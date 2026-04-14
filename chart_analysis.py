# chart_analysis.py

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def draw_envelope_chart(ticker, ma_period=10, envelope=0.10,
                        interval="day", start_date=None, end_date=None):
    """
    캔들차트 + 이평선 + 엔벨로프
    좌우 스크롤 + 확대/축소 가능!
    """
    # CSV에서 데이터 불러오기
    path = f"data/{interval}/{ticker}.csv"
    if not os.path.exists(path):
        print(f"[ERROR] {path} 파일 없음")
        return

    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.columns = [c.lower() for c in df.columns]

    print(df.columns)
    # 날짜 필터링
    if start_date:
        df = df[df.index >= start_date]
    if end_date:
        df = df[df.index <= end_date]

    # 이평선 + 엔벨로프 계산
    df['ma'] = df['close'].rolling(ma_period).mean()
    df['upper'] = df['ma'] * (1 + envelope)
    df['lower'] = df['ma'] * (1 - envelope)
    df['buy_target'] = df['lower'] * (1 - envelope)

    # 서브플롯 생성 (위: 가격, 아래: 거래량)
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
            increasing_line_color='red',    # 양봉 빨강
            decreasing_line_color='blue',   # 음봉 파랑
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
                  name=f'매수목표가',
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

    # 레이아웃 설정
    fig.update_layout(
        title=f'{ticker} {ma_period}일 엔벨로프 ({int(envelope*100)}%)',
        xaxis_rangeslider_visible=False,  # 하단 슬라이더 제거
        height=800,
        template='plotly_dark',  # 다크 테마
        xaxis2=dict(
            rangeselector=dict(  # 기간 선택 버튼
                buttons=[
                    dict(count=1, label="1M", step="month"),
                    dict(count=3, label="3M", step="month"),
                    dict(count=6, label="6M", step="month"),
                    dict(step="all", label="전체")
                ]
            )
        )
    )

    # 주말 제거 (코인은 365일이라 필요없지만 깔끔하게)
    fig.update_xaxes(
        type='category',  # x축 카테고리로 설정 (빈 날짜 제거)
        tickangle=45
    )

    fig.show()  # 브라우저에서 열림!


if __name__ == "__main__":
    draw_envelope_chart(
        ticker="KRW-XRP",
        ma_period=10,
        envelope=0.10,
        interval="day",
        start_date="2025-01-01",
        end_date="2026-04-05"
    )