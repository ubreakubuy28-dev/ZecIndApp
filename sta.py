# NEW SIDEBAR INPUTS
risk_amount = st.sidebar.number_input("Acceptable Loss ($)", value=10.0)
target_reward_ratio = 3 # 1:3 Ratio

if st.button("Refresh & Calculate Sizing"):
    # ... (indicators logic) ...
    
    # 1. Calculate the 'Risk Distance'
    # Based on current volatility, let's say Stop Loss is 2% away
    sl_dist_pct = 0.02 
    
    # 2. Position Sizing Formula: 
    # Position Size = Risk Amount / Stop Loss %
    # Example: If you want to lose $10 and SL is 2%, your size is $500
    total_position_value = risk_amount / sl_dist_pct
    
    # 3. 3-Spot Scale-In Plan
    p1_size = total_position_value * 0.25
    p2_size = total_position_value * 0.35
    p3_size = total_position_value * 0.40
    
    st.header(f"💰 Sizing for ${risk_amount} Risk")
    plan = {
        "Phase": ["Phase 1 (Start)", "Phase 2 (+45m)", "Phase 3 (+90m)"],
        "Sizing (USDT)": [f"${p1_size:,.2f}", f"${p2_size:,.2f}", f"${p3_size:,.2f}"],
        "Price Target": [f"${zec_price:,.2f}", f"${zec_price*0.992:,.2f}", f"${zec_price*0.985:,.2f}"]
    }
    st.table(pd.DataFrame(plan))
    
    # 4. Final Risk Stats
    st.info(f"If Stop Loss is hit: You lose **${risk_amount}**")
    st.success(f"If Take Profit is hit: You gain **${risk_amount * 3}** (1:3 Ratio)")
