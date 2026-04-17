# constants.py
API_CONFIG = {
    "ENDPOINTS": {
        "TOKEN": "/oauth2/tokenP",
        "DAILY_OHLCV": "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
        "ORDER_CASH": "/uapi/domestic-stock/v1/trading/order-cash",
        "INQUIRE_BALANCE": "/uapi/domestic-stock/v1/trading/inquire-balance",
    },
    "TR_IDS": {
        "DAILY_OHLCV": "FHKST03010100",
        "ORDER_CASH": "VTTC0802U",
        "INQUIRE_BALANCE": "VTTC8434R",
    }
}