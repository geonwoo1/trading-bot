import sqlite3
import datetime
import pandas as pd
import os

class DBManager:
    def __init__(self, db_name="trading.db"):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        db_path = os.path.join(parent_dir, db_name)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS my_watchlist (Code TEXT PRIMARY KEY)''')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS analysis_reports (
            ticker TEXT, analysis_date TEXT, close INTEGER, rsi REAL, report TEXT)''')
        self.conn.commit()

    def get_watchlist(self):
        """데이터를 전체 읽지 않고 필요한 목록만 쿼리로 추출"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT ticker FROM daily_prices")
        return [str(row[0]).zfill(6) for row in cursor.fetchall()]

    def save_analysis(self, ticker, data, report):
        self.conn.execute('''INSERT INTO analysis_reports VALUES (?, ?, ?, ?, ?)''',
                          (ticker, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                           int(data['close']), float(data['rsi']), report))
        self.conn.commit()

    def __del__(self):
        self.conn.close()