import time, re, os, datetime
from google import genai
from google.genai import types
from db_manager import DBManager
from broker import KisBroker
from indicators import calculate_indicators
import pandas as pd

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_gemini_analysis(ticker, current, context ='매수 고려중'):
    prompt = f"""
    당신은 10년 차 베테랑 증권사 애널리스트입니다. '{ticker}' 종목을 분석해주세요.
    현재 투자자의 상태는 '{context}'입니다.

    [기술적 지표]
    - 현재가: {current['close']:,}원
    - RSI(14): {current['rsi']:.2f}
    - 20일 이동평균선(MA20): {current['ma20']:.2f}원
    - 볼린저 밴드 하단: {current['bb_lower']:.2f}원

    [분석 요청]
    1. RSI 수치 기반 기술적 판단 (과매도/과매수 여부).
    2. 최근 1주일간 뉴스 검색 후 종합 투자 의견 제시.
    3. 해당 종목과 관련된 주요 테마들의 현재 상태 분석.
    4. 위 정보를 종합한 최종 투자 전략.
    5. 최종 점수 [SCORE: 0~100] 명시.

    답변은 투자자가 바로 이해할 수 있도록 간결하고 전문적인 톤으로 작성해주세요.
    """
    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt,
        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
    return response.text

def main():
    db = DBManager()
    broker = KisBroker()
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    tickers = db.get_watchlist()
    
    print(f"[전체 스캔 시작] 총 {len(tickers)}개 종목 분석 중...")
    analyzed_list = []
    
    for i, ticker in enumerate(tickers):
        if (i + 1) % 100 == 0: print(f" -> {i + 1}개 종목 스캔 완료")
        
        df = db.get_price_data(ticker)
        if df is None or df['date'].iloc[-1] != today:
            today_data = broker.get_daily_ohlcv(ticker)
            if today_data:
                new_df = pd.DataFrame(today_data)
                db.save_daily_data(new_df)
                df = pd.concat([df, new_df]).drop_duplicates().sort_values('date').tail(180)
        
        df = calculate_indicators(df)
        current = df.iloc[-1]
        
        if current['rsi'] < 35:
            analyzed_list.append({'ticker': ticker, 'data': current})
            print(f"   ! 포착: {ticker} (RSI: {current['rsi']:.2f})")
    
    # 상위 50개 분석
    top_50 = sorted(analyzed_list, key=lambda x: x['data']['rsi'])[:50]
    print(f"\n[심층 분석 시작] 상위 {len(top_50)}개 AI 분석 진행")
    
    for i, item in enumerate(top_50):
        print(f" -> [{i+1}/50] 분석: {item['ticker']}")
        report = get_gemini_analysis(item['ticker'], item['data'])
        
        print(f"\n--- [리포트: {item['ticker']}] ---\n{report}\n" + "-"*30)
        
        score = int(re.search(r'\[SCORE:\s*(\d+)\]', report).group(1)) if re.search(r'\[SCORE:\s*(\d+)\]', report) else 0
        db.save_analysis(item['ticker'], item['data'], score, report)
        
        if "[DECISION: BUY]" in report and score >= 80:
            broker.buy_market_order(item['ticker'], 1)
            db.save_trade(item['ticker'], item['data']['close'], 1, f"Score: {score}")
        
        time.sleep(20)
if __name__ == "__main__":
    main()