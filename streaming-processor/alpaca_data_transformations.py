"""
Technical indicators and transformations for stock market data
"""
from pyspark.sql import DataFrame, Window
from pyspark.sql.functions import (
    col, avg, stddev, min as sql_min, max as sql_max,
    sum as sql_sum, count, lag, when, lit, expr, unix_timestamp,
    from_json, window as time_window
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    LongType, TimestampType, IntegerType
)
import logging

logger = logging.getLogger(__name__)


# Alpaca message schemas
TRADE_SCHEMA = StructType([
    StructField("T", StringType()),           # Message type
    StructField("S", StringType()),           # Symbol
    StructField("p", DoubleType()),           # Price
    StructField("s", LongType()),             # Size
    StructField("t", StringType()),           # Timestamp
    StructField("x", StringType()),           # Exchange
    StructField("i", LongType()),             # Trade ID
    StructField("z", StringType()),           # Tape
    StructField("received_at", DoubleType()), # Client timestamp
    StructField("client_timestamp", StringType())
])

QUOTE_SCHEMA = StructType([
    StructField("T", StringType()),           # Message type
    StructField("S", StringType()),           # Symbol
    StructField("bp", DoubleType()),          # Bid price
    StructField("bs", LongType()),            # Bid size
    StructField("ap", DoubleType()),          # Ask price
    StructField("as", LongType()),            # Ask size
    StructField("t", StringType()),           # Timestamp
    StructField("bx", StringType()),          # Bid exchange
    StructField("ax", StringType()),          # Ask exchange
    StructField("z", StringType()),           # Tape
    StructField("received_at", DoubleType()),
    StructField("client_timestamp", StringType())
])

BAR_SCHEMA = StructType([
    StructField("T", StringType()),           # Message type
    StructField("S", StringType()),           # Symbol
    StructField("o", DoubleType()),           # Open
    StructField("h", DoubleType()),           # High
    StructField("l", DoubleType()),           # Low
    StructField("c", DoubleType()),           # Close
    StructField("v", LongType()),             # Volume
    StructField("t", StringType()),           # Timestamp
    StructField("n", IntegerType()),          # Number of trades
    StructField("vw", DoubleType()),          # VWAP
    StructField("received_at", DoubleType()),
    StructField("client_timestamp", StringType())
])


def parse_alpaca_messages(df: DataFrame) -> DataFrame:
    """
    Parse raw Alpaca JSON messages into structured data
    
    Args:
        df: Raw DataFrame with 'data' column containing JSON
    
    Returns:
        Parsed DataFrame with separate columns for each message type
    """
    # Parse JSON based on message type
    # First, cast data to string
    df_string = df.selectExpr("CAST(data AS STRING) as json_data")
    
    # Parse JSON (assuming each message is a single object, not array)
    parsed_df = df_string.select(
        from_json(col("json_data"), TRADE_SCHEMA).alias("parsed")
    ).select("parsed.*")
    
    # Convert timestamp string to actual timestamp
    parsed_df = parsed_df.withColumn(
        "timestamp",
        expr("to_timestamp(t, \"yyyy-MM-dd'T'HH:mm:ss.SSS'Z'\")")
    )
    
    return parsed_df


def calculate_basic_statistics(df: DataFrame, window_duration: str = "1 minute") -> DataFrame:
    """
    Calculate basic streaming statistics per symbol
    
    Args:
        df: Parsed DataFrame with price and symbol columns
        window_duration: Window duration (e.g., "1 minute", "5 minutes")
    
    Returns:
        DataFrame with aggregated statistics
    """
    # Define windowing
    windowed_df = df.groupBy(
        time_window(col("timestamp"), window_duration),
        col("S").alias("symbol")
    ).agg(
        sql_min("p").alias("min_price"),
        sql_max("p").alias("max_price"),
        avg("p").alias("mean_price"),
        stddev("p").alias("std_price"),
        sql_sum("s").alias("total_volume"),
        count("*").alias("num_trades")
    )
    
    # Calculate variance manually if needed
    windowed_df = windowed_df.withColumn(
        "variance_price",
        when(col("std_price").isNotNull(), col("std_price") * col("std_price")).otherwise(0)
    )
    
    # Calculate price range
    windowed_df = windowed_df.withColumn(
        "price_range",
        col("max_price") - col("min_price")
    )
    
    return windowed_df


