import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import requests

# CONFIGURATION (Use Streamlit Secrets for real deployment)
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]
exchange = ccxt.binanceus()

def send_ping(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

def get_indicators(symbol, timeframe='15m'):
    """Fetches OHLCV and calculates multiple technical indicators."""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    
    # RSI (Standard)
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    # Stochastic RSI (Loose/Sensitive)
    stoch_rsi = ta.stochrsi(df['close'], length=14, rsi_length=14, k=3, d=3)
    df = pd.concat([df, stoch_rsi], axis=1)
    
    # EMA Crossover (Fast trend)
    df['ema_9'] = ta.ema(df['close'], length=9)
    df['ema_21'] = ta.ema(df['close'], length=21)
    
    return df.iloc[-1], df.iloc[:-1]['vol'].mean()

# DASHBOARD UI
st.title("ZEC Master Signal Dashboard")
tab1, tab2 = st.tabs(["🚀 HTF Reversal (Safe)", "⚡ Intraday Scalper (Loose)"])

if st.button("Refresh All Flags"):
    # Data Fetching
    zec_data, zec_avg_vol = get_indicators('ZEC/USDT')
    btc_data, _ = get_indicators('BTC/USDT')
    eth_data, _ = get_indicators('ETH/USDT')

    # --- AREA 1: HTF REVERSAL (STRICT) ---
    with tab1:
        st.subheader("High-Conviction Signals")
        htf_flags = 0
        if btc_data['rsi'] < 35: htf_flags += 1
        if eth_data['rsi'] < 35: htf_flags += 1
        if zec_data['vol'] > (zec_avg_vol * 2.5): htf_flags += 1
        
        st.metric("HTF Confluence Score", f"{htf_flags} / 3")
        if htf_flags >= 2: st.success("🔥 MAJOR REVERSAL SIGNAL DETECTED")

    # --- AREA 2: INTRADAY SCALPER (LOOSE) ---
    with tab2:
        st.subheader("High-Frequency Scalp Flags")
        # Define Loose Conditions
        f1 = zec_data['STOCHRSIk_14_14_3_3'] < 20   # Stoch RSI Oversold
        f2 = zec_data['ema_9'] > zec_data['ema_21'] # Bullish EMA Cross
        f3 = zec_data['rsi'] < 45                   # Early RSI recovery
        f4 = zec_data['vol'] > (zec_avg_vol * 1.3)  # Moderate Vol Spike
        
        # Quantity over quality for the loose tab
        scalp_flags = sum([f1, f2, f3, f4])
        
        # Color-coded tiles using Columns
        c1, c2, c3, c4 = st.columns(4)
        c1.write("Stoch RSI" if not f1 else "🟢 Stoch RSI")
        c2.write("EMA Trend" if not f2 else "🟢 EMA Trend")
        c3.write("RSI Early" if not f3 else "🟢 RSI Early")
        c4.write("Vol Bump" if not f4 else "🟢 Vol Bump")
        
        st.metric("Scalp Strength", f"{scalp_flags} / 4")
        
        if scalp_flags >= 3:
            st.warning("⚡ SCALP OPPORTUNITY: High Confluence")
            send_ping(f"⚡ Scalp Signal: {scalp_flags}/4 Flags active for ZEC at {zec_data['close']}")
