import streamlit as st
import plotly.graph_objects as go
import Config as cfg
import Fetcher
import ccxt
import time
import pandas as pd

import streamlit as st

# --- UI Configuration ---
st.set_page_config(layout="wide", page_title="Scanner")
st.title("📈 MEXC — Bull Trend Scanner")

# создаём вкладки
tab1, tab2 = st.tabs(["📊 Top scanned", "Favorite"])

with tab1:
    st.header("Graphics for filtred currencies")
    
        # Sidebar controls
    col1, col2 = st.sidebar, st.sidebar
    INTERVAL = col1.selectbox("Timeframe (candles)", ["1m", "3m", "5m", "15m", "30m", "1h"], index=2)
    TOP_N = col1.slider("How many pairs check by volume", 10, 300, 80)
    MIN_QUOTE_VOLUME = col1.number_input("Min voulume for 24h (USDT)", value=700000, step=50000)
    SAMPLE_LIMIT = col1.slider("Amount of candles", 10, 50, 30)
    REFRESH_BTN = col1.button("Refresh now")
    MAX_PRICE = col1.slider("Max price (USDT)", value=10.0, step=0.1, min_value=0.0, max_value=50.0)
    TIMEFRAME = cfg.TF_MAP[INTERVAL]
    EXCHANGE = getattr(ccxt, cfg.MEXC_ID)({'enableRateLimit': True})
    
    # --- UI Layout and Display ---
    placeholder = st.empty()
    
    with st.spinner("Scanning..."):
        tickers = Fetcher.safe_fetch_tickers(EXCHANGE, TOP_N, MIN_QUOTE_VOLUME, MAX_PRICE)

        if not tickers:
            st.warning("No currencies found with the criteria.")
        else:
            results = []

            for i, m in enumerate(tickers):
                symbol_ccxt = m['symbol_ccxt']
                last = m['last']

                time.sleep(0.03)
                df_ohlc = Fetcher.fetch_ohlcv(symbol_ccxt, TIMEFRAME, SAMPLE_LIMIT, EXCHANGE)
                if df_ohlc is None:
                    continue

                df_ind = Fetcher.compute_indicators(df_ohlc)

                # EMA filters
                if (
                    # EMA5 > EMA10 > EMA20 on the last 3 candles
                    all(df_ind['EMA5'].iloc[-i] > df_ind['EMA10'].iloc[-i] > df_ind['EMA20'].iloc[-i]
                        for i in range(2, 5))
                    and
                    # EMA5 and EMA10 are rising
                    df_ind['EMA5'].iloc[-2] > df_ind['EMA5'].iloc[-3]
                    and df_ind['EMA10'].iloc[-2] > df_ind['EMA10'].iloc[-3]
                    and
                    #  EMA5 is above the close price of the previous candle
                    df_ind['close'].iloc[-2] > df_ind['EMA5'].iloc[-2]
                    and
                    # Volume on the previous candle is greater than the 20-period averages
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
            } for r in results]) 
            # .sort_values(['last'], ascending=False).reset_index(drop=True)


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


with tab2:
    st.header("Graphics for favourite currencies")








