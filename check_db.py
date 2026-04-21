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
    ticker_data = pd.read_sql(f"SELECT * FROM daily_prices WHERE ticker='{ticker}' ORDER BY date DESC LIMIT 5;", conn)
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
def check_recent_data():
    conn = sqlite3.connect('trading.db')
    
    print("\n=== 전체 종목 중 가장 최근 데이터 5개 ===")
    # 모든 종목을 통틀어 날짜(date) 기준 내림차순으로 5개만 가져옵니다.
    query = "SELECT * FROM daily_prices order by date desc LIMIT 5;"
    
    recent_df = pd.read_sql(query, conn)
    
    if not recent_df.empty:
        print(recent_df)
    else:
        print("데이터가 존재하지 않습니다.")
        
    conn.close()

import sqlite3
import os

def clear_daily_prices_fixed():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'trading.db')
    
    conn = sqlite3.connect(db_path)
    # 기본적으로 sqlite3는 자동 커밋 모드가 아님을 인지해야 합니다.
    cursor = conn.cursor()
    try:
        print("데이터 삭제 중...")
        # 1. 데이터 삭제
        cursor.execute("DELETE FROM daily_prices")
        
        # 2. 커밋을 먼저 수행하여 트랜잭션을 완전히 종료합니다.
        conn.commit()
        print("데이터 삭제 완료 및 트랜잭션 종료.")

        # 3. 트랜잭션 외부에서 VACUUM 실행
        # (sqlite3 모듈의 기본 격리 수준 때문에 isolation_level을 None으로 잠시 설정)
        old_isolation_level = conn.isolation_level
        conn.isolation_level = None 
        conn.execute("VACUUM")
        conn.isolation_level = old_isolation_level
        
        print("DB 용량 최적화(VACUUM) 완료.")
        
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        conn.close()

def reset_daily_prices():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'trading.db')
    """기존 가격 테이블을 완전히 삭제하고 초기화하는 함수"""
    confirm = input("[주의] 기존 모든 가격 데이터를 삭제하시겠습니까? (y/n): ")
    if confirm.lower() == 'y':
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS daily_price")
        conn.commit()
        conn.close()
        print("[!] daily_price 테이블이 초기화되었습니다.")
    else:
        print("[*] 초기화를 취소합니다.")

if __name__ == "__main__":
    reset_daily_prices()
