import os
import time
import pandas as pd
import ta
import requests
from datetime import datetime, timedelta
import python_bithumb
from dotenv import load_dotenv
import json
from openai import OpenAI

# 환경 변수 로드 및 초기 설정
load_dotenv()
access_key = os.getenv("BITHUMB_ACCESS_KEY")
secret_key = os.getenv("BITHUMB_SECRET_KEY")
bithumb = python_bithumb.Bithumb(access_key, secret_key)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYMBOL = "KRW-BTC"
INTERVAL = "1h"
DAILY_TRADES = 5
MIN_KRW = 10001
FIXED_BUY_AMOUNT = 10001

# 기술적 지표 계산
def get_technical_indicators(df):
    df['MA5'] = ta.trend.sma_indicator(df['close'], window=5)
    df['MA20'] = ta.trend.sma_indicator(df['close'], window=20)
    df['RSI'] = ta.momentum.rsi(df['close'], window=14)
    macd = ta.trend.MACD(df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['Upper_BB'] = bollinger.bollinger_hband()
    df['Lower_BB'] = bollinger.bollinger_lband()
    return df

# 공포/탐욕 지수 가져오기
def fetch_fear_and_greed():
    try:
        response = requests.get("https://api.alternative.me/fng/", timeout=10)
        return int(response.json()['data'][0]['value'])
    except Exception as e:
        print(f"❗ 공포 탐욕 지수 오류: {str(e)}")
        return None

# AI 판단 함수
def get_ai_decision(df, fear_greed):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """당신은 금융 전문가입니다. 다음 지표를 종합 분석하여 매수, 매도, 홀딩 중 하나의 결정을 JSON 형식으로 내려주세요:
1. 이동평균선(5일 vs 20일) 크로스오버: MA5와 MA20의 관계 분석
2. RSI 과매수/과매도 상태: RSI 지표를 활용한 시장의 과열/침체 판단
3. MACD 선과 시그널 선 관계: MACD, MACD_Signal 선의 교차 및 방향성 분석
4. 볼린저 밴드 위치: 현재 가격이 볼린저 밴드 내 어느 위치에 있는지 파악
5. 공포/탐욕 지수: 시장의 전반적인 투자 심리 (극단적 공포 또는 탐욕 상태)
6. 거래량 변화 추이: 최근 거래량 변화를 분석하여 투자 심리 및 추세 강도 파악

**투자 원칙:**
- **손실 최소화**: 안정적인 투자를 최우선 목표로 손실 위험을 최소화합니다.
- **보수적 매매**: 최소 3개 이상의 긍정적 지표가 확인될 때만 신중하게 매수를 고려합니다.
- **위험 관리**: 2개 이상의 부정적 지표가 감지되면 즉시 매도하여 리스크를 관리합니다.
- **탐욕 경계**: 탐욕 지수가 과도하게 높을 때는 시장 과열을 경계하고 매도 우선 전략을 고려합니다.

**JSON 형식 예시:**
```json
{"decision": "buy", "reason": "MA5>MA20, RSI 28, MACD 상승"}
"""},
                {"role": "user", "content": f"""최근 100개 {INTERVAL} 봉 데이터:
{df[['open','high','low','close','volume','MA5','MA20','RSI','MACD','MACD_Signal','Upper_BB','Lower_BB']].tail().to_markdown()}
공포 탐욕 지수: {fear_greed}/100"""}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as json_error:
        print(f"❗ AI 판단 JSON 디코드 오류: {str(json_error)}")
        return {}
    except Exception as e:
        print(f"❗ AI 판단 오류: {str(e)}")
        return {}

# 매수 조건 확인
def should_buy(df, fear_greed):
    latest = df.iloc[-1]
    buy_reasons = []
    if latest['MA5'] > latest['MA20']:
        buy_reasons.append(1)
    if latest['RSI'] < 35:
        buy_reasons.append(2)
    if latest['MACD'] > latest['MACD_Signal']:
        buy_reasons.append(3)
    if latest['close'] < latest['Lower_BB']:
        buy_reasons.append(4)
    if fear_greed and fear_greed < 30:
        buy_reasons.append(5)
    if len(buy_reasons) >= 3:
        return buy_reasons
    else:
        return []

