import os, re, time
import pandas as pd
from google import genai
from google.genai import types
from db_manager import DBManager
from broker import KisBroker
from indicators import calculate_indicators
from datetime import datetime
from pykrx import stock
# ==============================
# [전략 파라미터]
# ==============================
MAX_POSITION_RATIO = 0.2
STOP_LOSS_PCT = 0.08
TAKE_PROFIT_PCT = 0.15
RSI_BUY = 40
RSI_SELL = 75
MIN_AI_SCORE = 55
MAX_AI_ANALYZE = 30  # 무료 티어 속도를 고려해 30개로 조절

# ==============================
# AI 설정
# ==============================
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ==============================
# 유틸
# ==============================
def get_ai_score_and_reason(ticker, data):
    """AI에게 점수와 판단 근거를 요청합니다."""
    print(f"   - [{ticker}] AI 심층 분석 중...", end="", flush=True)
    stock_name = data.get('name', ticker)
    prompt = f"""
    너는 15년차 수석 투자 애널리스트이며, 초기 상승 신호를 포착하는 트레이딩 전문가다.
    완벽한 확정보다 '선반영 가능성'과 '수급 변화'를 더 중요하게 평가한다.

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

    ※ RSI 30~45 구간 + 상승 시도 → +10
    ※ MA20 상향 돌파 직전 → +10
    ※ 테마 강세 → +10
    ※ 단기 급등 후 뉴스 → -10 (이미 반영)

    [4. 출력 형식] (절대 변경 금지, 항목별 점수를 반드시 포함하라)
    [SCORE: 총합점수숫자만]
    [TECH: 기술적 상태 분석 이유와 점수 (점수/40)(40자 이내)]
    [NEWS: 뉴스/이벤트 분석 내용과 점수 (점수/30)(40자 이내)]
    [THEME: 테마/섹터 수급 분석 이유와 점수 (점수/30)(40자 이내)]
    [REASON: 위 항목들을 종합한 최종 매수/매도 근거 (100자 이내)]
    """
    try:
        # 모델명은 자네가 사용하는 버전에 맞춰 확인하게나 (예: gemini-2.0-flash 등)
        res = client.models.generate_content(model="gemini-3.1-flash-lite-preview", contents=prompt)
        text = res.text
        
        # 2. 정규식 추출
        score_match = re.search(r'\[SCORE:\s*(\d+)\]', text)
        tech_match = re.search(r'\[TECH:\s*(.*?)\]', text)
        news_match = re.search(r'\[NEWS:\s*(.*?)\]', text)
        theme_match = re.search(r'\[THEME:\s*(.*?)\]', text)
        reason_match = re.search(r'\[REASON:\s*(.*?)\]', text)
        
        score = int(score_match.group(1)) if score_match else 50
        
        # [핵심] 이제 변수명 자체가 "분석 결과"를 담게 되네
        tech_result = tech_match.group(1).strip() if tech_match else "데이터 부족"
        news_result = news_match.group(1).strip() if news_match else "재료 확인 불가"
        theme_result = theme_match.group(1).strip() if theme_match else "수급 파악 불가"
        final_reason = reason_match.group(1).strip() if reason_match else "종합 판단 근거 누락"
        
        # 3. 터미널 출력 (이제 "이유"가 직접 찍힐 걸세!)
        print(f" 완료! (종합 점수: {score}점)")
        print(f"     ├─ [차트 분석]: {tech_result}") 
        print(f"     ├─ [뉴스 분석]: {news_result}") 
        print(f"     ├─ [테마 분석]: {theme_result}") 
        print(f"     └─ [종합 판단]: {final_reason}")
        return score, final_reason
    except Exception as e:
        print(f" 실패: {e}")
        return 50, f"오류 발생: {str(e)}"


