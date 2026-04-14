from db_manager import DBManager
from broker import KisBroker
from analyzer import TechnicalAnalyzer
import time

def main():
    db = DBManager()
    broker = KisBroker(db_manager=db)
    
    ticker = "005930"  # 삼성전자
    name = "삼성전자"
    
    print(f"=== [{name}] 분석 파이프라인 시작 ===")
    
    # 1. 잔고 동기화
    print("1. 계좌 잔고 동기화 중...")
    broker.sync_data()
    
    # 2. 과거 시세 데이터 수집 (API 호출)
    print(f"2. {name} 과거 시세 API 요청 중...")
    price_data = broker.get_daily_ohlcv(ticker)
    
    # [중요] API가 데이터를 줬는지 확인
    if not price_data:
        print("!!! 위기: API로부터 받은 데이터가 0건입니다. (API 응답 확인 필요) !!!")
        return

    print(f"   -> API 수집 성공: {len(price_data)}건의 데이터를 받았습니다.")

    # 3. 데이터 DB 적재
    print("3. DB에 시세 데이터 적재 중...")
    db.save_prices(ticker, price_data)
    
    # 4. 분석을 위해 DB에서 데이터 다시 로드
    print("4. 분석용 데이터 로드 및 지표 계산 중...")
    df = db.get_prices_as_df(ticker)
    
    # 데이터 유효성 최종 확인
    if len(df) >= 20:
        df = TechnicalAnalyzer.add_indicators(df)
        signal = TechnicalAnalyzer.get_signal(df)
        
        print("\n" + "="*40)
        print(f" 종목명: {name} ({ticker})")
        print(f" 분석일: {df.iloc[-1]['date']}")
        print(f" 현재가: {df.iloc[-1]['close']:,}원")
        print(f" RSI 지표: {df.iloc[-1]['rsi']:.2f}")
        print(f" 최종 신호: {signal}")
        print("="*40)
    else:
        print(f"\n[실패] DB 데이터가 부족합니다. (현재 DB 내 데이터: {len(df)}일치)")
        print("Tip: db_manager.py의 save_prices 함수가 제대로 작동하는지 확인하세요.")

if __name__ == "__main__":
    main()