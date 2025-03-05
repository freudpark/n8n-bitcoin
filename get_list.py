import jwt
import uuid
import hashlib
import time
from urllib.parse import urlencode
import requests
import os
from dotenv import load_dotenv
import json

# 환경 변수 로드 (반드시 .env 파일에 BITHUMB_ACCESS_KEY, BITHUMB_SECRET_KEY 설정 필요)
load_dotenv()
accessKey = os.getenv("BITHUMB_ACCESS_KEY")  # 발급받은 API KEY
secretKey = os.getenv("BITHUMB_SECRET_KEY") # 발급받은 SECRET KEY
apiUrl = 'https://api.bithumb.com'

def get_recent_orders_bithumb_api(market="KRW-BTC", limit=5):
    """Bithumb Private API (v1/orders) 직접 호출하여 최근 주문 현황 조회

    Args:
        market (str):  마켓 심볼 (기본값: "KRW-BTC", 예: "KRW-BTC", "BTC-ETH")
        limit (int): 조회할 최근 주문 건수 (기본값: 5, 최대 100)

    Returns:
        dict: 최근 주문 현황 정보 (API 응답 JSON), 오류 발생 시 None 반환
              API 응답 JSON 구조는 Bithumb API 문서 참고
    """
    try:
        # === 1. API Parameters 설정 ===
        param = dict(
            market=market,
            limit=limit, # 조회할 주문 건수 (최대 100) - 사용자 입력 파라미터 사용
            page=1,      # 페이지 번호 (기본값: 1) - 최근 주문 조회를 위해 1 페이지 사용
            order_by='desc' # 주문 정렬 방식 (내림차순: desc, 오름차순: asc) - 최근 주문 조회를 위해 내림차순 사용
        )
        query = urlencode(param) # URL encode parameter

        # === 2. Nonce 및 Timestamp 생성 ===
        nonce = str(uuid.uuid4())
        timestamp = round(time.time() * 1000)

        # === 3. Query Hash 생성 ===
        hash = hashlib.sha512()
        hash.update(query.encode())
        query_hash = hash.hexdigest()

        # === 4. JWT Payload 생성 ===
        payload = {
            'access_key': accessKey,     # Bithumb Access Key
            'nonce': nonce,            # Nonce 값
            'timestamp': timestamp,      # Timestamp (milliseconds)
            'query_hash': query_hash,     # Query Hash
            'query_hash_alg': 'SHA512',  # Hash Algorithm (SHA512 고정)
        }

        # === 5. JWT Token 생성 ===
        jwt_token = jwt.encode(payload, secretKey) # JWT Token 생성 (payload, Secret Key)

        # === 6. Authorization Header 생성 ===
        authorization_token = 'Bearer {}'.format(jwt_token) # Bearer Token
        headers = {
            'Authorization': authorization_token # Authorization header에 JWT Token 추가
        }

        # === 7. API 호출 (GET 방식) ===
        api_path = '/v1/orders' # API 엔드포인트 경로 (v1/orders)
        request_url = apiUrl + api_path + '?' + query # API 요청 URL (Endpoint + Path + Query String)

        print("\n[DEBUGGING - get_recent_orders_bithumb_api] API 요청 URL:", request_url) # API 요청 URL 출력 (추가)
        print("[DEBUGGING - get_recent_orders_bithumb_api] Headers:", headers)       # HTTP Headers 출력 (추가)


        response = requests.get(request_url, headers=headers) # GET request with headers and query string

        print("\n[DEBUGGING - get_recent_orders_bithumb_api] API Response Status Code:", response.status_code) # HTTP 응답 상태 코드 출력 (추가)
        response.raise_for_status() # HTTPError 발생 시 raise (예: 404, 500 등) - HTTP 에러 발생 여부 확인 (기존 코드 유지)

        result_json = response.json() # 응답 JSON 파싱
        print("\n[DEBUGGING - get_recent_orders_bithumb_api] API Response JSON (Before Status Check):") # Bithumb API 응답 JSON (상태 코드 체크 전) 출력 (추가)
        print(json.dumps(result_json, indent=4, ensure_ascii=False)) # JSON 데이터 예쁘게 출력

        if result_json['status'] != '0000': # API 요청 실패 시 (status 코드가 '0000' 이 아니면 실패)
            print("\n[DEBUGGING - get_recent_orders_bithumb_api] Bithumb API Error Status Code:", result_json['status']) # Bithumb API 에러 상태 코드 출력 (추가)
            print("[DEBUGGING - get_recent_orders_bithumb_api] Bithumb API Error Message:", result_json['message'])    # Bithumb API 에러 메시지 출력 (추가)
            raise Exception(f"Bithumb API Error: {result_json['message']} (Status Code: {result_json['status']})") # Bithumb API 에러 발생 시 예외 발생 (기존 코드 유지)


        # === [기존 디버깅 코드 - 함수 외부로 이동] ===  (기존 디버깅 코드는 if __name__ == '__main__': 블록으로 옮겨서 함수 호출 직후에 실행하도록 수정)


        return result_json # API 응답 JSON 반환 (data 필드에 주문 현황 정보 포함)

    except Exception as e: # 예외 처리 (오류 발생 시)
        print(f"⚠️ Bithumb API 호출 오류: {e}") # 오류 메시지 출력 (기존 코드 유지)
        return None # 오류 발생 시 None 반환 (기존 코드 유지)

if __name__ == '__main__':
    print("⏳ 최근 5회 주문 현황 조회 시작...")
    recent_orders = get_recent_orders_bithumb_api(market="KRW-BTC", limit=5) # KRW-BTC 마켓 최근 5회 주문 현황 조회

    # === [디버깅 코드 강제 삽입 (함수 호출 직후)] ===
    print("\n[DEBUGGING] API 응답 데이터 (recent_orders) type:", type(recent_orders)) # recent_orders 변수의 type 출력
    if recent_orders and 'data' in recent_orders: # recent_orders가 None이 아니고 'data' 키가 있는지 확인 (수정)
        print("[DEBUGGING] recent_orders['data'] type:", type(recent_orders['data'])) # recent_orders['data'] 의 type 출력
        print("\n[DEBUGGING] recent_orders['data'] content (JSON):") # recent_orders['data'] 내용 출력
        if isinstance(recent_orders['data'], (dict, list)): # recent_orders['data'] 가 딕셔너리 또는 리스트인 경우에만 JSON 출력 (오류 방지)
            print(json.dumps(recent_orders['data'], indent=4, ensure_ascii=False)) # JSON 데이터 예쁘게 출력
        else:
            print("[DEBUGGING] recent_orders['data'] is not JSON serializable:", recent_orders['data']) # JSON 직렬화 불가능한 경우 출력
    else:
        print("[DEBUGGING] recent_orders['data'] 키가 없거나 recent_orders가 None") # 'data' 키가 없거나 recent_orders가 None인 경우 메시지 출력
    print("\n====================================\n")
    #