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
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 2. 테이블 생성 및 인덱스 설정
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            ticker TEXT,
            date TEXT,
            close INTEGER,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker_date ON daily_prices (ticker, date)")
    
    # 3. 감시 종목 리스트업 + 코스피 지수 추가
    cursor.execute("SELECT Code FROM my_watchlist")
    tickers = [row[0] for row in cursor.fetchall()]
    
    # [수정] FinanceDataReader에서 코스피 지수 코드는 'KS11'입니다.
    # 리스트 맨 앞에 추가하여 시장 데이터부터 수집하도록 합니다.
    market_index_code = 'KS11'
    if market_index_code not in tickers:
        tickers.insert(0, market_index_code)
    
    # 4. 날짜 설정
    today_dt = datetime.now()
    today_str = today_dt.strftime('%Y-%m-%d')
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 데이터 업데이트 시작...")

    for ticker in tqdm(tickers):
        try:
            # [수정] DB에 저장할 땐 'KOSPI'라는 이름으로 통일 (main.py 호환용)
            save_name = 'KOSPI' if ticker == 'KS11' else ticker

            # 5. 종목별 마지막 저장일 확인
            cursor.execute("SELECT MAX(date) FROM daily_prices WHERE ticker = ?", (save_name,))
            last_date = cursor.fetchone()[0]
            
            if last_date:
                last_dt = datetime.strptime(last_date, '%Y-%m-%d')
                start_fetch = (last_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                # 데이터가 아예 없으면 200일치 최초 수집 (MA60 계산을 위해 넉넉히)
                start_fetch = (today_dt - timedelta(days=250)).strftime('%Y-%m-%d')

            if start_fetch > today_str:
                continue
                
            # 6. 데이터 수집
            df = fdr.DataReader(ticker, start=start_fetch, end=today_str)
            
            if df.empty:
                continue
                
            # 7. 데이터 정제
            df = df.reset_index()[['Date', 'Close', 'Volume']]
            df.columns = ['date', 'close', 'volume']
            df['ticker'] = save_name  # 'KS11' 대신 'KOSPI'로 저장
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')
            
            # 8. DB 저장
            df.to_sql('daily_prices', conn, if_exists='append', index=False)
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"\n[!] {ticker} 수집 중 오류: {e}")
            continue
            
    # 9. 데이터 관리 (최신 200일치 유지)
    print("\n[*] 오래된 데이터 정리 중 (종목별 최신 200일 유지)...")
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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 모든 작업이 완료되었습니다!")

if __name__ == "__main__":
    fetch_and_save_prices()