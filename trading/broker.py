import requests, json, os, time
from datetime import datetime, timedelta  # [추가] 날짜 계산용
from dotenv import load_dotenv
from constants import API_CONFIG

load_dotenv()

TOKEN_FILE = "token.json"  # [추가] 토큰 저장 파일명

class KisBroker:
    def __init__(self):
        self.url = os.getenv("URL")
        self.app_key = os.getenv("APP_KEY")
        self.app_secret = os.getenv("APP_SECRET")
        self.cano = os.getenv("CANO")
        self.acnt_prdt_cd = os.getenv("ACNT_PRDT_CD")
        self.access_token = self._get_token()

    def _get_token(self):
        # 1. 파일이 존재하고, 23시간 이내라면 파일에서 읽기
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                    created_at = datetime.fromisoformat(token_data['created_at'])
                    if datetime.now() - created_at < timedelta(hours=23):
                        print("[*] 기존 토큰 재사용 중...")
                        return token_data['access_token']
            except Exception as e:
                print(f"[*] 토큰 파일 읽기 실패, 새로 발급합니다. ({e})")

        # 2. 토큰이 없거나 만료되었다면 새로 발급
        print("[*] 새 토큰 발급 중...")
        url = f"{self.url}{API_CONFIG['ENDPOINTS']['TOKEN']}"
        body = {"grant_type": "client_credentials", "appkey": self.app_key, "appsecret": self.app_secret}
        res = requests.post(url, data=json.dumps(body))
        new_token = res.json().get('access_token')

        # 3. 발급 시간과 함께 파일에 저장
        with open(TOKEN_FILE, 'w') as f:
            json.dump({
                'access_token': new_token,
                'created_at': datetime.now().isoformat()
            }, f)
        return new_token

    def get_daily_ohlcv(self, ticker):
        path = API_CONFIG['ENDPOINTS']['DAILY_OHLCV']
        headers = {
            "authorization": f"Bearer {self.access_token}", 
            "appKey": self.app_key, 
            "appSecret": self.app_secret, 
            "tr_id": API_CONFIG['TR_IDS']['DAILY_OHLCV']
        }
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker, "FID_PERIOD_DIV_CODE": "D", "FID_ORG_ADJ_PRC": "1"}
        
        for attempt in range(3):
            try:
                res = requests.get(f"{self.url}/{path}", params=params, headers=headers)
                data = res.json().get('output2', [])
                return [{"close": int(item['stck_clpr'])} for item in reversed(data)]
            except Exception:
                time.sleep(5)
        return []

    def buy_market_order(self, ticker, qty):
        path = API_CONFIG['ENDPOINTS']['ORDER_CASH']
        headers = {
            "authorization": f"Bearer {self.access_token}", 
            "appKey": self.app_key, 
            "appSecret": self.app_secret, 
            "tr_id": API_CONFIG['TR_IDS']['ORDER_CASH']
        }
        data = {"CANO": self.cano, "ACNT_PRDT_CD": self.acnt_prdt_cd, "PDNO": ticker, "ORD_QTY": str(qty), "ORD_UNPR": "0", "ORD_DVSN": "01"}
        return requests.post(f"{self.url}/{path}", data=json.dumps(data), headers=headers).json()

    def get_balance(self):
        path = API_CONFIG['ENDPOINTS']['INQUIRE_BALANCE']
        headers = {
            "authorization": f"Bearer {self.access_token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": API_CONFIG['TR_IDS']['INQUIRE_BALANCE']
        }
        params = {
            "CANO": self.cano, "ACNT_PRDT_CD": self.acnt_prdt_cd, "AFHR_FLPR_YN": "N",
            "INQR_DVSN": "02", "UNPR_DVSN": "01", "PRCS_DVSN": "00", "OFL_YN": "N",
            "FUND_STTL_ICLD_YN" : "N", "FUND_STTL_ICLD_YN" : "N", "FNCG_AMT_AUTO_RDPT_YN" : "N",
            "CTX_AREA_FK100" : "", "CTX_AREA_NK100" :""
        }
        res = requests.get(f"{self.url}/{path}", params=params, headers=headers).json()

        # --- [디버깅 추가] 응답 전체를 출력하여 확인 ---
        print("\n" + "="*50)
        print("[DEBUG] 한국투자증권 API 전체 응답:")
        print(json.dumps(res, indent=4, ensure_ascii=False))
        print("="*50 + "\n")
        # ----
        # [방어 로직] 토큰 만료시 재발급 및 재시도
        if res.get('rt_cd') == "1":
            print("[!] 토큰 에러 발생! 토큰 갱신 후 재시도합니다.")
            if os.path.exists(TOKEN_FILE): os.remove(TOKEN_FILE)
            self.access_token = self._get_token()
            headers['authorization'] = f"Bearer {self.access_token}"
            res = requests.get(f"{self.url}/{path}", params=params, headers=headers).json()

        stocks = []
        for item in res.get('output1', []):
            stocks.append({
                "ticker": item['pdno'],
                "name": item['prdt_name'],
                "qty": int(item['hldg_qty']),
                "avg_price": int(item['pchs_avg_pric']),
                "current_price": int(item['prpr'])
            })
            
        output2 = res.get('output2', [])
        cash = int(output2[0].get('dnca_tot_amt', 0)) if output2 else 0
        return {"cash": cash, "stocks": stocks}