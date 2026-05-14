import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
import importlib

# Ensure utils can be imported
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import utils

# Render global UI and Search
current_ticker, currency_label, exchange_rate = utils.setup_page_ui()

st.title("🏦 Fundamentals & Equity Research")

# --- HELPER FUNCTIONS ---
def color_metric(val, benchmark, lower_is_better=True):
    if pd.isna(val) or pd.isna(benchmark):
        return "gray"
    if lower_is_better:
        return "green" if val < benchmark else "red"
    else:
        return "green" if val > benchmark else "red"

if current_ticker:
    with st.spinner(f"Fetching full research report for {current_ticker}..."):
        try:
            session = utils.get_yf_session()
            stock = yf.Ticker(current_ticker, session=session)
            info = stock.info
            
            # Add a header with current price and company name
            name = info.get('shortName', info.get('longName', current_ticker))
            website = info.get('website', '')
            logo_html = ""
            if website:
                domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
                logo_url = f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=128"
                logo_html = f'<img src="{logo_url}" width="40" height="40" style="margin-left: 15px; border-radius: 5px; vertical-align: middle;" onerror="this.style.display=\'none\'">'
            st.markdown(f"<h2 style='display: flex; align-items: center;'>{name} ({current_ticker}){logo_html}</h2>", unsafe_allow_html=True)
            
            market_cap_str = utils.format_large_currency(info.get('marketCap', 0) * exchange_rate, currency_label)
            st.markdown(f"**Sector:** {info.get('sector', 'N/A')} | **Industry:** {info.get('industry', 'N/A')} | **Market Cap:** {market_cap_str}")
            st.markdown("---")
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📊 Valuation Ratios")
                sector_pe_avg = info.get('industryPE', info.get('sectorPE', 20.0)) 
                if pd.isna(sector_pe_avg): sector_pe_avg = 20.0
                
                benchmarks = {
                    "P/E (TTM)": sector_pe_avg,
                    "Forward P/E": sector_pe_avg * 0.9,
                    "PEG Ratio": 1.5,
                    "P/B Ratio": 3.0,
                    "P/S Ratio": 2.5,
                    "EV/EBITDA": 12.0
                }
                
                vals = {
                    "P/E (TTM)": info.get("trailingPE"),
                    "Forward P/E": info.get("forwardPE"),
                    "PEG Ratio": info.get("pegRatio"),
                    "P/B Ratio": info.get("priceToBook"),
                    "P/S Ratio": info.get("priceToSalesTrailing12Months"),
                    "EV/EBITDA": info.get("enterpriseToEbitda")
                }
                
                table_html = """
                <table style="width:100%; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #444;">
                        <th style="text-align:left; padding:8px;">Metric</th>
                        <th style="text-align:right; padding:8px;">Value</th>
                        <th style="text-align:right; padding:8px;">Sector Avg</th>
                    </tr>
                """
                for metric, val in vals.items():
                    bench = benchmarks[metric]
                    if val is None or pd.isna(val):
                        val_str = "N/A"
                        color = "white"
                    else:
                        val_str = f"{val:.2f}"
                        color = "#00ff00" if val < bench else "#ff4444"
                        
                    table_html += f"""
                    <tr style="border-bottom: 1px solid #333;">
                        <td style="padding:8px;">{metric}</td>
                        <td style="text-align:right; padding:8px; color:{color}; font-weight:bold;">{val_str}</td>
                        <td style="text-align:right; padding:8px; color:#aaa;">{bench:.2f}</td>
                    </tr>
                    """
                table_html += "</table>"
                st.markdown(table_html, unsafe_allow_html=True)
                
            with col2:
                st.subheader("🛡️ Financial Health Scorecard")
                
                try:
                    inc = stock.income_stmt
                    bs = stock.balance_sheet
                    cf = stock.cashflow
                except:
                    inc = pd.DataFrame()
                    bs = pd.DataFrame()
                    cf = pd.DataFrame()

                score = 0
                max_score = 100
                
                prof_score = 0
                gm = info.get("grossMargins", 0)
                nm = info.get("profitMargins", 0)
                roe = info.get("returnOnEquity", 0)
                
                if gm and gm > 0.4: prof_score += 8
                elif gm and gm > 0.2: prof_score += 4
                
                if nm and nm > 0.15: prof_score += 9
                elif nm and nm > 0.05: prof_score += 4
                
                if roe and roe > 0.15: prof_score += 8
                elif roe and roe > 0.08: prof_score += 4
                
                growth_score = 0
                rev_g = info.get("revenueGrowth", 0)
                eps_g = info.get("earningsGrowth", 0)
                
                if rev_g and rev_g > 0.1: growth_score += 10
                elif rev_g and rev_g > 0.0: growth_score += 5
                
                if eps_g and eps_g > 0.1: growth_score += 15
                elif eps_g and eps_g > 0.0: growth_score += 7
                
                safe_score = 0
                de = info.get("debtToEquity", 100)
                cr = info.get("currentRatio", 0)
                
                if de and de < 50: safe_score += 12
                elif de and de < 100: safe_score += 6
                
                if cr and cr > 1.5: safe_score += 13
                elif cr and cr > 1.0: safe_score += 6
                
                mom_score = 0
                ret_1y = info.get("52WeekChange", 0)
                spy_1y = info.get("SandP52WeekChange", 0)
                
                if ret_1y and spy_1y and ret_1y > spy_1y: mom_score += 25
                elif ret_1y and ret_1y > 0: mom_score += 10
                
                total_score = prof_score + growth_score + safe_score + mom_score
                
                score_color = "green" if total_score >= 70 else "orange" if total_score >= 40 else "red"
                st.markdown(f"<h1 style='text-align: center; color: {score_color}; font-size: 4rem; margin-bottom: 0;'>{total_score}/100</h1>", unsafe_allow_html=True)
                
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=[prof_score*4, growth_score*4, safe_score*4, mom_score*4],
                    theta=['Profitability', 'Growth', 'Safety', 'Momentum'],
                    fill='toself',
                    fillcolor=f'rgba(0, 255, 0, 0.2)' if total_score >=70 else 'rgba(255, 165, 0, 0.2)' if total_score >=40 else 'rgba(255, 0, 0, 0.2)',
                    line_color=score_color
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=False,
                    height=250,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            
            # --- ROW 2: EARNINGS & CONSENSUS ---
            col3, col4 = st.columns([1, 1])
            
            with col3:
                st.subheader("📅 Earnings Analysis")
                try:
                    earnings_history = stock.get_earnings_dates(limit=8)
                    if earnings_history is not None and not earnings_history.empty:
                        past_earnings = earnings_history.dropna(subset=['Reported EPS', 'EPS Estimate'])
                        if not past_earnings.empty:
                            past_earnings = past_earnings.sort_index().tail(8)
                            
                            beats = (past_earnings['Reported EPS'] > past_earnings['EPS Estimate']).sum()
                            total = len(past_earnings)
                            st.markdown(f"**Beat/Miss Streak:** Beat **{beats}** out of the last **{total}** quarters.")
                            
                            fig_earn = go.Figure()
                            # EPS values can technically be converted by exchange_rate too!
                            fig_earn.add_trace(go.Bar(x=past_earnings.index.strftime('%Y-%m-%d'), y=past_earnings['EPS Estimate'] * exchange_rate, name=f'Estimate ({currency_label})', marker_color='gray'))
                            fig_earn.add_trace(go.Bar(x=past_earnings.index.strftime('%Y-%m-%d'), y=past_earnings['Reported EPS'] * exchange_rate, name=f'Actual ({currency_label})', marker_color='#00ff00'))
                            
                            fig_earn.update_layout(
                                barmode='group',
                                template='plotly_dark',
                                height=300,
                                margin=dict(l=0, r=0, t=10, b=0),
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)"
                            )
                            st.plotly_chart(fig_earn, use_container_width=True)
                        else:
                            st.info("No reported EPS history found.")
                    else:
                        st.info("Earnings data not available.")
                        
                    if 'nextEarningsDate' in info:
                        st.markdown(f"**Next Earnings Date:** {info['nextEarningsDate']}")
                except Exception as e:
                    st.warning(f"Could not load earnings data: {e}")

            with col4:
                st.subheader("🎯 Analyst Consensus")
                try:
                    recs = stock.recommendations
                    if recs is not None and not recs.empty:
                        if 'period' in recs.columns:
                            latest_recs = recs[recs['period'] == '0m'].iloc[0]
                        else:
                            latest_recs = recs.iloc[-1]
                            
                        sb = latest_recs.get('strongBuy', 0)
                        b = latest_recs.get('buy', 0)
                        h = latest_recs.get('hold', 0)
                        s = latest_recs.get('sell', 0)
                        ss = latest_recs.get('strongSell', 0)
                        
                        fig_rec = go.Figure(data=[go.Pie(
                            labels=['Strong Buy', 'Buy', 'Hold', 'Sell', 'Strong Sell'],
                            values=[sb, b, h, s, ss],
                            hole=.4,
                            marker_colors=['#00ff00', '#99ff99', '#aaaaaa', '#ff9999', '#ff0000']
                        )])
                        fig_rec.update_layout(
                            height=300,
                            margin=dict(l=0, r=0, t=10, b=0),
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            showlegend=True
                        )
                        st.plotly_chart(fig_rec, use_container_width=True)
                    else:
                        st.info("Analyst recommendations not available.")
                        
                    curr_price = info.get('currentPrice', info.get('regularMarketPrice'))
                    target_mean = info.get('targetMeanPrice')
                    if curr_price and target_mean:
                        upside = ((target_mean - curr_price) / curr_price) * 100
                        up_color = "green" if upside > 0 else "red"
                        
                        st.markdown(f"**Current Price:** {utils.format_currency(curr_price * exchange_rate, currency_label)}")
                        st.markdown(f"**Average Target:** {utils.format_currency(target_mean * exchange_rate, currency_label)}")
                        st.markdown(f"**Implied Upside:** <span style='color:{up_color}; font-weight:bold;'>{upside:.2f}%</span>", unsafe_allow_html=True)
                        
                except Exception as e:
                    st.warning(f"Could not load analyst data: {e}")

            st.markdown("---")
            
            # --- ROW 3: DCF VALUATION CALCULATOR ---
            st.subheader("🧮 DCF Valuation Calculator")
            st.markdown("Interactive Discounted Cash Flow model to estimate intrinsic value.")
            
            try:
                fcf_ttm = info.get('freeCashflow')
                if not fcf_ttm and not cf.empty:
                    try:
                        ocf = cf.loc['Operating Cash Flow'].iloc[0]
                        capex = cf.loc['Capital Expenditure'].iloc[0]
                        fcf_ttm = ocf + capex 
                    except:
                        pass
            except:
                fcf_ttm = None

            shares_out = info.get('sharesOutstanding')
            curr_price = info.get('currentPrice', info.get('regularMarketPrice'))
            
            if fcf_ttm and shares_out and curr_price:
                col_dcf1, col_dcf2, col_dcf3 = st.columns([1, 1, 2])
                
                with col_dcf1:
                    st.markdown("**Model Inputs**")
                    eps_g = info.get('earningsGrowth', 0.1)
                    if pd.isna(eps_g): eps_g = 0.1
                    
                    growth_rate = st.number_input("Growth Rate (Yrs 1-5) %", value=float(eps_g*100), step=1.0) / 100.0
                    discount_rate = st.number_input("Discount Rate (WACC) %", value=9.0, step=0.5) / 100.0
                    term_growth = st.number_input("Terminal Growth Rate %", value=2.5, step=0.1) / 100.0
                    
                with col_dcf2:
                    st.markdown("**Company Data**")
                    st.write(f"**FCF (TTM):** {utils.format_large_currency(fcf_ttm * exchange_rate, currency_label)}")
                    st.write(f"**Shares Out:** {utils.format_large_currency(shares_out, 'USD ($)').replace('$', '')} shares")
                    st.write(f"**Current Price:** {utils.format_currency(curr_price * exchange_rate, currency_label)}")
                    
                with col_dcf3:
                    future_fcf = []
                    current_fcf = fcf_ttm
                    for i in range(1, 6):
                        current_fcf *= (1 + growth_rate)
                        future_fcf.append(current_fcf)
                        
                    tv = (future_fcf[-1] * (1 + term_growth)) / (discount_rate - term_growth)
                    
                    pv_fcf = sum([f / ((1 + discount_rate)**i) for i, f in enumerate(future_fcf, 1)])
                    pv_tv = tv / ((1 + discount_rate)**5)
                    
                    intrinsic_value_eq = pv_fcf + pv_tv
                    intrinsic_value_per_share = intrinsic_value_eq / shares_out
                    
                    margin_of_safety = ((intrinsic_value_per_share - curr_price) / intrinsic_value_per_share) * 100
                    
                    st.markdown("**Valuation Output**")
                    st.metric("Intrinsic Value per Share", utils.format_currency(intrinsic_value_per_share * exchange_rate, currency_label))
                    
                    mos_color = "green" if margin_of_safety > 0 else "red"
                    st.markdown(f"**Margin of Safety:** <span style='color:{mos_color}; font-size:1.5rem; font-weight:bold;'>{margin_of_safety:.2f}%</span>", unsafe_allow_html=True)
                    
                    if margin_of_safety > 15:
                        signal = "STRONG BUY"
                        sig_color = "#00ff00"
                    elif margin_of_safety > 0:
                        signal = "BUY"
                        sig_color = "#99ff99"
                    elif margin_of_safety > -15:
                        signal = "HOLD"
                        sig_color = "#aaaaaa"
                    else:
                        signal = "SELL"
                        sig_color = "#ff4444"
                        
                    st.markdown(f"**DCF Signal:** <span style='color:{sig_color}; font-weight:bold;'>{signal}</span>", unsafe_allow_html=True)
            else:
                st.info("Sufficient data (FCF, Shares Outstanding, or Price) not available for DCF calculation.")
                
            st.markdown("---")
            st.subheader(f"Raw Financial Statements ({currency_label})")
            tab1, tab2, tab3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])
            
            with tab1:
                try:
                    if not inc.empty:
                        # Multiply raw financials by exchange rate
                        inc_conv = inc * exchange_rate
                        st.dataframe(inc_conv.map(lambda x: f"{x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x), use_container_width=True)
                    else:
                        st.write("Not available")
                except: st.write("Error loading")
            with tab2:
                try:
                    if not bs.empty:
                        bs_conv = bs * exchange_rate
                        st.dataframe(bs_conv.map(lambda x: f"{x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x), use_container_width=True)
                    else:
                        st.write("Not available")
                except: st.write("Error loading")
            with tab3:
                try:
                    if not cf.empty:
                        cf_conv = cf * exchange_rate
                        st.dataframe(cf_conv.map(lambda x: f"{x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x), use_container_width=True)
                    else:
                        st.write("Not available")
                except: st.write("Error loading")
                
        except Exception as e:
            st.error(f"Error fetching fundamentals for {current_ticker}: {e}")

# --- FOOTER ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>Data: Yahoo Finance | Built for Educational Purposes Only</p>", unsafe_allow_html=True)
