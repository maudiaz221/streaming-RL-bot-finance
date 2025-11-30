"""
PySpark Data Preparation Pipeline for Cryptocurrency Time Series Modeling

This module processes raw JSON kline (candlestick) data from S3 and transforms it
into engineered CSV datasets ready for time series price prediction models.
"""

from pyspark.sql import SparkSession, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    LongType, IntegerType, TimestampType, BooleanType
)
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_raw_data(spark: SparkSession, s3_path: str) -> DataFrame:
    """
    Load raw JSON data from S3 and filter for kline events only.
    
    Args:
        spark: Active SparkSession
        s3_path: S3 path to JSON files (e.g., 's3://bucket/path/*.json')
    
    Returns:
        DataFrame with kline events only, ready for extraction
    """
    logger.info(f"Loading raw data from {s3_path}")
    
    # Read JSON as text and manually parse to extract only what we need
    df_text = spark.read.text(s3_path)
    
    # Use get_json_object to extract specific fields without schema conflicts
    df = df_text.select(
        F.get_json_object(F.col("value"), "$.event_type").alias("event_type"),
        F.get_json_object(F.col("value"), "$.exchange").alias("exchange"),
        F.get_json_object(F.col("value"), "$.symbol").alias("root_symbol"),
        # Extract kline fields directly
        F.get_json_object(F.col("value"), "$.data.k.t").cast(LongType()).alias("kline_start_time"),
        F.get_json_object(F.col("value"), "$.data.k.T").cast(LongType()).alias("kline_close_time"),
        F.get_json_object(F.col("value"), "$.data.k.s").alias("symbol"),
        F.get_json_object(F.col("value"), "$.data.k.i").alias("interval"),
        F.get_json_object(F.col("value"), "$.data.k.o").alias("open"),
        F.get_json_object(F.col("value"), "$.data.k.c").alias("close"),
        F.get_json_object(F.col("value"), "$.data.k.h").alias("high"),
        F.get_json_object(F.col("value"), "$.data.k.l").alias("low"),
        F.get_json_object(F.col("value"), "$.data.k.v").alias("volume"),
        F.get_json_object(F.col("value"), "$.data.k.n").cast(IntegerType()).alias("number_of_trades"),
        F.get_json_object(F.col("value"), "$.data.k.q").alias("quote_volume"),
        F.get_json_object(F.col("value"), "$.data.k.V").alias("taker_buy_volume"),
        F.get_json_object(F.col("value"), "$.data.k.Q").alias("taker_buy_quote_volume"),
    )
    
    # Filter for kline events only (ignore trade events)
    df_klines = df.filter(F.col("event_type") == "kline")
    
    kline_count = df_klines.count()
    logger.info(f"Loaded {kline_count} kline records")
    
    return df_klines


def extract_kline_features(df: DataFrame) -> DataFrame:
    """
    Transform and type-cast kline features that were extracted during load.
    
    Args:
        df: DataFrame with extracted kline data
    
    Returns:
        DataFrame with properly typed and formatted kline features
    """
    logger.info("Processing kline features")
    
    # Convert timestamps and cast types
    df_extracted = df.select(
        # Convert kline start time from milliseconds to timestamp
        F.from_unixtime(F.col("kline_start_time") / 1000).cast(TimestampType()).alias("timestamp"),
        
        # Symbol and interval
        F.col("symbol"),
        F.col("interval"),
        
        # OHLC prices - cast to double for precision
        F.col("open").cast(DoubleType()).alias("open"),
        F.col("high").cast(DoubleType()).alias("high"),
        F.col("low").cast(DoubleType()).alias("low"),
        F.col("close").cast(DoubleType()).alias("close"),
        
        # Volume metrics
        F.col("volume").cast(DoubleType()).alias("volume"),
        F.col("quote_volume").cast(DoubleType()).alias("quote_volume"),
        
        # Trade counts and taker buy volumes
        F.col("number_of_trades"),
        F.col("taker_buy_volume").cast(DoubleType()).alias("taker_buy_volume"),
        F.col("taker_buy_quote_volume").cast(DoubleType()).alias("taker_buy_quote_volume"),
        
        # Exchange info
        F.col("exchange"),
        
        # Kline close time for reference
        F.from_unixtime(F.col("kline_close_time") / 1000).cast(TimestampType()).alias("kline_close_time")
    )
    
    # Sort by symbol and timestamp for proper time series ordering
    df_extracted = df_extracted.orderBy("symbol", "timestamp")
    
    logger.info("Kline features processed successfully")
    
    return df_extracted


