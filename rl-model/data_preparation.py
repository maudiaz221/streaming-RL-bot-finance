"""
Data preparation utilities for RL model training
"""
import os
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from typing import Tuple, Optional
import glob

logger = logging.getLogger(__name__)


def load_historical_data(data_path: str, symbol: str = None) -> Optional[pd.DataFrame]:
    """
    Load historical data from parquet files
    
    Args:
        data_path: Path to data directory
        symbol: Optional symbol to filter
    
    Returns:
        DataFrame with historical data
    """
    try:
        # Check if path exists
        if not os.path.exists(data_path):
            logger.error(f"Data path does not exist: {data_path}")
            return None
        
        # Find parquet files
        if symbol:
            # Look for symbol-specific files
            pattern = f"{data_path}/**/S={symbol}/**/*.parquet"
            files = glob.glob(pattern, recursive=True)
            
            if not files:
                # Try alternative pattern
                pattern = f"{data_path}/**/*{symbol}*.parquet"
                files = glob.glob(pattern, recursive=True)
        else:
            # Load all parquet files
            pattern = f"{data_path}/**/*.parquet"
            files = glob.glob(pattern, recursive=True)
        
        if not files:
            logger.warning(f"No parquet files found in {data_path}")
            # Try to load from CSV as fallback
            return load_csv_data(data_path, symbol)
        
        logger.info(f"Found {len(files)} parquet files")
        
        # Load all files
        dfs = []
        for file in files:
            try:
                df = pd.read_parquet(file)
                dfs.append(df)
            except Exception as e:
                logger.warning(f"Failed to read {file}: {e}")
        
        if not dfs:
            return None
        
        # Concatenate all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Filter by symbol if specified
        if symbol and 'S' in combined_df.columns:
            combined_df = combined_df[combined_df['S'] == symbol]
        
        # Sort by timestamp
        if 'timestamp' in combined_df.columns:
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
        elif 't' in combined_df.columns:
            combined_df['timestamp'] = pd.to_datetime(combined_df['t'])
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
        
        logger.info(f"Loaded {len(combined_df)} records")
        
        return combined_df
        
    except Exception as e:
        logger.error(f"Error loading historical data: {e}")
        return None


def load_csv_data(data_path: str, symbol: str = None) -> Optional[pd.DataFrame]:
    """
    Load historical data from CSV files (fallback)
    
    Args:
        data_path: Path to data directory
        symbol: Optional symbol to filter
    
    Returns:
        DataFrame with historical data
    """
    try:
        # Find CSV files
        if symbol:
            pattern = f"{data_path}/**/*{symbol}*.csv"
        else:
            pattern = f"{data_path}/**/*.csv"
        
        files = glob.glob(pattern, recursive=True)
        
        if not files:
            logger.warning(f"No CSV files found in {data_path}")
            return generate_sample_data(symbol or 'SAMPLE')
        
        logger.info(f"Found {len(files)} CSV files")
        
        # Load files
        dfs = []
        for file in files:
            try:
                df = pd.read_csv(file)
                dfs.append(df)
            except Exception as e:
                logger.warning(f"Failed to read {file}: {e}")
        
        if not dfs:
            return None
        
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Sort by timestamp
        if 'timestamp' in combined_df.columns:
            combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'])
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
        
        return combined_df
        
    except Exception as e:
        logger.error(f"Error loading CSV data: {e}")
        return None


def generate_sample_data(symbol: str = 'SAMPLE', n_samples: int = 1000) -> pd.DataFrame:
    """
    Generate sample data for testing when no real data is available
    
    Args:
        symbol: Stock symbol
        n_samples: Number of samples to generate
    
    Returns:
        DataFrame with synthetic data
    """
    logger.warning("Generating synthetic data for testing...")
    
    np.random.seed(42)
    
    # Generate price series (random walk)
    returns = np.random.normal(0.0002, 0.02, n_samples)
    prices = 100 * np.exp(np.cumsum(returns))
    
    # Generate timestamps
    timestamps = pd.date_range(start='2024-01-01', periods=n_samples, freq='1min')
    
    # Generate OHLC
    opens = prices + np.random.normal(0, 0.5, n_samples)
    highs = np.maximum(opens, prices) + np.abs(np.random.normal(0, 0.5, n_samples))
    lows = np.minimum(opens, prices) - np.abs(np.random.normal(0, 0.5, n_samples))
    closes = prices
    volumes = np.random.randint(1000, 10000, n_samples)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'S': symbol,
        'o': opens,
        'h': highs,
        'l': lows,
        'c': closes,
        'v': volumes
    })
    
    # Calculate technical indicators
    df = calculate_indicators(df)
    
    return df


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical indicators if not present
    
    Args:
        df: DataFrame with OHLC data
    
    Returns:
        DataFrame with indicators
    """
    # Calculate indicators only if they don't exist
    if 'rsi' not in df.columns:
        df['rsi'] = calculate_rsi_simple(df['c'])
    
    if 'macd_line' not in df.columns or 'macd_signal' not in df.columns:
        macd, signal = calculate_macd_simple(df['c'])
        df['macd_line'] = macd
        df['macd_signal'] = signal
    
    if 'bb_upper' not in df.columns:
        df['bb_middle'] = df['c'].rolling(20).mean()
        df['bb_std'] = df['c'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        df.drop('bb_std', axis=1, inplace=True)
    
    if 'ma_5min' not in df.columns:
        df['ma_5min'] = df['c'].rolling(5).mean()
    
    if 'ma_15min' not in df.columns:
        df['ma_15min'] = df['c'].rolling(15).mean()
    
    if 'price_momentum' not in df.columns:
        df['price_momentum'] = df['c'].pct_change(5)
    
    if 'volatility' not in df.columns:
        df['volatility'] = df['c'].rolling(20).std()
    
    if 'volume_ratio' not in df.columns:
        df['volume_ma'] = df['v'].rolling(20).mean()
        df['volume_ratio'] = df['v'] / df['volume_ma']
        df.drop('volume_ma', axis=1, inplace=True)
    
    # Fill NaN values
    df = df.fillna(method='bfill').fillna(method='ffill').fillna(0)
    
    return df


def calculate_rsi_simple(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd_simple(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
    """Calculate MACD"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line


def prepare_training_data(df: pd.DataFrame, train_split: float = 0.8) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split data into training and test sets
    
    Args:
        df: Complete dataset
        train_split: Ratio for training data
    
    Returns:
        Tuple of (train_df, test_df)
    """
    # Ensure data is sorted by timestamp
    if 'timestamp' in df.columns:
        df = df.sort_values('timestamp').reset_index(drop=True)
    
    # Calculate split index
    split_idx = int(len(df) * train_split)
    
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    logger.info(f"Data split: {len(train_df)} train, {len(test_df)} test")
    
    return train_df, test_df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and validate data
    
    Args:
        df: Raw DataFrame
    
    Returns:
        Cleaned DataFrame
    """
    # Remove duplicates
    if 'timestamp' in df.columns:
        df = df.drop_duplicates(subset=['timestamp'], keep='first')
    
    # Remove rows with invalid prices
    if 'c' in df.columns:
        df = df[df['c'] > 0]
    
    # Remove rows with too many NaN values
    threshold = len(df.columns) * 0.5
    df = df.dropna(thresh=threshold)
    
    # Fill remaining NaN values
    df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
    
    return df




