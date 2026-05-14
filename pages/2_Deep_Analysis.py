import streamlit as st
import yfinance as yf
import pandas as pd
import sys
import os
import importlib

# Ensure utils can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import utils

# Render global UI and Search
current_ticker, currency_label, exchange_rate = utils.setup_page_ui()

st.title("🔍 Deep Analysis")
st.markdown("Detailed stock analysis and profile information.")

if current_ticker:
    with st.spinner(f"Fetching data for {current_ticker}..."):
        try:
            stock = yf.Ticker(current_ticker)
            info = stock.info
            
            if 'symbol' not in info and 'shortName' not in info:
                st.error(f"Ticker '{current_ticker}' not found or no data available.")
            else:
                current_price = info.get('currentPrice', info.get('regularMarketPrice', info.get('previousClose', 0)))
                previous_close = info.get('previousClose', current_price)
                
                change = current_price - previous_close
                pct_change = (change / previous_close) * 100 if previous_close else 0
                
                name = info.get('longName', info.get('shortName', current_ticker))
                website = info.get('website', '')
                logo_html = ""
                if website:
                    domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                    logo_url = f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=128"
                    logo_html = f'<img src="{logo_url}" width="40" height="40" style="margin-left: 15px; border-radius: 5px; vertical-align: middle;" onerror="this.style.display=\'none\'">'
                st.markdown(f"<h3 style='display: flex; align-items: center;'>{name} ({current_ticker}){logo_html}</h3>", unsafe_allow_html=True)
                
                delta_color = "normal" if change >= 0 else "inverse"
                st.metric("Current Price", utils.format_currency(current_price * exchange_rate, currency_label), 
                          f"{utils.format_currency(change * exchange_rate, currency_label)} ({pct_change:.2f}%)", delta_color=delta_color)
                
                st.divider()
                st.markdown("### Company Profile")
                st.write(info.get('longBusinessSummary', 'No business summary available.'))
                
                st.markdown("### Key Statistics")
                col1, col2, col3, col4 = st.columns(4)
                
                market_cap = info.get('marketCap', 0)
                col1.metric("Market Cap", utils.format_large_currency(market_cap * exchange_rate, currency_label))
                col2.metric("PE Ratio (TTM)", info.get('trailingPE', 'N/A'))
                col3.metric("52 Week High", utils.format_currency(info.get('fiftyTwoWeekHigh', 0) * exchange_rate, currency_label))
                col4.metric("52 Week Low", utils.format_currency(info.get('fiftyTwoWeekLow', 0) * exchange_rate, currency_label))
                
                st.markdown("### Analyst Ratings")
                col1, col2 = st.columns(2)
                col1.metric("Target Mean Price", utils.format_currency(info.get('targetMeanPrice', 0) * exchange_rate, currency_label))
                col2.metric("Recommendation", str(info.get('recommendationKey', 'N/A')).capitalize())
                
        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")

# --- FOOTER ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>Data: Yahoo Finance | Built for Educational Purposes Only</p>", unsafe_allow_html=True)
