import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

# 1. 환경 설정 및 클라이언트 초기화
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# 2. 재시도 로직
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_gemini_with_search(prompt):
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.3,
    )
    
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=prompt,
        config=config
    )
    return response

# 3. 분석 수행 함수
def analyze_stock_ticker(ticker):
    print(f"[{ticker}] 뉴스 분석을 시작합니다...")
    
    prompt = f"""
    너는 10년 차 베테랑 증권사 애널리스트야. '{ticker}'에 대해 최근 1주일간의 주요 뉴스를 검색하여 분석 보고서를 작성해줘.
    
    [분석 가이드라인]
    1. 뉴스 요약: 최신순으로 핵심 뉴스 3~5가지를 요약할 것.
    2. 호재/악재 분류: 각 뉴스가 주가에 미칠 영향을 명확히 구분할 것.
    3. 주가 전망 점수: 0~100점 사이로 점수를 매기고, 그 이유를 분석 내용에 근거하여 작성할 것.
    4. 출처 표기: 분석에 사용된 기사 제목과 출처(언론사)를 반드시 명시할 것.
    
    답변은 가독성을 위해 마크다운 표와 불렛 포인트를 적극 활용해줘.
    """
    
    response = call_gemini_with_search(prompt)
    return response.text

# 4. 메인 실행부
if __name__ == "__main__":
    ticker_list = ["삼성전자"]
    
    for ticker in ticker_list:
        try:
            result = analyze_stock_ticker(ticker)
            print(f"\n{'='*20} 분석 결과 [{ticker}] {'='*20}\n")
            print(result)
        except Exception as e:
            print(f"\n[오류 발생] {ticker} 분석 실패: {e}")