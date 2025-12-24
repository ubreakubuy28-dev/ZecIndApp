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

# 2. UI HEADER & GLOBAL SETTINGS
st.title("🛡️ ZEC Master Risk & Reversal Radar")

st.sidebar.header("Global Risk Settings")
risk_usd = st.sidebar.number_input("Acceptable Loss ($)", value=10.0)
target_rr = st.sidebar.slider("Risk-to-Reward (1:X)", 1, 10, 3)
sl_dist_pct = st.sidebar.slider("Stop Loss Distance (%)", 0.5, 5.0, 2.0)

# SIDEBAR: CURRENT POSITION INFO
st.sidebar.markdown("---")
st.sidebar.header("Current Position")
pos_type = st.sidebar.radio("Direction:", ["None", "Short", "Long"])
unit_type = st.sidebar.radio("Input Size in:", ["ZEC Units", "USDT Value"])
current_size_val = st.sidebar.number_input(f"Current Size ({unit_type})", value=0.0)

if st.button("🔄 Analyze & Calculate Reversal"):
    data, avg_vol = get_indicators('ZEC/USDT')
    price = data['close']
    
    # Unit Conversion
    current_size_usdt = current_size_val if unit_type == "USDT Value" else current_size_val * price

    # ⚡ THE 4 PRIMARY FLAGS (RESTORED)
    f1 = data['STOCHRSIk_14_14_3_3'] < 20 if pos_type != "Long" else data['STOCHRSIk_14_14_3_3'] > 80
    f2 = data['ema_9'] > data['ema_21'] if pos_type != "Long" else data['ema_9'] < data['ema_21']
    f3 = data['rsi'] < 45 if pos_type != "Long" else data['rsi'] > 55
    f4 = data['vol'] > (avg_vol * 1.3)
    score = sum([f1, f2, f3, f4])

    # SIZING MATH
    total_pos_val = risk_usd / (sl_dist_pct / 100)
    
    # 📊 LIQUIDATION ZONES (COINGLASS DATA)
    st.info("📊 **Key Liquidation Zones (ZEC/USDT)**\n"
            "* **Short Squeeze Zone**: $450 - $465 (Short liquidations concentrated here)\n"
            "* **Current Magnet**: $415 (Strong local support/resistance)\n"
            "* **Long Flush Zone**: $380 - $400 (Deeper liquidity pool for long reversals)")

    # REVERSAL CALCULATION
    st.header(f"Strategy for ZEC @ ${price:,.2f} ({pos_type} Reversal)")
    
    if pos_type != "None":
        # FLIP MATH: Close current + Add Phase 1 of new
        phase1_new_usdt = total_pos_val * 0.25
        flip_order_total = current_size_usdt + phase1_new_usdt
        
        action = "BUY" if pos_type == "Short" else "SELL"
        st.warning(f"🔄 **FLIP ACTION**: {action} **${flip_order_total:,.2f}** (~{flip_order_total/price:.2f} ZEC)")
        
        plan_data = {
            "Phase": ["1 (The Flip)", "2 (+45m)", "3 (+90m)"],
            "Order Size (USDT)": [f"${flip_order_total:,.2f}", f"${total_pos_val*0.35:,.2f}", f"${total_pos_value*0.40:,.2f}"],
            "Liquidity Marker": ["At $415 Pivot", "Near $405/$430 Clusters", "At $380/$475 Exhaustion"]
        }
    else:
        # Standard Fresh Entry Plan
        plan_data = {
            "Phase": ["1 (Initial)", "2 (+45m)", "3 (+90m)"],
            "Order Size (USDT)": [f"${total_pos_val*0.25:,.2f}", f"${total_pos_val*0.35:,.2f}", f"${total_pos_val*0.40:,.2f}"],
            "Liquidity Marker": ["At $415 Pivot", "Near $405/$430 Clusters", "At $380/$475 Exhaustion"]
        }
    
    st.table(pd.DataFrame(plan_data))

    # TARGETS & RISK SUMMARY
    st.subheader(f"Goals (1:{target_rr} Ratio)")
    avg_entry = price * (0.992 if pos_type != "Long" else 1.008)
    sl_price = avg_entry * (1 - (sl_dist_pct / 100)) if pos_type != "Long" else avg_entry * (1 + (sl_dist_pct / 100))
    tp_price = avg_entry * (1 + (sl_dist_pct * target_rr / 100)) if pos_type != "Long" else avg_entry * (1 - (sl_dist_pct * target_rr / 100))
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Entry", f"${avg_entry:,.2f}")
    c2.metric("Stop Loss", f"${sl_price:,.2f}")
    c3.metric("Take Profit", f"${tp_price:,.2f}")
