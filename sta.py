import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import requests

# CONFIGURATION
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]
exchange = ccxt.binanceus()

def send_ping(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

def get_indicators(symbol, timeframe='15m'):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df['rsi'] = ta.rsi(df['close'], length=14)
    stoch_rsi = ta.stochrsi(df['close'], length=14, rsi_length=14, k=3, d=3)
    df = pd.concat([df, stoch_rsi], axis=1)
    df['ema_9'] = ta.ema(df['close'], length=9)
    df['ema_21'] = ta.ema(df['close'], length=21)
    return df.iloc[-1], df.iloc[:-1]['vol'].mean()

# DASHBOARD UI
st.title("🛡️ ZEC Master Signal & Risk Radar")

# SIDEBAR RISK INPUTS
st.sidebar.header("Risk Settings")
capital = st.sidebar.number_input("Trade Budget (USDT)", value=100.0)
target_pct = st.sidebar.slider("Profit Target %", 1.0, 15.0, 6.0)
leverage = st.sidebar.number_input("Leverage (X)", value=10)

if st.button("Refresh & Calculate Signal"):
    zec_data, zec_avg_vol = get_indicators('ZEC/USDT')
    zec_price = zec_data['close']

    # ⚡ SCALPER FLAGS (LOOSE)
    f1 = zec_data['STOCHRSIk_14_14_3_3'] < 20
    f2 = zec_data['ema_9'] > zec_data['ema_21']
    f3 = zec_data['rsi'] < 45
    f4 = zec_data['vol'] > (zec_avg_vol * 1.3)
    score = sum([f1, f2, f3, f4])

    # 📊 STATUS AREA
    st.metric("ZEC Price", f"${zec_price:,.2f}")
    c1, c2, c3, c4 = st.columns(4)
    c1.write("🟢 Stoch" if f1 else "Stoch")
    c2.write("🟢 EMA" if f2 else "EMA")
    c3.write("🟢 RSI" if f3 else "RSI")
    c4.write("🟢 Vol" if f4 else "Vol")

    # 🛡️ DCA PLANNER (45-Min Increments)
    st.header("Strategic Entry Plan")
    e1, e2, e3 = zec_price, zec_price * 0.99, zec_price * 0.98
    avg_e = (e1 * 0.25) + (e2 * 0.35) + (e3 * 0.40)
    
    # Risk-to-Reward 1:3 Logic
    tp_price = avg_e * (1 + (target_pct / 100))
    sl_pct = target_pct / 3
    sl_price = avg_e * (1 - (sl_pct / 100))
    
    plan = {
        "Phase": ["Phase 1 (Start)", "Phase 2 (+45m)", "Phase 3 (+90m)"],
        "Alloc": ["25%", "35%", "40%"],
        "Entry Price": [f"${e1:,.2f}", f"${e2:,.2f}", f"${e3:,.2f}"]
    }
    st.table(pd.DataFrame(plan))

    # 🎯 TARGETS
    st.subheader("Trade Goals (1:3 Ratio)")
    res1, res2, res3 = st.columns(3)
    res1.metric("Avg Entry", f"${avg_e:,.2f}")
    res2.metric("Stop Loss", f"${sl_price:,.2f}", f"-{sl_pct:.2f}%")
    res3.metric("Take Profit", f"${tp_price:,.2f}", f"+{target_pct:.2f}%")

    if score >= 3:
        send_ping(f"🚨 SIGNAL: {score}/4 Flags! Entry 1: ${e1} | Stop: ${sl_price}")
