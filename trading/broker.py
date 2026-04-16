import requests, json, os
from dotenv import load_dotenv

load_dotenv()

class KisBroker:
    def __init__(self):
        self.url = os.getenv("URL")
        self.app_key = os.getenv("APP_KEY")
        self.app_secret = os.getenv("APP_SECRET")
        self.cano = os.getenv("CANO")
        self.acnt_prdt_cd = os.getenv("ACNT_PRDT_CD")
        self.access_token = self._get_token()

    def _get_token(self):
        url = f"{self.url}/oauth2/tokenP"
        body = {"grant_type": "client_credentials", "appkey": self.app_key, "appsecret": self.app_secret}
        res = requests.post(url, data=json.dumps(body))
        return res.json().get('access_token')

    def get_daily_ohlcv(self, ticker):
            path = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
            headers = {"authorization": f"Bearer {self.access_token}", "appKey": self.app_key, "appSecret": self.app_secret, "tr_id": "FHKST03010100"}
            params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker, "FID_PERIOD_DIV_CODE": "D", "FID_ORG_ADJ_PRC": "1"}
            
            # 재시도 로직 추가
            for attempt in range(3): # 최대 3번 시도
                try:
                    res = requests.get(f"{self.url}/{path}", params=params, headers=headers)
                    data = res.json().get('output2', [])
                    return [{"close": int(item['stck_clpr'])} for item in reversed(data)]
                except Exception as e:
                    print(f"[!] 연결 끊김 발생. 5초 대기 후 재시도... ({attempt+1}/3)")
                    time.sleep(5) 
            return []

    def buy_market_order(self, ticker, qty):
        path = "/uapi/domestic-stock/v1/trading/order-cash"
        headers = {"authorization": f"Bearer {self.access_token}", "appKey": self.app_key, "appSecret": self.app_secret, "tr_id": "VTTC0802U"}
        data = {"CANO": self.cano, "ACNT_PRDT_CD": self.acnt_prdt_cd, "PDNO": ticker, "ORD_QTY": str(qty), "ORD_UNPR": "0", "ORD_DVSN": "01"}
        return requests.post(f"{self.url}/{path}", data=json.dumps(data), headers=headers).json()