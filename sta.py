import streamlit as st
import ccxt
import requests
import pandas_ta as ta
import pandas as pd

# CONFIGURATION
# Updated Configuration using Streamlit Secrets
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]
# Change the exchange to binanceus
exchange = ccxt.binanceus()

def send_ping(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

def get_rsi(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    return df.ta.rsi(length=14).iloc[-1]

def check_volume_spike(symbol, timeframe='15m', lookback=20, multiplier=2.0):
    """Detects if current volume is significantly higher than the average."""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=lookback + 1)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    
    current_vol = df['vol'].iloc[-1]
    avg_vol = df['vol'].iloc[:-1].mean() # Average of previous candles
    
    is_spike = current_vol > (avg_vol * multiplier)
    return is_spike, current_vol, avg_vol

# SITE FRONTEND
st.title("ZEC Multi-Flag Radar")

if st.button("Check Flags Now"):
    # 1. Fetch Price and RSIs
    zec_price = exchange.fetch_ticker('ZEC/USDT')['last']
    btc_rsi = get_rsi('BTC/USDT')
    eth_rsi = get_rsi('ETH/USDT')
    
    # 2. Check Volume Spike (2x multiplier)
    zec_spike, cur_v, avg_v = check_volume_spike('ZEC/USDT')
    
    flags = 0
    flag_details = []

    if btc_rsi < 30: 
        flags += 1
        flag_details.append("BTC RSI Oversold")
    if eth_rsi < 30: 
        flags += 1
        flag_details.append("ETH RSI Oversold")
    if zec_spike:
        flags += 1
        flag_details.append(f"ZEC Volume Spike ({cur_v:.0f} vs avg {avg_v:.0f})")

    # Display results on screen
    st.write(f"**Current ZEC Price:** ${zec_price}")
    st.write(f"**BTC RSI:** {btc_rsi:.2f} | **ETH RSI:** {eth_rsi:.2f}")
    st.write(f"**Flags Triggered:** {flags}")
    
    if flag_details:
        st.info("Active Signals: " + ", ".join(flag_details))

    # 3. Send Telegram Ping if 2 or more flags hit
    if flags >= 2:
        msg = f"🚨 SIGNAL: {flags} flags active!\nZEC Price: ${zec_price}\nSignals: {', '.join(flag_details)}"
        send_ping(msg)
        st.success("Telegram Alert Sent!")
    else:
        st.warning("Not enough flags for an alert.")

