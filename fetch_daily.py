import sqlite3
import FinanceDataReader as fdr
from tqdm import tqdm
import time
from datetime import datetime, timedelta

def fetch_and_save_prices():
    # 경로 문제 방지를 위해 현재 파일 위치 기준 절대 경로 사용
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'trading.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 날짜 설정 (오늘부터 180일 전)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    
    cursor.execute("SELECT Code FROM my_watchlist")
    tickers = [row[0] for row in cursor.fetchall()]
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            ticker TEXT,
            date TEXT,
            close INTEGER,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    ''')
    
    print(f"총 {len(tickers)}개 종목의 {start_date} ~ {end_date} 데이터 수집 시작!")
    
    for ticker in tqdm(tickers):
        try:
            # period 대신 start, end 사용
            df = fdr.DataReader(ticker, start=start_date, end=end_date)
            
            if df.empty:
                continue
                
            df = df.reset_index()[['Date', 'Close', 'Volume']]
            df.columns = ['date', 'close', 'volume']
            df['ticker'] = ticker
            
            df.to_sql('daily_prices', conn, if_exists='append', index=False)
            time.sleep(0.05)
        except Exception as e:
            continue
            
    conn.commit()
    conn.close()
    print("데이터 수집 완료!")

if __name__ == "__main__":
    fetch_and_save_prices()