import os
from dotenv import load_dotenv
load_dotenv()
import python_bithumb
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def buy_bitcoin_once_10000():
    """
    1회 실행 시 10,000원 상당의 비트코인을 매수하고 종료하는 함수.
    반복 매수 기능 및 AI 판단 로직은 제거됨.
    """
    try:
        # 빗썸 API 키 로드
        access_key = os.getenv("BITHUMB_ACCESS_KEY")
        secret_key = os.getenv("BITHUMB_SECRET_KEY")
        if not access_key or not secret_key:
            logging.error("API 키를 환경 변수에서 찾을 수 없습니다. BITHUMB_ACCESS_KEY 및 BITHUMB_SECRET_KEY 환경 변수를 설정해주세요.")
            return

        bithumb = python_bithumb.Bithumb(access_key, secret_key)

        # 원화 잔고 조회 및 예외 처리
        try:
            krw_balance_str = bithumb.get_balance("KRW")
            krw_balance = krw_balance_str # 수정된 코드: 직접 할당 (float으로 반환될 경우)
            logging.info(f"내 원화 잔고: {krw_balance} KRW")
        except Exception as e:
            logging.error(f"원화 잔고 조회 실패: {e}")
            return

        buy_amount_krw = 10000  # 매수할 금액 (10,000원)

        # 매수 로직
        if krw_balance >= buy_amount_krw:
            logging.info(f"### {buy_amount_krw}원 매수 주문 실행 ###")
            try:
                order_result = bithumb.buy_market_order("KRW-BTC", buy_amount_krw)
                logging.info(f"### 매수 주문 결과: {order_result} ###") # 주문 결과 전체 로깅

                # 주문 성공 여부 간략하게 출력 (status 코드 확인 X)
                logging.info("### 비트코인 매수 주문 요청 성공 ###") # 요청 성공으로 간주 (실제 체결 성공은 별도 확인 필요)


            except Exception as e:
                logging.error(f"### 매수 주문 실행 중 오류 발생: {e} ###") # 일반적인 매수 주문 실행 오류 메시지
                logging.error(f"오류 내용: {e}") # 발생한 예외 객체 내용 상세 출력
        else:
            logging.warning(f"### 매수 실패: 원화 잔고 부족 ({buy_amount_krw}원 미만) ###")

    except Exception as e: # 함수 전체 예외 처리
        logging.error(f"### buy_bitcoin_once_10000 함수 실행 중 예기치 않은 오류 발생: {e} ###")

    finally:
        logging.info("### 프로그램 종료 ###") # 프로그램 종료 로그 메시지 명확화


if __name__ == "__main__":
    buy_bitcoin_once_10000() # 1회 매수 함수 호출