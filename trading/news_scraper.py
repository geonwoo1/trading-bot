import requests
from bs4 import BeautifulSoup

def get_news_titles(keyword):
    # 네이버 뉴스 검색 결과 페이지
    url = f"https://search.naver.com/search.naver?where=news&query={keyword}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 뉴스 제목들 가져오기
    titles = [item.text for item in soup.select('a.news_tit')]
    return titles

# 테스트
if __name__ == "__main__":
    keyword = "AI 반도체"
    print(f"=== '{keyword}' 관련 뉴스 ===")
    for title in get_news_titles(keyword):
        print(f"- {title}")