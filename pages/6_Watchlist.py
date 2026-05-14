import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import json
import os
import plotly.graph_objects as go
from scipy.signal import find_peaks
import sys
import importlib

# Ensure utils can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import utils

# Render global UI and Search
current_ticker, currency_label, exchange_rate = utils.setup_page_ui()

st.title("⭐ Watchlist & Trade Setup Builder")

# --- Watchlist Storage ---
WATCHLIST_FILE = "watchlist.json"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, 'r') as f:
                return json.load(f)
        except:
            return ['AAPL', 'MSFT', 'NVDA', 'TSLA']
    return ['AAPL', 'MSFT', 'NVDA', 'TSLA']

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(watchlist, f)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()

# Add current_ticker to watchlist if it exists and not already there
if current_ticker and current_ticker not in st.session_state.watchlist:
    st.session_state.watchlist.append(current_ticker)
    save_watchlist(st.session_state.watchlist)

# --- Top Actions ---
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    with st.form("add_ticker_form", clear_on_submit=True):
        new_ticker = st.text_input("Add Ticker Symbol").upper()
        submitted = st.form_submit_button("Add to Watchlist")
        if submitted and new_ticker:
            if new_ticker not in st.session_state.watchlist:
                st.session_state.watchlist.append(new_ticker)
                save_watchlist(st.session_state.watchlist)
                st.rerun()
            else:
                st.warning(f"{new_ticker} is already in your watchlist.")

with col2:
    with st.form("remove_ticker_form", clear_on_submit=True):
        rem_ticker = st.selectbox("Remove Ticker", [""] + st.session_state.watchlist)
        rem_submitted = st.form_submit_button("Remove")
        if rem_submitted and rem_ticker:
            st.session_state.watchlist.remove(rem_ticker)
            save_watchlist(st.session_state.watchlist)
            st.rerun()

# --- Live Table ---
st.markdown("### Live Watchlist Metrics")
if not st.session_state.watchlist:
    st.info("Your watchlist is empty.")
else:
    @st.cache_data(ttl=300)
    def fetch_watchlist_data(tickers):
        data = []
        for t in tickers:
            try:
                stock = yf.Ticker(t)
                df = stock.history(period="6mo")
                if not df.empty and len(df) > 30:
                    curr_price = df['Close'].iloc[-1]
                    prev_price = df['Close'].iloc[-2]
                    pct_change = ((curr_price - prev_price) / prev_price) * 100
                    
                    df.ta.rsi(length=14, append=True)
                    df.ta.macd(fast=12, slow=26, signal=9, append=True)
                    rsi = df['RSI_14'].iloc[-1]
                    macdh = df['MACDh_12_26_9'].iloc[-1]
                    macd_sig = "Bullish" if macdh > 0 else "Bearish"
                    
                    vol_sma = df['Volume'].rolling(30).mean().iloc[-1]
                    vol = df['Volume'].iloc[-1]
                    vol_alert = "Yes ⚠️" if vol > (2 * vol_sma) else "No"
                    
                    score = 0
                    if rsi < 30: score += 2
                    elif rsi > 70: score -= 2
                    if macdh > 0: score += 1
                    if curr_price > df['Close'].rolling(50).mean().iloc[-1]: score += 1
                    
                    data.append({
                        "Ticker": t,
                        "Price": curr_price,
                        "Change %": pct_change,
                        "RSI (14)": round(rsi, 2),
                        "MACD Signal": macd_sig,
                        "Vol Alert": vol_alert,
                        "Tech Score": score
                    })
            except Exception:
                pass
        return pd.DataFrame(data)

    with st.spinner("Crunching technicals..."):
        wl_df = fetch_watchlist_data(st.session_state.watchlist)
        if not wl_df.empty:
            
            # Format currency strings correctly for display
            display_df = wl_df.copy()
            display_df["Price"] = display_df["Price"].apply(lambda x: utils.format_currency(x * exchange_rate, currency_label))
            
            styled_df = display_df.style.map(
                lambda x: f"color: {'#00ff00' if x > 0 else '#ff4444'}; font-weight:bold;", subset=['Change %']
            ).map(
                lambda x: 'color: #00ff00' if x == 'Bullish' else 'color: #ff4444' if x == 'Bearish' else '', subset=['MACD Signal']
            ).map(
                lambda x: 'color: yellow; font-weight:bold;' if x == 'Yes ⚠️' else '', subset=['Vol Alert']
            ).format({'Change %': "{:.2f}%"})
            
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            csv = wl_df.to_csv(index=False).encode('utf-8')
            with col3:
                st.download_button("📥 Export CSV", data=csv, file_name="watchlist.csv", mime="text/csv")

st.divider()

# --- Trade Setup Builder ---
st.markdown("## 🛠️ Trade Setup Builder (Analyst's Edge)")
st.markdown("Build high-probability trade setups using structural technical analysis.")

