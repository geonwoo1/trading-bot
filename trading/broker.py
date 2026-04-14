import requests
import json
import os
import datetime
from dotenv import load_dotenv
from db_manager import DBManager

load_dotenv()

class KisBroker:
    def __init__(self, db_manager):
        self.db = db_manager
        self.url = os.getenv("URL")
        self.app_key = os.getenv("APP_KEY")
        self.app_secret = os.getenv("APP_SECRET")
        self.cano = os.getenv("CANO")
        self.acnt_prdt_cd = os.getenv("ACNT_PRDT_CD")
        self.token_file = "token.txt"
        self.access_token = self._load_or_get_token()

    def _load_or_get_token(self):
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as f: return f.read().strip()
        return None

    def get_my_portfolio(self):
        """잔고 조회 API 호출"""
        path = "/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "TTTC8018R"
        }
        params = {"CANO": self.cano, "ACNT_PRDT_CD": self.acnt_prdt_cd, "INQR_DVSN": "02"}
        res = requests.get(f"{self.url}/{path}", params=params, headers=headers)
        data = res.json()
        return [{
            "ticker": item['pdno'],
            "name": item['prdt_name'],
            "qty": int(item['hldg_qty']),
            "avg_price": float(item['pchs_avg_pric']),
            "eval_amt": float(item['evlu_amt'])
        } for item in data.get('output1', [])]

    def buy_market_order(self, ticker, qty):
        """시장가 매수 주문"""
        path = "/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "VTTC0802U"
        }
        data = {
            "CANO": self.cano, "ACNT_PRDT_CD": self.acnt_prdt_cd, 
            "PDNO": ticker, "ORD_QTY": str(qty), "ORD_UNPR": "0"
        }
        res = requests.post(f"{self.url}/{path}", data=json.dumps(data), headers=headers)
        return res.json()

    def sync_data(self):
        """잔고 조회 후 DB에 동기화"""
        portfolio = self.get_my_portfolio()
        self.db.save_portfolio(portfolio)
        print("포트폴리오 동기화 성공!")

    def get_daily_ohlcv(self, ticker):
            # 주말 대응: 오늘이 토/일이면 금요일을 마지막 거래일로 설정
            today = datetime.datetime.now()
            offset = today.weekday() - 4 if today.weekday() > 4 else 0
            end_date = (today - datetime.timedelta(days=offset)).strftime("%Y%m%d")
            start_date = (today - datetime.timedelta(days=200)).strftime("%Y%m%d")
            
            path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appKey": self.app_key,
                "appSecret": self.app_secret,
                "tr_id": "FHKST03010100",
                "custtype": "P"
            }
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": ticker,
                "FID_INPUT_DATE_1": 20260102,
                "FID_INPUT_DATE_2": 20260410,
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "1"
            }
            res = requests.get(f"{self.url}/{path}", params=params, headers=headers)
            data = res.json()
            
            if data.get('rt_cd') != '0':
                print(f"[API 에러] {data.get('msg1')}")
                return []
                
            return [{"date": item['stck_bsop_date'], "close": int(item['stck_clpr']), "volume": int(item['acml_vol'])} 
                    for item in data.get('output2', [])]
if __name__ == "__main__":
    db = DBManager()
    broker = KisBroker(db_manager=db)
    
    # 1. 포트폴리오 동기화
    broker.sync_data()
    
    # 2. 삼성전자 과거 일봉 데이터 호출 테스트
    ticker = "005930"
    print(f"\n[테스트] {ticker} 데이터 호출 시작...")
    price_data = broker.get_daily_ohlcv(ticker)
    
    if price_data:
        print(f"가져온 데이터 개수: {len(price_data)}일")
        print(f"최근 데이터: {price_data[0]}") # 최근 날짜 데이터 출력
        
        # 3. DB 저장 테스트
        db.save_prices(ticker, price_data)
        print("데이터 DB 저장 완료!")
    else:
        print("데이터를 가져오지 못했습니다. API 응답을 확인하세요.")

    # 4. DB 출력
    print(f"\n{'종목명':<10} | {'수량':<5} | {'평가금액':<10}")
    print("-" * 30)
    for row in db.get_portfolio():
        print(f"{row[1]:<10} | {row[2]:<5} | {row[4]:<10}")