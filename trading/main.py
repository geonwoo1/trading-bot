import time
import pandas as pd
from google import genai
from google.genai import types
from db_manager import DBManager
from broker import KisBroker
from dotenv import load_dotenv
import os

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def calculate_rsi(price_list, period=14):
    df = pd.DataFrame(price_list)
    if len(df) < period: return None
    delta = df['close'].diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_gemini_analysis(ticker, data, context="매수 고려 중"):
    prompt = f"""
    당신은 10년 차 베테랑 증권사 애널리스트입니다. '{ticker}' 종목을 분석해주세요.
    현재 투자자의 상태는 '{context}'입니다.

    [데이터]
    - 현재가: {data['close']:,}원
    - RSI(14): {data['rsi']:.2f}

    [분석 요청]
    1. RSI 수치 기반 기술적 판단 (과매도/과매수 여부).
    2. 최근 1주일간 뉴스 검색 후 종합 투자 의견 제시.
    3. 해당 종목과 관련된 주요 테마들의 현재 상태 분석 (상승세/하락세/횡보).
    4. 위 정보를 종합한 최종 투자 전략.
    5. 최종 점수 [SCORE: 0~100] 명시.

    답변은 투자자가 바로 이해할 수 있도록 간결하고 전문적인 톤으로 작성해주세요.
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
    tickers = db.get_watchlist()
    
    print(f"--- 총 {len(tickers)}개 종목 분석 시작 ---")
    
    for i, ticker in enumerate(tickers):
        if i % 10 == 0:
            print(f"[{i}/{len(tickers)}] 처리 중: {ticker}")
            
        ohlcv = broker.get_daily_ohlcv(ticker)
        if not ohlcv: continue
        
        rsi = calculate_rsi(ohlcv)
        if rsi is not None and rsi < 35:
            print(f"  -> 포착: {ticker} (RSI: {rsi:.2f})")
            report = get_gemini_analysis(ticker, {'close': ohlcv[-1]['close'], 'rsi': rsi})
            
            if "[DECISION: BUY]" in report:
                print(f"  -> 매수 실행: {ticker}")
                broker.buy_market_order(ticker, 1)
                db.save_analysis(ticker, {'close': ohlcv[-1]['close'], 'rsi': rsi}, report)
            
            time.sleep(20) # API 제한 준수

if __name__ == "__main__":
    main()