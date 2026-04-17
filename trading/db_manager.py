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
        # 분석 리포트와 거래 기록 테이블 생성
        self.conn.execute('''CREATE TABLE IF NOT EXISTS analysis_reports (
            ticker TEXT, analysis_date TEXT, close INTEGER, rsi REAL, score INTEGER, report TEXT)''')
        
        self.conn.execute('''CREATE TABLE IF NOT EXISTS trade_history (
            ticker TEXT, trade_date TEXT, execution_price INTEGER, quantity INTEGER, total_amount INTEGER, msg TEXT)''')
        self.conn.commit()
        # 현재 보유 종목 및 자산 상태 테이블
        self.conn.execute('''CREATE TABLE IF NOT EXISTS portfolio (
            ticker TEXT PRIMARY KEY, 
            stock_name TEXT,
            quantity INTEGER,      -- 보유 수량
            avg_buy_price REAL,    -- 매수 평균가
            current_price INTEGER, -- 현재가
            total_amount REAL,     -- 평가 금액 (수량 * 현재가)
            profit_rate REAL,      -- 수익률
            weight REAL,           -- 비중 (%)
            updated_at TEXT        -- 업데이트 시각
        )''')

        # 계좌 잔고 현황 (예수금 등)
        self.conn.execute('''CREATE TABLE IF NOT EXISTS account_status (
            id INTEGER PRIMARY KEY CHECK (id = 1), -- 단일 레코드 유지
            total_asset REAL,      -- 총 자산 (예수금 + 주식)
            cash_balance REAL,     # 주문 가능 현금
            stock_asset REAL,      # 주식 평가 총액
            updated_at TEXT
        )''')

    def get_price_data(self, ticker):
        # 180일치 데이터 조회
        query = f"SELECT * FROM daily_prices WHERE ticker = '{ticker}' ORDER BY date DESC LIMIT 180"
        df = pd.read_sql(query, self.conn)
        return df.sort_values('date') if not df.empty else None

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