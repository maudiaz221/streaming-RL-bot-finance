#!/usr/bin/env python3
"""
Kinesis Stream Reader for EMR
Reads streaming data from AWS Kinesis and processes it with Spark Structured Streaming

Usage on EMR:
    spark-submit \
        --packages org.apache.spark:spark-sql-kinesis_2.12:3.3.0 \
        --conf spark.sql.streaming.schemaInference=true \
        kinesis_reader_emr.py
"""

import os
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, get_json_object
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType

# ============================================================================
# CONFIGURATION
# ============================================================================

# Read from environment variables (set these in EMR Step or in cluster config)
KINESIS_STREAM_NAME = os.getenv("KINESIS_STREAM_NAME", "stock-market-stream")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_OUTPUT_BUCKET = os.getenv("S3_OUTPUT_BUCKET", "s3://your-bucket-name")
S3_CHECKPOINT_PATH = f"{S3_OUTPUT_BUCKET}/checkpoints"
S3_OUTPUT_PATH = f"{S3_OUTPUT_BUCKET}/processed"

print(f"📊 Kinesis Stream: {KINESIS_STREAM_NAME}")
print(f"📍 Region: {AWS_REGION}")
print(f"💾 Output: {S3_OUTPUT_PATH}")


# ============================================================================
# SPARK SESSION
# ============================================================================

def create_spark_session():
    """Create Spark session configured for Kinesis streaming on EMR"""
    
    spark = SparkSession.builder \
        .appName("KinesisStreamReader") \
        .config("spark.sql.streaming.schemaInference", "true") \
        .config("spark.sql.shuffle.partitions", "10") \
        .config("spark.streaming.stopGracefullyOnShutdown", "true") \
        .getOrCreate()
    
    # Set log level
    spark.sparkContext.setLogLevel("WARN")
    
    print(f"✅ Spark Session Created: {spark.version}")
    return spark


# ============================================================================
# READ FROM KINESIS
# ============================================================================

def read_kinesis_stream(spark):
    """
    Read streaming data from Kinesis
    
    Returns DataFrame with columns:
    - data: binary (the actual payload)
    - partitionKey: string
    - sequenceNumber: string
    - approximateArrivalTimestamp: timestamp
    """
    
    print(f"📥 Connecting to Kinesis stream: {KINESIS_STREAM_NAME}")
    
    kinesis_df = spark.readStream \
        .format("kinesis") \
        .option("streamName", KINESIS_STREAM_NAME) \
        .option("region", AWS_REGION) \
        .option("initialPosition", "TRIM_HORIZON") \
        .load()
    
    print("✅ Connected to Kinesis stream")
    print(f"   Schema: {kinesis_df.schema}")
    
    return kinesis_df


# ============================================================================
# PARSE JSON DATA
# ============================================================================

def parse_json_data(kinesis_df):
    """
    Parse the JSON data from Kinesis binary payload
    
    The Kinesis 'data' field is binary, we need to:
    1. Cast to string
    2. Parse JSON
    3. Extract fields
    """
    
    print("🔧 Parsing JSON data from Kinesis payload...")
    
    # Step 1: Convert binary data to string
    string_df = kinesis_df.selectExpr("CAST(data AS STRING) as json_string")
    
    # Step 2: Extract message type to filter
    typed_df = string_df.withColumn(
        "msg_type", 
        get_json_object(col("json_string"), "$.T")
    )
    
    print("✅ JSON parsed, message types detected")
    return typed_df


# ============================================================================
# PROCESS DIFFERENT MESSAGE TYPES
# ============================================================================

def extract_trade_data(df):
    """Extract trade (T='t') data"""
    
    print("📊 Extracting trade data...")
    
    trade_df = df.filter(col("msg_type") == "t")
    
    # Extract fields using get_json_object
    trade_df = trade_df.select(
        get_json_object(col("json_string"), "$.T").alias("type"),
        get_json_object(col("json_string"), "$.S").alias("symbol"),
        get_json_object(col("json_string"), "$.p").cast("double").alias("price"),
        get_json_object(col("json_string"), "$.s").cast("long").alias("size"),
        get_json_object(col("json_string"), "$.t").alias("timestamp"),
        get_json_object(col("json_string"), "$.x").alias("exchange")
    )
    
    print(f"   Columns: {trade_df.columns}")
    return trade_df


