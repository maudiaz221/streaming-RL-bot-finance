import requests
import json
import threading
import time
import os
import sys
import pandas as pd
import numpy as np
import joblib
import websocket
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import subprocess

# Configuration
MODEL_PATH = "ts-model/model.pkl"
RETRAIN_INTERVAL_HOURS = 6
STREAMS = [
    "btcusdt@kline_1m",
    "ethusdt@kline_1m",
    "bnbusdt@kline_1m"
]
SOCKET_URL = f"wss://stream.binance.com:9443/stream?streams={'/'.join(STREAMS)}"

# Global State
model = None
data_window = {
    "BTCUSDT": pd.DataFrame(),
    "ETHUSDT": pd.DataFrame(),
    "BNBUSDT": pd.DataFrame()
}
latest_predictions = {}

# Live metrics tracking
prediction_history = [] # List of {symbol, predicted_return, actual_return, timestamp}
model_metrics = {
    "mae": 0.0, 
    "rmse": 0.0, 
    "last_trained": None,
    "accuracy_direction": 0.0, # % of times direction was correct
    "total_predictions": 0
}

app = FastAPI(title="Crypto Prediction API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_model():
    global model, model_metrics
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            model_metrics["last_trained"] = datetime.now().isoformat()
            print(f"Model loaded from {MODEL_PATH}")
        except Exception as e:
            print(f"Error loading model: {e}")
    else:
        print("No model found. Waiting for training pipeline.")

def update_live_metrics(symbol, actual_close, prev_prediction):
    """
    Compare previous prediction with actual outcome to update live metrics.
    """
    if not prev_prediction:
        return

    # Calculate what actually happened
    prev_price = prev_prediction['current_price']
    actual_return = ((actual_close - prev_price) / prev_price) * 100
    predicted_return = prev_prediction['predicted_return']
    
    # Direction check: Did we predict up and it went up? (or down/down)
    direction_correct = (predicted_return * actual_return) > 0
    
    # Record history
    prediction_history.append({
        "symbol": symbol,
        "predicted_return": predicted_return,
        "actual_return": actual_return,
        "direction_correct": direction_correct,
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep history somewhat limited
    if len(prediction_history) > 1000:
        prediction_history.pop(0)
        
    # Update aggregated metrics
    correct_count = sum(1 for p in prediction_history if p['direction_correct'])
    model_metrics['total_predictions'] = len(prediction_history)
    model_metrics['accuracy_direction'] = (correct_count / len(prediction_history)) * 100 if prediction_history else 0.0

def fetch_historical_data():
    """Bootstrap data_window with recent history."""
    print("Bootstrapping history...")
    base_url = "https://api.binance.com/api/v3/klines"
    
    for symbol in STREAMS:
        try:
            # Extract "BTCUSDT" from "btcusdt@kline_1m"
            clean_symbol = symbol.split("@")[0].upper()
            
            print(f"Fetching history for {clean_symbol}...")
            params = {
                "symbol": clean_symbol,
                "interval": "1m",
                "limit": 50 
            }
            response = requests.get(base_url, params=params)
            data = response.json()
            
            if isinstance(data, list):
                records = []
                for k in data:
                    # [t, o, h, l, c, v, ...]
                    records.append({
                        "timestamp": pd.to_datetime(k[0], unit='ms'),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5])
                    })
                
                df = pd.DataFrame(records)
                data_window[clean_symbol] = df
                print(f"Loaded {len(df)} records for {clean_symbol}")
                
                # Attempt prediction immediately
                if model:
                    features = calculate_features(df)
                    if features is not None:
                        pred_return = model.predict(features)[0]
                        current_price = df.iloc[-1]['close']
                        predicted_price = current_price * (1 + pred_return/100)
                        
                        latest_predictions[clean_symbol] = {
                            "symbol": clean_symbol,
                            "current_price": current_price,
                            "predicted_price": predicted_price,
                            "predicted_return": pred_return,
                            "timestamp": datetime.now().isoformat(),
                            "confidence": "High" if abs(pred_return) > 0.05 else "Low"
                        }

        except Exception as e:
            print(f"Error fetching history for {symbol}: {e}")

def calculate_features(df):
    """
    Re-implement feature engineering on a pandas DataFrame (without Spark).
    Matches logic in data_preparation.py
    """
    if len(df) < 20:  # Need at least 20 rows for MA_20
        return None
        
    # Sort just in case
    df = df.sort_values("timestamp")
    
    # Calculate features on the tail
    # We only need the last row's features for prediction
    
    # Returns
    df['prev_close'] = df['close'].shift(1)
    df['price_change_pct'] = ((df['close'] - df['prev_close']) / df['prev_close']) * 100
    df['log_return'] = np.log(df['close'] / df['prev_close'])
    
    # MAs
    df['ma_5'] = df['close'].rolling(window=5).mean()
    df['ma_10'] = df['close'].rolling(window=10).mean()
    df['ma_20'] = df['close'].rolling(window=20).mean()
    
    # Volatility (10-period std of log returns)
    df['volatility_10'] = df['log_return'].rolling(window=10).std()
    
    # Volume
    df['prev_volume'] = df['volume'].shift(1)
    df['volume_change_pct'] = ((df['volume'] - df['prev_volume']) / df['prev_volume']) * 100
    
    # Momentum
    df['close_5_ago'] = df['close'].shift(5)
    df['momentum_5'] = ((df['close'] - df['close_5_ago']) / df['close_5_ago']) * 100
    
    df['close_10_ago'] = df['close'].shift(10)
    df['momentum_10'] = ((df['close'] - df['close_10_ago']) / df['close_10_ago']) * 100
    
    # Spread
    df['hl_spread'] = df['high'] - df['low']
    df['hl_spread_pct'] = (df['hl_spread'] / df['low']) * 100
    
    # Return last row as features
    last_row = df.iloc[-1]
    
    features = [
        'price_change_pct', 
        'log_return', 
        'volatility_10', 
        'volume_change_pct', 
        'momentum_5', 
        'momentum_10', 
        'hl_spread_pct'
    ]
    
    # Check for NaNs
    if last_row[features].isnull().any():
        return None
        
    return last_row[features].to_frame().T

def on_message(ws, message):
    global data_window, latest_predictions
    try:
        msg = json.loads(message)
        if 'data' in msg and 'e' in msg['data'] and msg['data']['e'] == 'kline':
            k = msg['data']['k']
            symbol = msg['data']['s']
            is_closed = k['x']
            
            if is_closed:
                # Parse record
                record = {
                    "timestamp": pd.to_datetime(k['t'], unit='ms'),
                    "open": float(k['o']),
                    "high": float(k['h']),
                    "low": float(k['l']),
                    "close": float(k['c']),
                    "volume": float(k['v'])
                }
                
                # Check metrics against previous prediction BEFORE updating window
                if symbol in latest_predictions:
                    update_live_metrics(symbol, record['close'], latest_predictions[symbol])
                
                # Append to window
                df = data_window[symbol]
                new_row = pd.DataFrame([record])
                df = pd.concat([df, new_row], ignore_index=True)
                
                # Keep last 50 rows
                if len(df) > 50:
                    df = df.iloc[-50:]
                
                data_window[symbol] = df
                
                # Make NEW Prediction
                if model:
                    features = calculate_features(df)
                    if features is not None:
                        pred_return = model.predict(features)[0]
                        current_price = record['close']
                        predicted_price = current_price * (1 + pred_return/100)
                        
                        latest_predictions[symbol] = {
                            "symbol": symbol,
                            "current_price": current_price,
                            "predicted_price": predicted_price,
                            "predicted_return": pred_return,
                            "timestamp": datetime.now().isoformat(),
                            "confidence": "High" if abs(pred_return) > 0.05 else "Low"
                        }
                        print(f"[{symbol}] Pred: {pred_return:.4f}% -> {predicted_price:.2f}")

    except Exception as e:
        print(f"WS Error: {e}")

def start_websocket():
    def run():
        while True:
            try:
                ws = websocket.WebSocketApp(
                    SOCKET_URL,
                    on_message=on_message,
                    on_error=lambda ws, err: print(f"WebSocket Error: {err}"),
                    on_close=lambda ws, code, msg: print("WebSocket Closed")
                )
                ws.run_forever()
                time.sleep(5) # Reconnect delay
            except Exception as e:
                print(f"WS Connection Failed: {e}")
                time.sleep(5)
                
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()

def run_retraining_pipeline():
    print("Starting automated retraining...")
    try:
        # Run the pipeline script
        # We assume it's in the same directory structure
        cmd = [sys.executable, "ts-model/run_pipeline.py"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Retraining successful. Reloading model...")
            load_model()
        else:
            print(f"Retraining failed:\n{result.stderr}")
            
    except Exception as e:
        print(f"Retraining error: {e}")

@app.on_event("startup")
def startup_event():
    load_model()
    fetch_historical_data()
    start_websocket()
    
    # Scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_retraining_pipeline, 'interval', hours=RETRAIN_INTERVAL_HOURS)
    scheduler.start()

@app.get("/predict/{symbol}")
def get_prediction(symbol: str):
    symbol = symbol.upper()
    if symbol in latest_predictions:
        # Merge prediction with current global metrics
        pred = latest_predictions[symbol].copy()
        pred["metrics"] = model_metrics
        return pred
    return {"status": "waiting_for_data", "symbol": symbol}

@app.get("/metrics")
def get_metrics():
    return model_metrics

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
