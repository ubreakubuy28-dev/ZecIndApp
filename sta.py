import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta

# 1. CONFIGURATION
exchange = ccxt.binanceus()

def get_indicators(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df['rsi'] = ta.rsi(df['close'], length=14)
    stch = ta.stochrsi(df['close'], length=14, rsi_length=14, k=3, d=3)
    df = pd.concat([df, stch], axis=1)
    df['ema_9'] = ta.ema(df['close'], length=9)
    df['ema_21'] = ta.ema(df['close'], length=21)
    return df.iloc[-1], df.iloc[:-1]['vol'].mean()

# 2. UI HEADER & RISK SETTINGS
st.title("🛡️ ZEC Master Risk & Reversal Radar")

st.sidebar.header("Global Risk Settings")
risk_usd = st.sidebar.number_input("Acceptable Loss ($)", value=10.0)
target_rr = st.sidebar.slider("Risk-to-Reward (1:X)", 1, 10, 3)
sl_dist_pct = st.sidebar.slider("Stop Loss Distance (%)", 0.5, 5.0, 2.0)

st.sidebar.markdown("---")
st.sidebar.header("Current Short Info")
in_short = st.sidebar.checkbox("Currently in a Short?", value=False)
short_qty_zec = st.sidebar.number_input("Short Qty (ZEC Units)", value=0.0)

if st.button("🔄 Analyze & Calculate Plan"):
    data, avg_vol = get_indicators('ZEC/USDT')
    price = data['close']
    
    # ⚡ FLAGS
    f1, f2, f3, f4 = data['STOCHRSIk_14_14_3_3'] < 20, data['ema_9'] > data['ema_21'], data['rsi'] < 45, data['vol'] > (avg_vol * 1.3)
    score = sum([f1, f2, f3, f4])

    # SIZING MATH
    total_long_val = risk_usd / (sl_dist_pct / 100)
    e1, e2, e3 = price, price * 0.992, price * 0.985
    avg_entry = (e1 * 0.25) + (e2 * 0.35) + (e3 * 0.40)
    
    # 📊 DASHBOARD HEADER
    st.metric("ZEC Price", f"${price:,.2f}", f"{score}/4 Flags Active")

    # 3-PHASE TABLE (ADAPTIVE)
    st.header("Strategic Scale-In Plan")
    
    if in_short:
        close_short_usd = short_qty_zec * price
        phase1_long_usd = total_long_val * 0.25
        flip_order = close_short_usd + phase1_long_usd
        
        st.warning(f"🔄 **FLIP DETECTED**: To reverse, your first buy order is **${flip_order:,.2f}**")
        
        plan_data = {
            "Phase": ["Phase 1 (The Flip)", "Phase 2 (+45m)", "Phase 3 (+90m)"],
            "Order Size (USDT)": [f"${flip_order:,.2f}", f"${total_long_val*0.35:,.2f}", f"${total_long_val*0.40:,.2f}"],
            "Logic": ["Closes Short + Adds 25% Long", "Adds 35% Long", "Adds 40% Long"]
        }
    else:
        plan_data = {
            "Phase": ["Phase 1 (Initial)", "Phase 2 (+45m)", "Phase 3 (+90m)"],
            "Order Size (USDT)": [f"${total_long_val*0.25:,.2f}", f"${total_long_val*0.35:,.2f}", f"${total_long_val*0.40:,.2f}"],
            "Logic": ["25% Deployment", "35% Deployment", "40% Deployment"]
        }
    
    st.table(pd.DataFrame(plan_data))

    # 🎯 TARGETS
    st.subheader(f"Goals (1:{target_rr} Ratio)")
    sl_price = avg_entry * (1 - (sl_dist_pct / 100))
    tp_price = avg_entry * (1 + (sl_dist_pct * target_rr / 100))
    
    res1, res2, res3 = st.columns(3)
    res1.metric("Avg Long Entry", f"${avg_entry:,.2f}")
    res2.metric("Long Stop Loss", f"${sl_price:,.2f}")
    res3.metric("Long Take Profit", f"${tp_price:,.2f}")
