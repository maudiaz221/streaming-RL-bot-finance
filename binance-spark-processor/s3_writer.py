"""
S3 Writer for raw and processed parquet files with time-based partitioning
"""
import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from typing import Dict, Any
import logging
import io
from config import Config

logger = logging.getLogger(__name__)


class S3Writer:
    """
    Handles writing raw and processed parquet files to S3 with time-based partitioning.
    """
    
    def __init__(self):
        """Initialize S3 client with configuration"""
        self.s3_client = boto3.client(
            's3',
            region_name=Config.AWS_REGION,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
        )
        self.bucket = Config.S3_BUCKET
        logger.info(f"S3Writer initialized for bucket: {self.bucket}")
    
    def write_raw_kline_batch_by_minute(self, kline_batch: list, timestamp: datetime):
        """
        Write a batch of raw klines (all symbols for one minute) to S3 as a single parquet file.
        
        Args:
            kline_batch: List of kline data dictionaries (all symbols for the same minute)
            timestamp: Timestamp for partitioning (the minute these klines belong to)
        """
        if not kline_batch:
            return
        
        try:
            # Convert batch to DataFrame (each row is one symbol)
            df = pd.DataFrame(kline_batch)
            
            # Generate S3 path with time partitioning (no symbol in path)
            s3_path = Config.get_s3_raw_path('', timestamp)
            
            # Create filename with just the timestamp (contains all symbols)
            filename = f"klines_{timestamp.strftime('%Y%m%d_%H%M%S')}.parquet"
            s3_key = f"{s3_path}/{filename}"
            
            # Convert to parquet in memory
            table = pa.Table.from_pandas(df)
            parquet_buffer = io.BytesIO()
            pq.write_table(table, parquet_buffer, compression='snappy')
            parquet_buffer.seek(0)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=parquet_buffer.getvalue(),
                ContentType='application/octet-stream'
            )
            
            logger.info(f"✅ Raw batch ({len(kline_batch)} symbols) written to s3://{self.bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"❌ Error writing raw batch to S3: {e}")
            raise
    
    def write_processed_kline_batch_by_minute(self, processed_batch: list, timestamp: datetime):
        """
        Write a batch of processed klines (all symbols for one minute) to S3 as a single parquet file.
        
        Args:
            processed_batch: List of processed data dictionaries (all symbols for the same minute)
            timestamp: Timestamp for partitioning (the minute these klines belong to)
        """
        if not processed_batch:
            return
        
        try:
            # Convert batch to DataFrame (each row is one symbol)
            df = pd.DataFrame(processed_batch)
            
            # Generate S3 path with time partitioning (no symbol in path)
            s3_path = Config.get_s3_clean_path('', timestamp)
            
            # Create filename with just the timestamp (contains all symbols)
            filename = f"klines_{timestamp.strftime('%Y%m%d_%H%M%S')}.parquet"
            s3_key = f"{s3_path}/{filename}"
            
            # Convert to parquet in memory
            table = pa.Table.from_pandas(df)
            parquet_buffer = io.BytesIO()
            pq.write_table(table, parquet_buffer, compression='snappy')
            parquet_buffer.seek(0)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=parquet_buffer.getvalue(),
                ContentType='application/octet-stream'
            )
            
            logger.info(f"✅ Processed batch ({len(processed_batch)} symbols) written to s3://{self.bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"❌ Error writing processed batch to S3: {e}")
            raise


if __name__ == "__main__":
    # Test S3 writer
    logging.basicConfig(level=logging.INFO)
    
    try:
        Config.validate()
        writer = S3Writer()
        
        # Test raw write with batch (all symbols for one minute)
        test_klines = [
            {
                'event_type': 'kline',
                'symbol': 'BTCUSDT',
                'exchange': 'binance',
                'data': {'test': 'data'},
                'received_at': 1234567890.0,
                'client_timestamp': '2024-01-01T00:00:00.000Z'
            },
            {
                'event_type': 'kline',
                'symbol': 'ETHUSDT',
                'exchange': 'binance',
                'data': {'test': 'data'},
                'received_at': 1234567890.0,
                'client_timestamp': '2024-01-01T00:00:00.000Z'
            },
            {
                'event_type': 'kline',
                'symbol': 'BNBUSDT',
                'exchange': 'binance',
                'data': {'test': 'data'},
                'received_at': 1234567890.0,
                'client_timestamp': '2024-01-01T00:00:00.000Z'
            }
        ]
        
        timestamp = datetime.now()
        s3_key = writer.write_raw_kline_batch_by_minute(test_klines, timestamp)
        print(f"Test write successful: {s3_key}")
        
    except Exception as e:
        print(f"Test failed: {e}")

