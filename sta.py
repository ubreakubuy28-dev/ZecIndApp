import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import requests

# 1. CONFIGURATION
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]
exchange = ccxt.binanceus() # Using US endpoint for Streamlit compatibility

def send_ping(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
    requests.get(url)

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
risk_usd = st.sidebar.number_input("Acceptable Loss ($)", value=10.0, help="Max $ you will lose if Stop Loss is hit.")
target_rr = st.sidebar.slider("Risk-to-Reward (1:X)", 1, 10, 3)
sl_dist_pct = st.sidebar.slider("Stop Loss Distance (%)", 0.5, 5.0, 2.0)

# 3. CURRENT POSITION (FOR REVERSAL)
st.sidebar.markdown("---")
st.sidebar.header("Current Short Info")
in_short = st.sidebar.checkbox("In a Short Position?", value=True)
short_qty_zec = st.sidebar.number_input("Short Qty (ZEC Units)", value=28.8, help="Found in 'Total' column on BloFin.")

if st.button("🔄 Analyze & Calculate Reversal"):
    data, avg_vol = get_indicators('ZEC/USDT')
    price = data['close']
    
    # ⚡ FLAGS
    f1, f2, f3, f4 = data['STOCHRSIk_14_14_3_3'] < 20, data['ema_9'] > data['ema_21'], data['rsi'] < 45, data['vol'] > (avg_vol * 1.3)
    score = sum([f1, f2, f3, f4])

    # SECTION 1: FRESH ENTRY SIZING
    st.header("1. Fresh Long Strategy")
    total_pos_value = risk_usd / (sl_dist_pct / 100) # [Position Size Formula](https://flipster.io/en/blog/how-to-use-a-crypto-position-size-calculator-like-a-pro)
    
    col1, col2 = st.columns(2)
    col1.metric("Max Position Size", f"${total_pos_value:,.2f}")
    col2.metric("Score", f"{score}/4 Flags")

    # SECTION 2: THE REVERSAL (FLIP) CALCULATOR
    st.header("2. Reversal & Position Flip")
    if in_short:
        close_short_usd = short_qty_zec * price
        phase1_long_usd = total_pos_value * 0.25
        flip_order_total = close_short_usd + phase1_long_usd
        
        st.warning(f"**Action**: Place a BUY Market order for **${flip_order_total:,.2f}**")
        st.write(f"👉 This closes your **${close_short_usd:,.2f}** short and adds your first **${phase1_long_usd:,.2f}** long entry.")
        
        # Scale-In Table
        avg_entry = price * 0.992 # Estimated after 3 scales
        sl_price = avg_entry * (1 - (sl_dist_pct / 100))
        tp_price = avg_entry * (1 + (sl_dist_pct * target_rr / 100))

        scale_df = pd.DataFrame({
            "Timing": ["Immediate (The Flip)", "+45 Mins (Phase 2)", "+90 Mins (Phase 3)"],
            "Buy Amount (USDT)": [f"${flip_order_total:,.2f}", f"${total_pos_value*0.35:,.2f}", f"${total_pos_value*0.40:,.2f}"],
            "Order Type": ["Market Reverse", "Market/Limit", "Market/Limit"]
        })
        st.table(scale_df)

        # FINAL TARGETS
        st.subheader(f"Long Targets (1:{target_rr} Ratio)")
        res1, res2, res3 = st.columns(3)
        res1.metric("New Avg Entry", f"${avg_entry:,.2f}")
        res2.metric("New Stop Loss", f"${sl_price:,.2f}")
        res3.metric("New Take Profit", f"${tp_price:,.2f}")
    else:
        st.info("No active short detected. Use Section 1 for new long entries.")

    if score >= 3:
        send_ping(f"🚨 REVERSAL SIGNAL: {score}/4 flags! Flip Order: ${flip_order_total:,.2f}")
