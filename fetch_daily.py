import sqlite3
import FinanceDataReader as fdr
from tqdm import tqdm
import time
import os
from datetime import datetime, timedelta
import pandas as pd

def fetch_and_save_prices():
    # 1. 환경 설정 및 DB 연결
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'trading.db')
    
    print(f"[*] DB 경로: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 2. 테이블 생성 (스키마 강제 지정)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            ticker TEXT,
            name TEXT,
            date TEXT,
            close INTEGER,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker_date ON daily_prices (ticker, date)")
    
    # 3. 감시 종목 리스트업
    try:
        cursor.execute("SELECT Code, Name FROM my_watchlist")
        watchlist_data = cursor.fetchall()
        # { '005930': '삼성전자' } 형태의 딕셔너리
        watchlist = {str(row[0]): str(row[1]) for row in watchlist_data}
        tickers = list(watchlist.keys())
    except sqlite3.OperationalError:
        print("[!] my_watchlist 테이블을 찾을 수 없습니다.")
        return

    # 코스피 지수 데이터 추가
    if 'KS11' not in tickers:
        tickers.insert(0, 'KS11')
        watchlist['KS11'] = 'KOSPI'
    
    # 4. 날짜 설정
    today_dt = datetime.now()
    today_str = today_dt.strftime('%Y-%m-%d')
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 데이터 업데이트 시작 (대상: {len(tickers)}종목)")

    for ticker in tqdm(tickers):
        try:
            # --- [수정 구간: 변수명 명확화] ---
            # DB에 저장될 실제 '코드'와 '이름'을 명확히 정의합니다.
            if ticker == 'KS11':
                current_ticker_code = 'KOSPI'
                current_stock_name = 'KOSPI'
            else:
                current_ticker_code = ticker  # 예: '005930'
                current_stock_name = watchlist.get(ticker, ticker) # 이름 없으면 코드라도 넣음

            # 5. 마지막 저장일 확인 (current_ticker_code 기준)
            cursor.execute("SELECT MAX(date) FROM daily_prices WHERE ticker = ?", (current_ticker_code,))
            res = cursor.fetchone()
            last_date = res[0] if res else None
            
            if last_date:
                last_dt = datetime.strptime(last_date, '%Y-%m-%d')
                start_fetch = (last_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                start_fetch = (today_dt - timedelta(days=250)).strftime('%Y-%m-%d')

            if start_fetch > today_str:
                continue
                
            # 6. 데이터 수집 (fdr에는 원래의 ticker '005930' 혹은 'KS11' 전달)
            df = fdr.DataReader(ticker, start=start_fetch, end=today_str)
            
            if df.empty:
                continue
                
            # 7. 데이터 정제 및 주입
            df = df.reset_index()[['Date', 'Close', 'Volume']]
            df.columns = ['date', 'close', 'volume']
            
            # 여기서 꼬였던 부분 해결: 현재 루프의 정보를 정확히 대입
            df['ticker'] = current_ticker_code
            df['name'] = current_stock_name
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            
            # 8. DB 저장
            df = df[['ticker', 'name', 'date', 'close', 'volume']]
            df.to_sql('daily_prices', conn, if_exists='append', index=False)
            
            time.sleep(0.05) 
            
        except Exception as e:
            print(f"\n[!] {ticker} 수집 중 오류: {e}")
            continue
            
    # 9. 데이터 관리
    print("\n[*] 데이터 정리 중 (최신 200일 유지)...")
    cleanup_query = '''
        DELETE FROM daily_prices 
        WHERE (ticker, date) IN (
            SELECT ticker, date FROM (
                SELECT ticker, date, 
                       ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
                FROM daily_prices
            ) WHERE rn > 200
        )
    '''
    cursor.execute(cleanup_query)
    
    conn.commit()
    conn.close()
    print(f"\n[✔] 모든 데이터 업데이트가 완료되었습니다!")

if __name__ == "__main__":
    fetch_and_save_prices()