# 매도 조건 확인
def should_sell(df, fear_greed, buy_prices):
    latest = df.iloc[-1]
    sell_reasons = []
    if latest['MA5'] < latest['MA20']:
        sell_reasons.append(1)
    if latest['RSI'] > 65:
        sell_reasons.append(2)
    if latest['MACD'] < latest['MACD_Signal']:
        sell_reasons.append(3)
    if latest['close'] > latest['Upper_BB']:
        sell_reasons.append(4)
    if fear_greed and fear_greed > 70:
        sell_reasons.append(5)
    if len(sell_reasons) >= 2:
        return sell_reasons
    else:
        return []

# 잔고 확인 함수 (수정됨)
def check_balance():
    balance_info = {}
    try:
        # get_balance가 실수 값을 반환한다고 가정
        balance_info['KRW'] = bithumb.get_balance("KRW")
        balance_info['BTC'] = bithumb.get_balance("BTC")
        balance_list = []
        for i, (currency, amount) in enumerate(balance_info.items(), 1):
            balance_list.append(f"{i}. 보유 {currency}: {amount:.5f} {currency}")
        return balance_list
    except Exception as e:
        print(f"❗ 잔고 확인 오류: {str(e)}")
        return ["잔고 확인에 실패했습니다."]

# 메인 로직
if __name__ == "__main__":
    buy_prices = []  # 매수 가격 기록
    buy_fees = []    # 매수 수수료 기록
    trades_today = 0
    last_trade_time = None
    last_reset_date = None  # 자정 리셋 날짜 추적

    print("--- 자동 매매 시작 ---")

    while True:
        try:
            now = datetime.now()
            current_hour = now.hour

            # 자정에 일일 매매 횟수 초기화
            if current_hour == 0 and now.minute < 5:
                if now.date() != last_reset_date:
                    trades_today = 0
                    last_reset_date = now.date()
                    print("🔄 일일 매매 횟수 초기화 (자정 기준)")

            # OHLCV 데이터 가져오기
            df = python_bithumb.get_ohlcv(SYMBOL, INTERVAL)
            if df is None or df.empty:
                print("❗ OHLCV 데이터 조회 실패, 5초 후 재시도...")
                time.sleep(5)
                continue

            # 최근 100개 데이터만 사용
            df = df.tail(100)

            df = get_technical_indicators(df)
            fear_greed = fetch_fear_and_greed()

            buy_reasons = should_buy(df, fear_greed)
            sell_reasons = should_sell(df, fear_greed, buy_prices)

            # 잔고 출력
            balance_info = check_balance()
            if balance_info:
                print("💰 계좌 잔고:")
                for balance_item in balance_info:
                    print(f"  - {balance_item}")
            else:
                print("❗ 잔고 확인 실패")

            # 매수 로직
            if buy_reasons and trades_today < DAILY_TRADES:
                if FIXED_BUY_AMOUNT <= bithumb.get_balance("KRW"):
                    print("🟢 매수 신호 발생!")
                    print("매수 사유:")
                    for reason_number in buy_reasons:
                        if reason_number == 1:
                            print(f"  {reason_number}. 이동평균선 (MA5 > MA20)")
                        elif reason_number == 2:
                            print(f"  {reason_number}. RSI (RSI < 35)")
                        elif reason_number == 3:
                            print(f"  {reason_number}. MACD (MACD > MACD_Signal)")
                        elif reason_number == 4:
                            print(f"  {reason_number}. 볼린저 밴드 (현재 가격 < 볼린저 밴드 하단)")
                        elif reason_number == 5:
                            print(f"  {reason_number}. 시장 심리 (공포 탐욕 지수 < 30)")

                    try:
                        orderbook = bithumb.get_orderbook(SYMBOL)
                        if orderbook and orderbook['asks']:
                            ask_price = orderbook['asks'][0]['price']
                            buy_amount = FIXED_BUY_AMOUNT / ask_price
                            buy_result = bithumb.buy_market_order(SYMBOL, buy_amount)

                            if buy_result:
                                buy_price = ask_price
                                buy_prices.append(buy_price)
                                buy_fees.append(buy_result.get('fee', 0))
                                trades_today += 1
                                last_trade_time = now
                                print(f"🚀 {now.strftime('%H:%M:%S')} BTC 시장가 매수 주문 성공! - 매수 가격: {buy_price} KRW, 매수 금액: {FIXED_BUY_AMOUNT} KRW, 수수료: {buy_result.get('fee', 'N/A')}")
                                print(f"📊 오늘 총 매수 횟수: {trades_today}/{DAILY_TRADES}")
                            else:
                                print(f"❗ {now.strftime('%H:%M:%S')} BTC 시장가 매수 주문 실패: {buy_result}")
                        else:
                            print("❗ 매수 호가 정보를 가져오는데 실패했습니다.")
                    except Exception as e:
                        print(f"❗ BTC 매수 중 오류 발생: {e}")
                else:
                    print(f"⛔ KRW 잔고 부족 - {now.strftime('%H:%M:%S')} 매수 대기...")
            else:
                if not buy_reasons:
                    print(f"⛔ 매수 조건 미충족 - {now.strftime('%H:%M:%S')} 매수 대기...")
                elif trades_today >= DAILY_TRADES:
                    print(f"⛔ 하루 최대 매수 횟수 초과 ({DAILY_TRADES}회) - {now.strftime('%H:%M:%S')} 매수 대기...")

            # 매도 로직
            if sell_reasons and buy_prices:
                print("🔴 매도 신호 발생!")
                print("매도 사유:")
                for reason_number in sell_reasons:
                    if reason_number == 1:
                        print(f"  {reason_number}. 이동평균선 (MA5 < MA20)")
                    elif reason_number == 2:
                        print(f"  {reason_number}. RSI (RSI > 65)")
                    elif reason_number == 3:
                        print(f"  {reason_number}. MACD (MACD < MACD_Signal)")
                    elif reason_number == 4:
                        print(f"  {reason_number}. 볼린저 밴드 (현재 가격 > 볼린저 밴드 상단)")
                    elif reason_number == 5:
                        print(f"  {reason_number}. 시장 심리 (공포 탐욕 지수 > 70)")

                try:
                    average_buy_price = sum(buy_prices) / len(buy_prices)
                    current_price = python_bithumb.get_current_price(SYMBOL)

                    if current_price and current_price > MIN_KRW:
                        sell_amount = bithumb.get_balance("BTC")
                        if sell_amount > 0:
                            sell_result = bithumb.sell_market_order(SYMBOL, sell_amount)

                            if sell_result:
                                sell_price = current_price
                                total_buy_fees = sum(buy_fees)
                                sell_fee = sell_result.get('fee', 0)
                                total_fees = total_buy_fees + sell_fee
                                profit = (sell_price * sell_amount) - (average_buy_price * sell_amount) - total_fees
                                profit_rate = (profit / (average_buy_price * sell_amount)) * 100 if (average_buy_price * sell_amount) != 0 else 0

                                print(f"🚀 {now.strftime('%H:%M:%S')} BTC 시장가 매도 주문 성공! - 매도 가격: {sell_price} KRW, 매도 수량: {sell_amount} BTC, 수수료: {sell_result.get('fee', 'N/A')}")
                                print(f"💰 총 수익: {profit:.2f} KRW, 수익률: {profit_rate:.2f}% (평균 매수 가격: {average_buy_price:.2f} KRW)")

                                buy_prices = []
                                buy_fees = []
                            else:
                                print(f"❗ {now.strftime('%H:%M:%S')} BTC 시장가 매도 주문 실패: {sell_result}")
                        else:
                            print("❗ 매도 가능 수량이 없습니다.")
                    else:
                        print(f"⛔ 현재 가격이 최소 매도 금액 미만 ({MIN_KRW} KRW) 이거나 가격 정보를 가져올 수 없습니다.")
                except Exception as e:
                    print(f"❗ BTC 매도 중 오류 발생: {e}")
            else:
                if not sell_reasons:
                    print(f"⛔ 매도 조건 미충족 - {now.strftime('%H:%M:%S')} 매도 대기...")
                elif not buy_prices:
                    print(f"⛔ 매도할 BTC 잔액 부족 - {now.strftime('%H:%M:%S')} 매도 대기...")

            print(f"⏳ {INTERVAL} 봉 업데이트 대기 (다음 업데이트 시간: {(now.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(hours=1)).strftime('%H:%M:%S')})")
            time.sleep(10)

        except Exception as e:
            print(f"❗ 메인 루프 오류 발생: {e}")
            time.sleep(5)