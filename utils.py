import streamlit as st
import yfinance as yf
from datetime import datetime
import os
import pandas as pd
import pytz

CURRENCIES = {
    "USD ($)": {"code": "USD", "symbol": "$"},
    "EURO (€)": {"code": "EUR", "symbol": "€"},
    "JAPANESE YEN (¥)": {"code": "JPY", "symbol": "¥"},
    "BRITISH POUND (£)": {"code": "GBP", "symbol": "£"},
    "INDIAN RUPEE (₹)": {"code": "INR", "symbol": "₹"}
}

@st.cache_data(ttl=3600) # Cache exchange rates for 1 hour to prevent API throttling
def get_exchange_rate(target_code):
    if target_code == "USD":
        return 1.0
    try:
        # e.g. "EUR=X" is Yahoo's ticker for USD to EUR
        ticker_str = f"{target_code}=X"
        rate = yf.Ticker(ticker_str).history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except Exception as e:
        # Fallback if yfinance fails
        st.sidebar.warning(f"Failed to fetch {target_code} rate. Using USD.")
        return 1.0

def format_currency(value, currency_label):
    if value is None or str(value).lower() == "nan":
        return "N/A"
    
    symbol = CURRENCIES[currency_label]["symbol"]
    # For large numbers, Yen/Rupee might not need decimal points if very large, but we'll stick to 2
    if CURRENCIES[currency_label]["code"] == "JPY":
        return f"{symbol}{value:,.0f}"
    return f"{symbol}{value:,.2f}"

def format_large_currency(num, currency_label):
    if pd.isna(num) or num is None:
        return "N/A"
    
    symbol = CURRENCIES[currency_label]["symbol"]
    if num >= 1e12:
        return f"{symbol}{num/1e12:.2f}T"
    elif num >= 1e9:
        return f"{symbol}{num/1e9:.2f}B"
    elif num >= 1e6:
        return f"{symbol}{num/1e6:.2f}M"
    else:
        return f"{symbol}{num:,.0f}"

def toggle_theme():
    if st.session_state.theme == 'Dark Terminal':
        st.session_state.theme = 'Light Report'
    else:
        st.session_state.theme = 'Dark Terminal'

def get_market_status():
    """Determine if NYSE is open or closed."""
    try:
        tz = pytz.timezone('US/Eastern')
        now = datetime.now(tz)
        
        # Check if weekend
        if now.weekday() >= 5:
            return "🔴 CLOSED (Weekend)"
        
        # Check market hours (9:30 AM to 4:00 PM EST)
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if market_open <= now <= market_close:
            return "🟢 OPEN"
        elif now < market_open:
            return "🟡 PRE-MARKET"
        else:
            return "🔴 CLOSED (After Hours)"
    except:
        # Fallback
        return "Unknown"

