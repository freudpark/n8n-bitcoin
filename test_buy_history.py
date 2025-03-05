import os
import time
import hashlib
import hmac
import base64
import requests
import json
import urllib.parse
from dotenv import load_dotenv
from datetime import datetime

# 환경 변수 로드 (반드시 .env 파일에 BITHUMB_ACCESS_KEY, BITHUMB_SECRET_KEY 설정 필요)
load_dotenv()
access_key = os.getenv("BITHUMB_ACCESS_KEY")
secret_key = os.getenv("BITHUMB_SECRET_KEY")

API_ENDPOINT = "https://api.bithumb.com" # Bithumb API 엔드포인트 URL (고정값)

def get_recent_buy_history_bithumb_api(symbol="BTC", count=3):
    """Bithumb Private API (info/order_detail) 직접 호출하여 최근 매수 거래 내역 조회

    Args:
        symbol (str):  조회할 가상자산 심볼 (기본값: "BTC")
        count (int): 조회할 최근 매수 기록 횟수 (기본값: 3)

    Returns:
        list: 최근 매수 거래 내역 (최대 count 개수), 거래 내역이 없으면 빈 리스트 반환
              각 거래 내역은 {'datetime': 매수일시, 'amount': 매수금액} 딕셔너리 형태
    """
    try:
        path = "/info/order_detail" # info/order_detail API 경로 (고정값)
        market = f"{symbol}_KRW"    # Bithumb 마켓 심볼 (예: BTC_KRW)
        params = {
            "order_currency": market,
            "payment_currency": "KRW",
            "count": count, # Bithumb API 는 count 인자 지원 안함 (deprecated), 요청 횟수로 조절 (실제 코드에서는 페이지네이션 구현 필요)
            "offset": 0,   # Bithumb API 는 offset 인자 지원 안함 (deprecated), 페이지네이션으로 구현 필요 (실제 코드에서는 페이지네이션 구현 필요)
            "type": "bid"  # 매수 거래만 조회 (bid: 매수, ask: 매도) - info/order_detail API 는 type 인자 지원 안함 (deprecated), 전체 거래 내역 조회 후 필터링 해야 함 (실제 코드에서는 전체 거래 내역 조회 후 필터링 구현 필요)
        }

        # === 1. Nonce 값 생성 ===
        nonce = str(int(time.time() * 1000)) # milliseconds timestamp

        # === 2. API Signature 생성 ===
        # 2-1. Public API + Private API Parameter 조합 (UTF-8 인코딩)
        param_str = urllib.parse.urlencode(params).encode('utf-8') # Public API parameters (URL encoding)
        api_path = path # Private API path
        combined_str = api_path.encode('utf-8') + b'\x00' + param_str + b'\x00' + nonce.encode('utf-8') # API path + null byte + parameter string + null byte + nonce

        # 2-2. Secret Key (Base64 Decode) -> HMAC-SHA512 Hash (with Combined String) -> Base64 Encode
        secret_key_bytes = base64.b64decode(secret_key) # Secret Key Base64 Decode (수정: base64.b64decode() 사용)
        signature = hmac.new(secret_key_bytes, combined_str, hashlib.sha512).digest() # HMAC-SHA512 Hash
        api_sign = base64.b64encode(signature).decode('utf-8')   # API Signature Base64 Encode

        # === 3. Private API 요청 (with 계좌 인증) ===
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Api-Key': access_key,
            'Api-Sign': api_sign,
            'Api-Nonce': nonce
        }

        # Public API 요청 (예시)
        # response = requests.get(API_ENDPOINT + path, params=params, headers=headers, timeout=10) # Public API 요청 방식 (headers 불필요) - Private API 요청 방식으로 변경

        # Private API 요청
        response = requests.post(API_ENDPOINT + path, headers=headers, data=params, timeout=10) # Private API 요청 방식 (headers, data 필요)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생 (예: 400, 401, 500 등)

        # JSON 응답 파싱
        result_json = response.json()

        if result_json['status'] != "0000": # API 요청 실패 시 (status 코드가 "0000" 이 아니면 실패)
            raise Exception(f"Bithumb API Error: {result_json['message']} (Status Code: {result_json['status']})") # Exception 발생시켜 except 블록에서 처리

        print("\n==================== Bithumb API 응답 전체 데이터 (JSON) ====================\n") # 구분선 추가
        print(json.dumps(result_json, indent=4, ensure_ascii=False)) # JSON 데이터 예쁘게 출력 (indent=4: 들여쓰기, ensure_ascii=False: 한글 깨짐 방지)
        print("\n=========================================================================\n") # 구분선 추가

        transactions = result_json['data'] # 거래 내역 데이터 추출 (기존 코드 - 주석 처리 또는 삭제 가능)
        buy_history = [] # 매수 기록 저장할 리스트 초기화 (주석 처리 또는 삭제 가능)
        buy_count = 0    # 매수 기록 카운트 초기화 (주석 처리 또는 삭제 가능)


        return buy_history # 빈 리스트 반환 (API 응답 데이터 확인이 목적이므로, 매수 기록 필터링 및 반환 기능은 잠시 생략)

    except Exception as e: # except 블록 추가 (모든 예외 처리)
        print(f"⚠️ Bithumb API 호출 오류: {e}") # 오류 메시지 출력
        return [] # 오류 발생 시 빈 리스트 반환

if __name__ == "__main__":
    print("⏳ 최근 3회 매수 기록 조회 시작...")
    recent_buys = get_recent_buy_history_bithumb_api(symbol="BTC", count=3) # BTC 최근 3회 매수 기록 조회

    if recent_buys: # 현재는 항상 빈 리스트가 반환되므로, 이 조건문은 항상 False (API 응답 데이터 확인이 목적)
        print("\n✅ 최근 3회 매수 기록 (Bithumb API):")
        for buy in recent_buys:
            # datetime 형식 변환 (YYYY-MM-DD HH:MM:SS) - 현재는 실행되지 않음
            datetime_obj = datetime.strptime(buy['datetime'], "%Y-%m-%d %H:%M:%S")
            formatted_datetime = datetime_obj.strftime("%Y-%m-%d %H:%M:%S") # 보기 좋게 format 변경

            print(f"- 매수일시: {formatted_datetime}, 매수금액: {buy['amount']:,}원") # 현재는 실행되지 않음
    else:
        print("\n❌ 매수 기록 조회 실패 또는 매수 기록 없음 (Bithumb API)") # Bithumb API 명시 - API 호출 자체는 성공해도 빈 리스트가 반환되므로, 이 메시지가 출력될 수 있음

    print("\n✅ 최근 3회 매수 기록 조회 완료 (Bithumb API)") # Bithumb API 명시 - API 호출 시 오류가 발생하지 않고, 함수가 정상적으로 종료되었음을 의미