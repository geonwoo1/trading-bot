import os
import sqlite3
import time
import google.generativeai as genai
from dotenv import load_dotenv
from serpapi import GoogleSearch

# 1. 환경 설정
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# SerpApi 키 (없다면 SERPAPI_API_KEY를 .env에 추가하세요)
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

# 2. 모델 설정 (사용 가능한 모델 자동 선택)
def get_model():
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            return genai.GenerativeModel(m.name)
    return None

model = get_model()

# 3. 뉴스 가져오기 (SerpApi 사용)
def fetch_news(ticker_name):
    params = {
        "engine": "google",
        "q": f"{ticker_name} 주식 뉴스",
        "tbm": "nws",
        "api_key": SERPAPI_KEY
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    
    news_titles = [item['title'] for item in results.get('news_results', [])]
    return news_titles[:3]

# 4. AI 점수 산출
def get_ai_score(ticker, news_list):
    news_text = "\n".join(news_list)
    
    print(f"\n--- [뉴스 분석] {ticker} ---")
    for i, title in enumerate(news_list, 1):
        print(f"{i}. {title}")
    
    prompt = f"종목({ticker}) 향후 주가 상승 가능성 0~100점 사이 숫자만 답변. 뉴스: {news_text}"
    response = model.generate_content(prompt)
    
    try:
        score = int(response.text.strip())
        print(f"-> 분석 결과: {score}점")
        return score
    except:
        return 50

# 5. 메인 로직
def run_analysis():
    print("분석을 시작합니다...")
    conn = sqlite3.connect('../trading.db')
    cursor = conn.cursor()
    
    # 예시 티커 (실제 데이터 로직에 맞춰 변경)
    ticker = "000815"
    signal = "BUY"  # 테스트용 강제 신호
    
    if signal == "BUY":
        print(f"매수 신호 포착: {ticker}")
        news_list = fetch_news(ticker)
        news_score = get_ai_score(ticker, news_list)
        
        # 임시 점수 계산
        chart_score = 80 
        final_score = (chart_score + news_score) / 2
        
        cursor.execute("""
            INSERT INTO stock_scores (ticker, date, chart_score, news_score, final_score)
            VALUES (?, DATE('now'), ?, ?, ?)
        """, (ticker, chart_score, news_score, final_score))
        
        conn.commit()
        print("저장 완료 -> 전체 분석 및 DB 저장 완료!")
    
    conn.close()

if __name__ == "__main__":
    run_analysis()