def setup_page_ui():
    # --- STATE INIT ---
    if 'theme' not in st.session_state:
        st.session_state.theme = 'Dark Terminal'
    if 'currency' not in st.session_state:
        st.session_state.currency = "USD ($)"
    if 'exchange_rate' not in st.session_state:
        st.session_state.exchange_rate = 1.0
    if 'current_ticker' not in st.session_state:
        st.session_state.current_ticker = "SPY"
    if 'search_history' not in st.session_state:
        st.session_state.search_history = ["SPY"]

    def handle_search():
        new_t = st.session_state.global_search_input.upper().strip()
        if new_t:
            st.session_state.current_ticker = new_t
            if new_t in st.session_state.search_history:
                st.session_state.search_history.remove(new_t)
            st.session_state.search_history.insert(0, new_t)
            if len(st.session_state.search_history) > 5:
                st.session_state.search_history = st.session_state.search_history[:5]
        st.session_state.global_search_input = ""

    # --- THEME INJECTION ---
    # Note: Do not indent the <style> tags with 4 spaces or markdown will render them as code blocks!
    if st.session_state.theme == 'Light Report':
        st.markdown("""
<style>
.stApp { background-color: #f4f6f9; color: #1e1e1e; }
[data-testid="stSidebar"] { background-color: #ffffff; color: #1e1e1e; border-right: 1px solid #e0e0e0; }
h1, h2, h3, h4 { color: #111827 !important; }
.stMetric-value { color: #111827 !important; }
</style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
<style>
.stApp { background-color: #0e1117; color: #ffffff; }
[data-testid="stSidebar"] { background-color: #161b22; color: #ffffff; border-right: 1px solid #333; }
</style>
        """, unsafe_allow_html=True)

    # --- TOP SEARCH BAR (Main Content Area) ---
    st.subheader("🔍 Quick Search")
    st.text_input("Search Ticker", placeholder="e.g. AAPL, TSLA (Press Enter to search)", key="global_search_input", on_change=handle_search)
    
    if st.session_state.search_history:
        # Use an expander to mimic a dropdown toggle for recent searches
        with st.expander("🕒 Recent Searches (Click to toggle)", expanded=False):
            cols = st.columns(min(len(st.session_state.search_history), 5))
            for i, hist_ticker in enumerate(st.session_state.search_history[:5]):
                if cols[i].button(hist_ticker, key=f"hist_main_{hist_ticker}_{i}", use_container_width=True):
                    st.session_state.current_ticker = hist_ticker
                    st.rerun()

    st.markdown("---")

    # --- SIDEBAR CONTENT ---
    st.sidebar.title("📈 Terminal")
    
    # Market Status
    status = get_market_status()
    st.sidebar.markdown(f"**Market Status:** {status}")
    
    # Real-time clock using fragments to update automatically
    @st.fragment(run_every="1s")
    def display_clock():
        try:
            tz = pytz.timezone('US/Eastern')
            now_est = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S EST")
            st.sidebar.markdown(f"🕒 **{now_est}**")
        except:
            pass
        
    display_clock()
    st.sidebar.divider()

    # --- TOP BUTTONS ---
    st.sidebar.button(f"🌓 Toggle Theme (Current: {st.session_state.theme})", on_click=toggle_theme, use_container_width=True)
    
    # --- CURRENCY SELECTOR ---
    selected_currency = st.sidebar.selectbox("💱 Currency", list(CURRENCIES.keys()), index=list(CURRENCIES.keys()).index(st.session_state.currency))
    
    if selected_currency != st.session_state.currency:
        st.session_state.currency = selected_currency
        with st.sidebar:
            with st.spinner("Fetching FX rate..."):
                st.session_state.exchange_rate = get_exchange_rate(CURRENCIES[selected_currency]["code"])
        st.rerun()

    st.sidebar.markdown("---")
    
    # --- SIDEBAR HISTORY ---
    st.sidebar.subheader("🕒 Search History")
    if st.session_state.search_history:
        # Arrange history vertically in sidebar for better fit
        for i, hist_ticker in enumerate(st.session_state.search_history[:5]):
            if st.sidebar.button(f"🔎 {hist_ticker}", key=f"hist_side_{hist_ticker}_{i}", use_container_width=True):
                st.session_state.current_ticker = hist_ticker
                st.rerun()
    else:
        st.sidebar.caption("No history yet.")

    st.sidebar.markdown("---")
    
    # --- TOP MOVERS ---
    st.sidebar.subheader("🔥 Top Movers")
    top_movers_demo = {"NVDA": "+4.2%", "AMD": "+3.1%", "TSLA": "-2.5%", "META": "+1.8%"}
    for t, c in top_movers_demo.items():
        color = "green" if "+" in c else "red"
        st.sidebar.markdown(f"**{t}** <span style='float:right; color:{color};'>{c}</span>", unsafe_allow_html=True)

    return st.session_state.current_ticker, st.session_state.currency, st.session_state.exchange_rate
