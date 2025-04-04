import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from tradingview_ta import TA_Handler, Interval
import time

# --- App Configuration ---
st.set_page_config(
    page_title="Marks FX Academy Trading Analysis",
    page_icon="📊",
    layout="wide"
)

# --- Configuration ---
TARGET_PAIRS = {
    'XAUUSD': {'symbol': 'XAUUSD', 'exchange': 'FX', 'screener': 'cfd', 'pip_value': 0.01},
    'AUDJPY': {'symbol': 'AUDJPY', 'exchange': 'FX', 'screener': 'forex', 'pip_value': 0.01},
    'GBPJPY': {'symbol': 'GBPJPY', 'exchange': 'FX', 'screener': 'forex', 'pip_value': 0.01},
    'SPX500': {'symbol': 'SPX', 'exchange': 'SP', 'screener': 'cfd', 'pip_value': 0.1},
    'USDJPY': {'symbol': 'USDJPY', 'exchange': 'FX', 'screener': 'forex', 'pip_value': 0.01}
}

TIMEFRAMES = {
    'DAILY': Interval.INTERVAL_1_DAY,
    '4H': Interval.INTERVAL_4_HOURS,
    '1H': Interval.INTERVAL_1_HOUR,
    '15M': Interval.INTERVAL_15_MINUTES
}

TRADE_CONFIG = {
    'RISK_REWARD_RATIOS': [1.5, 2.0, 3.0],
    'MAX_RISK_PERCENT': 1.0,
    'MIN_PIPS': {
        'XAUUSD': 50,
        'AUDJPY': 30,
        'GBPJPY': 40,
        'SPX500': 10,
        'USDJPY': 20
    },
    'FIB_LEVELS': [0.236, 0.382, 0.5, 0.618, 0.786, 0.886],
    'MIN_ATR_MULTIPLIER': 1.5
}

# --- App UI ---
st.title("📊 Marks FX Academy Trading Analysis")
st.markdown("""
    Real-time trading signals for major currency pairs and commodities.
    Analysis includes entry points, stop losses, and take profit levels.
""")

# Add sidebar controls
with st.sidebar:
    st.header("Configuration")
    auto_refresh = st.checkbox("Auto-refresh every 5 minutes", True)
    selected_pairs = st.multiselect(
        "Select pairs to analyze",
        list(TARGET_PAIRS.keys()),
        default=list(TARGET_PAIRS.keys())
    )
    risk_level = st.slider("Risk Level (%)", 0.5, 5.0, 1.0, step=0.5)

# --- Core Functions (Same as original) ---
def get_tradingview_data(symbol_config, interval):
    """Fetch data from TradingView with robust error handling"""
    try:
        handler = TA_Handler(
            symbol=symbol_config['symbol'],
            exchange=symbol_config['exchange'],
            screener=symbol_config['screener'],
            interval=interval,
            timeout=10
        )
        analysis = handler.get_analysis()

        if not analysis or not hasattr(analysis, 'indicators'):
            st.error(f"No analysis data returned for {symbol_config['symbol']} ({interval})")
            return None

        # Convert indicators to dictionary format
        indicators = analysis.indicators

        # Calculate ATR if not available
        if 'ATR' not in indicators:
            if 'high' in indicators and 'low' in indicators and 'close' in indicators:
                # Simple ATR calculation (1 period)
                tr = max(
                    indicators['high'] - indicators['low'],
                    abs(indicators['high'] - indicators['close']),
                    abs(indicators['low'] - indicators['close'])
                )
                indicators['ATR'] = tr
            else:
                indicators['ATR'] = (indicators['high'] - indicators['low']) * 0.5

        # Ensure we have all required data points
        required = ['close', 'high', 'low', 'open', 'RSI']
        for indicator in required:
            if indicator not in indicators:
                st.warning(f"Missing {indicator} in analysis for {symbol_config['symbol']}")
                return None

        return {'indicators': indicators, 'summary': analysis.summary}
    except Exception as e:
        st.error(f"Error fetching {symbol_config['symbol']} ({interval}): {str(e)}")
        return None

# [Keep all your other original functions exactly as they are:
# identify_market_structure(), find_liquidity_zones(), 
# calculate_trade_levels(), get_multi_timeframe_data(),
# analyze_pair() - but change print() to st.warning()/st.error()]

# --- Modified run_analysis() for Streamlit ---
def run_analysis():
    """Main analysis function adapted for Streamlit"""
    st.subheader("Latest Market Analysis")
    st.write(f"Last updated: {datetime.now(pytz.timezone('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not selected_pairs:
        st.warning("Please select at least one pair to analyze")
        return

    with st.spinner("Running analysis... This may take a minute"):
        results = []
        for pair_name in selected_pairs:
            pair_config = TARGET_PAIRS[pair_name]
            result = analyze_pair(pair_name, pair_config)
            if result:
                results.append(result)
            time.sleep(1)  # Rate limiting

        if results:
            # Display summary table
            st.success("Analysis complete! Found trade setups")
            
            # Create DataFrame for display
            df_data = []
            for r in results:
                df_data.append({
                    'Pair': r['pair'],
                    'Price': r['price'],
                    'Trend': r['trend'],
                    'Entry': r['entry'],
                    'Stop Loss': r['stop_loss'],
                    'Risk (pips)': abs(r['entry'] - r['stop_loss']) / r['pip_value'],
                    'TP1': r['take_profit'][0],
                    'TP2': r['take_profit'][1],
                    'TP3': r['take_profit'][2],
                    'RSI': r['rsi'],
                    'ATR': r['atr']
                })
            
            df = pd.DataFrame(df_data)
            
            # Format the DataFrame display
            styler = df.style.format({
                'Price': '{:.2f}',
                'Entry': '{:.2f}',
                'Stop Loss': '{:.2f}',
                'TP1': '{:.2f}',
                'TP2': '{:.2f}',
                'TP3': '{:.2f}',
                'RSI': '{:.1f}' if pd.notna(df['RSI']) else 'N/A',
                'ATR': '{:.2f}',
                'Risk (pips)': '{:.1f}'
            }).applymap(lambda x: 'color: green' if isinstance(x, str) and x == 'BULLISH' else 
                       'color: red' if isinstance(x, str) and x == 'BEARISH' else '', 
                       subset=['Trend'])
            
            st.dataframe(styler, use_container_width=True)
            
            # Detailed view
            st.subheader("Detailed Trade Setups")
            for r in results:
                with st.expander(f"{r['pair']} ({r['trend']}) - Current Price: {r['price']:.2f}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Entry", f"{r['entry']:.2f}")
                        st.metric("Stop Loss", f"{r['stop_loss']:.2f}", 
                                 delta=f"{(r['stop_loss']-r['entry']):.2f}")
                    with col2:
                        st.metric("Take Profit 1", f"{r['take_profit'][0]:.2f}")
                        st.metric("Take Profit 2", f"{r['take_profit'][1]:.2f}")
                        st.metric("Take Profit 3", f"{r['take_profit'][2]:.2f}")
                    
                    st.write(f"**RSI:** {r['rsi']:.1f if r['rsi'] is not None else 'N/A'} | "
                            f"**ATR:** {r['atr']:.2f} | "
                            f"**Risk:** {abs(r['entry'] - r['stop_loss'])/r['pip_value']:.1f} pips")
        else:
            st.warning("No valid trade setups found for selected pairs")

# --- Run the app ---
if __name__ == "__main__":
    run_analysis()
    if auto_refresh:
        time.sleep(300)  # 5 minutes
        st.experimental_rerun()