def calculate_moving_averages(df: DataFrame, symbol_col: str = "S", price_col: str = "p") -> DataFrame:
    """
    Calculate moving averages for different time windows
    
    Args:
        df: DataFrame with timestamp, symbol, and price
        symbol_col: Symbol column name
        price_col: Price column name
    
    Returns:
        DataFrame with moving averages
    """
    # Calculate 5-minute moving average
    df = df.withColumn(
        "ma_5min",
        avg(price_col).over(
            Window.partitionBy(symbol_col)
            .orderBy(col("timestamp").cast("long"))
            .rangeBetween(-300, 0)  # 5 minutes in seconds
        )
    )
    
    # Calculate 15-minute moving average
    df = df.withColumn(
        "ma_15min",
        avg(price_col).over(
            Window.partitionBy(symbol_col)
            .orderBy(col("timestamp").cast("long"))
            .rangeBetween(-900, 0)  # 15 minutes in seconds
        )
    )
    
    # Calculate 1-hour moving average
    df = df.withColumn(
        "ma_1hour",
        avg(price_col).over(
            Window.partitionBy(symbol_col)
            .orderBy(col("timestamp").cast("long"))
            .rangeBetween(-3600, 0)  # 1 hour in seconds
        )
    )
    
    return df


def calculate_rsi(df: DataFrame, period: int = 14, symbol_col: str = "S", price_col: str = "c") -> DataFrame:
    """
    Calculate Relative Strength Index (RSI)
    
    Args:
        df: DataFrame with OHLC data (use close price)
        period: RSI period (default 14)
        symbol_col: Symbol column name
        price_col: Price column name (typically close)
    
    Returns:
        DataFrame with RSI column
    """
    # Define window for each symbol
    window_spec = Window.partitionBy(symbol_col).orderBy("timestamp")
    
    # Calculate price changes
    df = df.withColumn("prev_price", lag(price_col, 1).over(window_spec))
    df = df.withColumn("price_change", col(price_col) - col("prev_price"))
    
    # Separate gains and losses
    df = df.withColumn(
        "gain",
        when(col("price_change") > 0, col("price_change")).otherwise(0)
    )
    df = df.withColumn(
        "loss",
        when(col("price_change") < 0, -col("price_change")).otherwise(0)
    )
    
    # Calculate average gain and loss over period
    window_rolling = (
        Window.partitionBy(symbol_col)
        .orderBy("timestamp")
        .rowsBetween(-period + 1, 0)
    )
    
    df = df.withColumn("avg_gain", avg("gain").over(window_rolling))
    df = df.withColumn("avg_loss", avg("loss").over(window_rolling))
    
    # Calculate RS and RSI
    df = df.withColumn(
        "rs",
        when(col("avg_loss") != 0, col("avg_gain") / col("avg_loss")).otherwise(100)
    )
    df = df.withColumn(
        "rsi",
        lit(100) - (lit(100) / (lit(1) + col("rs")))
    )
    
    # Clean up intermediate columns
    df = df.drop("prev_price", "price_change", "gain", "loss", "avg_gain", "avg_loss", "rs")
    
    return df


