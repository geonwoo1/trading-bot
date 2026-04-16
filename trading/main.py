import time
import pandas as pd
from google import genai
from db_manager import DBManager
from broker import KisBroker
from dotenv import load_dotenv
import os

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def calculate_rsi(price_list, period=14):
    df = pd.DataFrame(price_list)
    delta = df['close'].diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

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

def main():
    db = DBManager()
    broker = KisBroker()
    
    for ticker in db.get_watchlist():
        ohlcv = broker.get_daily_ohlcv(ticker)
        if not ohlcv: continue
        
        rsi = calculate_rsi(ohlcv)
        if rsi < 35: # 과매도 종목 필터링
            print(f"포착: {ticker} (RSI: {rsi:.2f})")
            report = get_gemini_analysis(ticker, {'close': ohlcv[-1]['close'], 'rsi': rsi})
            
            if "[DECISION: BUY]" in report:
                print(f"매수 실행: {ticker}")
                broker.buy_market_order(ticker, 1) # 1주 매수
                db.save_analysis(ticker, {'close': ohlcv[-1]['close'], 'rsi': rsi}, report)
            
            time.sleep(20) # API 호출 제한 준수

if __name__ == "__main__":
    main()