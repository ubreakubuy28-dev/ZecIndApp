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

# SITE FRONTEND
st.title("ZEC Multi-Flag Radar")
if st.button("Check Flags Now"):
    zec_price = exchange.fetch_ticker('ZEC/USDT')['last']
    btc_rsi = get_rsi('BTC/USDT')
    eth_rsi = get_rsi('ETH/USDT')
    
    flags = 0
    if btc_rsi < 30: flags += 1
    if eth_rsi < 30: flags += 1
    # Add CoinGlass liquidation check logic here later
    
    st.write(f"ZEC Price: {zec_price} | BTC RSI: {btc_rsi:.2f} | Flags: {flags}")
    
    if flags >= 2:

        send_ping(f"🚨 SIGNAL: {flags} flags active! ZEC at {zec_price}")