def engineer_features(df: DataFrame) -> DataFrame:
    """
    Engineer time series features for modeling using window functions.
    
    Args:
        df: DataFrame with extracted kline features
    
    Returns:
        DataFrame with engineered features
    """
    logger.info("Engineering time series features")
    
    # Define window specifications partitioned by symbol, ordered by timestamp
    window_symbol = Window.partitionBy("symbol").orderBy("timestamp")
    
    # Windows for moving averages and rolling calculations
    window_5 = Window.partitionBy("symbol").orderBy("timestamp").rowsBetween(-4, 0)
    window_10 = Window.partitionBy("symbol").orderBy("timestamp").rowsBetween(-9, 0)
    window_20 = Window.partitionBy("symbol").orderBy("timestamp").rowsBetween(-19, 0)
    
    # Start with the base dataframe
    df_features = df
    
    # === Price Changes and Returns ===
    df_features = df_features.withColumn(
        "prev_close",
        F.lag("close", 1).over(window_symbol)
    )
    
    df_features = df_features.withColumn(
        "price_change",
        F.col("close") - F.col("prev_close")
    )
    
    df_features = df_features.withColumn(
        "price_change_pct",
        F.when(
            F.col("prev_close").isNotNull() & (F.col("prev_close") != 0),
            ((F.col("close") - F.col("prev_close")) / F.col("prev_close")) * 100
        ).otherwise(None)
    )
    
    df_features = df_features.withColumn(
        "log_return",
        F.when(
            F.col("prev_close").isNotNull() & (F.col("prev_close") > 0) & (F.col("close") > 0),
            F.log(F.col("close") / F.col("prev_close"))
        ).otherwise(None)
    )
    
    # === Moving Averages ===
    df_features = df_features.withColumn(
        "ma_5",
        F.avg("close").over(window_5)
    )
    
    df_features = df_features.withColumn(
        "ma_10",
        F.avg("close").over(window_10)
    )
    
    df_features = df_features.withColumn(
        "ma_20",
        F.avg("close").over(window_20)
    )
    
    # === Volatility (10-period rolling std of returns) ===
    df_features = df_features.withColumn(
        "volatility_10",
        F.stddev("log_return").over(window_10)
    )
    
    # === Volume Features ===
    df_features = df_features.withColumn(
        "volume_ma_5",
        F.avg("volume").over(window_5)
    )
    
    df_features = df_features.withColumn(
        "prev_volume",
        F.lag("volume", 1).over(window_symbol)
    )
    
    df_features = df_features.withColumn(
        "volume_change_pct",
        F.when(
            F.col("prev_volume").isNotNull() & (F.col("prev_volume") != 0),
            ((F.col("volume") - F.col("prev_volume")) / F.col("prev_volume")) * 100
        ).otherwise(None)
    )
    
    # === Price Momentum ===
    df_features = df_features.withColumn(
        "close_5_ago",
        F.lag("close", 5).over(window_symbol)
    )
    
    df_features = df_features.withColumn(
        "close_10_ago",
        F.lag("close", 10).over(window_symbol)
    )
    
    df_features = df_features.withColumn(
        "momentum_5",
        F.when(
            F.col("close_5_ago").isNotNull() & (F.col("close_5_ago") != 0),
            ((F.col("close") - F.col("close_5_ago")) / F.col("close_5_ago")) * 100
        ).otherwise(None)
    )
    
    df_features = df_features.withColumn(
        "momentum_10",
        F.when(
            F.col("close_10_ago").isNotNull() & (F.col("close_10_ago") != 0),
            ((F.col("close") - F.col("close_10_ago")) / F.col("close_10_ago")) * 100
        ).otherwise(None)
    )
    
    # === High-Low Spread ===
    df_features = df_features.withColumn(
        "hl_spread",
        F.col("high") - F.col("low")
    )
    
    df_features = df_features.withColumn(
        "hl_spread_pct",
        F.when(
            F.col("low").isNotNull() & (F.col("low") != 0),
            ((F.col("high") - F.col("low")) / F.col("low")) * 100
        ).otherwise(None)
    )
    
    # Drop temporary columns
    df_features = df_features.drop("prev_close", "prev_volume", "close_5_ago", "close_10_ago")
    
    logger.info("Time series features engineered successfully")
    
    return df_features


def save_by_symbol(df: DataFrame, output_path: str) -> Dict[str, int]:
    """
    Save data to separate CSV files for each symbol.
    
    Args:
        df: DataFrame with engineered features
        output_path: Base output path (local or S3)
    
    Returns:
        Dictionary with symbol counts
    """
    logger.info(f"Saving data to {output_path}")
    
    # Get list of unique symbols
    symbols = [row.symbol for row in df.select("symbol").distinct().collect()]
    symbol_counts = {}
    
    # Select columns in desired order for output
    output_columns = [
        "timestamp", "symbol", "interval", "exchange",
        "open", "high", "low", "close", "volume",
        "number_of_trades", "quote_volume", "taker_buy_volume", "taker_buy_quote_volume",
        "price_change", "price_change_pct", "log_return",
        "ma_5", "ma_10", "ma_20",
        "volatility_10",
        "volume_ma_5", "volume_change_pct",
        "momentum_5", "momentum_10",
        "hl_spread", "hl_spread_pct"
    ]
    
    # Save each symbol to its own CSV file
    for symbol in symbols:
        logger.info(f"Processing symbol: {symbol}")
        
        # Filter for this symbol and sort by timestamp
        df_symbol = df.filter(F.col("symbol") == symbol).orderBy("timestamp")
        
        # Count records
        count = df_symbol.count()
        symbol_counts[symbol] = count
        
        # Define output file path
        output_file = f"{output_path}/{symbol}.csv"
        
        # Write to CSV with header
        df_symbol.select(output_columns).coalesce(1).write.mode("overwrite").option("header", "true").csv(output_file)
        
        logger.info(f"Saved {count} records for {symbol} to {output_file}")
    
    return symbol_counts


