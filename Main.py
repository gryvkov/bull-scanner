import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import Config as cfg
import Fetcher
import ccxt
import time
import pandas as pd
import streamlit as st
from datetime import datetime  


# --- UI Configuration ---
st.set_page_config(layout="wide", page_title="Scanner")
st.title("📈 MEXC — Bull Trend Scanner")
Fetcher.init_db(cfg.DB_FILE)

# --- Tabs ---
tab1, tab2 = st.tabs(["Top scanned", "Volume peak"])

with tab1:
    st.header("Graphics for filtred currencies")
    
    # --- Sidebar controls ---
    col1, col2 = st.sidebar, st.sidebar
    interval = col1.selectbox("Timeframe (candles)", ["1m", "3m", "5m", "15m", "30m", "1h"], index=2)
    count_pairs = col1.slider("How many pairs check by volume", 10, 500, 300)
    min_quote_volume = col1.number_input("Min voulume for 24h (USDT)", value=600000, step=50000)
    sample_limit = col1.slider("Amount of candles", 10, 50, 30)
    refresh_btn = col1.button("Refresh now")
    max_price = col1.slider("Max price (USDT)", value=2.0, step=1.0, min_value=0.0, max_value=500.0)
    timeframe = cfg.TF_MAP[interval]
    exchange = getattr(ccxt, cfg.MEXC_ID)({'enableRateLimit': True})
    tickers = Fetcher.safe_fetch_tickers(exchange, count_pairs, min_quote_volume, max_price)


    # --- UI ---
    placeholder = st.empty()
    
    with st.spinner("Scanning..."):
        

        if not tickers:
            st.warning("No currencies found with the criteria.")
        else:
            results = []

            for i, m in enumerate(tickers):
                symbol_ccxt = m['symbol_ccxt']
                last = m['last']

                time.sleep(0.03)
                df_ohlc = Fetcher.fetch_ohlcv(symbol_ccxt, timeframe, sample_limit, exchange)
                if df_ohlc is None:
                    continue

                df_ind = Fetcher.compute_indicators(df_ohlc)

                # --- EMA conditions + volume + green candle ---
                if (
                    (df_ind['close'].iloc[-1] > df_ind['open'].iloc[-1]) 
                    and (df_ind['close'].iloc[-2] > df_ind['open'].iloc[-2])
                ):
                    results.append({
                        'symbol': symbol_ccxt,
                        'last': last,
                        'quoteVolume24h': m['quoteVolume'],
                        'df': df_ind
                    })

            # Display result table
            df_ui = pd.DataFrame([{
                'symbol': row['symbol'],
                'last': row['last'],
                'quoteVolume24h': row['quoteVolume24h']
            } for row in results]) 
            


            if df_ui.empty:
                st.info("No data for sending")
            else:
                st.dataframe(df_ui)

        
        # --- Show Charts ---
        for idx, c in enumerate(results):

            st.markdown(f"### {c['symbol']} ")
            df_plot = c['df'].copy()

            # Создаем фигуру с 2 рядами: цена (ряд 1), объем (ряд 2)
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                row_heights=[0.7, 0.3],  # высота рядов
                vertical_spacing=0.05
            )

            # --- Candles ---
            fig.add_trace(go.Candlestick(
                x=df_plot['dt'],
                open=df_plot['open'],
                high=df_plot['high'],
                low=df_plot['low'],
                close=df_plot['close'],
                name='price'
            ), row=1, col=1)

            # --- MA track ---
            fig.add_trace(go.Scatter(x=df_plot['dt'], y=df_plot['MA5'], name='MA5'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot['dt'], y=df_plot['MA10'], name='MA10'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot['dt'], y=df_plot['MA20'], name='MA20'), row=1, col=1)

            # --- Volume ---
            fig.add_trace(go.Bar(
                x=df_plot['dt'],
                y=df_plot['volume'],
                name="Volume",
                marker_color="rgba(0, 150, 200, 0.6)"
            ), row=2, col=1)

            # --- Axis settings ---
            fig.update_layout(
                height=600,
                margin=dict(t=30),
                showlegend=True,
                xaxis_rangeslider_visible=False
            )

            st.plotly_chart(fig, use_container_width=True)
        
        # Manual refresh rerun
        if refresh_btn:
            st.rerun()

# with tab2:
#     placeholder_header = st.empty()
#     placeholder_tab2 = st.empty()

#     # create empty DataFrame in session state if not exists
#     if 'favorites_history' not in st.session_state:
#         st.session_state.favorites_history = pd.DataFrame(columns=['symbol', 'last', 'datetime'])

#     while True:

#         for m in tickers:
#             symbol_ccxt = m['symbol_ccxt']
#             last = m['last']

#             time.sleep(10)
#             df_ohlc = Fetcher.fetch_ohlcv(symbol_ccxt, timeframe, sample_limit, exchange)
#             if df_ohlc is None:
#                 continue

#             df_ind = Fetcher.compute_indicators(df_ohlc)

#             # --- Volume increase condition + green candle ---
#             if (
#                 df_ind['volume'].iloc[-1] >= 4 * df_ind['volume'].iloc[-2]
#                 and df_ind['close'].iloc[-1] > df_ind['open'].iloc[-1]
#                 and df_ind['volume'].iloc[-1] > min_quote_volume
#             ):
#                 # --- check if symbol already in favorites
#                 idx = st.session_state.favorites_history.index[
#                     st.session_state.favorites_history['symbol'] == symbol_ccxt
#                 ].tolist()
                
#                 if idx:
#                     # --- if yes, update last price and datetime ---
#                     st.session_state.favorites_history.at[idx[0], 'last'] = last
#                     st.session_state.favorites_history.at[idx[0], 'datetime'] = datetime.now()
#                 else:
#                     # --- if not, add new entry ---
#                     st.session_state.favorites_history = pd.concat([
#                         st.session_state.favorites_history,
#                         pd.DataFrame([{
#                             'symbol': symbol_ccxt,
#                             'last': last,
#                             'datetime': datetime.now()
#                         }])
#                     ], ignore_index=True)

#         # --- Track rows count in header    ---
#         placeholder_header.subheader(
#             f"Graphics for favourite currencies ({len(st.session_state.favorites_history)})"
#         )

#         # --- Show actual table ---
#         with placeholder_tab2.container():
#             if not st.session_state.favorites_history.empty:
#                 st.dataframe(st.session_state.favorites_history)
#             else:
#                 st.info("not found matches for favorites")
        
#         tickers = Fetcher.safe_fetch_tickers(exchange, count_pairs, min_quote_volume, max_price)

#         time.sleep(5)




