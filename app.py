import streamlit as st
from datetime import datetime
import pytz

# Page config must be the first Streamlit command
st.set_page_config(
    page_title="Trading Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def get_market_status():
    """Determine if NYSE is open or closed."""
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

# Shared UI Elements
with st.sidebar:
    st.title("📈 Terminal")
    
    # Market Status
    status = get_market_status()
    st.markdown(f"**Market Status:** {status}")
    
    # Real-time clock using fragments to update automatically
    @st.fragment(run_every="1s")
    def display_clock():
        tz = pytz.timezone('US/Eastern')
        now_est = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S EST")
        st.markdown(f"🕒 **{now_est}**")
        
    display_clock()
    st.divider()

# Navigation setup
dashboard = st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📊", default=True)
analysis = st.Page("pages/2_Deep_Analysis.py", title="Deep Analysis", icon="🔍")
charts = st.Page("pages/3_Technical_Charts.py", title="Technical Charts", icon="📉")
fundamentals = st.Page("pages/4_Fundamentals.py", title="Fundamentals", icon="🏦")
news = st.Page("pages/5_News_Sentiment.py", title="News & Sentiment", icon="🗞️")
watchlist = st.Page("pages/6_Watchlist.py", title="Watchlist", icon="⭐")

pg = st.navigation([dashboard, analysis, charts, fundamentals, news, watchlist])
pg.run()