def calculate_macd(
    df: DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    symbol_col: str = "S",
    price_col: str = "c"
) -> DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    
    Args:
        df: DataFrame with price data
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period
        symbol_col: Symbol column name
        price_col: Price column name
    
    Returns:
        DataFrame with MACD columns
    """
    # Simple approximation using SMA instead of EMA for streaming context
    # In production, consider using more sophisticated EMA calculation
    
    window_spec = Window.partitionBy(symbol_col).orderBy("timestamp")
    
    # Calculate fast and slow moving averages
    df = df.withColumn(
        "ema_fast",
        avg(price_col).over(
            window_spec.rowsBetween(-fast_period + 1, 0)
        )
    )
    
    df = df.withColumn(
        "ema_slow",
        avg(price_col).over(
            window_spec.rowsBetween(-slow_period + 1, 0)
        )
    )
    
    # Calculate MACD line
    df = df.withColumn(
        "macd_line",
        col("ema_fast") - col("ema_slow")
    )
    
    # Calculate signal line
    df = df.withColumn(
        "macd_signal",
        avg("macd_line").over(
            window_spec.rowsBetween(-signal_period + 1, 0)
        )
    )
    
    # Calculate histogram
    df = df.withColumn(
        "macd_histogram",
        col("macd_line") - col("macd_signal")
    )
    
    # Clean up intermediate columns
    df = df.drop("ema_fast", "ema_slow")
    
    return df


def calculate_bollinger_bands(
    df: DataFrame,
    period: int = 20,
    std_dev: int = 2,
    symbol_col: str = "S",
    price_col: str = "c"
) -> DataFrame:
    """
    Calculate Bollinger Bands
    
    Args:
        df: DataFrame with price data
        period: Period for moving average
        std_dev: Number of standard deviations
        symbol_col: Symbol column name
        price_col: Price column name
    
    Returns:
        DataFrame with Bollinger Bands columns
    """
    window_spec = (
        Window.partitionBy(symbol_col)
        .orderBy("timestamp")
        .rowsBetween(-period + 1, 0)
    )
    
    # Calculate middle band (SMA)
    df = df.withColumn(
        "bb_middle",
        avg(price_col).over(window_spec)
    )
    
    # Calculate standard deviation
    df = df.withColumn(
        "bb_std",
        stddev(price_col).over(window_spec)
    )
    
    # Calculate upper and lower bands
    df = df.withColumn(
        "bb_upper",
        col("bb_middle") + (col("bb_std") * lit(std_dev))
    )
    
    df = df.withColumn(
        "bb_lower",
        col("bb_middle") - (col("bb_std") * lit(std_dev))
    )
    
    # Calculate band width
    df = df.withColumn(
        "bb_width",
        col("bb_upper") - col("bb_lower")
    )
    
    # Clean up
    df = df.drop("bb_std")
    
    return df


def detect_price_anomalies(df: DataFrame, threshold: float = 3.0) -> DataFrame:
    """
    Detect price anomalies using z-score method
    
    Args:
        df: DataFrame with price data
        threshold: Z-score threshold for anomaly detection
    
    Returns:
        DataFrame with anomaly flag
    """
    # Calculate z-score for price
    df = df.withColumn(
        "price_zscore",
        (col("p") - col("mean_price")) / col("std_price")
    )
    
    # Flag anomalies
    df = df.withColumn(
        "is_anomaly",
        when(
            (col("price_zscore") > threshold) | (col("price_zscore") < -threshold),
            lit(True)
        ).otherwise(lit(False))
    )
    
    return df


def calculate_bid_ask_spread(df: DataFrame) -> DataFrame:
    """
    Calculate bid-ask spread from quote data
    
    Args:
        df: DataFrame with bid and ask prices
    
    Returns:
        DataFrame with spread columns
    """
    df = df.withColumn(
        "bid_ask_spread",
        col("ap") - col("bp")
    )
    
    df = df.withColumn(
        "spread_pct",
        (col("bid_ask_spread") / col("bp")) * 100
    )
    
    df = df.withColumn(
        "mid_price",
        (col("ap") + col("bp")) / 2
    )
    
    return df


def enrich_for_rl_model(df: DataFrame) -> DataFrame:
    """
    Create feature set for RL model inference
    
    Args:
        df: DataFrame with calculated indicators
    
    Returns:
        DataFrame with RL features
    """
    # Calculate price momentum
    window_spec = Window.partitionBy("S").orderBy("timestamp")
    
    df = df.withColumn(
        "price_momentum",
        (col("p") - lag("p", 5).over(window_spec)) / lag("p", 5).over(window_spec)
    )
    
    # Calculate volatility (rolling std)
    df = df.withColumn(
        "volatility",
        stddev("p").over(
            Window.partitionBy("S")
            .orderBy("timestamp")
            .rowsBetween(-20, 0)
        )
    )
    
    # Normalize volume
    df = df.withColumn(
        "volume_ma",
        avg("s").over(
            Window.partitionBy("S")
            .orderBy("timestamp")
            .rowsBetween(-20, 0)
        )
    )
    
    df = df.withColumn(
        "volume_ratio",
        col("s") / when(col("volume_ma") > 0, col("volume_ma")).otherwise(1)
    )
    
    return df

