import sqlite3
import pandas as pd
import datetime
import os
class DBManager:
    def __init__(self, db_name="trading.db"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        db_path = os.path.join(parent_dir, db_name)
        
        print(f"[DEBUG] DB 연결 경로: {db_path}")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        # 모든 실행을 self.conn.execute로 통일하면 cursor 정의 순서 리스크를 줄일 수 있네.
        
        # 1. 분석 리포트 및 거래 기록
        self.conn.execute('''CREATE TABLE IF NOT EXISTS analysis_reports (
            ticker TEXT, analysis_date TEXT, close INTEGER, rsi REAL, score INTEGER, report TEXT,
            PRIMARY KEY (ticker, analysis_date))''')
        
        self.conn.execute('''CREATE TABLE IF NOT EXISTS trade_history (
            ticker TEXT, trade_date TEXT, execution_price INTEGER, quantity INTEGER, total_amount INTEGER, msg TEXT)''')

        # 2. 포트폴리오 (이제 stock_name이 확실히 들어갔군!)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS portfolio (
                ticker TEXT PRIMARY KEY,
                stock_name TEXT,
                quantity INTEGER,
                avg_buy_price INTEGER,
                current_price INTEGER,
                total_amount INTEGER,
                profit_rate REAL,
                weight REAL,
                updated_at TEXT
            )
        ''')

        # 3. 계좌 상태
        self.conn.execute('''CREATE TABLE IF NOT EXISTS account_status (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_asset REAL,
                    cash_balance REAL,
                    stock_asset REAL,
                    updated_at TEXT
        )''')
        
        self.conn.commit()

    def get_price_data(self, ticker):
        """최근 180일치 데이터 조회 (비어있을 경우 빈 DataFrame 반환)"""

        query = "SELECT * FROM daily_prices WHERE ticker = ? ORDER BY date DESC LIMIT 180"
        
        try:
            df = pd.read_sql(query, self.conn, params=(ticker,))
            if df.empty:
                print(f"[!] DB에 {ticker} 데이터가 없습니다.")
                return pd.DataFrame() # None 대신 빈 객체 반환
            
            return df.sort_values('date')
        except Exception as e:
            print(f"[!] DB 조회 중 오류 발생: {e}")
            return pd.DataFrame()

    def save_daily_data(self, df):
        # 새로운 데이터 append
        df.to_sql('daily_prices', self.conn, if_exists='append', index=False)

    def save_analysis(self, ticker, data, score, report):
        # 컬럼명을 직접 명시하여 데이터가 엉뚱한 곳에 들어가는 것을 방지합니다.
        self.conn.execute('''
            INSERT INTO analysis_reports (ticker, analysis_date, close, rsi, score, report)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (ticker, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
            int(data['close']), float(data['rsi']), int(score), report))
        self.conn.commit()

    def save_trade(self, ticker, price, qty, msg):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.conn.execute('''INSERT INTO trade_history VALUES (?, ?, ?, ?, ?, ?)''',
                          (ticker, now, int(price), int(qty), int(price * qty), msg))
        self.conn.commit()

    def get_watchlist(self):
        df = pd.read_sql("SELECT DISTINCT ticker FROM daily_prices", self.conn)
        return df['ticker'].dropna().astype(str).str.zfill(6).tolist()

    def save_account_status(self, total_asset, cash_balance, stock_asset):
        """계좌 잔고 정보를 DB에 저장 (id가 1인 레코드를 갱신)"""
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.conn.execute('''
            INSERT OR REPLACE INTO account_status (id, total_asset, cash_balance, stock_asset, updated_at)
            VALUES (1, ?, ?, ?, ?)
        ''', (float(total_asset), float(cash_balance), float(stock_asset), now))
        self.conn.commit()
    def clear_portfolio_table(self):
        """포트폴리오 테이블 전체 삭제"""
        self.conn.execute("DELETE FROM portfolio")
        self.conn.commit()

    def save_portfolio_item(self, ticker, name, qty, avg, curr, total, profit, weight):
        """포트폴리오 정보 저장"""
        self.conn.execute('''
            INSERT OR REPLACE INTO portfolio 
            (ticker, stock_name, quantity, avg_buy_price, current_price, total_amount, profit_rate, weight, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ticker, name, qty, avg, curr, total, profit, weight, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        self.conn.commit()