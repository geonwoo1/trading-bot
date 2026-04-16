import sqlite3
import pandas as pd
import os
import time
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# DB 경로 설정 (상위 폴더에 있는 trading.db)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'trading.db')

def calculate_rsi(series, period=14):
    """표준 RSI 계산 (직접 구현)"""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Wilder's Smoothing 적용
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_analysis_data(ticker):
    """DB에서 데이터를 가져와 RSI 계산"""
    conn = sqlite3.connect(DB_PATH)
    query = f"SELECT date, close FROM daily_prices WHERE ticker = '{ticker}'"
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty: return None
    
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    df = df.sort_values('date')
    df['close'] = pd.to_numeric(df['close'])
    df['rsi'] = calculate_rsi(df['close'], period=14)
    
    return df.iloc[-1] # 마지막 행 데이터

def get_gemini_analysis(ticker, data):
    """Gemini API 호출 (뉴스 검색 포함)"""
    prompt = f"""
    당신은 10년 차 베테랑 증권사 애널리스트입니다. '{ticker}' 종목을 분석해주세요.
    - 현재가: {data['close']:,}원
    - RSI(14): {data['rsi']:.2f}
    
    [분석 요청]
    1. RSI 수치 기반 기술적 판단.
    2. 최근 1주일간 뉴스 검색 후 종합 투자 의견 제시.
    3. 최종 점수 [SCORE: 0~100] 명시.
    """
    try:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=config
        )
        return response.text
    except Exception as e:
        return f"분석 중 에러 발생: {e}"

def save_analysis_to_db(ticker, data, report):
    """분석 결과 저장"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_reports (
            ticker TEXT, analysis_date TEXT, close INTEGER, rsi REAL, report TEXT,
            PRIMARY KEY (ticker, analysis_date)
        )
    ''')
    cursor.execute('''
        INSERT OR REPLACE INTO analysis_reports (ticker, analysis_date, close, rsi, report)
        VALUES (?, ?, ?, ?, ?)
    ''', (ticker, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), int(data['close']), float(data['rsi']), report))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # 1. 대상 종목 가져오기
    conn = sqlite3.connect(DB_PATH)
    tickers = [row[0] for row in conn.execute("SELECT Code FROM my_watchlist").fetchall()]
    conn.close()

    print(f"총 {len(tickers)}개 종목 RSI 계산 시작...")
    
    rsi_list = []
    for ticker in tickers:
        data = get_analysis_data(ticker)
        if data is not None and not pd.isna(data['rsi']):
            rsi_list.append({'ticker': ticker, 'data': data, 'rsi': data['rsi']})

    # 2. 과매도 기준 RSI 낮은 순 상위 10개 추출
    top_10 = sorted(rsi_list, key=lambda x: x['rsi'])[:10]

    # 3. AI 분석 및 DB 저장
    print(f"상위 10개 종목 AI 심층 분석 시작...")
    for item in top_10:
        print(f"분석 중: {item['ticker']} (RSI: {item['rsi']:.2f})")
        report = get_gemini_analysis(item['ticker'], item['data'])
        save_analysis_to_db(item['ticker'], item['data'], report)
        
        # API 할당량 보호를 위한 강제 대기 (분당 3회 제한)
        time.sleep(20) 
    
    print("모든 작업이 완료되었습니다.")