import os, re, time
import pandas as pd
from google import genai
from db_manager import DBManager
from broker import KisBroker
from indicators import calculate_indicators
from datetime import datetime, timedelta, timezone

# ==============================
# [전략 파라미터]
# ==============================
STOP_LOSS_PCT = 0.05
EARLY_STOP_LOSS = 0.03
HOLD_DAYS_LIMIT = 3

TAKE_PROFIT_PARTIAL = 0.05

RSI_BUY = 40
MIN_AI_SCORE = 70
MAX_AI_ANALYZE = 10

# ==============================
# AI 설정
# ==============================
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ==============================
# 유틸
# ==============================
def wait_for_market_open():
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now < target_time:
        wait_seconds = (target_time - now).total_seconds()
        print(f"[*] 현재 시간: {now.strftime('%H:%M:%S')}")
        print(f"[*] 장 시작까지 {int(wait_seconds)}초 대기 중...")
        time.sleep(wait_seconds)
        print("[*] 시장이 개장되었습니다.")

def get_holding_days(db, ticker):
    buy_date = db.get_last_buy_date(ticker)
    if not buy_date:
        return 0
    return (datetime.now().date() - buy_date.date()).days

def get_ai_score_and_reason(ticker, data):
    """AI에게 점수와 판단 근거를 요청합니다."""
    
    # 데이터 객체에서 종목명을 가져옵니다.
    stock_name = data.get('name', ticker)

    # 출력 형식을 종목명(코드)으로 변경
    print(f"   - [{stock_name}({ticker})] AI 심층 분석 중...", end="", flush=True)

    prompt = f"""
    너는 15년차 수석 투자 애널리스트이며, 초기 상승 신호를 포착하는 트레이딩 전문가다.
    완벽한 확정보다 '선반영 가능성'과 '수급 변화'를 더 중요하게 평가한다.
    그리고 수익이 2~3일 내로 날 것 같은 종목들을 우선 추천하고 매도 가격까지 추천해줘. 

    [분석 대상]
    - 종목: {stock_name} ({ticker})

    [1. 기술적 데이터]
    - 현재가: {data.get('close'):,.0f}
    - RSI(14): {data.get('rsi'):.2f}
    - MA20: {data.get('ma20'):,.2f}
    - MA60: {data.get('ma60'):,.2f}
    - 볼린저밴드 하단: {data.get('bb_lower'):,.2f}

    [2. 핵심 판단 로직]
    1) 기술적 선행 신호 탐지
    - RSI 30~45 구간 → "초기 반등 가능 구간"으로 가산
    - MA20이 MA60 근접 or 상향 돌파 시 → 강한 가산
    - 볼린저 하단 근접 후 반등 시 → 선매집 신호로 판단
    2) 뉴스/이벤트 해석 (선반영 포함)
    - 뉴스가 없더라도 "이상 거래/가격 흐름" 있으면 긍정 해석
    - 뉴스는 '이미 반영' vs '추가 상승 여지' 구분
    3) 테마 수급 (중요)
    - 현재 시장에서 돈이 몰리는 테마인지 최우선 평가
    - 종목 자체보다 테마 흐름이 더 강하면 가산
    [3. 점수 산정 (공격형)]
    - 기술적 선행 신호: 0~50
    - 테마 수급: 0~30
    - 뉴스/이벤트: 0~20
    [4. 출력 형식] (절대 변경 금지, 항목별 점수를 반드시 포함하라)
    [SCORE: 총합점수숫자만]
    [TECH: 기술적 상태 분석 이유와 점수 (점수/40)(40자 이내)]
    [NEWS: 뉴스/이벤트 분석 내용과 점수 (점수/30)(40자 이내)]
    [THEME: 테마/섹터 수급 분석 이유와 점수 (점수/30)(40자 이내)]
    [REASON: 위 항목들을 종합한 최종 매수/매도 근거 (100자 이내)]
    [SELL: 추천 매도 가격]
    """
    try:
        # 모델명은 실제 사용하는 환경에 맞게 조정 (예: gemini-2.0-flash)
        # gemma-4-31b-it
        res = client.models.generate_content(model="gemini-3.1-flash-lite-preview", contents=prompt)
        text = res.text
        
        score_match = re.search(r'\[SCORE:\s*(\d+)\]', text)
        tech_match = re.search(r'\[TECH:\s*(.*?)\]', text)
        news_match = re.search(r'\[NEWS:\s*(.*?)\]', text)
        theme_match = re.search(r'\[THEME:\s*(.*?)\]', text)
        reason_match = re.search(r'\[REASON:\s*(.*?)\]', text)
        sell_match = re.search(r'\[SELL:\s*(.*?)\]', text)

        score = int(score_match.group(1)) if score_match else 50
        tech_result = tech_match.group(1).strip() if tech_match else "데이터 부족"
        news_result = news_match.group(1).strip() if news_match else "재료 확인 불가"
        theme_result = theme_match.group(1).strip() if theme_match else "수급 파악 불가"
        final_reason = reason_match.group(1).strip() if reason_match else "종합 판단 근거 누락"
        sell = sell_match.group(1).strip() if sell_match else "매도 가격 설정 불가"

        print(f" 완료! (종합 점수: {score}점)")
        print(f"     ├─ [차트 분석]: {tech_result}")
        print(f"     ├─ [뉴스 분석]: {news_result}")
        print(f"     ├─ [테마 분석]: {theme_result}")
        print(f"     └─ [종합 판단]: {final_reason}")
        print(f"     └─ [추천 매도가격]: {sell}")

        return score, final_reason

    except Exception as e:
        print(f" 실패: {e}")
        return 50, f"오류 발생: {str(e)}"

