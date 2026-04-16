import sqlite3
import pandas as pd

def view_db():
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()
    
    print("=== 현재 포트폴리오 상태 ===")
    cursor.execute("SELECT * FROM portfolio")
    rows = cursor.fetchall()
    
    if not rows:
        print("데이터가 없습니다.")
    else:
        for row in rows:
            # row: (ticker, name, qty, avg_price, eval_amt, last_updated)
            print(f"종목코드: {row[0]} | 이름: {row[1]} | 수량: {row[2]} | 평단가: {row[3]} | 평가금액: {row[4]} | 갱신시간: {row[5]}")
    
    conn.close()
def check_my_db():
    conn = sqlite3.connect('trading.db')
    
    # 1. 테이블 목록 확인
    tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
    print("=== DB 내 테이블 목록 ===")
    print(tables)
    
    # 2. my_watchlist에 데이터가 잘 들어갔는지 확인 (상위 5개만)
    print("\n=== my_watchlist 데이터 미리보기 (상위 5개) ===")
    watchlist = pd.read_sql("SELECT * FROM my_watchlist LIMIT 5;", conn)
    print(watchlist)
    
    # 3. 데이터 개수 확인 (1000개가 맞는지)
    count = pd.read_sql("SELECT COUNT(*) as total FROM my_watchlist;", conn)
    print(f"\n총 데이터 개수: {count['total'][0]}개")
    
    conn.close()

def check_data():
    conn = sqlite3.connect('trading.db')
    
    # 1. 일봉 데이터 테이블 상위 10개 조회
    print("=== daily_prices 테이블 데이터 샘플 (상위 10개) ===")
    df_sample = pd.read_sql("SELECT * FROM daily_prices LIMIT 10;", conn)
    print(df_sample)
    
    # 2. 데이터가 총 몇 개 들어갔는지 확인
    count = pd.read_sql("SELECT COUNT(*) as total FROM daily_prices;", conn)
    print(f"\n총 저장된 일봉 데이터 개수: {count['total'][0]}개")
    
    # 3. 특정 종목(예: 삼성전자 005930) 데이터만 뽑아보기
    ticker = '005930'
    ticker_data = pd.read_sql(f"SELECT * FROM daily_prices WHERE ticker='{ticker}' LIMIT 5;", conn)
    print(f"\n=== 삼성전자(005930) 데이터 샘플 ===")
    print(ticker_data)
    
    conn.close()
def check_analysis_reports():
    """AI가 분석한 리포트 최근 5개 확인"""
    conn = sqlite3.connect('trading.db')
    print("\n=== 최근 AI 분석 리포트 (최근 5건) ===")
    try:
        query = "SELECT * FROM analysis_reports ORDER BY analysis_date DESC LIMIT 5;"
        df = pd.read_sql(query, conn)
        print(df)
    except Exception as e:
        print(f"분석 리포트 확인 실패: {e}")
    conn.close()

def check_trade_history():
    """실제 매매 기록 확인"""
    conn = sqlite3.connect('trading.db')
    print("\n=== 실제 매매 내역 확인 ===")
    try:
        query = "SELECT * FROM trade_history ORDER BY trade_date DESC;"
        df = pd.read_sql(query, conn)
        if df.empty:
            print("아직 체결된 거래가 없습니다.")
        else:
            print(df)
    except Exception as e:
        print(f"매매 내역 확인 실패: {e}")
    conn.close()
def check_table_schema():
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(analysis_reports);")
    columns = cursor.fetchall()
    print("\n=== analysis_reports 테이블 구조 ===")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_analysis_reports()