def update_portfolio(broker, db):
    print("\n" + "="*60)
    print(f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 포트폴리오 리포트 ".center(60, "■"))
    print("="*60)
    
    balance = broker.get_balance()
    
    real_stocks = [s for s in balance['stocks'] if s['ticker'] not in ['KOSPI', 'KS11']]
    stock_value = sum(s['qty'] * s['current_price'] for s in real_stocks)
    total_asset = balance['cash'] + stock_value
    
    print(f"{'종목명':<12} | {'보유량':>5} | {'평균단가':>10} | {'현재가':>10} | {'수익률':>8}")
    print("-" * 60)
    
    for s in real_stocks:
        profit_rate = ((s['current_price'] - s['avg_price']) / s['avg_price']) * 100
        color = "\033[91m" if profit_rate > 0 else "\033[94m"
        reset = "\033[0m"
        
        print(f"{s['name']:<12} | {s['qty']:>8} | {s['avg_price']:>12,.0f} | {s['current_price']:>12,.0f} | {color}{profit_rate:>7.2f}%{reset}")
        
        weight = (s['qty'] * s['current_price'] / total_asset) * 100
        db.save_portfolio_item(
            s['ticker'], s['name'], s['qty'], s['avg_price'],
            s['current_price'], s['qty']*s['current_price'], profit_rate, weight
        )

    print("-" * 60)
    cash_ratio = (balance['cash'] / total_asset) * 100
    stock_ratio = (stock_value / total_asset) * 100
    
    print(f" [예수금] {balance['cash']:>15,.0f}원 ({cash_ratio:>5.1f}%)")
    print(f" [주식액] {stock_value:>15,.0f}원 ({stock_ratio:>5.1f}%)")
    print(f" [총자산] {total_asset:>15,.0f}원")
    print("="*60 + "\n")
    
    db.save_account_status(total_asset, balance['cash'], stock_value)
    
    balance['stocks'] = real_stocks
    return balance, total_asset


def calculate_qty(total_asset, price):
    target_value = total_asset * 0.05
    return int(target_value // price)


# ==============================
# 메인 로직
# ==============================
def main():
    db, broker = DBManager(), KisBroker()
    print(f"\n{'='*50}\n[*] 시스템 가동 시간: {datetime.now()}\n{'='*50}")

    balance, total_asset = update_portfolio(broker, db)

    # 0. 시장 필터
    print("\n[단계 0] 시장 트렌드 확인 (KOSPI)")
    market_df = calculate_indicators(db.get_price_data("KOSPI"))
    if market_df is None or market_df.empty or 'ma60' not in market_df.columns:
        print("    [!] 시장 데이터 부족으로 신규 매수 금지")
        allow_buy = False
    else:
        m = market_df.iloc[-1]
        print(f"    - KOSPI: {m['close']} / MA60: {m['ma60']:.2f}")
        allow_buy = m['close'] >= m['ma60']
        print(f"    - 결과: {'상승장(매수 가능)' if allow_buy else '하락장(매수 금지)'}")

    # 1. 보유 종목 관리
    print(f"\n[단계 1] 보유 종목 점검 ({len(balance['stocks'])}개)")
    for stock in balance['stocks']:
        ticker, name = stock['ticker'], stock['name']
        df = calculate_indicators(db.get_price_data(ticker))
        if df is None or df.empty: continue
        row = df.iloc[-1]
        price, rsi, avg = row['close'], row['rsi'], stock['avg_price']
        profit_rt = (price - avg) / avg * 100
        print(f"    > {name}({ticker}): 수익률 {profit_rt:.2f}% / RSI: {rsi:.1f}")

        if price < avg * (1 - STOP_LOSS_PCT):
            print("      [매도] 손절선 도달")
            broker.sell_market_order(ticker, stock['qty'])
        elif profit_rt/100 > TAKE_PROFIT_PCT and rsi > RSI_SELL:
            print("      [매도] 익절 및 고RSI 도달")
            broker.sell_market_order(ticker, stock['qty'])
        else:
            # 매도 조건 아닐 때만 AI 분석 진행
            score, reason = get_ai_score_and_reason(ticker, row.to_dict())
            
            # API 호출 간격 유지 (4초)
            time.sleep(4) 
            
            if score < 30:
                print(f"      [매도] AI 부정적 의견: {reason}")
                broker.sell_market_order(ticker, stock['qty'])

    # 2. 신규 종목 스캔
    if not allow_buy:
        print("\n[단계 2] 하락장으로 스캔 종료")
        return

    print("\n[단계 2] 종목 스캔 및 선별 AI 분석")
    owned = [s['ticker'] for s in balance['stocks']]
    targets = [t for t in db.get_watchlist() if t not in owned]
    print(f"    - {len(targets)}개 종목 기술적 필터링 중...", end="", flush=True)

    pre_candidates = []
    for ticker in targets:
        df = calculate_indicators(db.get_price_data(ticker))
        if df is None or df.empty or len(df) < 60: continue
        row = df.iloc[-1]
        if row['rsi'] < RSI_BUY or row['close'] < row['bb_lower']:
            pre_candidates.append((ticker, row))
    print(f" 완료! (대상: {len(pre_candidates)}개)")

    pre_candidates.sort(key=lambda x: x[1]['rsi'])
    candidates = []
    analyze_count = min(len(pre_candidates), MAX_AI_ANALYZE)
    
    print(f"    - 상위 {analyze_count}개 AI 분석 시작 (약 {analyze_count * 4}초 소요 예정)...")
    for ticker, row in pre_candidates[:analyze_count]:
        score, reason = get_ai_score_and_reason(ticker, row.to_dict())
        if score >= MIN_AI_SCORE:
            candidates.append((ticker, score, row['close']))
        
        # API 호출 간격 유지 (4초)
        time.sleep(10)

    # 3. 매수 실행
    print(f"\n[단계 3] 최종 매수 실행 (후보: {len(candidates)}개)")
    candidates.sort(key=lambda x: x[1], reverse=True)
    for ticker, score, price in candidates:
        qty = calculate_qty(total_asset, price)
        if qty <= 0 or balance['cash'] < qty * price: continue
        print(f"    [▶] 매수 주문: {ticker} (Score: {score})")
        broker.buy_market_order(ticker, qty)
        
        # 매수 후 포트폴리오 즉시 갱신
        balance, total_asset = update_portfolio(broker, db)

    print(f"\n{'='*50}\n[*] 시스템 종료: {datetime.now()}\n{'='*50}")

if __name__ == "__main__":
    main()