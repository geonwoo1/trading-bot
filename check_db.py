import sqlite3

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

if __name__ == "__main__":
    view_db()