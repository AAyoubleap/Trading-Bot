import MetaTrader5 as mt5
import ta
import pandas as pd
import time
import logging
import datetime

def get_realtime_data(symbol, timeframe, num_ticks):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_ticks)
    if rates is None or len(rates) == 0:
        return None  # Return None if there's no data
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

# Function to calculate EMA
def calculate_ema(data, period):
    ema = ta.trend.ema_indicator(data['close'], window=period)
    return ema

# Function to calculate RSI
def calculate_rsi(data, period=14):
    rsi = ta.momentum.RSIIndicator(data['close'], window=period)
    return rsi.rsi()

def calculate_stochastic(df,  k_period=14, d_period=3):
    df['%K'] = ta.momentum.stoch(df['high'], df['low'], df['close'])
    df['%D'] = df['%K'].rolling(window=d_period).mean()
    K = df['%K'].iloc[-1]
    D = df['%D'].iloc[-1]
    return K, D
    
def calculate_macd(df, short_period=12, long_period=26, signal_period=9):
    df['MACD'] = ta.trend.MACD(df['close']).macd()
    df['Signal_Line'] = ta.trend.MACD(df['close']).macd_signal()
    macd = df['MACD'].iloc[-1]
    signal_line = df['Signal_Line'].iloc[-1]
    return macd, signal_line

# Function to execute trades based on the strategy
def execute_strategy(symbol, sl, tp, data, ma1_period=14, ma2_period=21, ma3_period=50,
                    lot=0.05, comment="Trade 2", magic=12345):
        
    price = data['close'].iloc[-1]

    # Calculate moving averages
    ma1 = calculate_ema(data, ma1_period).iloc[-1]
    ma2 = calculate_ema(data, ma2_period).iloc[-1]
    ma3 = calculate_ema(data, ma3_period).iloc[-1]

    # Calculate RSI
    rsi = calculate_rsi(data).iloc[-1]

    # Define trading conditions
    buy_condition = ma1 > ma2 and ma2 > ma3 and rsi > 52
    sell_condition = ma1 < ma2 and ma2 < ma3 and rsi < 48

    # Connect to MT5 and execute trades
    mt5.initialize()
    if buy_condition:
        sl_buy_price = price - sl * mt5.symbol_info(symbol).point * 10
        tp_buy_price = price + tp * mt5.symbol_info(symbol).point * 10
        # Place the buy order with stop loss
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY,
            "sl": sl_buy_price,
            "tp": tp_buy_price,
            "deviation": 10,
            "magic": magic,
            "comment": comment,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            status_message = "Buy order placed successfully."
        else:
            status_message = f"Failed to place buy order. Error: {result.comment}"
    elif sell_condition:
        sl_sell_price = price + sl * mt5.symbol_info(symbol).point * 10
        tp_sell_price = price - tp * mt5.symbol_info(symbol).point * 10
        request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": lot,
                    "type": mt5.ORDER_TYPE_SELL,
                    "sl": sl_sell_price ,  # Set the stop loss price
                    "tp": tp_sell_price,
                    "deviation": 10,
                    "magic": magic,
                    "comment": comment,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                    "type_time": mt5.ORDER_TIME_GTC
                }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            status_message = "Sell order placed successfully."
        else:
            status_message = f"Failed to place sell order. Error: {result.comment}"
    else:
        status_message = 'Waiting for signal!'
        
    return status_message

def triple_threat_trading(price_data, symbol, lot, sl, tp, magic=123000, comment='Trade 1'):
    
    last_rsi = calculate_rsi(price_data).iloc[-1]
    K, D = calculate_stochastic(price_data)
    MACD, signal_line = calculate_macd(price_data)
                
    if last_rsi > 50 and K < 20 and D < 20 and MACD > signal_line:
        
        # Buy signal
        entry_price = mt5.symbol_info_tick(symbol).ask
        sl_buy_price = entry_price - sl * mt5.symbol_info(symbol).point * 10
        tp_buy_price = entry_price + tp * mt5.symbol_info(symbol).point * 10

        
        # Place the buy order with stop loss
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY,
            "price": entry_price,
            "sl": sl_buy_price,
            "tp": tp_buy_price,
            "deviation": 10,
            "magic": magic,
            "comment": comment,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            status_message = "Buy order placed successfully."
        else:
            status_message = f"Failed to place buy order. Error: {result.comment}"

    elif last_rsi < 50 and K > 80 and D > 80 and MACD < signal_line:
        
        # Sell signal
        entry_price = mt5.symbol_info_tick(symbol).bid
        sl_sell_price = entry_price + sl * mt5.symbol_info(symbol).point * 10
        tp_sell_price = entry_price - tp * mt5.symbol_info(symbol).point * 10
        
        # Place the sell order with stop loss
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_SELL,
            "price": entry_price,
            "sl": sl_sell_price,  # Set the stop loss price
            "tp": tp_sell_price,
            "deviation": 10,
            "magic": magic,
            "comment": comment,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "type_time": mt5.ORDER_TIME_GTC
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            status_message = "Sell order placed successfully."
        else:
            status_message = f"Failed to place sell order. Error: {result.comment}"
    else:
        status_message = 'Waiting for signal!'
        
    return status_message

