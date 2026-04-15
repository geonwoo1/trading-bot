# create_table.py (아까 알려드린 코드와 동일)
import sqlite3
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'trading.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 테마 테이블 생성
# 1. 테마 테이블 생성
# 1. 테마 테이블 생성
cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock_themes (
        ticker TEXT PRIMARY KEY,
        theme_name TEXT
    )
''')

conn.commit()
conn.close()
print("stock_themes 테이블 생성 완료!")