import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from scipy.signal import find_peaks
import sys
import os
import importlib

# Ensure utils can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import utils

# Render global UI and Search
current_ticker, currency_label, exchange_rate = utils.setup_page_ui()

st.title("📉 Technical Analysis")

# Move to sidebar for more space
st.sidebar.header("Chart Settings")

# 1D / 1W / 1M / 3M / 6M / 1Y / 5Y
period_map = {
    "1D": "1d",
    "1W": "5d",
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "5Y": "5y"
}
period_label = st.sidebar.selectbox("Timeframe", list(period_map.keys()), index=5)
period = period_map[period_label]

st.sidebar.markdown("---")
st.sidebar.markdown("### Trend Indicators")
show_ema = st.sidebar.checkbox("EMA (9, 21)", value=True)
show_sma = st.sidebar.checkbox("SMA (50, 200) & Crosses", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands (20,2)", value=False)

st.sidebar.markdown("### Momentum Oscillators")
show_rsi = st.sidebar.checkbox("RSI (14)", value=True)
show_macd = st.sidebar.checkbox("MACD (12, 26, 9)", value=True)
show_stochrsi = st.sidebar.checkbox("Stochastic RSI", value=False)
show_willr = st.sidebar.checkbox("Williams %R", value=False)

st.sidebar.markdown("### Volume Analysis")
show_vol_prof = st.sidebar.checkbox("Volume Profile", value=False)
show_obv = st.sidebar.checkbox("OBV", value=False)
show_unusual_vol = st.sidebar.checkbox("Unusual Volume Alert", value=True)

st.sidebar.markdown("### Pattern Detection")
show_sr = st.sidebar.checkbox("Support/Resistance (Swing Highs/Lows)", value=False)
show_patterns = st.sidebar.checkbox("Auto-detect Patterns", value=False)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_technical_data(ticker, period):
    stock = yf.Ticker(ticker)
    return stock.history(period=period)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_info(ticker):
    stock = yf.Ticker(ticker)
    return stock.info

if current_ticker:
    with st.spinner("Analyzing technicals..."):
        try:
            fetch_period = period
            if period in ["1d", "5d", "1mo", "3mo", "6mo"]:
                fetch_period = "1y" # Fetch at least 1 year to calculate 200 SMA
            elif period == "1y":
                fetch_period = "2y"
                
            df_full_cached = fetch_technical_data(current_ticker, fetch_period)
            df_full = df_full_cached.copy() if not df_full_cached.empty else df_full_cached
            
            if not df_full.empty:
                info = fetch_stock_info(current_ticker)
                name = info.get('shortName', info.get('longName', current_ticker))
                website = info.get('website', '')
                logo_html = ""
                if website:
                    domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                    logo_url = f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=128"
                    logo_html = f'<img src="{logo_url}" width="40" height="40" style="margin-left: 15px; border-radius: 5px; vertical-align: middle;" onerror="this.style.display=\'none\'">'
                st.markdown(f"<h2 style='display: flex; align-items: center;'>{name} ({current_ticker}){logo_html}</h2>", unsafe_allow_html=True)
                
                # Apply exchange rate to Price Data (Open, High, Low, Close) so charts show correct currency
                for col in ['Open', 'High', 'Low', 'Close']:
                    df_full[col] = df_full[col] * exchange_rate
                
                # Calculate indicators on full data first
                if show_ema:
                    df_full.ta.ema(length=9, append=True)
                    df_full.ta.ema(length=21, append=True)
                if show_sma:
                    df_full.ta.sma(length=50, append=True)
                    df_full.ta.sma(length=200, append=True)
                if show_bb:
                    df_full.ta.bbands(length=20, std=2, append=True)
                
                if show_rsi:
                    df_full.ta.rsi(length=14, append=True)
                if show_macd:
                    # MACD input uses close price, it scales linearly so we don't strictly need to adjust it
                    df_full.ta.macd(fast=12, slow=26, signal=9, append=True)
                if show_stochrsi:
                    df_full.ta.stochrsi(append=True)
                if show_willr:
                    df_full.ta.willr(append=True)
                
                if show_obv:
                    df_full.ta.obv(append=True)
                    
                df_full['Vol_30SMA'] = df_full['Volume'].rolling(window=30).mean()
                df_full['Unusual_Vol'] = df_full['Volume'] > (2 * df_full['Vol_30SMA'])

                slice_map = {
                    "1d": 1,
                    "5d": 5,
                    "1mo": 21,
                    "3mo": 63,
                    "6mo": 126,
                    "1y": 252,
                    "5y": 1260
                }
                display_rows = slice_map.get(period, len(df_full))
                df = df_full.tail(display_rows).copy()

                subplots = 2 # Main + Volume
                row_heights = [0.6, 0.2]
                    
                active_oscillators = []
                if show_rsi: active_oscillators.append("RSI")
                if show_macd: active_oscillators.append("MACD")
                if show_stochrsi: active_oscillators.append("STOCHRSI")
                if show_willr: active_oscillators.append("WILLR")
                if show_obv: active_oscillators.append("OBV")
                
                subplots += len(active_oscillators)
                row_heights.extend([0.2] * len(active_oscillators))
                
                total_height = sum(row_heights)
                row_heights = [h/total_height for h in row_heights]

                specs = [[{"secondary_y": True}]] + [[{"secondary_y": False}]] * (subplots - 1)
                
                fig = make_subplots(rows=subplots, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.03, row_heights=row_heights,
                                    specs=specs)
                
                # 1. Main Chart
                fig.add_trace(go.Candlestick(x=df.index,
                                             open=df['Open'], high=df['High'],
                                             low=df['Low'], close=df['Close'],
                                             name=f'Price ({currency_label})',
                                             increasing_line_color='#00ff00',
                                             decreasing_line_color='#ff0000'), row=1, col=1)
                
                if show_sr:
                    peaks, _ = find_peaks(df['High'], distance=5)
                    valleys, _ = find_peaks(-df['Low'], distance=5)
                    
                    recent_peaks = df['High'].iloc[peaks].tail(3)
                    recent_valleys = df['Low'].iloc[valleys].tail(3)
                    
                    for p in recent_peaks:
                        fig.add_hline(y=p, line_dash="dash", line_color="rgba(0, 255, 0, 0.5)", row=1, col=1, annotation_text="Res", annotation_position="top left")
                    for v in recent_valleys:
                        fig.add_hline(y=v, line_dash="dash", line_color="rgba(255, 0, 0, 0.5)", row=1, col=1, annotation_text="Sup", annotation_position="bottom left")
                        
                if show_patterns:
                    peaks, _ = find_peaks(df['High'], distance=5)
                    valleys, _ = find_peaks(-df['Low'], distance=5)
                    
                    # Double Top
                    peak_prices = df.iloc[peaks]['High']
                    if len(peak_prices) >= 2:
                        for i in range(1, len(peak_prices)):
                            p1 = peak_prices.iloc[i-1]
                            p2 = peak_prices.iloc[i]
                            if abs(p1 - p2) / p1 < 0.02: 
                                idx1 = peak_prices.index[i-1]
                                idx2 = peak_prices.index[i]
                                trough = df.loc[idx1:idx2]['Low'].min()
                                if trough < min(p1, p2) * 0.95: 
                                    fig.add_annotation(x=idx2, y=p2, text="Double Top", showarrow=True, arrowhead=1, row=1, col=1)
                                    
                    # Double Bottom
                    valley_prices = df.iloc[valleys]['Low']
                    if len(valley_prices) >= 2:
                        for i in range(1, len(valley_prices)):
                            v1 = valley_prices.iloc[i-1]
                            v2 = valley_prices.iloc[i]
                            if abs(v1 - v2) / v1 < 0.02: 
                                idx1 = valley_prices.index[i-1]
                                idx2 = valley_prices.index[i]
                                crest = df.loc[idx1:idx2]['High'].max()
                                if crest > max(v1, v2) * 1.05: 
                                    fig.add_annotation(x=idx2, y=v2, text="Double Bottom", showarrow=True, arrowhead=1, ay=40, row=1, col=1)

                if show_ema:
                    if 'EMA_9' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['EMA_9'], line=dict(color='#33ccff', width=1.5), name='EMA 9'), row=1, col=1)
                    if 'EMA_21' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['EMA_21'], line=dict(color='#ff33cc', width=1.5), name='EMA 21'), row=1, col=1)
                
                if show_sma:
                    if 'SMA_50' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='#ff9900', width=1.5), name='SMA 50'), row=1, col=1)
                    if 'SMA_200' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], line=dict(color='#ffffff', width=2), name='SMA 200'), row=1, col=1)
                    
                    if 'SMA_50' in df.columns and 'SMA_200' in df.columns:
                        cross_up = (df['SMA_50'] > df['SMA_200']) & (df['SMA_50'].shift(1) <= df['SMA_200'].shift(1))
                        cross_down = (df['SMA_50'] < df['SMA_200']) & (df['SMA_50'].shift(1) >= df['SMA_200'].shift(1))
                        
                        golden_crosses = df[cross_up]
                        death_crosses = df[cross_down]
                        
                        for idx, row in golden_crosses.iterrows():
                            fig.add_annotation(x=idx, y=row['SMA_50'], text="Golden Cross", showarrow=True, arrowhead=1, arrowcolor="gold", font=dict(color="gold"), ay=-40, row=1, col=1)
                        for idx, row in death_crosses.iterrows():
                            fig.add_annotation(x=idx, y=row['SMA_50'], text="Death Cross", showarrow=True, arrowhead=1, arrowcolor="red", font=dict(color="red"), ay=40, row=1, col=1)

                if show_bb:
                    upper_bb = [c for c in df.columns if c.startswith('BBU_')][0]
                    lower_bb = [c for c in df.columns if c.startswith('BBL_')][0]
                    mid_bb = [c for c in df.columns if c.startswith('BBM_')][0]
                    fig.add_trace(go.Scatter(x=df.index, y=df[upper_bb], line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dash'), name='Upper BB'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df[lower_bb], line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dash'), name='Lower BB', fill='tonexty', fillcolor='rgba(255, 255, 255, 0.05)'), row=1, col=1)
                    
                if show_vol_prof:
                    min_price = df['Low'].min()
                    max_price = df['High'].max()
                    price_bins = np.linspace(min_price, max_price, 50)
                    
                    df['Price_Bin'] = pd.cut(df['Close'], bins=price_bins)
                    vol_prof = df.groupby('Price_Bin', observed=False)['Volume'].sum()
                    bin_centers = [(b.left + b.right) / 2 for b in vol_prof.index]
                    
                    fig.add_trace(go.Bar(x=vol_prof.values, y=bin_centers, orientation='h', 
                                         name='Volume Profile', marker_color='rgba(100, 150, 250, 0.2)', 
                                         hoverinfo='skip', showlegend=False), row=1, col=1, secondary_y=True)

                colors = ['#00ff00' if row['Close'] >= row['Open'] else '#ff0000' for idx, row in df.iterrows()]
                fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='Volume'), row=2, col=1)
                
                if show_unusual_vol:
                    unusual = df[df['Unusual_Vol']]
                    fig.add_trace(go.Scatter(x=unusual.index, y=unusual['Volume'], mode='markers', 
                                             marker=dict(symbol='triangle-up', size=10, color='yellow'), 
                                             name='Unusual Volume'), row=2, col=1)

                current_row = 3
                for osc in active_oscillators:
                    if osc == "RSI":
                        rsi_col = [c for c in df.columns if c.startswith('RSI_')][0]
                        fig.add_trace(go.Scatter(x=df.index, y=df[rsi_col], line=dict(color='#ffff00', width=1.5), name='RSI'), row=current_row, col=1)
                        fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,0,0,0.5)", row=current_row, col=1)
                        fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,255,0,0.5)", row=current_row, col=1)
                        fig.add_hrect(y0=70, y1=100, fillcolor="red", opacity=0.1, layer="below", row=current_row, col=1)
                        fig.add_hrect(y0=0, y1=30, fillcolor="green", opacity=0.1, layer="below", row=current_row, col=1)
                        fig.update_yaxes(range=[0, 100], row=current_row, col=1)
                        
                    elif osc == "MACD":
                        macd_line = [c for c in df.columns if c.startswith('MACD_')][0]
                        macds_line = [c for c in df.columns if c.startswith('MACDs_')][0]
                        macdh_line = [c for c in df.columns if c.startswith('MACDh_')][0]
                        
                        macd_colors = ['#00ff00' if val >= 0 else '#ff0000' for val in df[macdh_line]]
                        fig.add_trace(go.Scatter(x=df.index, y=df[macd_line], line=dict(color='#00bfff'), name='MACD'), row=current_row, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df[macds_line], line=dict(color='#ff9900'), name='Signal'), row=current_row, col=1)
                        fig.add_trace(go.Bar(x=df.index, y=df[macdh_line], marker_color=macd_colors, name='MACD Hist'), row=current_row, col=1)
                        
                    elif osc == "STOCHRSI":
                        stochk = [c for c in df.columns if c.startswith('STOCHRSIk_')][0]
                        stochd = [c for c in df.columns if c.startswith('STOCHRSId_')][0]
                        fig.add_trace(go.Scatter(x=df.index, y=df[stochk], line=dict(color='#00bfff'), name='%K'), row=current_row, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df[stochd], line=dict(color='#ff9900'), name='%D'), row=current_row, col=1)
                        fig.add_hline(y=80, line_dash="dash", line_color="rgba(255,0,0,0.5)", row=current_row, col=1)
                        fig.add_hline(y=20, line_dash="dash", line_color="rgba(0,255,0,0.5)", row=current_row, col=1)
                        fig.update_yaxes(range=[0, 100], row=current_row, col=1)
                        
                    elif osc == "WILLR":
                        willr = [c for c in df.columns if c.startswith('WILLR_')][0]
                        fig.add_trace(go.Scatter(x=df.index, y=df[willr], line=dict(color='#ff33cc'), name='Will %R'), row=current_row, col=1)
                        fig.add_hline(y=-20, line_dash="dash", line_color="rgba(255,0,0,0.5)", row=current_row, col=1)
                        fig.add_hline(y=-80, line_dash="dash", line_color="rgba(0,255,0,0.5)", row=current_row, col=1)

                    elif osc == "OBV":
                        obv = [c for c in df.columns if c.startswith('OBV')][0]
                        fig.add_trace(go.Scatter(x=df.index, y=df[obv], line=dict(color='#ffffff'), name='OBV'), row=current_row, col=1)
                    
                    current_row += 1

                fig.update_layout(
                    template="plotly_dark",
                    xaxis_rangeslider_visible=False,
                    height=600 + (len(active_oscillators) * 150),
                    margin=dict(l=20, r=20, t=40, b=20),
                    paper_bgcolor="#111111", 
                    plot_bgcolor="#111111",
                    hovermode="x unified",
                    showlegend=False,
                    dragmode="zoom"
                )
                
                fig.update_yaxes(title_text=f"Price ({currency_label})", row=1, col=1, secondary_y=False)
                if show_vol_prof:
                    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, secondary_y=True, row=1, col=1, range=[0, vol_prof.max() * 3])
                
                fig.update_yaxes(title_text="Volume", row=2, col=1)
                for i, osc in enumerate(active_oscillators):
                    fig.update_yaxes(title_text=osc, row=3+i, col=1)
                    
                for i in range(1, subplots):
                    fig.update_xaxes(showticklabels=False, row=i, col=1)
                
                fig.update_xaxes(
                    rangebreaks=[
                        dict(bounds=["sat", "mon"])
                    ]
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Insights Section
                st.markdown("### 📊 Automated Insights")
                cols = st.columns(4)
                with cols[0]:
                    if show_rsi:
                        current_rsi = df[rsi_col].iloc[-1]
                        rsi_status = "Overbought" if current_rsi > 70 else "Oversold" if current_rsi < 30 else "Neutral"
                        st.metric("RSI (14)", f"{current_rsi:.2f}", rsi_status, delta_color="inverse" if rsi_status == "Overbought" else "normal")
                    else:
                        st.metric("RSI (14)", "N/A", "Enable RSI")
                with cols[1]:
                    if show_macd:
                        current_macd = df[macdh_line].iloc[-1]
                        macd_status = "Bullish" if current_macd > 0 else "Bearish"
                        st.metric("MACD Histogram", f"{current_macd:.2f}", macd_status)
                    else:
                        st.metric("MACD Histogram", "N/A", "Enable MACD")
                with cols[2]:
                    if show_sma:
                        if 'SMA_50' in df.columns and 'SMA_200' in df.columns:
                            trend = "Bullish" if df['SMA_50'].iloc[-1] > df['SMA_200'].iloc[-1] else "Bearish"
                            st.metric("Long Term Trend", trend, "SMA 50 > 200" if trend == "Bullish" else "SMA 50 < 200")
                    else:
                        st.metric("Long Term Trend", "N/A", "Enable SMA")
                with cols[3]:
                    current_price = df['Close'].iloc[-1]
                    prev_price = df['Close'].iloc[-2]
                    pct_change = (current_price - prev_price) / prev_price * 100
                    st.metric("Current Price", utils.format_currency(current_price, currency_label), f"{pct_change:.2f}%")

            else:
                st.warning("No data found for this ticker and period.")
        except Exception as e:
            st.error(f"Error analyzing technical data: {e}")

# --- FOOTER ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>Data: Yahoo Finance | Built for Educational Purposes Only</p>", unsafe_allow_html=True)
