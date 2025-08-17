import streamlit as st
import pandas as pd
import ccxt
import time
import plotly.graph_objects as go

# --- UI Configuration ---
st.set_page_config(layout="wide", page_title="Scanner")
st.title("📈 MEXC — Bull Trend Scanner")

# Sidebar controls
col1, col2 = st.sidebar, st.sidebar
INTERVAL = col1.selectbox("Timeframe (candles)", ["1m", "3m", "5m", "15m", "30m", "1h"], index=2)
TOP_N = col1.slider("How many pairs check by volume", 10, 300, 80)
MIN_QUOTE_VOLUME = col1.number_input("Min voulume for 24h (USDT)", value=700000, step=50000)
SAMPLE_LIMIT = col1.slider("Amount of candles", 10, 50, 30)
REFRESH_BTN = col1.button("Refresh now")
MAX_PRICE = col1.slider("Max price (USDT)", value=10, step=1, min_value=0, max_value=100)

# --- Exchange Setup ---
EXCHANGE_ID = "mexc"
exchange = getattr(ccxt, EXCHANGE_ID)({'enableRateLimit': True})

TF_MAP = {"1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1h"}
TIMEFRAME = TF_MAP[INTERVAL]


# --- Fetch Top Pairs ---
def safe_fetch_tickers():
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
                if last_price <= MAX_PRICE:  # фильтр
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
def fetch_ohlcv(symbol_ccxt, timeframe, limit):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol_ccxt, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['dt'] = pd.to_datetime(df['ts'], unit='ms')
        return df
    except Exception:
        return None


# --- Compute indicators: EMA для условий и SMA для графиков ---
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


# --- UI Layout and Display ---
placeholder = st.empty()

with st.spinner("Scanning..."):
    tickers = safe_fetch_tickers()

    if not tickers:
        st.warning("No currencies found with the criteria.")
    else:
        results = []

        for i, m in enumerate(tickers):
            symbol_ccxt = m['symbol_ccxt']
            last = m['last']

            time.sleep(0.03)
            df_ohlc = fetch_ohlcv(symbol_ccxt, TIMEFRAME, SAMPLE_LIMIT)
            if df_ohlc is None:
                continue

            df_ind = compute_indicators(df_ohlc)

            # Фильтр по EMA
            if (
                # EMA5 > EMA10 > EMA20 на последних 3 свечах
                all(df_ind['EMA5'].iloc[-i] > df_ind['EMA10'].iloc[-i] > df_ind['EMA20'].iloc[-i]
                    for i in range(2, 5))
                and
                # Наклон EMA положительный (растут)
                df_ind['EMA5'].iloc[-2] > df_ind['EMA5'].iloc[-3]
                and df_ind['EMA10'].iloc[-2] > df_ind['EMA10'].iloc[-3]
                and
                # Цена выше EMA5
                df_ind['close'].iloc[-2] > df_ind['EMA5'].iloc[-2]
                and
                # Объём выше среднего за 20 свечей
                df_ind['volume'].iloc[-2] > df_ind['volume'].rolling(20).mean().iloc[-2]
            ):
                results.append({
                    'symbol': symbol_ccxt,
                    'last': last,
                    'quoteVolume24h': m['quoteVolume'],
                    'df': df_ind
                })

        # Display result table
        df_ui = pd.DataFrame([{
            'symbol': r['symbol'],
            'last': r['last'],
            'quoteVolume24h': r['quoteVolume24h']
        } for r in results]).sort_values(['last'], ascending=False).reset_index(drop=True)

        if df_ui.empty:
            st.info("No data for sending")
        else:
            st.dataframe(df_ui)

        # --- Show Charts ---
        for idx, c in enumerate(results):
            st.markdown(f"### {c['symbol']}")

            df_plot = c['df'].copy()
            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=df_plot['dt'],
                open=df_plot['open'],
                high=df_plot['high'],
                low=df_plot['low'],
                close=df_plot['close'],
                name='price'
            ))

            # На графике показываем SMA (MA5, MA10, MA20)
            fig.add_trace(go.Scatter(x=df_plot['dt'], y=df_plot['MA5'], name='MA5'))
            fig.add_trace(go.Scatter(x=df_plot['dt'], y=df_plot['MA10'], name='MA10'))
            fig.add_trace(go.Scatter(x=df_plot['dt'], y=df_plot['MA20'], name='MA20'))

            fig.update_layout(height=500, margin=dict(t=30))
            st.plotly_chart(fig, use_container_width=True)

# Manual refresh rerun
if REFRESH_BTN:
    st.rerun()
