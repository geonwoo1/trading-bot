import time, re, os, datetime
from google import genai
from google.genai import types
from db_manager import DBManager
from broker import KisBroker
from indicators import calculate_indicators
import pandas as pd

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_gemini_analysis(ticker, current, context='매수 고려중'):
    # AI 분석을 위한 프롬프트 정의
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

    # 재시도 로직 적용 (최대 3번)
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", # gemini-2.5-flash 대신 안정적인 2.0 권장
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            return response.text
        
        except Exception as e:
            error_msg = str(e)
            
            # 서버 과부하(503) 발생 시
            if "503" in error_msg:
                print(f"[!] 서버 과부하 발생 (503). {attempt+1}번째 재시도 중... 30초 대기")
                time.sleep(30)
            
            # 할당량 초과(429) 발생 시
            elif "429" in error_msg:
                print(f"[!] 할당량 초과 (429). 대기 필요. 60초 대기...")
                time.sleep(60)
            
            # 그 외의 에러
            else:
                print(f"[!] 분석 중 에러 발생 ({ticker}): {error_msg}")
                break 

    return "[SCORE: 0] 분석 실패"
def update_portfolio_status(broker, db):
    # 1. 한국투자증권 API로 잔고 조회
    balance_data = broker.get_balance() 
    # balance_data 예시: {'cash': 5000000, 'stocks': [{'ticker': '005930', 'name': '삼성전자', 'qty': 10, 'avg_price': 70000, 'current_price': 72000}, ...]}
    total_stock_asset = sum(s['qty'] * s['current_price'] for s in balance_data['stocks'])
    total_asset = balance_data['cash'] + total_stock_asset
    
    print(f"--- 계좌 상태 업데이트 ---")
    print(f"총 자산: {total_asset:,}원 (현금: {balance_data['cash']:,}원 / 주식: {total_stock_asset:,}원)")
    # 2. DB에 전체 계좌 현황 저장
    db.save_account_status(total_asset, balance_data['cash'], total_stock_asset)
    # 3. 종목별 비중 계산 및 저장
    for s in balance_data['stocks']:
        amount = s['qty'] * s['current_price']
        weight = (amount / total_asset) * 100 if total_asset > 0 else 0
        profit_rate = ((s['current_price'] - s['avg_price']) / s['avg_price']) * 100
        
        print(f"-> {s['name']}({s['ticker']}): 비중 {weight:.2f}% / 수익률 {profit_rate:.2f}%")
        
        # DB에 종목별 상세 데이터 저장 (Insert or Replace)
        db.save_portfolio_item(s['ticker'], s['name'], s['qty'], s['avg_price'], s['current_price'], amount, profit_rate, weight)
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
    top_50 = sorted(analyzed_list, key=lambda x: x['data']['rsi'])[:5]
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