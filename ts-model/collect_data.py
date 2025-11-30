import websocket
import json
import time
import threading
import os
import signal
import sys
import argparse
import requests

# Configuration
DEFAULT_DURATION = 300  # Run for 5 minutes by default
DEFAULT_OUTPUT = "ts-model/raw_data.json"
STREAMS = [
    "btcusdt@kline_1m",
    "ethusdt@kline_1m",
    "bnbusdt@kline_1m"
]
SOCKET_URL = f"wss://stream.binance.com:9443/stream?streams={'/'.join(STREAMS)}"

# Global flag to control execution
running = True
OUTPUT_FILE = DEFAULT_OUTPUT

def fetch_historical_data(output_file):
    """Fetch recent historical klines to bootstrap the dataset."""
    print("Bootstrapping with historical data...")
    base_url = "https://api.binance.com/api/v3/klines"
    
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    with open(output_file, "a") as f:
        for symbol in symbols:
            try:
                print(f"Fetching history for {symbol}...")
                params = {
                    "symbol": symbol,
                    "interval": "1m",
                    "limit": 50
                }
                response = requests.get(base_url, params=params)
                data = response.json()
                
                if not isinstance(data, list):
                    print(f"Error fetching {symbol}: {data}")
                    continue
                    
                count = 0
                for k in data:
                    # k is [open_time, open, high, low, close, vol, close_time, quote_asset_vol, trades, taker_buy_base, taker_buy_quote, ignore]
                    kline_obj = {
                        "t": k[0],
                        "T": k[6],
                        "s": symbol,
                        "i": "1m",
                        "o": k[1],
                        "c": k[4],
                        "h": k[2],
                        "l": k[3],
                        "v": k[5],
                        "n": k[8],
                        "q": k[7],
                        "V": k[9],
                        "Q": k[10]
                    }
                    
                    record = {
                        "event_type": "kline",
                        "symbol": symbol,
                        "exchange": "binance",
                        "data": {
                            "e": "kline",
                            "E": k[6], # Use close time as event time approx
                            "s": symbol,
                            "k": kline_obj
                        }
                    }
                    f.write(json.dumps(record) + "\n")
                    count += 1
                print(f"Added {count} historical records for {symbol}")
                
            except Exception as e:
                print(f"Failed to fetch history for {symbol}: {e}")

def on_message(ws, message):
    try:
        data = json.loads(message)
        
        # Check if it's a kline message
        if 'data' in data and 'e' in data['data'] and data['data']['e'] == 'kline':
            kline_data = data['data']
            # Only save closed candles to ensure data integrity for time series features
            if not kline_data['k']['x']:
                return
                
            symbol = kline_data['s']
            
            # Construct the record structure expected by data_preparation.py
            record = {
                "event_type": "kline",
                "symbol": symbol,
                "exchange": "binance",
                "data": kline_data
            }
            
            # Append to file in NDJSON format
            with open(OUTPUT_FILE, "a") as f:
                f.write(json.dumps(record) + "\n")
            
            print(f"Recorded kline for {symbol} at {kline_data['k']['t']}")
            
    except Exception as e:
        print(f"Error processing message: {e}")

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("WebSocket connection closed")

def on_open(ws):
    print("WebSocket connection opened")
    print(f"Listening for streams: {STREAMS}")
    print(f"Saving data to {OUTPUT_FILE}")

def stop_collection(signum, frame):
    global running
    print("\nStopping data collection...")
    running = False
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="Duration in seconds")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output file path")
    parser.add_argument("--bootstrap", action="store_true", help="Fetch historical data on start")
    args = parser.parse_args()
    
    global OUTPUT_FILE
    OUTPUT_FILE = args.output

    # Register signal handlers
    signal.signal(signal.SIGINT, stop_collection)
    signal.signal(signal.SIGTERM, stop_collection)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    if os.path.exists(OUTPUT_FILE):
        print(f"Appending to existing file: {OUTPUT_FILE}")
    
    # Bootstrap if requested or if file is small (implied logic, but here explicit)
    if args.bootstrap:
        fetch_historical_data(OUTPUT_FILE)
    
    # Create WebSocket connection
    ws = websocket.WebSocketApp(
        SOCKET_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Run WebSocket in a separate thread
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    
    # Run for specified duration
    start_time = time.time()
    try:
        while running:
            elapsed = time.time() - start_time
            if elapsed >= args.duration:
                print(f"Duration of {args.duration}s reached. Stopping...")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        ws.close()
        print("Done.")

if __name__ == "__main__":
    main()
