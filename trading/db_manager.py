import sqlite3
import pandas as pd

class DBManager:
    def __init__(self, db_path="trading.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        """테이블이 없으면 생성"""
        with sqlite3.connect(self.db_path) as conn:
            # 포트폴리오 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio (
                    ticker TEXT PRIMARY KEY, name TEXT, qty INTEGER, 
                    avg_price REAL, eval_amt REAL, last_updated TIMESTAMP
                )
            """)
            # 시세 데이터 테이블 (차트 분석용)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_prices (
                    ticker TEXT, date TEXT, close INTEGER, volume INTEGER,
                    PRIMARY KEY (ticker, date)
                )
            """)
            conn.commit()

    def save_portfolio(self, portfolio_list):
        """포트폴리오 저장"""
        with sqlite3.connect(self.db_path) as conn:
            for item in portfolio_list:
                conn.execute("""
                    INSERT OR REPLACE INTO portfolio (ticker, name, qty, avg_price, eval_amt, last_updated)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (item['ticker'], item['name'], item['qty'], item['avg_price'], item['eval_amt']))
            conn.commit()

    def save_prices(self, ticker, price_data):
        """시세 데이터(OHLCV) 저장"""
        with sqlite3.connect(self.db_path) as conn:
            for item in price_data:
                conn.execute("""
                    INSERT OR IGNORE INTO daily_prices (ticker, date, close, volume)
                    VALUES (?, ?, ?, ?)
                """, (ticker, item['date'], item['close'], item['volume']))
            conn.commit()

    def get_portfolio(self):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT * FROM portfolio").fetchall()

    def get_prices_as_df(self, ticker):
        """DB 데이터를 판다스로 로드"""
        with sqlite3.connect(self.db_path) as conn:
            query = f"SELECT * FROM daily_prices WHERE ticker='{ticker}' ORDER BY date ASC"
            return pd.read_sql(query, conn)