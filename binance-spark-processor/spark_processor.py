"""
PySpark Structured Streaming Processor with Feature Engineering
"""
from pyspark.sql import SparkSession, DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType,
    LongType, IntegerType, TimestampType, BooleanType
)
from datetime import datetime, timezone
import logging
from typing import Dict, Any
from config import Config

logger = logging.getLogger(__name__)


class SparkProcessor:
    """
    PySpark processor for real-time kline data with feature engineering.
    """
    
    def __init__(self):
        """Initialize Spark session with S3 configuration"""
        self.spark = self._create_spark_session()
        logger.info("SparkProcessor initialized")
    
    def _create_spark_session(self) -> SparkSession:
        """Create and configure Spark session with Spark UI enabled"""
        logger.info("Creating Spark session...")

        # Ensure spark-events directory exists (volume mount may override Dockerfile creation)
        import os
        spark_events_dir = "/app/logs/spark-events"
        os.makedirs(spark_events_dir, exist_ok=True)
        logger.info(f"Spark events directory: {spark_events_dir}")

        spark = SparkSession.builder \
            .appName(Config.SPARK_APP_NAME) \
            .master(Config.SPARK_MASTER) \
            .config("spark.hadoop.fs.s3a.access.key", Config.AWS_ACCESS_KEY_ID) \
            .config("spark.hadoop.fs.s3a.secret.key", Config.AWS_SECRET_ACCESS_KEY) \
            .config("spark.hadoop.fs.s3a.endpoint", f"s3.{Config.AWS_REGION}.amazonaws.com") \
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.ui.enabled", "true") \
            .config("spark.ui.port", "4040") \
            .config("spark.ui.host", "0.0.0.0") \
            .config("spark.eventLog.enabled", "true") \
            .config("spark.eventLog.dir", spark_events_dir) \
            .config("spark.history.fs.logDirectory", spark_events_dir) \
            .config("spark.ui.retainedJobs", "100") \
            .config("spark.ui.retainedStages", "100") \
            .config("spark.sql.ui.retainedExecutions", "100") \
            .config("spark.worker.ui.retainedExecutors", "100") \
            .config("spark.executor.metrics.enabled", "true") \
            .getOrCreate()

        # Set log level to reduce noise
        spark.sparkContext.setLogLevel("WARN")

        logger.info("✅ Spark session created successfully")
        logger.info(f"📊 Spark UI available at: http://0.0.0.0:4040")
        return spark
    
    def extract_kline_features(self, kline_msg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and transform kline features from raw message.
        
        Args:
            kline_msg: Normalized kline message from WebSocket
        
        Returns:
            Dictionary with extracted features
        """
        try:
            data = kline_msg.get("data", {})
            kline = data.get("k", {})
            
            # Extract kline start time as timestamp
            kline_start_time = int(kline.get("t", 0))
            timestamp = datetime.fromtimestamp(kline_start_time / 1000, tz=timezone.utc)
            
            # Extract all features
            features = {
                "timestamp": timestamp,
                "symbol": kline.get("s", kline_msg.get("symbol", "UNKNOWN")),
                "interval": kline.get("i", "1m"),
                "exchange": kline_msg.get("exchange", "binance"),
                "open": float(kline.get("o", 0)),
                "high": float(kline.get("h", 0)),
                "low": float(kline.get("l", 0)),
                "close": float(kline.get("c", 0)),
                "volume": float(kline.get("v", 0)),
                "number_of_trades": int(kline.get("n", 0)),
                "quote_volume": float(kline.get("q", 0)),
                "taker_buy_volume": float(kline.get("V", 0)),
                "taker_buy_quote_volume": float(kline.get("Q", 0)),
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting kline features: {e}")
            raise
    
    def engineer_features(self, df: DataFrame) -> DataFrame:
        """
        Engineer time series features using window functions.
        
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
        
        # Select columns in desired order (matching sample.csv)
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
        
        df_features = df_features.select(*output_columns)
        
        logger.info("Time series features engineered successfully")
        
        return df_features
    
    def process_kline_batch(self, kline_messages: list) -> list:
        """
        Process a batch of kline messages and return engineered features.
        
        Args:
            kline_messages: List of normalized kline messages
        
        Returns:
            List of processed data dictionaries with engineered features
        """
        if not kline_messages:
            return []
        
        try:
            logger.info(f"Processing batch of {len(kline_messages)} kline messages")
            
            # Extract features from each message
            extracted_features = [self.extract_kline_features(msg) for msg in kline_messages]
            
            # Convert to DataFrame
            df = self.spark.createDataFrame(extracted_features)
            
            # Engineer features
            df_engineered = self.engineer_features(df)
            
            # Convert back to list of dictionaries
            processed_data = []
            for row in df_engineered.collect():
                # Convert Row to dictionary and format timestamp
                row_dict = row.asDict()
                if row_dict.get('timestamp'):
                    row_dict['timestamp'] = row_dict['timestamp'].strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                processed_data.append(row_dict)
            
            logger.info(f"✅ Processed {len(processed_data)} records")
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Error processing kline batch: {e}")
            raise
    
    def process_single_kline(self, kline_msg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single kline message and return engineered features.
        
        Note: For single records, feature engineering with window functions will have
        limited context. It's more efficient to batch process multiple records.
        
        Args:
            kline_msg: Normalized kline message
        
        Returns:
            Dictionary with processed data and engineered features
        """
        result = self.process_kline_batch([kline_msg])
        return result[0] if result else None
    
    def stop(self):
        """Stop Spark session"""
        logger.info("Stopping Spark session...")
        if self.spark:
            self.spark.stop()
        logger.info("✅ Spark session stopped")


if __name__ == "__main__":
    # Test Spark processor
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        Config.validate()
        processor = SparkProcessor()
        
        # Test with sample kline message
        test_kline = {
            "event_type": "kline",
            "symbol": "BTCUSDT",
            "exchange": "binance",
            "data": {
                "e": "kline",
                "E": 1234567890000,
                "s": "BTCUSDT",
                "k": {
                    "t": 1234567890000,
                    "T": 1234567949999,
                    "s": "BTCUSDT",
                    "i": "1m",
                    "o": "50000.00",
                    "c": "50100.00",
                    "h": "50200.00",
                    "l": "49900.00",
                    "v": "100.5",
                    "n": 250,
                    "q": "5000000.0",
                    "V": "50.25",
                    "Q": "2500000.0",
                    "x": True
                }
            },
            "received_at": 1234567890.0,
            "client_timestamp": "2024-01-01T00:00:00.000Z"
        }
        
        # Process single kline
        processed = processor.process_single_kline(test_kline)
        print(f"\nProcessed kline:")
        for key, value in processed.items():
            print(f"  {key}: {value}")
        
        processor.stop()
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

