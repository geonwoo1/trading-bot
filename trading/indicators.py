import pandas as pd
import numpy as np

def calculate_indicators(df):
    """
    데이터프레임에 기술적 지표(MA20, MA60, RSI, Bollinger Bands)를 추가하는 함수
    """
    # 데이터가 없거나 너무 적으면 그대로 반환
    if df is None or df.empty:
        return df

    # 원본 데이터 보호를 위해 복사본 사용
    df = df.copy()

    # 1. 이동평균선 (Moving Average) 계산
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma60'] = df['close'].rolling(window=60).mean() # <--- 에러를 해결하는 핵심 라인

    # 2. 볼린저 밴드 (Bollinger Bands) 계산
    # 표준편차(std) 계산 후 상단/하단 밴드 생성
    df['std'] = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['ma20'] + (df['std'] * 2)
    df['bb_lower'] = df['ma20'] - (df['std'] * 2)

    # 3. RSI (Relative Strength Index) 계산
    # 종가 차이 계산
    delta = df['close'].diff()
    
    # 상승분(gain)과 하락분(loss) 분리
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))

    # 단순 이동평균(SMA) 기반 RSI (기간: 14일)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()

    # 0으로 나누기 방지 및 RSI 공식 적용
    # RSI = 100 - (100 / (1 + RS))
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    return df