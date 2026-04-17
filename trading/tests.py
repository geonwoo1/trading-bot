from broker import KisBroker  # 본인의 브로커 모듈

def test_balance_fetch():
    broker = KisBroker()
    
    # 1. 잔고 및 보유 종목 호출
    # get_balance()가 어떤 형태(딕셔너리, 리스트 등)로 값을 반환하는지 확인
    data = broker.get_balance()
    
    print("--- [RAW DATA] API 응답 확인 ---")
    print(data)
    print("--------------------------------")
    
    # 2. 데이터 구조 확인 (가정: 딕셔너리 형태)
    # 실제 반환값 구조에 맞춰 아래 print 문을 수정하세요
    cash = data.get('cash', 0)
    stocks = data.get('stocks', [])
    
    print(f"현금 잔액: {cash:,}원")
    print(f"보유 종목 수: {len(stocks)}개")
    
    for s in stocks:
        print(f"종목명: {s['name']} | 티커: {s['ticker']} | 수량: {s['qty']} | 평균단가: {s['avg_price']}")

if __name__ == "__main__":
    test_balance_fetch()