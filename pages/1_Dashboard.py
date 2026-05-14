import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime
import sys
import os
import importlib

# Ensure utils can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import utils

# Render global UI and Search
current_ticker, currency_label, exchange_rate = utils.setup_page_ui()

# --- MAIN DASHBOARD ---
st.title("📊 Intelligent Market Dashboard")

if current_ticker:
    with st.spinner(f"Fetching data for {current_ticker}..."):
        try:
            stock = yf.Ticker(current_ticker)
            info = stock.info
            
            # Fetch 1-day 1-minute data for VWAP
            intraday = stock.history(period="1d", interval="1m")
            
            # --- COMPANY HEADER ---
            name = info.get('shortName', info.get('longName', current_ticker))
            website = info.get('website', '')
            logo_html = ""
            if website:
                domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                logo_url = f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=128"
                logo_html = f'<img src="{logo_url}" width="40" height="40" style="margin-left: 15px; border-radius: 5px; vertical-align: middle;" onerror="this.style.display=\'none\'">'
            
            st.markdown(f"<h2 style='display: flex; align-items: center;'>{name} ({current_ticker}){logo_html}</h2>", unsafe_allow_html=True)

            # --- PRICE PANEL ---
            st.markdown("### 📈 Price Panel")
            col1, col2, col3 = st.columns([1, 2, 1])
            
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            prev_close = info.get('previousClose', current_price)
            change = current_price - prev_close
            pct_change = (change / prev_close) * 100 if prev_close else 0
            
            with col1:
                st.metric("Current Price", utils.format_currency(current_price * exchange_rate, currency_label), 
                          f"{utils.format_currency(change * exchange_rate, currency_label)} ({pct_change:+.2f}%)")
                
            with col2:
                # VWAP Calculation
                if not intraday.empty and 'Volume' in intraday.columns:
                    intraday['Typical_Price'] = (intraday['High'] + intraday['Low'] + intraday['Close']) / 3
                    cum_vol = intraday['Volume'].cumsum()
                    valid_mask = cum_vol > 0
                    if valid_mask.any():
                        intraday['VWAP'] = (intraday['Typical_Price'] * intraday['Volume']).cumsum() / cum_vol
                        intraday['VWAP'] = intraday['VWAP'].ffill()
                        vwap = intraday['VWAP'].iloc[-1]
                        st.metric("VWAP (Intraday)", utils.format_currency(vwap * exchange_rate, currency_label))
                    else:
                        st.metric("VWAP (Intraday)", "N/A")
                else:
                    st.metric("VWAP", "N/A")
                    
                day_low = info.get('dayLow', intraday['Low'].min() if not intraday.empty else current_price)
                day_high = info.get('dayHigh', intraday['High'].max() if not intraday.empty else current_price)
                if day_low and day_high and (day_high > day_low):
                    range_pct = (current_price - day_low) / (day_high - day_low)
                    st.write(f"**Day Range:** {utils.format_currency(day_low * exchange_rate, currency_label)} ----------------- {utils.format_currency(day_high * exchange_rate, currency_label)}")
                    st.progress(min(max(range_pct, 0.0), 1.0))
                
            with col3:
                bid = info.get('bid', 0)
                ask = info.get('ask', 0)
                if bid and ask:
                    st.metric("Bid / Ask Spread", f"{utils.format_currency(bid * exchange_rate, currency_label)} / {utils.format_currency(ask * exchange_rate, currency_label)}", 
                              f"Spread: {utils.format_currency((ask - bid) * exchange_rate, currency_label)}", delta_color="off")
                else:
                    st.metric("Bid / Ask Spread", "N/A")
            
            st.divider()
            
            # --- ANALYST METRICS CARDS ---
            st.markdown("### 📊 Analyst Metrics")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            
            with m_col1:
                high_52 = info.get('fiftyTwoWeekHigh', 0)
                if high_52:
                    st.metric("vs 52-Week High", utils.format_currency(high_52 * exchange_rate, currency_label), 
                              f"{((current_price / high_52) - 1) * 100:+.2f}%")
                else:
                    st.metric("vs 52-Week High", "N/A")
                
            with m_col2:
                try:
                    spy = yf.Ticker("SPY").history(period="1mo")
                    stock_hist = stock.history(period="1mo")
                    if not spy.empty and not stock_hist.empty:
                        spy_ret = (spy['Close'].iloc[-1] / spy['Close'].iloc[0]) - 1
                        stock_ret = (stock_hist['Close'].iloc[-1] / stock_hist['Close'].iloc[0]) - 1
                        rs = stock_ret - spy_ret
                        st.metric("1mo Alpha vs S&P 500", f"{rs * 100:+.2f}%", f"Stock: {stock_ret*100:+.1f}% | SPY: {spy_ret*100:+.1f}%", delta_color="normal")
                    else:
                        st.metric("1mo Alpha vs S&P 500", "N/A")
                except:
                    st.metric("1mo Alpha vs S&P 500", "Error")
                    
            with m_col3:
                vol = info.get('volume', info.get('regularMarketVolume', 0))
                avg_vol = info.get('averageVolume', 0)
                vol_ratio = (vol / avg_vol) if avg_vol else 0
                st.metric("Today's Volume", f"{vol:,}", f"{vol_ratio:.2f}x Avg" if avg_vol else "N/A", delta_color="normal" if vol_ratio > 1 else "off")
                
            with m_col4:
                short_pct = info.get('shortPercentOfFloat', 0)
                if short_pct is not None:
                    short_pct *= 100
                dtc = info.get('shortRatio', 0)
                st.metric("Short Float %", f"{short_pct:.2f}%" if short_pct else "N/A", f"Days to Cover: {dtc:.2f}" if dtc else "", delta_color="off")

            st.divider()
            
            # --- MARKET BREADTH PANEL ---
            st.markdown("### 🌐 Market Breadth (Top S&P Components)")
            
            top_sp_tickers = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'BRK-B', 'TSLA', 'UNH', 
                              'JNJ', 'JPM', 'V', 'PG', 'MA', 'AVGO', 'HD', 'CVX', 'MRK', 'PEP']
            
            @st.cache_data(ttl=60)
            def get_breadth():
                try:
                    data = yf.download(top_sp_tickers, period="3mo", progress=False)['Close']
                    if data.empty: return 0, 0, 0
                    
                    today_ret = data.iloc[-1] / data.iloc[-2] - 1
                    advances = (today_ret > 0).sum()
                    declines = (today_ret < 0).sum()
                    
                    ma_50 = data.rolling(window=50).mean().iloc[-1]
                    above_50 = (data.iloc[-1] > ma_50).sum()
                    pct_above_50 = (above_50 / len(top_sp_tickers)) * 100
                    
                    return advances, declines, pct_above_50
                except:
                    return 0, 0, 0
                
            adv, dec, pct_above_50 = get_breadth()
            
            b_col1, b_col2, b_col3 = st.columns([1, 2, 1])
            with b_col1:
                st.metric("Advance / Decline", f"{adv} / {dec}", f"Ratio: {adv/dec:.2f}" if dec > 0 else "N/A", delta_color="normal" if adv > dec else "inverse")
            with b_col2:
                st.metric("% Above 50-Day MA", f"{pct_above_50:.1f}%")
                if pct_above_50 > 0:
                    st.progress(pct_above_50 / 100.0)
            
            st.markdown("#### Major Indices")
            indices = {"S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow Jones": "^DJI", "Russell 2000": "^RUT", "VIX": "^VIX"}
            
            @st.cache_data(ttl=60)
            def get_indices():
                idx_data = []
                for name, t in indices.items():
                    try:
                        hist = yf.Ticker(t).history(period="2d")
                        if len(hist) >= 2:
                            c = hist['Close'].iloc[-1]
                            p = hist['Close'].iloc[-2]
                            idx_data.append({"Index": name, "Price": c, "Change": c - p, "% Change": (c/p - 1)*100})
                    except:
                        pass
                return pd.DataFrame(idx_data)
                
            df_idx = get_indices()
            if not df_idx.empty:
                i_cols = st.columns(len(df_idx))
                for idx, row in df_idx.iterrows():
                    with i_cols[idx]:
                        delta_c = "inverse" if row['Index'] == "VIX" and row['Change'] > 0 else "normal"
                        if row['Index'] == "VIX" and row['Change'] < 0: delta_c = "normal"
                        # For indices, we generally keep the native value, maybe multiply by exchange rate if user wants?
                        # Since indices like S&P are points/USD, we can convert them.
                        st.metric(row['Index'], utils.format_currency(row['Price'] * exchange_rate, currency_label), 
                                  f"{utils.format_currency(row['Change'] * exchange_rate, currency_label)} ({row['% Change']:+.2f}%)", delta_color=delta_c)

        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")

# --- FOOTER ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>Data: Yahoo Finance | Built for Educational Purposes Only</p>", unsafe_allow_html=True)