def calculate_qty(total_asset, price):
    target_value = total_asset * 0.05
    return int(target_value // price)

# ==============================
# 메인
# ==============================
def main():
    db, broker = DBManager(), KisBroker()

    print(f"\n{'='*60}")
    print(f"[시스템 가동] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    balance = broker.get_balance()
    stocks = balance['stocks']
    total_asset = balance['cash'] + sum(s['qty'] * s['current_price'] for s in stocks)

    print(f"[*] 총 자산: {total_asset:,.0f}원 | 예수금: {balance['cash']:,.0f}원")

    sell_list = []

    # ==============================
    # 1. 매도 판단
    # ==============================
    print("\n[단계 1] 보유 종목 분석")

    for stock in stocks:
        ticker, name, qty, avg = stock['ticker'], stock['name'], stock['qty'], stock['avg_price']

        df = calculate_indicators(db.get_price_data(ticker))
        row = df.iloc[-1]
        if df is None or df.empty:
            continue
        score, reason = get_ai_score_and_reason(ticker, row.to_dict())

        row = df.iloc[-1]
        price = row['close']
        profit_rt = (price - avg) / avg
        holding_days = get_holding_days(db, ticker)

        print(f" > {name} | 수익:{profit_rt*100:.2f}% | 보유:{holding_days}일")

        if holding_days <= 2 and profit_rt <= -EARLY_STOP_LOSS:
            sell_list.append((ticker, name, qty, "초반 손절", price))
        elif profit_rt <= -STOP_LOSS_PCT:
            sell_list.append((ticker, name, qty, "최종 손절", price))
        elif holding_days >= HOLD_DAYS_LIMIT and profit_rt <= 0:
            sell_list.append((ticker, name, qty, "시간 손절", price))
        elif profit_rt >= TAKE_PROFIT_PARTIAL:
            sell_qty = int(qty * 0.5)
            if sell_qty > 0:
                sell_list.append((ticker, name, sell_qty, "부분 익절", price))

    print("\n[매도 예정]")
    if sell_list:
        for t, n, q, r, p in sell_list:
            print(f" ▶ {n}({t}) | {q}주 | {r}")
    else:
        print(" 없음")

    # ==============================
    # 2. 매도 실행
    # ==============================
    wait_for_market_open()

    for ticker, name, qty, reason, price in sell_list:
        broker.sell_market_order(ticker, qty)
        db.save_trade(ticker, reason, qty, price, datetime.now())
        print(f" [✔] {name}({ticker}) 매도 완료 ({reason})")

    time.sleep(1)
    balance = broker.get_balance()
    total_asset = balance['cash'] + sum(s['qty'] * s['current_price'] for s in balance['stocks'])

    # ==============================
    # 3. 매수 후보 탐색
    # ==============================
    print("\n[단계 3] 매수 후보 탐색")

    owned = [s['ticker'] for s in balance['stocks']]
    candidates = []

    for ticker in db.get_watchlist():
        if ticker in owned:
            continue

        df = calculate_indicators(db.get_price_data(ticker))
        if df is None or len(df) < 60:
            continue

        row = df.iloc[-1]
        # 종목명 가져오기 (row에 name 컬럼이 있다고 가정)
        stock_name = row.get('name', ticker) 

        if row['rsi'] < RSI_BUY and row['close'] <= row['ma20'] * 1.05:
            print(f"\n > {stock_name}({ticker}) 분석 중...")
            score, reason = get_ai_score_and_reason(ticker, row.to_dict())

            if score >= MIN_AI_SCORE:
                candidates.append((ticker, stock_name, score, row['close'], reason))

            time.sleep(2)

    print("\n[AI 통과 후보]")
    if candidates:
        for t, n, s, p, r in candidates:
            print(f" ▶ {n}({t}) | 점수:{s} | 가격:{p:,.0f}원")
    else:
        print(" 없음")

    # ==============================
    # 4. 매수 실행
    # ==============================
    print("\n[단계 4] 매수 실행")

    # 점수(score)는 튜플의 3번째(인덱스 2)에 위치함
    candidates.sort(key=lambda x: x[2], reverse=True)
    bought_list = []

    cash = balance['cash']

    for ticker, name, score, price, reason in candidates[:5]:
        qty = calculate_qty(total_asset, price)
        cost = qty * price

        if qty > 0 and cash >= cost:
            broker.buy_market_order(ticker, qty)
            db.save_trade(ticker, "BUY", qty, price, datetime.now())

            bought_list.append((ticker, name, qty, price, score))
            cash -= cost

            print(f" [✔] {name}({ticker}) 매수 | 수량:{qty} | 점수:{score}")
            print(f"     이유: {reason}")
        else:
            print(f" [ ] {name}({ticker}) 스킵 (잔고 부족)")

    print("\n[최종 매수 종목]")
    if bought_list:
        for t, n, q, p, s in bought_list:
            print(f" ▶ {n}({t}) | {q}주 | 가격:{p:,.0f}원 | 점수:{s}")
    else:
        print(" 없음")

    print(f"\n{'='*60}")
    print(f"[시스템 종료] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

# ==============================
if __name__ == "__main__":
    main()