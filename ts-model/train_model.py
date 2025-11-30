import pandas as pd
import numpy as np
import glob
import os
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import argparse

def load_data(data_path):
    all_files = glob.glob(os.path.join(data_path, "*/*.csv"))
    if not all_files:
        # Try searching directly in the path (in case it's not partitioned by folder in the way expected)
        all_files = glob.glob(os.path.join(data_path, "*.csv"))
    
    if not all_files:
        print(f"No CSV files found in {data_path}")
        return pd.DataFrame()

    print(f"Found {len(all_files)} CSV files")
    df_list = []
    for filename in all_files:
        try:
            df = pd.read_csv(filename)
            df_list.append(df)
        except Exception as e:
            print(f"Error reading {filename}: {e}")
    
    if not df_list:
        return pd.DataFrame()
        
    full_df = pd.concat(df_list, axis=0, ignore_index=True)
    return full_df

def prepare_data(df):
    # Sort by symbol and timestamp
    df = df.sort_values(by=['symbol', 'timestamp'])
    
    # Create Target: Next minute's close price return
    # We predict the percentage change for the next minute
    df['next_close'] = df.groupby('symbol')['close'].shift(-1)
    df['target_return'] = (df['next_close'] - df['close']) / df['close'] * 100
    
    # Drop NaNs (last row per symbol)
    df = df.dropna(subset=['target_return'])
    
    # Select features
    # Using relative features to allow one model for all coins
    feature_cols = [
        'price_change_pct', 
        'log_return', 
        'volatility_10', 
        'volume_change_pct', 
        'momentum_5', 
        'momentum_10', 
        'hl_spread_pct'
    ]
    
    # Handle NaNs in features (beginning of series)
    df = df.dropna(subset=feature_cols)
    
    return df, feature_cols

def train(data_path, model_path):
    print(f"Loading data from {data_path}...")
    df = load_data(data_path)
    
    if df.empty:
        print("No data loaded. Exiting.")
        return

    print(f"Loaded {len(df)} rows.")
    
    print("Preparing data...")
    df_processed, features = prepare_data(df)
    print(f"Data after processing: {len(df_processed)} rows")
    
    if len(df_processed) < 10:
        print("Not enough data to train. Exiting.")
        return

    X = df_processed[features]
    y = df_processed['target_return']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)
    
    print(f"Training RandomForestRegressor on {len(X_train)} samples...")
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Evaluate
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    
    print("\nModel Evaluation:")
    print(f"MAE: {mae:.4f}")
    print(f"RMSE: {rmse:.4f}")
    
    # Save
    print(f"\nSaving model to {model_path}")
    joblib.dump(model, model_path)
    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="ts-model/processed_output", help="Input directory containing CSVs")
    parser.add_argument("--output", default="ts-model/model.pkl", help="Output path for model file")
    args = parser.parse_args()
    
    train(args.input, args.output)

