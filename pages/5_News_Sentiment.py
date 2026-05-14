import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import re
import sys
import os
import importlib

# Ensure utils can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import utils

# Render global UI and Search
current_ticker, currency_label, exchange_rate = utils.setup_page_ui()

st.title("📰 News & Sentiment Analysis")

# Keyword dictionaries
bullish_keywords = ['beat', 'upgrade', 'record', 'growth', 'breakout', 'acquisition', 'soar', 'jump', 'surge', 'buy', 'higher', 'positive', 'win']
bearish_keywords = ['miss', 'downgrade', 'layoff', 'decline', 'investigation', 'loss', 'plunge', 'fall', 'sell', 'drop', 'lower', 'negative', 'warning']

def analyze_sentiment(text):
    if not text: return 0
    text = text.lower()
    bull_count = sum(1 for word in bullish_keywords if re.search(r'\b' + word + r'\b', text))
    bear_count = sum(1 for word in bearish_keywords if re.search(r'\b' + word + r'\b', text))
    return bull_count - bear_count

if current_ticker:
    with st.spinner(f"Analyzing sentiment for {current_ticker}..."):
        try:
            session = utils.get_yf_session()
            stock = yf.Ticker(current_ticker, session=session)
            
            info = stock.info
            name = info.get('shortName', info.get('longName', current_ticker))
            website = info.get('website', '')
            logo_html = ""
            if website:
                domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                logo_url = f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=128"
                logo_html = f'<img src="{logo_url}" width="40" height="40" style="margin-left: 15px; border-radius: 5px; vertical-align: middle;" onerror="this.style.display=\'none\'">'
            st.markdown(f"<h2 style='display: flex; align-items: center;'>{name} ({current_ticker}){logo_html}</h2>", unsafe_allow_html=True)
            st.markdown("---")
            # Layout
            col_news, col_sent = st.columns([2, 1])
            
            # Fetch News
            news = stock.news
            
            total_sentiment_score = 0
            
            with col_news:
                st.subheader("Latest Headlines")
                if news:
                    for item in news[:10]: # Top 10
                        content = item.get('content', item) # fallback to item if 'content' key doesn't exist
                        title = content.get('title', 'No Title')
                        summary = content.get('summary', '')
                        
                        # Calculate sentiment for this article
                        score = analyze_sentiment(title) + analyze_sentiment(summary)
                        total_sentiment_score += score
                        
                        if score > 0:
                            badge = "🟢 Bullish"
                        elif score < 0:
                            badge = "🔴 Bearish"
                        else:
                            badge = "🟡 Neutral"
                            
                        pub_time = content.get('pubDate')
                        if pub_time:
                            try:
                                # Example: 2026-05-12T21:02:00Z
                                dt = datetime.strptime(pub_time, "%Y-%m-%dT%H:%M:%SZ")
                                date_str = dt.strftime('%Y-%m-%d %H:%M')
                                time_disp = f"• {date_str}"
                            except:
                                time_disp = f"• {pub_time}"
                        else:
                            time_disp = ""
                            
                        provider = content.get('provider', {}).get('displayName', 'Unknown')
                        link = content.get('canonicalUrl', {}).get('url', '#')
                            
                        with st.container():
                            st.markdown(f"#### [{title}]({link})")
                            st.caption(f"**{provider}** {time_disp} | Sentiment: **{badge}**")
                            if summary:
                                st.write(summary)
                            st.markdown("---")
                else:
                    st.info(f"No recent news found for {current_ticker}.")
            
            with col_sent:
                st.subheader("Overall Sentiment")
                
                # Normalize total score for the gauge
                gauge_score = max(min(total_sentiment_score, 10), -10)
                
                if gauge_score > 3: main_color = "green"
                elif gauge_score < -3: main_color = "red"
                else: main_color = "yellow"
                
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = gauge_score,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': "Sentiment Meter"},
                    gauge = {
                        'axis': {'range': [-10, 10]},
                        'bar': {'color': main_color},
                        'steps': [
                            {'range': [-10, -3], 'color': "rgba(255, 0, 0, 0.2)"},
                            {'range': [-3, 3], 'color': "rgba(255, 255, 0, 0.2)"},
                            {'range': [3, 10], 'color': "rgba(0, 255, 0, 0.2)"}],
                        'threshold': {
                            'line': {'color': "white", 'width': 4},
                            'thickness': 0.75,
                            'value': gauge_score}
                    }
                ))
                fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, use_container_width=True)
                
                status = "Bullish" if gauge_score > 3 else "Bearish" if gauge_score < -3 else "Neutral"
                st.markdown(f"<h3 style='text-align: center; color: {main_color};'>{status}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center;'>Net Keyword Score: {total_sentiment_score}</p>", unsafe_allow_html=True)
                
                st.markdown("---")
                st.subheader("Insider Transactions")
                try:
                    insiders = stock.insider_transactions
                    if insiders is not None and not insiders.empty:
                        # Convert value columns using exchange rate if present
                        if 'Value' in insiders.columns:
                            insiders['Value'] = insiders['Value'] * exchange_rate
                        st.dataframe(insiders.head(10), use_container_width=True)
                    else:
                        st.info("No insider transactions found.")
                except Exception as e:
                    st.warning("Could not load insider transactions.")
                    
                st.markdown("---")
                st.subheader("Institutional Ownership")
                try:
                    inst = stock.institutional_holders
                    if inst is not None and not inst.empty:
                        if 'Value' in inst.columns:
                            inst['Value'] = inst['Value'] * exchange_rate
                        st.dataframe(inst.head(10), use_container_width=True)
                    else:
                        st.info("No institutional ownership data found.")
                except Exception as e:
                    st.warning("Could not load institutional ownership.")
                    
        except Exception as e:
            st.error(f"Error analyzing sentiment: {e}")

# --- FOOTER ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>Data: Yahoo Finance | Built for Educational Purposes Only</p>", unsafe_allow_html=True)
