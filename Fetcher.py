import streamlit as st
import pandas as pd
import sqlite3
import datetime
import Config as cfg


def __init__(self, api_key: str):
    self.api_key = api_key
    self.base_url = "https://open-api.coinglass.com/api/pro/v1"
    
    

# --- Fetch Pairs ---
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


# --- Fetch data ---
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

# --- Function for saving volume to our database ---
def save_price(symbol, price, volume):
    now = datetime.now().isoformat(timespec="seconds")
    conn = sqlite3.connect(cfg.DB_FILE)
    with conn:
        conn.execute("""
            INSERT INTO volumes_history (symbol, price, volume, date)
            VALUES (?, ?, ?)
        """, (symbol, price, volume, now))
    conn.close()

# --- Get price + volume for the last 'hours' hours ---
def get_volumes(symbol, hours=10):
    from datetime import datetime, timedelta
    since = (datetime.now() - timedelta(hours=hours)).isoformat(timespec="seconds")

    conn = sqlite3.connect(cfg.DB_FILE)
    cur = conn.execute("""
        SELECT price, volume, dt
        FROM volumes_history
        WHERE symbol=? AND dt >= ?
        ORDER BY dt ASC
    """, (symbol, since))
    rows = cur.fetchall()
    conn.close()
    return rows  # список [(price, volume, dt), ...]