# Initialize logging
logging.basicConfig(level=logging.INFO, filename='trading_bot.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')

import streamlit as st


def main():
    st.title('MT5 Trading Bot')

    with st.form(key='input_form'):
        login = st.text_input(label='Login ID')
        password = st.text_input(label='Password', type='password')
        server = st.text_input(label='Server')
        symbol = st.text_input(label='Symbol', value='EURUSD')
        sl = st.number_input('Stop Loss (pips)', value=10)
        tp = st.number_input('Take Profit (pips)', value=10)
        lot_size = st.number_input('Lot Size', value=0.01)
        strategy = st.selectbox("Select Strategy", ["EMA/RSI/Moving Average Crossover", "Triple Threat Trading"])
        # Display descriptions for each strategy
        if strategy == "EMA/RSI/Moving Average Crossover":
            st.markdown("""
                #### EMA/RSI/Moving Average Crossover Strategy
                - Uses Exponential Moving Averages (EMAs) and the Relative Strength Index (RSI).
                - **Buy Signal**: Generated when the shorter-term EMA is above the medium-term EMA, which is above the longer-term EMA, and the RSI is above 52.
                - **Sell Signal**: Generated when the opposite conditions are met.
            """)
        elif strategy == "Triple Threat Trading":
            st.markdown("""
                #### Triple Threat Trading Strategy
                - Utilizes the RSI, Stochastic Oscillator, and Moving Average Convergence Divergence (MACD).
                - **Buy Signal**: Generated when the RSI is above 50, both %K and %D lines of the Stochastic Oscillator are below 20, and the MACD line is above the signal line.
                - **Sell Signal**: Generated under opposite conditions.
            """)
        start_time = st.time_input("Select start time", value=datetime.time(10, 0))
        end_time = st.time_input("Select end time", value=datetime.time(14, 0))
        trading_time_duration = st.selectbox("Select trading time duration", ["1 minute", "5 minutes", "10 minutes", "15 minutes"])
        submit_button = st.form_submit_button(label='Submit')
        
        # Define a dictionary to map selected durations to seconds
        duration_to_seconds = {
            "1 minute": 60,
            "5 minutes": 300,
            "10 minutes": 600,
            "15 minutes": 900,
        }
        
        # Get the selected trading time duration in seconds
        trading_time_seconds = duration_to_seconds.get(trading_time_duration, 60)  # Default to 1 minute if not found

        
    # Add a placeholder for the status message
    status_placeholder = st.empty()
    
    # Add a placeholder for the countdown timer
    countdown_placeholder = st.empty()

    if submit_button:
        try:
            # Initialize the MT5 connection
            if not mt5.initialize():
                st.error("Error initializing MT5")
                mt5.shutdown()
                quit()

            # login to MT5
            authorized = mt5.login(int(login), password=password, server=server)
            if not authorized:
                st.error(f"Failed to connect at account #{login}, error code: {mt5.last_error()}")
                mt5.shutdown()
                quit()

            symbol = symbol
            timeframe = mt5.TIMEFRAME_M5
            num_ticks = 1000
            last_data = None

            # Convert start and end times to datetime objects for today
            now = datetime.datetime.now()
            start_datetime = datetime.datetime.combine(now.date(), start_time)
            end_datetime = datetime.datetime.combine(now.date(), end_time)
            
            # If the current time is before the scheduled start, wait until the start time
            while datetime.datetime.now() < start_datetime:
                time_until_start = (start_datetime - datetime.datetime.now()).total_seconds()
                min_sleep = min(time_until_start, 300)  # Sleep for 5 minutes or the remaining time until start
                time.sleep(min_sleep)
                        
            while datetime.datetime.now() < end_datetime:
                
                data = get_realtime_data(symbol, timeframe, num_ticks)
                if data is None:
                    logging.warning("No data received. Using the last known data.")
                    data = last_data
                else:
                    last_data = data
                    
                # Use selected strategy
                if strategy == "EMA/RSI/Moving Average Crossover":
                    status_message = execute_strategy(symbol=symbol, sl=sl, tp=tp, data=last_data, lot=lot_size)
                elif strategy == "Triple Threat Trading":
                    status_message = triple_threat_trading(price_data=last_data, symbol=symbol, lot=lot_size, sl=sl,  tp=tp)
                    
                # Update the status message on the Streamlit app
                status_placeholder.text(status_message)
                
                
                # Display the countdown timer before sleeping
                for remaining in range(trading_time_seconds, 0, -1):
                    mins, secs = divmod(remaining, 60)
                    timer = f"Next run in: {mins:02d}:{secs:02d}"
                    countdown_placeholder.text(timer)
                    time.sleep(1)  # Sleep for a second
    
                # Check if the current time has not passed the end time after sleeping
                if datetime.datetime.now() >= end_datetime:
                    break
                
                # Sleep for 5 minutes
                #time.sleep(trading_time_seconds)

        except KeyboardInterrupt:
            st.warning("Shutting down...")
        finally:
            mt5.shutdown()

if __name__ == "__main__":
    main()
