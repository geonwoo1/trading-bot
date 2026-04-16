import sqlite3
import datetime
import pandas as pd
import os

class DBManager:
    def __init__(self, db_name="trading.db"):
            # 현재 파일의 위치를 기준으로 한 단계 위(상위) 폴더의 경로를 구합니다.
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            db_path = os.path.join(parent_dir, db_name)
            
            print(f"[DEBUG] 연결 중인 DB 경로: {db_path}") # 경로 확인용
            
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self._create_tables()

    def _create_tables(self):
        """
        필수 데이터베이스 테이블 생성
        """
        # 1. 감시 대상 종목 테이블
        self.conn.execute('''CREATE TABLE IF NOT EXISTS my_watchlist (Code TEXT PRIMARY KEY)''')
        
        # 2. AI 분석 보고서 저장 테이블
        self.conn.execute('''CREATE TABLE IF NOT EXISTS analysis_reports (
            ticker TEXT, 
            analysis_date TEXT, 
            close INTEGER, 
            rsi REAL, 
            report TEXT)''')

        # 3. 실제 거래 기록 테이블
        self.conn.execute('''CREATE TABLE IF NOT EXISTS trade_history (
            ticker TEXT, 
            trade_date TEXT, 
            execution_price INTEGER, 
            quantity INTEGER, 
            total_amount INTEGER,
            msg TEXT)''')
        
        self.conn.commit()

    def get_watchlist(self):
        """
        daily_prices 테이블에서 고유 종목 코드를 가져옴
        """
        try:
            # daily_prices 테이블에서 고유한 ticker만 조회
            query = "SELECT DISTINCT ticker FROM daily_prices"
            df = pd.read_sql(query, self.conn)
            
            # 리스트 변환 및 6자리 문자열 포맷팅 (005930 유지)
            tickers = df['ticker'].dropna().astype(str).str.zfill(6).tolist()
            
            print(f"[DEBUG] DB에서 불러온 종목코드 ({len(tickers)}개): {tickers[:5]}...") 
            return tickers
            
        except Exception as e:
            print(f"[!] 에러 발생 (daily_prices 조회 실패 - 테이블 확인 필요): {e}")
            return []

    def save_analysis(self, ticker, data, report):
        """
        AI 분석 결과 저장
        """
        try:
            self.conn.execute('''INSERT INTO analysis_reports VALUES (?, ?, ?, ?, ?)''',
                              (ticker, 
                               datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                               int(data['close']), 
                               float(data['rsi']), 
                               report))
            self.conn.commit()
        except Exception as e:
            print(f"[!] 분석 저장 에러: {e}")

    def save_trade(self, ticker, price, qty, msg):
        """
        거래 성공 내역 저장
        """
        try:
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            total = int(price * qty)
            self.conn.execute('''INSERT INTO trade_history VALUES (?, ?, ?, ?, ?, ?)''',
                              (ticker, now, int(price), int(qty), total, msg))
            self.conn.commit()
        except Exception as e:
            print(f"[!] 거래 기록 저장 에러: {e}")

    def __del__(self):
        """
        프로그램 종료 시 연결 닫기
        """
        self.conn.close()