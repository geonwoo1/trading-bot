class TechnicalAnalyzer:
    @staticmethod
    def add_indicators(df):
        """이동평균선 및 RSI 추가"""
        df['close'] = df['close'].astype(float)
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def get_signal(df):
        """매수/매도 신호 판단"""
        if len(df) < 20: return "NOT_ENOUGH_DATA"
        last = df.iloc[-1]
        if last['ma5'] > last['ma20'] and last['rsi'] < 40:
            return "BUY"
        return "HOLD"