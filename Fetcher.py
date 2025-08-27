import requests
import streamlit as st
import pandas as pd



def __init__(self, api_key: str):
    self.api_key = api_key
    self.base_url = "https://open-api.coinglass.com/api/pro/v1"
    
    

# --- Fetch Top Pairs ---
def safe_fetch_tickers(exchange, TOP_N, MIN_QUOTE_VOLUME, MAX_PRICE):
    
    try:
        tickers = exchange.fetch_tickers()
    except Exception as e:
        st.error(f"Error with the fetch_tickers(): {e}")
        return []

    currencies = []
    for sym_ccxt, info in tickers.items():
        try:
            sym = sym_ccxt.replace('/', '')
            if sym.endswith("USDT"):
                qv = info.get('quoteVolume') or info.get('quoteVolume24h') or 0
                if not qv and info.get('baseVolume') and info.get('last'):
                    qv = float(info['baseVolume']) * float(info['last'])
                last_price = info.get('last') or 0
                if last_price <= MAX_PRICE:  # filter by max price
                    currencies.append({
                        'symbol_ccxt': sym_ccxt,
                        'symbol': sym,
                        'last': info.get('last'),
                        'quoteVolume': float(qv or 0)
                    })
        except Exception:
            continue

    df = pd.DataFrame(currencies)
    if df.empty:
        return []

    df = df.sort_values('quoteVolume', ascending=False).reset_index(drop=True)
    df = df[df['quoteVolume'] >= MIN_QUOTE_VOLUME]
    return df.head(TOP_N).to_dict('records')


# --- Fetch OHLCV data ---
def fetch_ohlcv(symbol_ccxt, timeframe, limit, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol_ccxt, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['dt'] = pd.to_datetime(df['ts'], unit='ms')
        return df
    except Exception:
        return None


# --- Compute indicators: EMA for conditions and SMA for graphics ---
def compute_indicators(df):
    df = df.copy()

    # EMA для условий
    df['EMA5'] = df['close'].ewm(span=5, adjust=False).mean()
    df['EMA10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()

    # SMA для графиков
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()

    return df


# --- Get short/long ratio ---

def get_binance_long_short_ratio(symbol, period="5m"):
    url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
    params = {"symbol": symbol, "period": period, "limit": 1}
    response = requests.get(url, params=params)
    data = response.json()
    return data[0]['longShortRatio'] if data else None
