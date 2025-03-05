
'''
 AI가 "hold" 결정을 3회 이상 연속으로 내릴 경우, 10,000원 상당의 비트코인을 매수한 후 프로그램이 종료되는 로직
 
 AI가 "hold" 결정을 3회 이상 연속으로 내릴 경우, 10,000원 상당의 비트코인을 매수한 후 프로그램이 종료되는 로직
 '''
import os
from dotenv import load_dotenv
load_dotenv()
import python_bithumb
import requests

# 연속 'hold' 결정 카운터 변수 초기화
consecutive_hold_count = 0

def ai_trading():
    global consecutive_hold_count # 전역 변수 사용 선언

    # 1. 빗썸 차트 데이터 가져오기 (30일 일봉)
    df = python_bithumb.get_ohlcv("KRW-BTC", interval="day", count=30)
    # 공포 탐욕지수 가져오기
    fearAndGreed = requests.get("https://api.alternative.me/fng/").json()['data'][0]
    print(fearAndGreed)

    # 2. AI에게 데이터 제공하고 판단 받기
    from openai import OpenAI
    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": """
당신은 비트코인 투자 전문가입니다. 제공된 차트 데이터와 다음 투자 원칙을 기반으로 매수, 매도, 또는 보유를 결정하세요. JSON 형식으로 응답하세요.

투자 원칙:
원칙 1: 절대 손해를 보지 마라.
원칙 2: 원칙 1을 절대 잊지 마라.

응답 예시:
{
    "decision": "buy",
    "reason": "어떤 기술적 이유"
}
{
    "decision": "sell",
    "reason": "어떤 기술적 이유"
}
{
    "decision": "hold",
    "reason": "어떤 기술적 이유"
}
"""
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""30일간의 OHLCV 데이터: {df.to_json()},
                                                공포 탐욕 지수: {fearAndGreed}"""
                        }
                    ]
                }
            ],
            response_format={
                "type": "json_object"
            }
        )
    result = response.choices[0].message.content

    # 3. AI의 판단에 따라 실제로 자동매매 진행하기
    import json
    result = json.loads(result)
    access = os.getenv("BITHUMB_ACCESS_KEY")
    secret = os.getenv("BITHUMB_SECRET_KEY")
    bithumb = python_bithumb.Bithumb(access, secret)

    my_krw = bithumb.get_balance("KRW")
    print(f"내 원화 잔고: {my_krw} KRW")
    my_btc = bithumb.get_balance("BTC")
    print(f"내 비트코인 잔고: {my_btc} BTC")
    print("### AI 결정: ", result["decision"].upper(), "###")
    print(f"### 사유: {result['reason']} ###")

    decision = result["decision"] # AI 결정 변수 저장

    if decision == "buy":
        consecutive_hold_count = 0 # 'buy' 또는 'sell' 시 카운터 초기화
        if my_krw > 10000:
            buy_amount_krw = 10000  # 한번에 구매할 원화 금액
            current_price = python_bithumb.get_current_price("KRW-BTC")
            print("### 매수 주문 실행 ###")
            bithumb.buy_market_order("KRW-BTC", buy_amount_krw) # [수정 후 코드] 매수 금액(KRW)으로 주문
            print(f"### {buy_amount_krw} KRW  매수 주문 완료 ###")
        else:
            print("### 매수 실패: 원화 잔고 부족 (10,000원 미만) ###")

    elif decision == "sell":
        consecutive_hold_count = 0 # 'buy' 또는 'sell' 시 카운터 초기화
        current_price = python_bithumb.get_current_price("KRW-BTC")
        if my_btc * current_price > 10000:
            print("### 매도 주문 실행 ###")
            bithumb.sell_market_order("KRW-BTC", my_btc)
        else:
            print("### 매도 실패: 비트코인 잔고 부족 (10000원 미만) ###")

    elif decision == "hold":
        consecutive_hold_count += 1 # 'hold' 시 카운터 증가
        print(f"### 현재 포지션 유지 (연속 Hold: {consecutive_hold_count}회) ###")
        if consecutive_hold_count >= 3: # 연속 3회 이상 'hold' 인 경우 매수 후 종료
            if my_krw > 10000:
                buy_amount_krw = 10000  # 한번에 구매할 원화 금액
                current_price = python_bithumb.get_current_price("KRW-BTC")
                print("### !!! 연속 3회 HOLD 발생 !!! 매수 주문 후 프로그램 종료 ###") # 종료 안내 메시지 변경
                bithumb.buy_market_order("KRW-BTC", buy_amount_krw) # [수정 후 코드] 매수 금액(KRW)으로 주문
                print(f"### {buy_amount_krw} KRW  매수 주문 완료 ###") # 매수 주문 완료 메시지 변경
                print("### 프로그램 종료 ###")
                exit() # 프로그램 종료
            else:
                print("### 매수 실패: 원화 잔고 부족 (10,000원 미만), 프로그램 종료 ###") # 종료 안내 메시지 변경
                exit() # 프로그램 종료


import time
while True:
    time.sleep(10)
    ai_trading()