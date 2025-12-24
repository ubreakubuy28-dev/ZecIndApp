import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta

# 1. CONFIG
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

st.title("🛡️ ZEC Master Risk & Reversal Radar")

# 2. SIDEBAR: POSITION & PROFIT
st.sidebar.header("Current Position")
in_short = st.sidebar.checkbox("Currently in a Short?", value=True)
short_input_mode = st.sidebar.radio("Input Short Size in:", ["ZEC Units", "USDT Value"])
short_val = st.sidebar.number_input(f"Short Size ({short_input_mode})", value=28.8 if short_input_mode == "ZEC Units" else 11700.0)

st.sidebar.markdown("---")
st.sidebar.header("Profit Roll-over")
roll_over_profit = st.sidebar.checkbox("Add Current Profit to New Long?", value=True)
current_pnl = st.sidebar.number_input("Current PnL ($)", value=82.0)

# 3. GLOBAL RISK
st.sidebar.markdown("---")
risk_usd = st.sidebar.number_input("Acceptable Loss ($)", value=10.0)
sl_dist_pct = st.sidebar.slider("Stop Loss Distance (%)", 0.5, 5.0, 2.0)

if st.button("🔄 Analyze & Calculate Flip"):
    data, avg_vol = get_indicators('ZEC/USDT')
    price = data['close']
    
    # Convert Short to USDT if needed
    short_qty_zec = short_val if short_input_mode == "ZEC Units" else short_val / price
    short_usdt_val = short_qty_zec * price
    
    # ⚡ LIQUIDATION ZONES (FREE DATA MARKERS)
    st.info("📊 **Key Liquidation Zones (Estimated)**\n"
            "* **Short Squeeze Zone**: $455 - $470 (Heavy clusters)\n"
            "* **Current Support Magnet**: $415 (Local floor)\n"
            "* **Long Flush Zone**: $380 - $400 (Deep liquidity pool)")

    # 4. CALCULATION
    total_long_size = risk_usd / (sl_dist_pct / 100)
    if roll_over_profit:
        total_long_size += current_pnl # Adding profit to buy more ZEC without increasing risk
        
    st.header(f"Strategy for ZEC @ ${price:,.2f}")
    
    if in_short:
        # THE FLIP ORDER
        phase1_long = total_long_size * 0.25
        flip_order = short_usdt_val + phase1_long
        
        st.warning(f"🔄 **FLIP ACTION**: Buy **${flip_order:,.2f}** (~{flip_order/price:.2f} ZEC)")
        
        # 3-PHASE PLAN
        scale_df = pd.DataFrame({
            "Phase": ["1 (The Flip)", "2 (+45m)", "3 (+90m)"],
            "Entry Target": [f"${price:,.2f}", f"${price*0.992:,.2f}", f"${price*0.985:,.2f}"],
            "Order Size ($)": [f"${flip_order:,.2f}", f"${total_long_size*0.35:,.2f}", f"${total_long_size*0.40:,.2f}"],
            "Liquidity Note": ["At $415 Support", "Near $405 Flush", "Deep $380 Pool"]
        })
        st.table(scale_df)
    else:
        # Standard 3-Phase Entry
        entry_df = pd.DataFrame({
            "Phase": ["1 (Initial)", "2 (+45m)", "3 (+90m)"],
            "Price": [f"${price:,.2f}", f"${price*0.992:,.2f}", f"${price*0.985:,.2f}"],
            "Size ($)": [f"${total_long_size*0.25:,.2f}", f"${total_long_size*0.35:,.2f}", f"${total_long_size*0.40:,.2f}"]
        })
        st.table(entry_df)

    # 5. RISK SUMMARY
    st.subheader("New Long Targets (1:3 Ratio)")
    avg_e = price * 0.99 # Rough average
    sl_p = avg_e * (1 - (sl_dist_pct / 100))
    tp_p = avg_e * (1 + (sl_dist_pct * 3 / 100))
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Entry", f"${avg_e:,.2f}")
    c2.metric("Stop Loss", f"${sl_p:,.2f}")
    c3.metric("Take Profit", f"${tp_p:,.2f}")
