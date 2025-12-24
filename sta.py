import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import requests

# 1. CONFIGURATION
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]
# Using binanceus to avoid US IP blocks common on Streamlit Cloud
exchange = ccxt.binanceus()

def send_ping(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

def get_indicators(symbol, timeframe='15m'):
    """Fetches data and calculates loose intraday indicators."""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    
    # RSI & Stochastic RSI
    df['rsi'] = ta.rsi(df['close'], length=14)
    stoch_rsi = ta.stochrsi(df['close'], length=14, rsi_length=14, k=3, d=3)
    df = pd.concat([df, stoch_rsi], axis=1)
    
    # EMA Trend
    df['ema_9'] = ta.ema(df['close'], length=9)
    df['ema_21'] = ta.ema(df['close'], length=21)
    
    return df.iloc[-1], df.iloc[:-1]['vol'].mean()

# 2. DASHBOARD UI
st.title("🛡️ ZEC Master Risk & Signal Radar")

# SIDEBAR RISK INPUTS
st.sidebar.header("Risk Management")
risk_amount = st.sidebar.number_input("Acceptable Loss ($)", value=10.0, help="The max dollars you will lose if Stop Loss is hit.")
target_rr = st.sidebar.slider("Risk-to-Reward Ratio (1:X)", 1, 10, 3)
sl_distance_pct = st.sidebar.slider("Stop Loss Distance (%)", 0.5, 5.0, 2.0)

if st.button("Refresh & Calculate Sizing"):
    # Data Fetching
    zec_data, zec_avg_vol = get_indicators('ZEC/USDT')
    zec_price = zec_data['close']

    # ⚡ SCALPER FLAGS (LOOSE)
    f1 = zec_data['STOCHRSIk_14_14_3_3'] < 20   # Stoch RSI Oversold
    f2 = zec_data['ema_9'] > zec_data['ema_21'] # Bullish EMA Cross
    f3 = zec_data['rsi'] < 45                   # Early RSI recovery
    f4 = zec_data['vol'] > (zec_avg_vol * 1.3)  # Moderate Vol Spike
    score = sum([f1, f2, f3, f4])

    # 📊 STATUS AREA
    st.metric("ZEC Price", f"${zec_price:,.2f}")
    c1, c2, c3, c4 = st.columns(4)
    c1.write("🟢 Stoch" if f1 else "Stoch")
    c2.write("🟢 EMA" if f2 else "EMA")
    c3.write("🟢 RSI" if f3 else "RSI")
    c4.write("🟢 Vol" if f4 else "Vol")

    # 🛡️ RISK CALCULATIONS
    # Position Size = Risk Amount / Stop Loss %
    # This ensures that a 2% drop equals exactly your $10 acceptable loss.
    total_pos_value = risk_amount / (sl_distance_pct / 100)
    
    # 45-Min Scaling Logic (3 Spots)
    e1, e2, e3 = zec_price, zec_price * 0.992, zec_price * 0.985
    avg_entry = (e1 * 0.25) + (e2 * 0.35) + (e3 * 0.40)
    
    # Target and Stop Prices
    tp_pct = sl_distance_pct * target_rr
    sl_price = avg_entry * (1 - (sl_distance_pct / 100))
    tp_price = avg_entry * (1 + (tp_pct / 100))
    
    # 📈 SCALE-IN PLAN TABLE
    st.header(f"💰 Position Plan (Total: ${total_pos_value:,.2f})")
    plan_df = pd.DataFrame({
        "Phase": ["Phase 1 (Start)", "Phase 2 (+45m)", "Phase 3 (+90m)"],
        "Sizing (USDT)": [f"${total_pos_value*0.25:,.2f}", f"${total_pos_value*0.35:,.2f}", f"${total_pos_value*0.40:,.2f}"],
        "Price Target": [f"${e1:,.2f}", f"${e2:,.2f}", f"${e3:,.2f}"]
    })
    st.table(plan_df)

    # 🎯 TRADE GOALS
    st.subheader(f"Goals (1:{target_rr} Ratio)")
    res1, res2, res3 = st.columns(3)
    res1.metric("Avg Entry", f"${avg_entry:,.2f}")
    res2.metric("Stop Loss", f"${sl_price:,.2f}", f"-{sl_distance_pct:.2f}%")
    res3.metric("Take Profit", f"${tp_price:,.2f}", f"+{tp_pct:.2f}%")
    
    st.info(f"🛡️ **Capital Safety**: If Stop Loss is hit, you lose exactly **${risk_amount}**.")

    # 🚀 TELEGRAM PING
    if score >= 3:
        msg = f"🚨 ZEC SIGNAL: {score}/4 Flags!\nEntry 1: ${e1:,.2f}\nStop Loss: ${sl_price:,.2f}\nTarget Size: ${total_pos_value:,.2f}"
        send_ping(msg)
        st.success("Signal alert sent to Telegram!")
