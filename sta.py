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
    return df.iloc[-1], df.iloc[:-1]['vol'].mean(), df['close'].iloc[-1]

# 2. UI HEADER & SIDEBAR
st.set_page_config(page_title="ZEC Master Radar", layout="wide")
st.title("🛡️ ZEC Master Risk & Reversal Radar")

st.sidebar.header("Global Risk Settings")
risk_usd = st.sidebar.number_input("Acceptable Loss ($)", value=250.0)
target_rr = st.sidebar.slider("Risk-to-Reward (1:X)", 1, 10, 3)
sl_dist_pct = st.sidebar.slider("Stop Loss Distance (%)", 0.5, 5.0, 2.0)

st.sidebar.markdown("---")
st.sidebar.header("Current Position Info")
pos_direction = st.sidebar.selectbox("Current Direction", ["None", "Short", "Long"])
unit_type = st.sidebar.radio("Input Size in:", ["ZEC Units", "USDT Value"])
current_size = st.sidebar.number_input(f"Current Size ({unit_type})", value=0.0)

# 3. MAIN LOGIC
if st.button("🔄 Analyze & Calculate Strategy"):
    data, avg_vol, price = get_indicators('ZEC/USDT')
    
    # ⚡ FLAGS (Dynamic based on Direction)
    # If None/Short, look for Long signals. If Long, look for Short signals.
    looking_for_long = (pos_direction != "Long")
    
    f1 = data['STOCHRSIk_14_14_3_3'] < 20 if looking_for_long else data['STOCHRSIk_14_14_3_3'] > 80
    f2 = data['ema_9'] > data['ema_21'] if looking_for_long else data['ema_9'] < data['ema_21']
    f3 = data['rsi'] < 45 if looking_for_long else data['rsi'] > 55
    f4 = data['vol'] > (avg_vol * 1.3)
    
    st.subheader("⚡ Live Signal Flags")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    col_f1.metric("Stoch RSI", "🟢 ACTIVE" if f1 else "WAITING")
    col_f2.metric("Trend", "🟢 BULLISH" if f2 else "BEARISH")
    col_f3.metric("RSI Level", f"{data['rsi']:.1f}", "🟢 SIGNAL" if f3 else "NEUTRAL")
    col_f4.metric("Vol Spike", "🟢 HIGH" if f4 else "LOW")

    # 4. CALCULATION
    total_pos_val = risk_usd / (sl_dist_pct / 100)
    current_val_usdt = current_size if unit_type == "USDT Value" else current_size * price
    
    st.markdown("---")
    tab1, tab2 = st.tabs(["🔄 Reversal (Flip)", "➕ Continuation (Add/Re-entry)"])

    # TAB 1: THE FLIP
    with tab1:
        st.header(f"Flip Strategy for ${price:,.2f}")
        if pos_direction != "None":
            phase1_entry = total_pos_val * 0.25
            flip_order = current_val_usdt + phase1_entry
            action = "BUY" if pos_direction == "Short" else "SELL"
            st.warning(f"**Action**: {action} **${flip_order:,.2f}** to close and reverse.")
            
            flip_df = pd.DataFrame({
                "Step": ["1. Flip Order", "2. Scale (+45m)", "3. Final (+90m)"],
                "Amount ($)": [f"${flip_order:,.2f}", f"${total_pos_val*0.35:,.2f}", f"${total_pos_val*0.40:,.2f}"],
                "Target": ["Immediate", "Flush Zone", "Exhaustion Zone"]
            })
            st.table(flip_df)
        else:
            st.info("No position to flip. Use continuation tab or enter fresh.")

    # TAB 2: THE ADD (CONTINUATION)
    with tab2:
        st.header(f"Continuation Strategy for ${price:,.2f}")
        # Logic: If Short, we want to 'Add' on relief rallies (higher price).
        # If Long, we want to 'Add' on dips (lower price).
        mult = 1.008 if pos_direction == "Short" else 0.992
        
        cont_df = pd.DataFrame({
            "Phase": ["Add 1 (Next Relief/Dip)", "Add 2", "Add 3"],
            "Price Point": [f"${price*mult:,.2f}", f"${price*(mult**2):,.2f}", f"${price*(mult**3):,.2f}"],
            "Add Amount ($)": [f"${total_pos_val*0.25:,.2f}", f"${total_pos_val*0.35:,.2f}", f"${total_pos_val*0.40:,.2f}"],
            "Logic": ["Test Resistance" if pos_direction=="Short" else "Test Support", "Scale Heavy", "Full Load"]
        })
        st.table(cont_df)

    # 5. RISK SUMMARY
    st.subheader("Active Management Goals")
    avg_e = price * (0.992 if looking_for_long else 1.008)
    sl_p = avg_e * (1 - (sl_dist_pct / 100)) if looking_for_long else avg_entry * (1 + (sl_dist_pct / 100))
    
    g1, g2 = st.columns(2)
    g1.metric("Stop Loss", f"${sl_p:,.2f}")
    g2.metric("New Liquidation Gap", f"{sl_dist_pct + 1:.1f}%")
