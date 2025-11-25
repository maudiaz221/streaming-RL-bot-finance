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
    
    # IMPORTANT: Read as TEXT first, then we'll parse by message type
    # The field "c" has different types in different message types:
    #   - Trades/Quotes: c = array of strings (conditions)
    #   - Bars: c = number (close price)
    # This causes schema conflicts if we read as JSON directly
    
    # Read as raw text (each line is one JSON object)
    text_df = spark.readStream \
        .format("text") \
        .option("maxFilesPerTrigger", "1") \
        .load(SparkConfig.LOCAL_INPUT_PATH)
    
    # Keep the raw JSON text - we'll parse it in each specific processing function
    # after filtering by message type
    logger.info(f"Data loaded from local files as text stream")
    
    return text_df


def process_trade_stream(df: "DataFrame") -> "DataFrame":
    """
    Process trade data stream with technical indicators
    
    Args:
        df: Streaming DataFrame (either raw from Kinesis or pre-parsed from local)
    
    Returns:
        Processed DataFrame with indicators and predictions
    """
    # Check if this is pre-parsed local data (has renamed columns)
    is_local_parsed = 'trade_timestamp' in df.columns
    
    if is_local_parsed:
        # Local mode with renamed columns - just convert timestamp
        from pyspark.sql.functions import to_timestamp
        df = df.withColumn(
            "timestamp",
            to_timestamp(col("trade_timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'")
        )
        # Rename symbol for consistency with technical indicators
        df = df.withColumnRenamed("symbol", "S")
        # price column 'p' is already named correctly
        # size column 's' is already named correctly
        
    else:
        # Kinesis mode - parse JSON
        if 'data' in df.columns:
            df = df.selectExpr("CAST(data AS STRING) as json_data")
            df = df.select(
                from_json(col("json_data"), TRADE_SCHEMA).alias("parsed")
            ).select("parsed.*")
        
        # Convert timestamp
        from pyspark.sql.functions import to_timestamp
        df = df.withColumn(
            "timestamp",
            to_timestamp(col("t"), "yyyy-MM-dd'T'HH:mm:ss'Z'")
        )
        
        # Filter only trade messages
        df = df.filter(col("T") == "t")
    
    # Add watermark for handling late data (only in streaming mode, not in batch)
    # We skip this since we're using foreachBatch
    # df = df.withWatermark("timestamp", SparkConfig.WATERMARK_DELAY)
    
    # Calculate moving averages on trade price
    logger.info("Calculating moving averages on trades...")
    df = calculate_moving_averages(df, symbol_col="S", price_col="price")
    
    # Rename for RL model compatibility
    df = df.withColumn("p", col("price"))
    df = df.withColumn("s", col("size"))
    
    # Enrich for RL model features
    logger.info("Enriching features for RL model...")
    df = enrich_for_rl_model(df)
    
    return df


def process_bar_stream(df: "DataFrame") -> "DataFrame":
    """
    Process bar (OHLCV) data stream with technical indicators
    
    Args:
        df: Streaming DataFrame (either raw from Kinesis or pre-parsed from local)
    
    Returns:
        Processed DataFrame with indicators
    """
    # Check if this is pre-parsed local data (has renamed columns)
    is_local_parsed = 'bar_timestamp' in df.columns
    
    if is_local_parsed:
        # Local mode with renamed columns - just convert timestamp
        from pyspark.sql.functions import to_timestamp
        df = df.withColumn(
            "timestamp",
            to_timestamp(col("bar_timestamp"), "yyyy-MM-dd'T'HH:mm:ss'Z'")
        )
        # Rename symbol for consistency with technical indicators
        df = df.withColumnRenamed("symbol", "S")
        df = df.withColumnRenamed("close", "c")  # For RSI, MACD, etc.
        
    else:
        # Kinesis mode - parse JSON
        if 'data' in df.columns:
            df = df.selectExpr("CAST(data AS STRING) as json_data")
            df = df.select(
                from_json(col("json_data"), BAR_SCHEMA).alias("parsed")
            ).select("parsed.*")
        
        # Convert timestamp 
        from pyspark.sql.functions import to_timestamp
        df = df.withColumn(
            "timestamp",
            to_timestamp(col("t"), "yyyy-MM-dd'T'HH:mm:ss'Z'")
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
    
    # Add aliases for RL model enrichment (it expects "p" for price and "s" for size)
    df = df.withColumn("p", col("c"))  # price = close for bars
    df = df.withColumn("s", col("volume"))  # size = volume for bars
    
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
    
    # Convert timestamp - handle potential column name conflicts
    from pyspark.sql.functions import to_timestamp
    df = df.withColumn(
        "timestamp_temp",
        to_timestamp(col("t"), "yyyy-MM-dd'T'HH:mm:ss'Z'")
    )
    
    if 'timestamp' in df.columns:
        df = df.drop('timestamp')
    
    df = df.withColumnRenamed("timestamp_temp", "timestamp")
    
    # Filter only quote messages
    df = df.filter(col("T") == "q")
    
    # Add watermark
    df = df.withWatermark("timestamp", SparkConfig.WATERMARK_DELAY)
    
    # Calculate bid-ask spread
    logger.info("Calculating bid-ask spread...")
    df = calculate_bid_ask_spread(df)
    
    return df


def process_and_write_batch(batch_df: "DataFrame", batch_id: int, output_path: str):
    """
    Process each micro-batch with indicators and write to storage
    This allows us to use row-based windows for technical indicators
    
    Args:
        batch_df: Raw micro-batch DataFrame
        batch_id: Batch ID
        output_path: Output path
    """
    if batch_df.count() > 0:
        logger.info(f"📦 Processing batch {batch_id} with {batch_df.count()} records")
        
        try:
            # Detect data type based on columns present
            columns = batch_df.columns
            
            if 'bar_timestamp' in columns:
                # Bar data - full technical indicators
                logger.info(f"   Type: BARS (OHLCV)")
                processed_batch = process_bar_stream(batch_df)
            elif 'trade_timestamp' in columns:
                # Trade data - simpler processing
                logger.info(f"   Type: TRADES (Real-time prices)")
                processed_batch = process_trade_stream(batch_df)
            else:
                logger.warning(f"   Unknown data type with columns: {columns}")
                processed_batch = batch_df
            
            # Write to parquet partitioned by symbol
            processed_batch.write \
                .mode("append") \
                .partitionBy("S") \
                .parquet(output_path)
            
            logger.info(f"✅ Batch {batch_id} processed and written successfully")
        except Exception as e:
            logger.error(f"❌ Error processing batch {batch_id}: {e}")
            raise
    else:
        logger.info(f"⚠️  Batch {batch_id} is empty, skipping")


def write_to_storage(df: "DataFrame", query_name: str, output_path: str):
    """
    Write streaming DataFrame to storage (S3 or local) using foreachBatch
    
    Args:
        df: Processed DataFrame
        query_name: Name for the streaming query
        output_path: Output path
    """
    
    logger.info(f"📤 Writing {query_name} to {output_path}")
    
    query = df.writeStream \
        .foreachBatch(lambda batch_df, batch_id: process_and_write_batch(batch_df, batch_id, output_path)) \
        .outputMode("append") \
        .option("checkpointLocation", f"{SparkConfig.get_checkpoint_path()}/{query_name}") \
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
            raw_text_df = read_from_local_files(spark)
            
            # Parse JSON and extract message type
            from pyspark.sql.functions import from_json, get_json_object
            from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType, ArrayType
            
            logger.info("🔧 Processing streaming data by message type...")
            
            # WORKAROUND for Spark schema inference issues: Use get_json_object to extract fields individually
            # This avoids the ambiguous reference errors from from_json()
            
            # Extract message type to filter
            raw_text_df = raw_text_df.withColumn("msg_type", get_json_object(col("value"), "$.T"))
            
            # Filter to only bar messages
            bar_text_df = raw_text_df.filter(col("msg_type") == "b")
            
            # Extract each field individually using get_json_object
            bar_df = bar_text_df.select(
                col("msg_type"),
                get_json_object(col("value"), "$.S").alias("symbol"),
                get_json_object(col("value"), "$.o").cast("double").alias("open"),
                get_json_object(col("value"), "$.h").cast("double").alias("high"),
                get_json_object(col("value"), "$.l").cast("double").alias("low"),
                get_json_object(col("value"), "$.c").cast("double").alias("close"),
                get_json_object(col("value"), "$.v").cast("long").alias("volume"),
                get_json_object(col("value"), "$.t").alias("bar_timestamp"),
                get_json_object(col("value"), "$.n").cast("long").alias("num_trades"),
                get_json_object(col("value"), "$.vw").cast("double").alias("vwap")
            )
            
            logger.info(f"Bar columns: {bar_df.columns}")
            
            # Also extract trade data
            logger.info("🔧 Extracting trade data...")
            trade_text_df = raw_text_df.filter(col("msg_type") == "t")
            
            trade_df = trade_text_df.select(
                col("msg_type"),
                get_json_object(col("value"), "$.S").alias("symbol"),
                get_json_object(col("value"), "$.i").cast("long").alias("trade_id"),
                get_json_object(col("value"), "$.x").alias("exchange"),
                get_json_object(col("value"), "$.p").cast("double").alias("price"),
                get_json_object(col("value"), "$.s").cast("long").alias("size"),
                get_json_object(col("value"), "$.z").alias("tape"),
                get_json_object(col("value"), "$.t").alias("trade_timestamp")
            )
            
            logger.info(f"Trade columns: {trade_df.columns}")
            
            # Pass raw data to foreachBatch - processing happens per batch
            bar_df_for_streaming = bar_df
            trade_df_for_streaming = trade_df
            
        else:
            raw_df = read_from_kinesis(spark)
            # For Kinesis, we'd need similar filtering logic here
            bar_df_for_streaming = raw_df
            trade_df_for_streaming = raw_df
        
        # Start multiple streaming queries
        logger.info("🚀 Starting streaming queries...")
        
        # Query 1: Process bars (once per minute)
        bar_output_path = f"{SparkConfig.get_output_path()}/processed_bars"
        bar_query = write_to_storage(bar_df_for_streaming, "bar_processing", bar_output_path)
        
        # Query 2: Process trades (real-time)
        trade_output_path = f"{SparkConfig.get_output_path()}/processed_trades"
        trade_query = write_to_storage(trade_df_for_streaming, "trade_processing", trade_output_path)
        
        logger.info("✅ All streaming queries started successfully!")
        logger.info(f"   Bar Query: {bar_query.name} (ID: {bar_query.id})")
        logger.info(f"   Trade Query: {trade_query.name} (ID: {trade_query.id})")
        logger.info("\n📊 Access Spark UI at: http://localhost:4040")
        logger.info("   Press Ctrl+C to stop the application\n")
        
        # Await termination of all queries
        spark.streams.awaitAnyTermination()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt received. Stopping gracefully...")
        for stream in spark.streams.active:
            logger.info(f"   Stopping {stream.name}...")
            stream.stop()
    except Exception as e:
        logger.error(f"❌ Error in streaming application: {e}")
        raise
    finally:
        logger.info("🛑 Stopping Spark session...")
        spark.stop()
        logger.info("✅ Application stopped")


if __name__ == "__main__":
    main()