def validate_data(df: DataFrame) -> Dict[str, any]:
    """
    Validate data quality and return statistics.
    
    Args:
        df: DataFrame to validate
    
    Returns:
        Dictionary with validation results
    """
    logger.info("Validating data quality")
    
    validation_report = {}
    
    # Total record count
    total_count = df.count()
    validation_report["total_records"] = total_count
    
    # Count by symbol
    symbol_counts = df.groupBy("symbol").count().collect()
    validation_report["records_by_symbol"] = {row.symbol: row["count"] for row in symbol_counts}
    
    # Check for null values in critical columns
    critical_columns = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]
    null_counts = {}
    
    for col in critical_columns:
        null_count = df.filter(F.col(col).isNull()).count()
        null_counts[col] = null_count
    
    validation_report["null_counts"] = null_counts
    
    # Check for duplicate timestamps per symbol
    duplicate_check = df.groupBy("symbol", "timestamp").count().filter(F.col("count") > 1)
    duplicate_count = duplicate_check.count()
    validation_report["duplicate_timestamps"] = duplicate_count
    
    if duplicate_count > 0:
        logger.warning(f"Found {duplicate_count} duplicate timestamp entries")
    
    # Time range by symbol
    time_ranges = df.groupBy("symbol").agg(
        F.min("timestamp").alias("first_timestamp"),
        F.max("timestamp").alias("last_timestamp")
    ).collect()
    
    validation_report["time_ranges"] = {
        row.symbol: {
            "first": str(row.first_timestamp),
            "last": str(row.last_timestamp)
        }
        for row in time_ranges
    }
    
    # Check for negative or zero prices (data quality issue)
    invalid_prices = df.filter(
        (F.col("open") <= 0) | (F.col("high") <= 0) | 
        (F.col("low") <= 0) | (F.col("close") <= 0)
    ).count()
    
    validation_report["invalid_prices"] = invalid_prices
    
    if invalid_prices > 0:
        logger.warning(f"Found {invalid_prices} records with invalid prices")
    
    logger.info("Data validation complete")
    
    return validation_report


def process_s3_data(
    spark: SparkSession, 
    input_s3_path: str, 
    output_s3_path: str
) -> Tuple[Dict[str, int], Dict[str, any]]:
    """
    Main orchestration function for the complete data processing pipeline.
    
    Args:
        spark: Active SparkSession
        input_s3_path: S3 path to input JSON files
        output_s3_path: S3 path for output CSV files
    
    Returns:
        Tuple of (symbol_counts, validation_report)
    """
    logger.info("=" * 80)
    logger.info("Starting Crypto Time Series Data Processing Pipeline")
    logger.info("=" * 80)
    
    # Step 1: Load raw data
    logger.info("Step 1/5: Loading raw data")
    df_raw = load_raw_data(spark, input_s3_path)
    
    # Step 2: Extract kline features
    logger.info("Step 2/5: Extracting kline features")
    df_extracted = extract_kline_features(df_raw)
    
    # Step 3: Engineer time series features
    logger.info("Step 3/5: Engineering features")
    df_engineered = engineer_features(df_extracted)
    
    # Step 4: Validate data
    logger.info("Step 4/5: Validating data")
    validation_report = validate_data(df_engineered)
    
    # Step 5: Save by symbol
    logger.info("Step 5/5: Saving data by symbol")
    symbol_counts = save_by_symbol(df_engineered, output_s3_path)
    
    logger.info("=" * 80)
    logger.info("Pipeline completed successfully!")
    logger.info(f"Processed {validation_report['total_records']} total records")
    logger.info(f"Symbols processed: {list(symbol_counts.keys())}")
    logger.info("=" * 80)
    
    return symbol_counts, validation_report


# Example usage
if __name__ == "__main__":
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("CryptoTimeSeriesDataPrep") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .getOrCreate()
    
    # Example paths (update with your actual S3 paths)
    input_path = "s3://your-bucket/raw-data/*.json"
    output_path = "s3://your-bucket/processed-data"
    
    # Or for local testing:
    # input_path = "ts-model/*.json"
    # output_path = "ts-model/output"
    
    # Process data
    try:
        symbol_counts, validation = process_s3_data(spark, input_path, output_path)
        
        print("\n" + "=" * 80)
        print("PROCESSING SUMMARY")
        print("=" * 80)
        print(f"\nRecords per symbol:")
        for symbol, count in symbol_counts.items():
            print(f"  {symbol}: {count:,} records")
        
        print(f"\nValidation Report:")
        print(f"  Total records: {validation['total_records']:,}")
        print(f"  Duplicate timestamps: {validation['duplicate_timestamps']}")
        print(f"  Invalid prices: {validation['invalid_prices']}")
        
    finally:
        spark.stop()

