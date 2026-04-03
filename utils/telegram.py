# utils/telegram.py - 텔레그램 알림

import requests
from dotenv import load_dotenv
import os

load_dotenv()

class TelegramNotifier:
    """
    텔레그램 알림 전송
    매수/매도/에러 발생 시 폰으로 알림
    """

    def __init__(self):
        self.token = os.getenv("TELEGRAM_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send(self, message: str):
        """메시지 전송"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"  # HTML 형식 지원
            }
            response = requests.post(url, data=data)
            return response.json()
        except Exception as e:
            print(f"텔레그램 전송 실패: {e}")
            return None

    def send_buy(self, ticker: str, price: float, amount: float, stage: int = 1):
        """매수 알림"""
        msg = (
            f"📈 <b>{stage}차 매수 주문</b>\n"
            f"종목: {ticker}\n"
            f"가격: {int(price):,}원\n"
            f"금액: {int(amount):,}원"
        )
        return self.send(msg)

    def send_sell(self, ticker: str, price: float, profit: float, action: str = "익절"):
        """매도 알림"""
        emoji = "✅" if action == "익절" else "🛑"
        msg = (
            f"{emoji} <b>{action}</b>\n"
            f"종목: {ticker}\n"
            f"가격: {int(price):,}원\n"
            f"수익률: {round(profit, 2)}%"
        )
        return self.send(msg)

    def send_error(self, error: str):
        """에러 알림"""
        msg = (
            f"🚨 <b>에러 발생</b>\n"
            f"{error}"
        )
        return self.send(msg)

    def send_daily_report(self, total_asset: float,
                          daily_profit: float, positions: dict):
        """일일 수익률 리포트"""
        position_str = ""
        for ticker, pos in positions.items():
            profit = (pos.get('current_price', 0) - pos['avg_buy_price']) \
                     / pos['avg_buy_price'] * 100
            position_str += f"\n  {ticker}: {round(profit, 2)}%"

        msg = (
            f"📊 <b>일일 리포트</b>\n"
            f"총자산: {int(total_asset):,}원\n"
            f"오늘 수익률: {round(daily_profit, 2)}%\n"
            f"보유 종목: {len(positions)}개"
            f"{position_str}"
        )
        return self.send(msg)


if __name__ == "__main__":
    notifier = TelegramNotifier()

    # 테스트 메시지 전송
    notifier.send("✅ 텔레그램 알림 테스트!")
    notifier.send_buy("KRW-BTC", 100000000, 100000)
    notifier.send_sell("KRW-BTC", 105000000, 5.0, "익절")
    notifier.send_daily_report(1000000, 5.0, {})
    notifier.send_error("에러 발생 테스트")