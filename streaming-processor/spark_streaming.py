"""
Main PySpark Structured Streaming application for stock market data processing
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, expr
from pyspark.sql.types import StringType
import logging
import sys

from config import SparkConfig
from alpaca_data_transformations import (
    TRADE_SCHEMA, QUOTE_SCHEMA, BAR_SCHEMA,
    calculate_moving_averages,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_bid_ask_spread,
    enrich_for_rl_model
)
from rl_model_inference import add_rl_predictions, simple_rule_based_strategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def create_spark_session() -> SparkSession:
    """Create and configure Spark session"""
    
    builder = SparkSession.builder \
        .appName(SparkConfig.APP_NAME)
    
    if not SparkConfig.LOCAL_MODE:
        # Add Kinesis package for AWS
        builder = builder.config(
            "spark.jars.packages",
            "org.apache.spark:spark-sql-kinesis_2.12:3.4.0"
        )
        
        # S3 configuration
        builder = builder.config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
            .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                    "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")
        
        if SparkConfig.AWS_ACCESS_KEY_ID and SparkConfig.AWS_SECRET_ACCESS_KEY:
            builder = builder.config("spark.hadoop.fs.s3a.access.key", SparkConfig.AWS_ACCESS_KEY_ID) \
                .config("spark.hadoop.fs.s3a.secret.key", SparkConfig.AWS_SECRET_ACCESS_KEY)
    
    # Memory and performance tuning
    builder = builder.config("spark.sql.streaming.checkpointLocation", SparkConfig.get_checkpoint_path()) \
        .config("spark.sql.shuffle.partitions", "10") \
        .config("spark.sql.streaming.schemaInference", "true")
    
    spark = builder.getOrCreate()
    
    # Set log level
    spark.sparkContext.setLogLevel("WARN")
    
    logger.info(f"✅ Spark session created: {SparkConfig.APP_NAME}")
    logger.info(f"   Local Mode: {SparkConfig.LOCAL_MODE}")
    logger.info(f"   Output Path: {SparkConfig.get_output_path()}")
    
    return spark


def read_from_kinesis(spark: SparkSession) -> "DataFrame":
    """Read streaming data from Kinesis"""
    
    logger.info(f"📥 Reading from Kinesis stream: {SparkConfig.KINESIS_STREAM_NAME}")
    
    kinesis_df = spark.readStream \
        .format("kinesis") \
        .option("streamName", SparkConfig.KINESIS_STREAM_NAME) \
        .option("region", SparkConfig.AWS_REGION) \
        .option("initialPosition", "TRIM_HORIZON") \
        .option("endpointUrl", SparkConfig.KINESIS_ENDPOINT) \
        .load()
    
    return kinesis_df


def read_from_local_files(spark: SparkSession) -> "DataFrame":
    """Read streaming data from local JSON files (for development)"""
    
    logger.info(f"📂 Reading from local files: {SparkConfig.LOCAL_INPUT_PATH}")
    
    # Read JSON files as stream
    file_df = spark.readStream \
        .format("json") \
        .schema(TRADE_SCHEMA) \
        .option("maxFilesPerTrigger", "1") \
        .load(SparkConfig.LOCAL_INPUT_PATH)
    
    return file_df


def process_trade_stream(df: "DataFrame") -> "DataFrame":
    """
    Process trade data stream with technical indicators
    
    Args:
        df: Raw streaming DataFrame
    
    Returns:
        Processed DataFrame with indicators and predictions
    """
    # Parse JSON from Kinesis data column (if present)
    if 'data' in df.columns:
        df = df.selectExpr("CAST(data AS STRING) as json_data")
        df = df.select(
            from_json(col("json_data"), TRADE_SCHEMA).alias("parsed")
        ).select("parsed.*")
    
    # Convert timestamp
    df = df.withColumn(
        "timestamp",
        expr("to_timestamp(t, \"yyyy-MM-dd'T'HH:mm:ss.SSS'Z'\")")
    )
    
    # Filter only trade messages
    df = df.filter(col("T") == "t")
    
    # Add watermark for handling late data
    df = df.withWatermark("timestamp", SparkConfig.WATERMARK_DELAY)
    
    # Calculate moving averages
    logger.info("Calculating moving averages...")
    df = calculate_moving_averages(df, symbol_col="S", price_col="p")
    
    # Enrich for RL model features
    logger.info("Enriching features for RL model...")
    df = enrich_for_rl_model(df)
    
    return df


def process_bar_stream(df: "DataFrame") -> "DataFrame":
    """
    Process bar (OHLCV) data stream with technical indicators
    
    Args:
        df: Raw streaming DataFrame
    
    Returns:
        Processed DataFrame with indicators
    """
    # Parse JSON from Kinesis (if present)
    if 'data' in df.columns:
        df = df.selectExpr("CAST(data AS STRING) as json_data")
        df = df.select(
            from_json(col("json_data"), BAR_SCHEMA).alias("parsed")
        ).select("parsed.*")
    
    # Convert timestamp
    df = df.withColumn(
        "timestamp",
        expr("to_timestamp(t, \"yyyy-MM-dd'T'HH:mm:ss'Z'\")")
    )
    
    # Filter only bar messages
    df = df.filter(col("T") == "b")
    
    # Add watermark
    df = df.withWatermark("timestamp", SparkConfig.WATERMARK_DELAY)
    
    # Calculate technical indicators
    logger.info("Calculating RSI...")
    df = calculate_rsi(df, period=SparkConfig.RSI_PERIOD, symbol_col="S", price_col="c")
    
    logger.info("Calculating MACD...")
    df = calculate_macd(
        df,
        fast_period=SparkConfig.MACD_FAST,
        slow_period=SparkConfig.MACD_SLOW,
        signal_period=SparkConfig.MACD_SIGNAL,
        symbol_col="S",
        price_col="c"
    )
    
    logger.info("Calculating Bollinger Bands...")
    df = calculate_bollinger_bands(
        df,
        period=SparkConfig.BB_PERIOD,
        std_dev=SparkConfig.BB_STD_DEV,
        symbol_col="S",
        price_col="c"
    )
    
    # Calculate moving averages on close price
    df = calculate_moving_averages(df, symbol_col="S", price_col="c")
    
    # Enrich for RL
    df = enrich_for_rl_model(df)
    
    # Add RL predictions or rule-based strategy
    if SparkConfig.RL_MODEL_ENABLED:
        logger.info("Adding RL model predictions...")
        try:
            model_path = SparkConfig.get_model_path()
            df = add_rl_predictions(df, model_path)
        except Exception as e:
            logger.warning(f"RL model prediction failed: {e}. Using rule-based strategy.")
            df = simple_rule_based_strategy(df)
    else:
        logger.info("Using rule-based trading strategy...")
        df = simple_rule_based_strategy(df)
    
    return df


def process_quote_stream(df: "DataFrame") -> "DataFrame":
    """
    Process quote data stream
    
    Args:
        df: Raw streaming DataFrame
    
    Returns:
        Processed DataFrame with bid-ask spread
    """
    # Parse JSON from Kinesis (if present)
    if 'data' in df.columns:
        df = df.selectExpr("CAST(data AS STRING) as json_data")
        df = df.select(
            from_json(col("json_data"), QUOTE_SCHEMA).alias("parsed")
        ).select("parsed.*")
    
    # Convert timestamp
    df = df.withColumn(
        "timestamp",
        expr("to_timestamp(t, \"yyyy-MM-dd'T'HH:mm:ss'Z'\")")
    )
    
    # Filter only quote messages
    df = df.filter(col("T") == "q")
    
    # Add watermark
    df = df.withWatermark("timestamp", SparkConfig.WATERMARK_DELAY)
    
    # Calculate bid-ask spread
    logger.info("Calculating bid-ask spread...")
    df = calculate_bid_ask_spread(df)
    
    return df


def write_to_storage(df: "DataFrame", query_name: str, output_path: str):
    """
    Write streaming DataFrame to storage (S3 or local)
    
    Args:
        df: Processed DataFrame
        query_name: Name for the streaming query
        output_path: Output path
    """
    
    logger.info(f"📤 Writing {query_name} to {output_path}")
    
    query = df.writeStream \
        .format("parquet") \
        .outputMode("append") \
        .option("path", output_path) \
        .option("checkpointLocation", f"{SparkConfig.get_checkpoint_path()}/{query_name}") \
        .partitionBy("S") \
        .trigger(processingTime=f"{SparkConfig.BATCH_INTERVAL_SECONDS} seconds") \
        .queryName(query_name) \
        .start()
    
    return query


def main():
    """Main function to run the streaming application"""
    
    logger.info("🚀 Starting Stock Market Streaming Application")
    logger.info("=" * 70)
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Read streaming data
        if SparkConfig.LOCAL_MODE:
            raw_df = read_from_local_files(spark)
        else:
            raw_df = read_from_kinesis(spark)
        
        # Process different message types
        # Note: In production, you might want to separate these based on message type
        # For simplicity, we'll process as bar data (most complete)
        
        logger.info("🔧 Processing streaming data...")
        processed_df = process_bar_stream(raw_df)
        
        # Write to storage
        output_path = f"{SparkConfig.get_output_path()}/processed_bars"
        query = write_to_storage(processed_df, "bar_processing", output_path)
        
        logger.info("✅ Streaming query started successfully!")
        logger.info(f"   Query Name: {query.name}")
        logger.info(f"   Query ID: {query.id}")
        logger.info("\n📊 Access Spark UI at: http://localhost:4040")
        logger.info("   Press Ctrl+C to stop the application\n")
        
        # Await termination
        query.awaitTermination()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt received. Stopping gracefully...")
        spark.streams.active[0].stop() if spark.streams.active else None
    except Exception as e:
        logger.error(f"❌ Error in streaming application: {e}")
        raise
    finally:
        logger.info("🛑 Stopping Spark session...")
        spark.stop()
        logger.info("✅ Application stopped")


if __name__ == "__main__":
    main()

