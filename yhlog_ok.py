import os
import python_bithumb
from dotenv import load_dotenv

# 환경 변수 로드 (반드시 .env 파일에 BITHUMB_ACCESS_KEY, BITHUMB_SECRET_KEY 설정 필요)
load_dotenv()
access_key = os.getenv("BITHUMB_ACCESS_KEY")
secret_key = os.getenv("BITHUMB_SECRET_KEY")

def get_account_balance():
    """python-bithumb 라이브러리 Bithumb.get_balances() 함수를 사용하여 전체 계좌 잔고 조회

    Returns:
        dict: 전체 계좌 잔고 정보 (딕셔너리), 오류 발생 시 None 반환
              딕셔너리 키: 화폐 티커 (예: 'KRW', 'BTC', 'ETH' 등), 값: 해당 화폐 잔고 정보 (딕셔너리)
              각 화폐 잔고 정보 딕셔너리는 'balance', 'available', 'trade_in_use', 'withdrawal_available', 'pending_withdrawal' 키 포함
    """
    try:
        bithumb = python_bithumb.Bithumb(access_key, secret_key) # Bithumb Private API 객체 생성 (API 키 필요)
        balances = bithumb.get_balances() # 전체 계좌 잔고 조회
        return balances
    except Exception as e:
        print(f"⚠️ python-bithumb 오류 발생: {e}")
        return None

if __name__ == "__main__":
    print("⏳ 계좌 잔고 조회 시작...")
    account_balance = get_account_balance() # 전체 계좌 잔고 조회

    if account_balance:
        print("\n✅ 계좌 잔고 (python-bithumb):")
        # print(account_balance) # 잔고 정보 딕셔너리 전체 출력 - 더 이상 딕셔너리 전체를 출력하지 않음

        # 잔고 정보 리스트 순회하며 특정 화폐의 잔고만 추출하여 출력 (수정)
        for balance_info in account_balance: # account_balance 리스트 순회
            currency = balance_info.get('currency') # 화폐 티커 가져오기 (예: 'KRW', 'BTC')

            if currency == 'KRW': # 원화(KRW) 잔고 정보인 경우
                print(f"\n💰 원화(KRW) 잔고:")
                total_balance_krw = float(balance_info['balance']) # 전체 잔고 (원화)
                locked_balance_krw = float(balance_info['locked'])   # 락(locked) 잔고 (원화)
                available_balance_krw = total_balance_krw - locked_balance_krw # 주문 가능 잔고 계산 (원화)

                print(f"  - 전체 잔고: {total_balance_krw:,.2f} 원")        # 'balance': 전체 잔고 - format 변경 (소수점 2자리, 천 단위 콤마)
                print(f"  - 락(주문/출금 대기) 잔고: {locked_balance_krw:,.2f} 원") # 'locked': 락 잔고 - format 변경 (소수점 2자리, 천 단위 콤마)
                print(f"  - 주문 가능 잔고: {available_balance_krw:,.2f} 원")   # 주문 가능 잔고 (계산 값) - format 변경 (소수점 2자리, 천 단위 콤마)

            elif currency == 'BTC': # 비트코인(BTC) 잔고 정보인 경우
                print(f"\n₿ 비트코인(BTC) 잔고:")
                total_balance_btc = float(balance_info['balance']) # 전체 잔고 (비트코인)
                locked_balance_btc = float(balance_info['locked'])   # 락(locked) 잔고 (비트코인)
                available_balance_btc = total_balance_btc - locked_balance_btc # 주문 가능 잔고 계산 (비트코인)

                print(f"  - 전체 잔고: {total_balance_btc:.8f} BTC")       # 'balance': 전체 잔고 - format 변경 (소수점 8자리)
                print(f"  - 락(주문/출금 대기) 잔고: {locked_balance_btc:.8f} BTC")    # 'locked': 락 잔고 - format 변경 (소수점 8자리)
                print(f"  - 주문 가능 잔고: {available_balance_btc:.8f} BTC")  # 주문 가능 잔고 (계산 값) - format 변경 (소수점 8자리)
        else:
            print("\n❌ 원화(KRW) 및 비트코인(BTC) 잔고 정보 없음") # 수정: 원화/비트코인 잔고 정보가 모두 없을 경우 메시지 출력 (else 블록 위치 수정)


    else:
        print("\n❌ 계좌 잔고 조회 실패 (python-bithumb)")

    print("\n✅ 계좌 잔고 조회 완료 (python-bithumb)")