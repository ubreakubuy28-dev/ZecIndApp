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
pos_direction = st.sidebar.selectbox("Am I already in a trade?", ["None", "Short", "Long"])
unit_type = st.sidebar.radio("Input Size in:", ["ZEC Units", "USDT Value"])
current_size = st.sidebar.number_input(f"Current Size ({unit_type})", value=0.0)

# 3. MAIN LOGIC
if st.button("🔄 Analyze & Calculate Reversal"):
    data, avg_vol, price = get_indicators('ZEC/USDT')
    
    # --- SECTION: THE 4 SIGNAL FLAGS ---
    st.subheader("⚡ Live Signal Flags")
    # Logic: If looking for Long, flags are oversold. If looking for Short, flags are overbought.
    is_reversing_to_long = (pos_direction != "Long")
    
    f1 = data['STOCHRSIk_14_14_3_3'] < 20 if is_reversing_to_long else data['STOCHRSIk_14_14_3_3'] > 80
    f2 = data['ema_9'] > data['ema_21'] if is_reversing_to_long else data['ema_9'] < data['ema_21']
    f3 = data['rsi'] < 45 if is_reversing_to_long else data['rsi'] > 55
    f4 = data['vol'] > (avg_vol * 1.3)
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    col_f1.metric("Stoch RSI", "🟢 ACTIVE" if f1 else "WAITING")
    col_f2.metric("EMA Trend", "🟢 BULLISH" if f2 else "BEARISH")
    col_f3.metric("RSI Level", f"{data['rsi']:.1f}", "🟢 BUY ZONE" if f3 else "NEUTRAL")
    col_f4.metric("Vol Spike", "🟢 HIGH" if f4 else "LOW")

    # --- SECTION: POSITION MATH ---
    st.markdown("---")
    st.header(f"Strategy for ZEC @ ${price:,.2f}")
    
    # Calculate New Position Size based on Risk
    total_new_pos_usdt = risk_usd / (sl_dist_pct / 100)
    current_val_usdt = current_size if unit_type == "USDT Value" else current_size * price

    if pos_direction != "None":
        # REVERSAL LOGIC
        phase1_new_entry = total_new_pos_usdt * 0.25
        flip_order_total = current_val_usdt + phase1_new_entry
        action_text = "BUY (to Close & Reverse)" if pos_direction == "Short" else "SELL (to Close & Reverse)"
        
        st.warning(f"🔄 **REVERSAL REQUIRED**: {action_text} **${flip_order_total:,.2f}**")
        
        plan_data = {
            "Phase": ["Phase 1 (The Flip)", "Phase 2 (+45m)", "Phase 3 (+90m)"],
            "Order Size (USDT)": [f"${flip_order_total:,.2f}", f"${total_new_pos_usdt*0.35:,.2f}", f"${total_new_pos_usdt*0.40:,.2f}"],
            "Liquidity Target": ["Current Pivot", "Flush Zone ($405)", "Exhaustion Zone ($380)"]
        }
    else:
        # FRESH ENTRY LOGIC
        plan_data = {
            "Phase": ["Phase 1 (Initial)", "Phase 2 (+45m)", "Phase 3 (+90m)"],
            "Order Size (USDT)": [f"${total_new_pos_usdt*0.25:,.2f}", f"${total_new_pos_usdt*0.35:,.2f}", f"${total_new_pos_usdt*0.40:,.2f}"],
            "Liquidity Target": ["Current Pivot", "Flush Zone ($405)", "Exhaustion Zone ($380)"]
        }
    
    st.table(pd.DataFrame(plan_data))

    # --- SECTION: GOALS ---
    st.subheader(f"Trade Goals (1:{target_rr} Ratio)")
    avg_entry = price * (0.992 if is_reversing_to_long else 1.008)
    sl_price = avg_entry * (1 - (sl_dist_pct / 100)) if is_reversing_to_long else avg_entry * (1 + (sl_dist_pct / 100))
    tp_price = avg_entry * (1 + (sl_dist_pct * target_rr / 100)) if is_reversing_to_long else avg_entry * (1 - (sl_dist_pct * target_rr / 100))
    
    g1, g2, g3 = st.columns(3)
    g1.metric("Estimated Avg Entry", f"${avg_entry:,.2f}")
    g2.metric("Stop Loss", f"${sl_price:,.2f}")
    g3.metric("Take Profit", f"${tp_price:,.2f}")
