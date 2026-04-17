import os, re, time, datetime, logging
from google import genai
from google.genai import types
from db_manager import DBManager
from broker import KisBroker
from indicators import calculate_indicators

# 로깅 설정: 매매 기록을 파일로도 저장
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.FileHandler("trading.log"), logging.StreamHandler()])

# AI 설정
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_gemini_analysis(ticker, data, context):
    """AI를 통한 종목 심층 분석 및 매매 결정"""
    prompt = f"종목: {ticker}, 데이터: {data}, 상황: {context}. [DECISION: BUY/SELL/HOLD], [SCORE: 0~100] 형식으로 답변."
    for attempt in range(3):
        try:
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
            return res.text
        except Exception as e:
            if "503" in str(e): time.sleep(30)
            elif "429" in str(e): time.sleep(60)
            else: break
    return "[DECISION: HOLD][SCORE: 0]"

def calculate_buy_amount(balance_data, score):
    """AI 점수에 따른 투자 비중 계산 (리스크 관리)"""
    cash = balance_data['cash']
    percent = 0.30 if score >= 95 else (0.20 if score >= 85 else 0.10)
    return int(cash * percent)

def update_portfolio_status(broker, db):
    """실제 계좌와 DB 동기화"""
    balance = broker.get_balance()
    total_asset = balance['cash'] + sum(s['qty'] * s['current_price'] for s in balance['stocks'])
    db.save_account_status(total_asset, balance['cash'], total_asset - balance['cash'])
    db.clear_portfolio_table()
    for s in balance['stocks']:
        db.save_portfolio_item(s['ticker'], s['name'], s['qty'], s['avg_price'], s['current_price'], s['qty']*s['current_price'], 0, 0)
    logging.info(f"[*] 동기화 완료: 총 자산 {total_asset:,}원")

def main():
    db, broker = DBManager(), KisBroker()
    logging.info(">>> 봇 가동 시작")
    
    update_portfolio_status(broker, db)
    balance = broker.get_balance()

    # 1. 보유 종목 관리 (매도/추가매수)
    for stock in balance['stocks']:
        ticker = stock['ticker']
        logging.info(f"[*] 분석 대상(보유): {stock['name']}({ticker})")
        df = calculate_indicators(db.get_price_data(ticker))
        report = get_gemini_analysis(ticker, df.iloc[-1].to_dict(), "보유 종목 매도/홀딩/추가매수 판단")
        
        decision = re.search(r'\[DECISION:\s*(.*?)\]', report)
        score = re.search(r'\[SCORE:\s*(\d+)\]', report)
        d, s = (decision.group(1).upper() if decision else "HOLD"), (int(score.group(1)) if score else 0)
        
        logging.info(f"[*] 결과: {d} (Score: {s})")
        if d == "SELL" and s >= 70:
            broker.sell_market_order(ticker, stock['qty'])
            update_portfolio_status(broker, db)
        elif d == "BUY" and s >= 85:
            qty = calculate_buy_amount(balance, s) // stock['current_price']
            if qty > 0:
                broker.buy_market_order(ticker, qty)
                update_portfolio_status(broker, db)

    # 2. 신규 종목 스캔
    all_tickers = db.get_watchlist()
    for ticker in [t for t in all_tickers if t not in [s['ticker'] for s in balance['stocks']]]:
        df = calculate_indicators(db.get_price_data(ticker))
        if df is not None and df.iloc[-1]['rsi'] < 35:
            logging.info(f"[*] 분석 대상(신규): {ticker}")
            report = get_gemini_analysis(ticker, df.iloc[-1].to_dict(), "신규 매수 고려중")
            score = int(re.search(r'\[SCORE:\s*(\d+)\]', report).group(1)) if re.search(r'\[SCORE:\s*(\d+)\]', report) else 0
            if "[DECISION: BUY]" in report and score >= 80:
                qty = calculate_buy_amount(balance, score) // df.iloc[-1]['close']
                if qty > 0:
                    broker.buy_market_order(ticker, qty)
                    update_portfolio_status(broker, db)
        time.sleep(1)

if __name__ == "__main__":
    main()