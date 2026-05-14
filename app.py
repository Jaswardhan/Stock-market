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

# Navigation setup
dashboard = st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📊", default=True)
analysis = st.Page("pages/2_Deep_Analysis.py", title="Deep Analysis", icon="🔍")
charts = st.Page("pages/3_Technical_Charts.py", title="Technical Charts", icon="📉")
fundamentals = st.Page("pages/4_Fundamentals.py", title="Fundamentals", icon="🏦")
news = st.Page("pages/5_News_Sentiment.py", title="News & Sentiment", icon="🗞️")
watchlist = st.Page("pages/6_Watchlist.py", title="Watchlist", icon="⭐")

pg = st.navigation([dashboard, analysis, charts, fundamentals, news, watchlist])
pg.run()
