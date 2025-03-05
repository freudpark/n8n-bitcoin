import os
import time
import pandas as pd
import ta
import requests
from datetime import datetime
import python_bithumb
from dotenv import load_dotenv
import json
from openai import OpenAI

# 환경변수 로드 및 API 객체 초기화
load_dotenv()
access_key = os.getenv("BITHUMB_ACCESS_KEY")
secret_key = os.getenv("BITHUMB_SECRET_KEY")
bithumb = python_bithumb.Bithumb(access_key, secret_key)
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 상수 정의
SYMBOL = "KRW-BTC"
INTERVAL = "1h"
DAILY_TRADES = 5
MIN_KRW = 10001
FIXED_BUY_AMOUNT = 10001

def get_technical_indicators(df):
    """
    OHLCV 데이터에 기술적 지표(MA, RSI, MACD, Bollinger Bands)를 추가합니다.
    """
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

def fetch_fear_and_greed():
    """
    대체 API를 통해 공포/탐욕 지수를 가져옵니다.
    """
    try:
        response = requests.get("https://api.alternative.me/fng/", timeout=10)
        return int(response.json()['data'][0]['value'])
    except Exception as e:
        print(f"❗ 공포 탐욕 지수 오류: {str(e)}")
        return None

def get_ai_decision(df, fear_greed):
    """
    OpenAI API를 사용하여 기술적 지표와 시장 심리를 종합 분석하고
    매수/매도/홀딩 결정을 JSON 형식으로 반환합니다.
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "당신은 금융 전문가입니다. 다음 지표를 종합 분석하여 매수, 매도, 홀딩 중 하나의 결정을 JSON 형식으로 내려주세요:\n"
                        "1. 이동평균선(5일 vs 20일) 크로스오버: MA5와 MA20의 관계 분석\n"
                        "2. RSI 과매수/과매도 상태: RSI 지표를 활용한 시장의 과열/침체 판단\n"
                        "3. MACD 선과 시그널 선 관계: MACD, MACD_Signal 선의 교차 및 방향성 분석\n"
                        "4. 볼린저 밴드 위치: 현재 가격이 볼린저 밴드 내 어느 위치에 있는지 파악\n"
                        "5. 공포/탐욕 지수: 시장의 전반적인 투자 심리 (극단적 공포 또는 탐욕 상태)\n"
                        "6. 거래량 변화 추이: 최근 거래량 변화를 분석하여 투자 심리 및 추세 강도 파악\n\n"
                        "**투자 원칙:**\n"
                        "- **손실 최소화**: 안정적인 투자를 최우선 목표로 손실 위험을 최소화합니다.\n"
                        "- **보수적 매매**: 최소 3개 이상의 긍정적 지표가 확인될 때만 신중하게 매수를 고려합니다.\n"
                        "- **위험 관리**: 2개 이상의 부정적 지표가 감지되면 즉시 매도하여 리스크를 관리합니다.\n"
                        "- **탐욕 경계**: 탐욕 지수가 과도하게 높을 때는 시장 과열을 경계하고 매도 우선 전략을 고려합니다.\n\n"
                        "**JSON 형식 예시:**\n"
                        "```json\n"
                        '{"decision": "buy", "reason": "MA5>MA20, RSI 28, MACD 상승"}\n'
                        "```"
                    )
                },
                {
                    "role": "user", 
                    "content": (
                        f"최근 100개 {INTERVAL} 봉 데이터:\n"
                        f"{df[['open','high','low','close','volume','MA5','MA20','RSI','MACD','MACD_Signal','Upper_BB','Lower_BB']].tail().to_markdown()}\n"
                        f"공포 탐욕 지수: {fear_greed}/100"
                    )
                }
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

def should_buy(df, fear_greed):
    """
    매수 조건을 평가하여 조건을 충족하면 해당 사유 번호 리스트를 반환합니다.
    """
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
    if fear_greed is not None and fear_greed < 30:
        buy_reasons.append(5)
    return buy_reasons if len(buy_reasons) >= 3 else []

def should_sell(df, fear_greed):
    """
    매도 조건을 평가하여 조건을 충족하면 해당 사유 번호 리스트를 반환합니다.
    """
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
    if fear_greed is not None and fear_greed > 70:
        sell_reasons.append(5)
    return sell_reasons if len(sell_reasons) >= 2 else []

def check_balance():
    """
    현재 계좌의 KRW 및 BTC 잔고를 확인합니다.
    bithumb.get_balance()가 float을 반환하므로 바로 사용합니다.
    """
    try:
        krw_balance = bithumb.get_balance("KRW")
        btc_balance = bithumb.get_balance("BTC")
        balance_list = [
            f"1. 보유 KRW: {krw_balance:.5f} KRW",
            f"2. 보유 BTC: {btc_balance:.5f} BTC"
        ]
        return balance_list
    except Exception as e:
        print(f"❗ 잔고 확인 오류: {str(e)}")
        return ["잔고 확인에 실패했습니다."]

if __name__ == "__main__":
    buy_orders = []
    trades_today = 0
    last_trade_time = None
    last_reset_date = datetime.now().date()

    print("--- 자동 매매 시작 ---")

    while True:
        try:
            now = datetime.now()
            if now.date() != last_reset_date:
                trades_today = 0
                last_reset_date = now.date()
                print("🔄 일일 매매 횟수 초기화 (자정 기준)")

            df = python_bithumb.get_ohlcv(SYMBOL, INTERVAL)
            if df is None or df.empty:
                print("❗ OHLCV 데이터 조회 실패, 5초 후 재시도...")
                time.sleep(5)
                continue

            df = df.tail(100)
            df = get_technical_indicators(df)
            fear_greed = fetch_fear_and_greed()

            buy_reasons = should_buy(df, fear_greed)
            sell_reasons = should_sell(df, fear_greed)

            balance_info = check_balance()
            if balance_info:
                print("💰 계좌 잔고:")
                for balance_item in balance_info:
                    print(f"  - {balance_item}")
            else:
                print("❗ 잔고 확인 실패")

            # 매수 신호 처리
            if buy_reasons and trades_today < DAILY_TRADES:
                available_krw = bithumb.get_balance("KRW")
                if FIXED_BUY_AMOUNT <= available_krw:
                    print("🟢 매수 신호 발생!")
                    print("매수 사유:")
                    for reason in buy_reasons:
                        if reason == 1:
                            print("  1. 이동평균선 (MA5 > MA20)")
                        elif reason == 2:
                            print("  2. RSI (RSI < 35)")
                        elif reason == 3:
                            print("  3. MACD (MACD > MACD_Signal)")
                        elif reason == 4:
                            print("  4. 볼린저 밴드 (현재 가격 < 볼린저 밴드 하단)")
                        elif reason == 5:
                            print("  5. 시장 심리 (공포 탐욕 지수 < 30)")

                    try:
                        orderbook = bithumb.get_orderbook(SYMBOL)
                        if orderbook and orderbook['asks']:
                            ask_price = orderbook['asks'][0]['price']
                            btc_amount = FIXED_BUY_AMOUNT / ask_price
                            buy_result = bithumb.buy_market_order(SYMBOL, btc_amount)
                            if buy_result:
                                buy_fee = buy_result.get('fee', 0)
                                buy_orders.append({
                                    'price': ask_price,
                                    'amount': btc_amount,
                                    'fee': buy_fee
                                })
                                trades_today += 1
                                last_trade_time = now
                                print(f"🚀 {now.strftime('%H:%M:%S')} BTC 시장가 매수 주문 성공! - 매수 가격: {ask_price} KRW, 매수 금액: {FIXED_BUY_AMOUNT} KRW, 수수료: {buy_fee}")
                                print(f"📊 오늘 총 매수 횟수: {trades_today}/{DAILY_TRADES}")
                            else:
                                print(f"❗ {now.strftime('%H:%M:%S')} BTC 시장가 매수 주문 실패: {buy_result}")
                        else:
                            print("❗ 매수 호가 정보를 가져오는데 실패했습니다.")
                    except Exception as e:
                        print(f"❗ BTC 매수 중 오류 발생: {e}")
                else:
                    print("❗ 매수 가능한 KRW 잔고 부족")
            else:
                if not buy_reasons:
                    print(f"⛔ 매수 조건 미충족 - {now.strftime('%H:%M:%S')} 매수 대기...")
                elif trades_today >= DAILY_TRADES:
                    print(f"⛔ 하루 최대 매수 횟수 초과 ({DAILY_TRADES}회) - {now.strftime('%H:%M:%S')} 매수 대기...")

            # 매도 신호 처리
            if sell_reasons and buy_orders:
                print("🔴 매도 신호 발생!")
                print("매도 사유:")
                for reason in sell_reasons:
                    if reason == 1:
                        print("  1. 이동평균선 (MA5 < MA20)")
                    elif reason == 2:
                        print("  2. RSI (RSI > 65)")
                    elif reason == 3:
                        print("  3. MACD (MACD < MACD_Signal)")
                    elif reason == 4:
                        print("  4. 볼린저 밴드 (현재 가격 > 볼린저 밴드 상단)")
                    elif reason == 5:
                        print("  5. 시장 심리 (공포 탐욕 지수 > 70)")

                try:
                    total_cost = sum(order['price'] * order['amount'] for order in buy_orders)
                    total_amount = sum(order['amount'] for order in buy_orders)
                    average_buy_price = total_cost / total_amount if total_amount != 0 else 0
                    cumulative_buy_fee = sum(order['fee'] for order in buy_orders)

                    current_price = python_bithumb.get_current_price(SYMBOL)
                    if current_price and current_price > MIN_KRW:
                        sell_amount = bithumb.get_balance("BTC")
                        if sell_amount > 0:
                            sell_result = bithumb.sell_market_order(SYMBOL, sell_amount)
                            if sell_result:
                                sell_fee = sell_result.get('fee', 0)
                                sell_price = current_price
                                profit = (sell_price * sell_amount) - total_cost - (cumulative_buy_fee + sell_fee)
                                profit_rate = (profit / total_cost * 100) if total_cost != 0 else 0

                                print(f"🚀 {now.strftime('%H:%M:%S')} BTC 시장가 매도 주문 성공! - 매도 가격: {sell_price} KRW, 매도 수량: {sell_amount} BTC, 수수료: {sell_fee}")
                                print(f"💰 총 수익: {profit:.2f} KRW, 수익률: {profit_rate:.2f}% (평균 매수 가격: {average_buy_price:.2f} KRW)")
                                buy_orders = []
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
                elif not buy_orders:
                    print(f"⛔ 매도할 BTC 잔액 부족 - {now.strftime('%H:%M:%S')} 매도 대기...")

            next_update = (now.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(hours=1)).strftime('%H:%M:%S')
            print(f"⏳ {INTERVAL} 봉 업데이트 대기 (다음 업데이트 시간: {next_update})")
            time.sleep(10)

        except Exception as e:
            print(f"❗ 메인 루프 오류 발생: {e}")
            time.sleep(5)
