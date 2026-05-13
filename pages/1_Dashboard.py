import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import time

st.title("📊 Intelligent Market Dashboard")

# Ticker Selection
ticker_symbol = st.text_input("Enter Primary Ticker", value="SPY").upper()

if ticker_symbol:
    with st.spinner(f"Fetching data for {ticker_symbol}..."):
        try:
            stock = yf.Ticker(ticker_symbol)
            info = stock.info
            
            # Fetch 1-day 1-minute data for VWAP
            intraday = stock.history(period="1d", interval="1m")
            
            # --- PRICE PANEL ---
            st.markdown("### 📈 Price Panel")
            col1, col2, col3 = st.columns(3)
            
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
            prev_close = info.get('previousClose', current_price)
            change = current_price - prev_close
            pct_change = (change / prev_close) * 100 if prev_close else 0
            
            with col1:
                st.metric("Current Price", f"${current_price:,.2f}", f"{change:+.2f} ({pct_change:+.2f}%)")
                
                # Pre/After Hours
                pre_market = info.get('preMarketPrice')
                post_market = info.get('postMarketPrice')
                if pre_market:
                    st.caption(f"Pre-Market: ${pre_market:,.2f}")
                if post_market:
                    st.caption(f"After-Hours: ${post_market:,.2f}")
                    
            with col2:
                bid = info.get('bid', 0)
                ask = info.get('ask', 0)
                if bid and ask:
                    st.metric("Bid / Ask Spread", f"${bid:,.2f} / ${ask:,.2f}", f"Spread: ${ask - bid:,.2f}", delta_color="off")
                else:
                    st.metric("Bid / Ask Spread", "N/A")
                
            with col3:
                # VWAP Calculation
                if not intraday.empty and 'Volume' in intraday.columns:
                    # Calculate typical price
                    intraday['Typical_Price'] = (intraday['High'] + intraday['Low'] + intraday['Close']) / 3
                    
                    # Prevent division by zero
                    cum_vol = intraday['Volume'].cumsum()
                    valid_mask = cum_vol > 0
                    
                    if valid_mask.any():
                        intraday['VWAP'] = (intraday['Typical_Price'] * intraday['Volume']).cumsum() / cum_vol
                        # Forward fill any NaNs at the beginning if volume was 0
                        intraday['VWAP'] = intraday['VWAP'].ffill()
                        vwap = intraday['VWAP'].iloc[-1]
                        st.metric("VWAP (Intraday)", f"${vwap:,.2f}")
                    else:
                        st.metric("VWAP (Intraday)", "N/A (No Volume)")
                else:
                    st.metric("VWAP", "N/A")

            # Day Range Slider
            day_low = info.get('dayLow', intraday['Low'].min() if not intraday.empty else current_price)
            day_high = info.get('dayHigh', intraday['High'].max() if not intraday.empty else current_price)
            
            if day_low and day_high and (day_high > day_low):
                range_pct = (current_price - day_low) / (day_high - day_low)
                st.write(f"**Day Range:** ${day_low:,.2f} --------------------------------------------- ${day_high:,.2f}")
                st.progress(min(max(range_pct, 0.0), 1.0))
            
            st.divider()
            
            # --- ANALYST METRICS CARDS ---
            st.markdown("### 📊 Analyst Metrics")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            
            with m_col1:
                high_52 = info.get('fiftyTwoWeekHigh', 0)
                low_52 = info.get('fiftyTwoWeekLow', 0)
                if high_52:
                    st.metric("vs 52-Week High", f"${high_52:,.2f}", f"{((current_price / high_52) - 1) * 100:+.2f}%")
                else:
                    st.metric("vs 52-Week High", "N/A")
                if low_52:
                    st.metric("vs 52-Week Low", f"${low_52:,.2f}", f"{((current_price / low_52) - 1) * 100:+.2f}%")
                else:
                    st.metric("vs 52-Week Low", "N/A")
                
            with m_col2:
                # Relative Strength vs SPY (1 Month)
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
                st.metric("Average Volume", f"{avg_vol:,}")
                
            with m_col4:
                short_pct = info.get('shortPercentOfFloat', 0)
                if short_pct is not None:
                    short_pct *= 100
                dtc = info.get('shortRatio', 0)
                st.metric("Short Float %", f"{short_pct:.2f}%" if short_pct else "N/A")
                st.metric("Days to Cover", f"{dtc:.2f}" if dtc else "N/A")

            st.divider()
            
            # --- MARKET BREADTH PANEL ---
            st.markdown("### 🌐 Market Breadth (Top S&P Components)")
            
            # Use top 20 components for speed
            top_sp_tickers = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'BRK-B', 'TSLA', 'UNH', 
                              'JNJ', 'JPM', 'V', 'PG', 'MA', 'AVGO', 'HD', 'CVX', 'MRK', 'PEP']
            
            @st.cache_data(ttl=60)
            def get_breadth():
                try:
                    data = yf.download(top_sp_tickers, period="3mo", progress=False)['Close']
                    if data.empty: return 0, 0, 0
                    
                    # Advance/Decline for today
                    today_ret = data.iloc[-1] / data.iloc[-2] - 1
                    advances = (today_ret > 0).sum()
                    declines = (today_ret < 0).sum()
                    
                    # % above 50-day MA
                    ma_50 = data.rolling(window=50).mean().iloc[-1]
                    above_50 = (data.iloc[-1] > ma_50).sum()
                    pct_above_50 = (above_50 / len(top_sp_tickers)) * 100
                    
                    return advances, declines, pct_above_50
                except:
                    return 0, 0, 0
                
            adv, dec, pct_above_50 = get_breadth()
            
            b_col1, b_col2, b_col3 = st.columns(3)
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
                        st.metric(row['Index'], f"{row['Price']:,.2f}", f"{row['Change']:+.2f} ({row['% Change']:+.2f}%)", delta_color=delta_c)

        except Exception as e:
            st.error(f"Error fetching data: {str(e)}")

# Auto-refresh every 60 seconds
time.sleep(60)
st.rerun()
