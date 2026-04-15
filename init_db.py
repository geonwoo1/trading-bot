import FinanceDataReader as fdr
import sqlite3
import os

def init_database():
    # 현재 파일과 같은 경로에 있는 trading.db 사용
    db_path = 'trading.db'
    
    if not os.path.exists(db_path):
        print(f"[경고] {db_path} 파일을 찾을 수 없습니다. 새로 생성합니다.")
    
    conn = sqlite3.connect(db_path)
    
    try:
        print("KRX 종목 정보를 불러오는 중...")
        # 전 종목 리스트 가져오기
        df_krx = fdr.StockListing('KRX')
        
        # 시가총액(Marcap) 기준 상위 1,000개 추출
        # 필수 컬럼: Code(종목코드), Name(종목명), Industry(업종), Marcap(시가총액)
        top_1000 = df_krx.sort_values(by='Marcap', ascending=False).head(1000)
        
        # my_watchlist 테이블로 저장 (기존 포트폴리오 데이터는 건드리지 않음)
        top_1000.to_sql('my_watchlist', conn, if_exists='replace', index=False)
        
        print(f"성공: {db_path} 내 'my_watchlist' 테이블에 1,000개 종목 적재 완료!")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()