def extract_bar_data(df):
    """Extract bar (T='b') data"""
    
    print("📈 Extracting bar data...")
    
    bar_df = df.filter(col("msg_type") == "b")
    
    bar_df = bar_df.select(
        get_json_object(col("json_string"), "$.T").alias("type"),
        get_json_object(col("json_string"), "$.S").alias("symbol"),
        get_json_object(col("json_string"), "$.o").cast("double").alias("open"),
        get_json_object(col("json_string"), "$.h").cast("double").alias("high"),
        get_json_object(col("json_string"), "$.l").cast("double").alias("low"),
        get_json_object(col("json_string"), "$.c").cast("double").alias("close"),
        get_json_object(col("json_string"), "$.v").cast("long").alias("volume"),
        get_json_object(col("json_string"), "$.t").alias("timestamp")
    )
    
    print(f"   Columns: {bar_df.columns}")
    return bar_df


def extract_quote_data(df):
    """Extract quote (T='q') data"""
    
    print("💱 Extracting quote data...")
    
    quote_df = df.filter(col("msg_type") == "q")
    
    quote_df = quote_df.select(
        get_json_object(col("json_string"), "$.T").alias("type"),
        get_json_object(col("json_string"), "$.S").alias("symbol"),
        get_json_object(col("json_string"), "$.bp").cast("double").alias("bid_price"),
        get_json_object(col("json_string"), "$.bs").cast("long").alias("bid_size"),
        get_json_object(col("json_string"), "$.ap").cast("double").alias("ask_price"),
        get_json_object(col("json_string"), "$.as").cast("long").alias("ask_size"),
        get_json_object(col("json_string"), "$.t").alias("timestamp")
    )
    
    print(f"   Columns: {quote_df.columns}")
    return quote_df


# ============================================================================
# WRITE TO S3
# ============================================================================

def write_to_s3(df, output_path, checkpoint_path, query_name):
    """
    Write streaming DataFrame to S3 in Parquet format
    
    Args:
        df: DataFrame to write
        output_path: S3 path for output data
        checkpoint_path: S3 path for checkpoints
        query_name: Name for the streaming query
    """
    
    print(f"📤 Writing {query_name} to {output_path}")
    
    query = df.writeStream \
        .format("parquet") \
        .outputMode("append") \
        .option("path", output_path) \
        .option("checkpointLocation", checkpoint_path) \
        .partitionBy("symbol") \
        .trigger(processingTime="10 seconds") \
        .queryName(query_name) \
        .start()
    
    print(f"✅ Query started: {query_name}")
    print(f"   ID: {query.id}")
    
    return query


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main streaming application"""
    
    print("=" * 70)
    print("🚀 Kinesis Stream Reader for EMR")
    print("=" * 70)
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Read from Kinesis
        kinesis_df = read_kinesis_stream(spark)
        
        # Parse JSON
        parsed_df = parse_json_data(kinesis_df)
        
        # Extract different message types
        trade_df = extract_trade_data(parsed_df)
        bar_df = extract_bar_data(parsed_df)
        quote_df = extract_quote_data(parsed_df)
        
        # Write each stream to separate S3 paths
        queries = []
        
        # Query 1: Trades
        trade_query = write_to_s3(
            trade_df,
            f"{S3_OUTPUT_PATH}/trades",
            f"{S3_CHECKPOINT_PATH}/trades",
            "trade_stream"
        )
        queries.append(trade_query)
        
        # Query 2: Bars
        bar_query = write_to_s3(
            bar_df,
            f"{S3_OUTPUT_PATH}/bars",
            f"{S3_CHECKPOINT_PATH}/bars",
            "bar_stream"
        )
        queries.append(bar_query)
        
        # Query 3: Quotes
        quote_query = write_to_s3(
            quote_df,
            f"{S3_OUTPUT_PATH}/quotes",
            f"{S3_CHECKPOINT_PATH}/quotes",
            "quote_stream"
        )
        queries.append(quote_query)
        
        print("\n" + "=" * 70)
        print("✅ All streaming queries started successfully!")
        print("=" * 70)
        print(f"📊 Processing data from Kinesis: {KINESIS_STREAM_NAME}")
        print(f"💾 Writing to S3: {S3_OUTPUT_PATH}")
        print(f"🔄 Checkpoint location: {S3_CHECKPOINT_PATH}")
        print("\n📈 Active Queries:")
        for q in queries:
            print(f"   - {q.name} (ID: {q.id})")
        print("\nPress Ctrl+C to stop")
        print("=" * 70 + "\n")
        
        # Wait for termination
        spark.streams.awaitAnyTermination()
        
    except KeyboardInterrupt:
        print("\n⚠️  Keyboard interrupt received. Stopping...")
        for stream in spark.streams.active:
            print(f"   Stopping {stream.name}...")
            stream.stop()
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        print("🛑 Stopping Spark session...")
        spark.stop()
        print("✅ Application stopped")


if __name__ == "__main__":
    main()



