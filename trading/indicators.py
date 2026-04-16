import pandas as pd

def calculate_indicators(df):
    # RSI 계산
    delta = df['close'].diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    avg_loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 20일 이동평균선
    df['ma20'] = df['close'].rolling(window=20).mean()
    
    # 볼린저 밴드
    df['std'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['ma20'] + (df['std'] * 2)
    df['bb_lower'] = df['ma20'] - (df['std'] * 2)
    
    return df