t_col1, t_col2 = st.columns([1, 2])
with t_col1:
    setup_ticker = st.selectbox("Select Ticker", st.session_state.watchlist, index=st.session_state.watchlist.index(current_ticker) if current_ticker in st.session_state.watchlist else 0)
    strategy = st.radio("Strategy Type", ["Breakout", "Pullback", "Reversal"])
    # Changed to use native capital in selected currency
    symbol = utils.CURRENCIES[currency_label]["symbol"]
    capital = st.number_input(f"Account Capital ({symbol})", value=10000, step=1000)
    risk_pct = st.slider("Risk per Trade (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.1) / 100.0

with t_col2:
    if setup_ticker:
        with st.spinner("Generating trade plan..."):
            stock = yf.Ticker(setup_ticker)
            
            info = stock.info
            name = info.get('shortName', info.get('longName', setup_ticker))
            website = info.get('website', '')
            logo_html = ""
            if website:
                domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                logo_url = f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=128"
                logo_html = f'<img src="{logo_url}" width="40" height="40" style="margin-left: 15px; border-radius: 5px; vertical-align: middle;" onerror="this.style.display=\'none\'">'
            st.markdown(f"<h3 style='display: flex; align-items: center;'>{name} ({setup_ticker}){logo_html}</h3>", unsafe_allow_html=True)
            
            df = stock.history(period="6mo")
            if not df.empty and len(df) > 30:
                df.ta.atr(length=14, append=True)
                
                # Multiply OHLC by exchange rate
                atr = df['ATRr_14'].iloc[-1] * exchange_rate
                curr_price = df['Close'].iloc[-1] * exchange_rate
                
                highs = df['High'] * exchange_rate
                lows = df['Low'] * exchange_rate
                
                peaks, _ = find_peaks(highs, distance=5)
                valleys, _ = find_peaks(-lows, distance=5)
                
                res_levels = highs.iloc[peaks].tail(3).values
                sup_levels = lows.iloc[valleys].tail(3).values
                
                nearest_res = min([r for r in res_levels if r > curr_price], default=curr_price * 1.05)
                nearest_sup = max([s for s in sup_levels if s < curr_price], default=curr_price * 0.95)
                
                if strategy == "Breakout":
                    entry = nearest_res * 1.002
                    stop = nearest_res - (atr * 1.0)
                elif strategy == "Pullback":
                    entry = nearest_sup * 1.002
                    stop = nearest_sup - (atr * 1.5)
                else: # Reversal
                    entry = curr_price
                    stop = nearest_sup - (atr * 2.0)
                    
                risk_per_share = entry - stop
                if risk_per_share <= 0: risk_per_share = 0.01
                
                target1 = entry + (risk_per_share * 1.5)
                target2 = entry + (risk_per_share * 2.5)
                target3 = entry + (risk_per_share * 4.0)
                
                total_risk_dollars = capital * risk_pct
                position_size_shares = int(total_risk_dollars // risk_per_share)
                position_size_dollars = position_size_shares * entry
                
                rr_ratio = (target2 - entry) / risk_per_share
                
                if rr_ratio >= 2.0:
                    st.success(f"✅ Valid Setup Found! Risk:Reward = 1:{rr_ratio:.2f}")
                    
                    st.markdown(f"""
                    <div style="background-color: #1e1e2e; padding: 20px; border-radius: 10px; border: 1px solid #333;">
                        <h3 style="margin-top:0; color:#00bfff;">Trade Plan: {setup_ticker} ({strategy})</h3>
                        <hr style="border-color:#333;">
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <p style="color:#aaa; margin:0;">Entry Price</p>
                                <h4 style="margin:0;">{utils.format_currency(entry, currency_label)}</h4>
                            </div>
                            <div>
                                <p style="color:#aaa; margin:0;">Stop Loss (1R)</p>
                                <h4 style="color:#ff4444; margin:0;">{utils.format_currency(stop, currency_label)}</h4>
                            </div>
                            <div>
                                <p style="color:#aaa; margin:0;">Risk / Share</p>
                                <h4 style="margin:0;">{utils.format_currency(risk_per_share, currency_label)}</h4>
                            </div>
                        </div>
                        <br>
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <p style="color:#aaa; margin:0;">Target 1 (1.5R)</p>
                                <h4 style="color:#00ff00; margin:0;">{utils.format_currency(target1, currency_label)}</h4>
                            </div>
                            <div>
                                <p style="color:#aaa; margin:0;">Target 2 (2.5R)</p>
                                <h4 style="color:#00ff00; margin:0;">{utils.format_currency(target2, currency_label)}</h4>
                            </div>
                            <div>
                                <p style="color:#aaa; margin:0;">Target 3 (4R)</p>
                                <h4 style="color:#00ff00; margin:0;">{utils.format_currency(target3, currency_label)}</h4>
                            </div>
                        </div>
                        <hr style="border-color:#333;">
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <p style="color:#aaa; margin:0;">Max Risk</p>
                                <h4 style="color:#ff4444; margin:0;">{utils.format_currency(total_risk_dollars, currency_label)}</h4>
                            </div>
                            <div>
                                <p style="color:#aaa; margin:0;">Position Size (Shares)</p>
                                <h4 style="margin:0;">{position_size_shares}</h4>
                            </div>
                            <div>
                                <p style="color:#aaa; margin:0;">Total Allocation</p>
                                <h4 style="margin:0;">{utils.format_currency(position_size_dollars, currency_label)}</h4>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning(f"⚠️ Setup Invalid. Risk:Reward is 1:{rr_ratio:.2f} (Minimum 1:2 required). Try a different strategy or wait for better pricing.")
            else:
                st.error("Not enough data to calculate setup.")

# --- FOOTER ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>Data: Yahoo Finance | Built for Educational Purposes Only</p>", unsafe_allow_html=True)
