import os, re, time, datetime
from google import genai
from google.genai import types
from db_manager import DBManager
from broker import KisBroker
from indicators import calculate_indicators

# AI 설정
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- [복원] 핵심 보조 함수들 ---
def get_gemini_analysis(ticker, data, context='매수 고려중'):
    """베테랑 애널리스트 분석 함수"""
    prompt = f"""
    당신은 10년 차 베테랑 증권사 애널리스트입니다. '{ticker}' 종목을 분석해주세요.
    현재 투자자의 상태는 '{context}'입니다.

    [기술적 지표]
    - 현재가: {data.get('close', 0):,}원
    - RSI(14): {data.get('rsi', 0):.2f}
    - 20일 이동평균선(MA20): {data.get('ma20', 0):.2f}원
    - 볼린저 밴드 하단: {data.get('bb_lower', 0):.2f}원

    [분석 요청]
    1. RSI 수치 기반 기술적 판단 (과매도/과매수 여부).
    2. 최근 1주일간 뉴스 검색 후 종합 투자 의견 제시.
    3. 해당 종목과 관련된 주요 테마들의 현재 상태 분석.
    4. 위 정보를 종합한 최종 투자 전략.
    5. 최종 점수 [SCORE: 0~100] 명시.
    6. 반드시 [DECISION: BUY/SELL/HOLD]를 포함할 것.
    """
    for attempt in range(3):
        try:
            res = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt, 
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            return res.text
        except Exception as e:
            # [수정] 실패 시 구체적인 에러 내용 출력
            error_msg = str(e)
            print(f"[!] AI 분석 시도 {attempt+1}회 실패: {error_msg}")
            
            if "503" in error_msg: 
                time.sleep(30)
            elif "429" in error_msg: 
                print("[!] 할당량 초과(429) 발생! 잠시 대기합니다.")
                time.sleep(60)
            else: 
                break
    
    # 실패 원인을 분석 결과에 포함하여 반환하도록 변경
    return f"[DECISION: HOLD][SCORE: 0] 분석 실패 (마지막 에러: API 호출 오류)"

def calculate_buy_amount(balance_data, score):
    """점수별 비중 계산"""
    cash = balance_data['cash']
    percent = 0.30 if score >= 95 else (0.20 if score >= 85 else 0.10)
    return int(cash * percent)

def update_portfolio_status(broker, db):
    """계좌 동기화 함수"""
    balance = broker.get_balance()
    total_asset = balance['cash'] + sum(s['qty'] * s['current_price'] for s in balance['stocks'])
    db.save_account_status(total_asset, balance['cash'], total_asset - balance['cash'])
    db.clear_portfolio_table()
    for s in balance['stocks']:
        db.save_portfolio_item(s['ticker'], s['name'], s['qty'], s['avg_price'], s['current_price'], s['qty']*s['current_price'], 0, 0)

# --- [메인 로직] ---
def main():
    db, broker = DBManager(), KisBroker()
    print(f"\n[{datetime.datetime.now()}] 봇 가동 시작.")
    
    update_portfolio_status(broker, db)
    balance = broker.get_balance()
    print(f"[*] 현재 계좌 자산: {balance['cash']:,}원 | 보유 종목: {len(balance['stocks'])}개")

    # 1. 보유 종목 관리
    for stock in balance['stocks']:
        ticker = stock['ticker']
        print(f"\n--- [보유 종목 분석] {stock['name']}({ticker}) ---")
        df = calculate_indicators(db.get_price_data(ticker))
        report = get_gemini_analysis(ticker, df.iloc[-1].to_dict(), "보유 종목 매도/홀딩/추가매수 판단")
        print(f"[AI 리포트 원문]\n{report.strip()}\n")
        
        decision = re.search(r'\[DECISION:\s*(.*?)\]', report)
        score = re.search(r'\[SCORE:\s*(\d+)\]', report)
        d, s = (decision.group(1).upper() if decision else "HOLD"), (int(score.group(1)) if score else 0)
        
        print(f"[최종 결정] 판단: {d} (Score: {s})")
        if d == "SELL" and s >= 70:
            broker.sell_market_order(ticker, stock['qty'])
            update_portfolio_status(broker, db)
        elif d == "BUY" and s >= 85:
            qty = calculate_buy_amount(balance, s) // stock['current_price']
            if qty > 0:
                broker.buy_market_order(ticker, qty)
                update_portfolio_status(broker, db)

    # 2. 신규 종목 스캔 (사전 확인 포함)
    all_tickers = db.get_watchlist()
    target_tickers = [t for t in all_tickers if t not in [s['ticker'] for s in balance['stocks']]]
    
    print(f"\n[*] 전체 {len(target_tickers)}개 종목 RSI 사전 확인 중...")
    rsi_low_list = [t for t in target_tickers if calculate_indicators(db.get_price_data(t)) is not None and calculate_indicators(db.get_price_data(t)).iloc[-1]['rsi'] < 35]
    print(f"[*] 사전 스캔 완료: RSI 35 미만인 종목은 총 {len(rsi_low_list)}개입니다.")
    
    candidates = []
    for ticker in rsi_low_list:
        df = calculate_indicators(db.get_price_data(ticker))
        print(f"[!] {ticker} 심층 분석 시작...")
        report = get_gemini_analysis(ticker, df.iloc[-1].to_dict(), "신규 매수 고려중")
        print(f"[AI 리포트 원문]\n{report.strip()}\n")
        
        score = int(re.search(r'\[SCORE:\s*(\d+)\]', report).group(1)) if re.search(r'\[SCORE:\s*(\d+)\]', report) else 0
        if "[DECISION: BUY]" in report and score >= 60:
            candidates.append({'ticker': ticker, 'score': score, 'price': df.iloc[-1]['close']})
            print(f" -> [후보 등록] {ticker} (Score: {score})")
        time.sleep(0.5)

    # 3. 비중 조절 및 일괄 매수 실행
    if candidates:
        candidates.sort(key=lambda x: x['score'], reverse=True)
        print(f"\n=== 최종 후보 {len(candidates)}개 일괄 매수 시작 ===")
        for cand in candidates:
            current_balance = broker.get_balance()
            qty = calculate_buy_amount(current_balance, cand['score']) // cand['price']
            if qty > 0:
                print(f"[!!!] 일괄 매수 실행: {cand['ticker']} (Score: {cand['score']})")
                broker.buy_market_order(cand['ticker'], qty)
                update_portfolio_status(broker, db)
    else:
        print("[*] 매수 조건을 만족하는 종목이 없습니다.")

if __name__ == "__main__":
    main()