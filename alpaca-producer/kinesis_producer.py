"""
Kinesis Producer for batched message writing
"""
import json
import time
import boto3
import logging
from typing import List, Dict, Any
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)


class KinesisProducer:
    """Batched Kinesis producer for efficient data ingestion"""
    
    def __init__(self, stream_name: str = None, region: str = None):
        self.stream_name = stream_name or Config.KINESIS_STREAM_NAME
        self.region = region or Config.AWS_REGION
        self.batch = []
        self.batch_size = Config.BATCH_SIZE
        self.last_flush_time = time.time()
        self.batch_timeout = Config.BATCH_TIMEOUT_SECONDS
        
        # Statistics
        self.total_records_sent = 0
        self.total_batches_sent = 0
        self.failed_records = 0
        
        # Initialize Kinesis client
        self.kinesis_client = boto3.client(
            'kinesis',
            region_name=self.region,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
        )
        
        logger.info(f"KinesisProducer initialized for stream: {self.stream_name}")
    
    def put_record(self, data: Dict[Any, Any], partition_key: str = None):
        """
        Add a record to the batch. Flushes if batch is full or timeout reached.
        
        Args:
            data: Dictionary to send to Kinesis
            partition_key: Partition key (defaults to symbol or timestamp)
        """
        if partition_key is None:
            # Try to extract symbol, fallback to timestamp
            partition_key = data.get('S', str(int(time.time() * 1000)))
        
        record = {
            'Data': json.dumps(data),
            'PartitionKey': partition_key
        }
        
        self.batch.append(record)
        
        # Check if we should flush
        current_time = time.time()
        if (len(self.batch) >= self.batch_size or 
            current_time - self.last_flush_time >= self.batch_timeout):
            self.flush()
    
    def flush(self):
        """Send all batched records to Kinesis"""
        if not self.batch:
            return
        
        try:
            # Kinesis PutRecords supports up to 500 records per request
            # Split into chunks if necessary
            chunk_size = 500
            for i in range(0, len(self.batch), chunk_size):
                chunk = self.batch[i:i + chunk_size]
                
                response = self.kinesis_client.put_records(
                    Records=chunk,
                    StreamName=self.stream_name
                )
                
                # Check for failures
                failed_count = response.get('FailedRecordCount', 0)
                if failed_count > 0:
                    logger.warning(f"Failed to send {failed_count} records to Kinesis")
                    self.failed_records += failed_count
                    
                    # Log failed records for debugging
                    for idx, record_response in enumerate(response['Records']):
                        if 'ErrorCode' in record_response:
                            logger.error(
                                f"Record {idx} failed: {record_response['ErrorCode']} - "
                                f"{record_response.get('ErrorMessage', 'No message')}"
                            )
                
                successful = len(chunk) - failed_count
                self.total_records_sent += successful
                self.total_batches_sent += 1
                
                logger.debug(
                    f"Sent batch {self.total_batches_sent}: "
                    f"{successful}/{len(chunk)} records successful"
                )
            
            # Clear batch and reset timer
            self.batch = []
            self.last_flush_time = time.time()
            
        except Exception as e:
            logger.error(f"Error flushing batch to Kinesis: {str(e)}")
            self.failed_records += len(self.batch)
            self.batch = []  # Clear batch to avoid retry loops
    
    def get_statistics(self) -> Dict[str, int]:
        """Get producer statistics"""
        return {
            'total_records_sent': self.total_records_sent,
            'total_batches_sent': self.total_batches_sent,
            'failed_records': self.failed_records,
            'current_batch_size': len(self.batch)
        }
    
    def close(self):
        """Flush remaining records and close"""
        logger.info("Closing KinesisProducer, flushing remaining records...")
        self.flush()
        logger.info(f"Final statistics: {self.get_statistics()}")


class LocalFileProducer:
    """Local file-based producer for development without AWS"""
    
    def __init__(self, output_path: str = None):
        self.output_path = output_path or Config.LOCAL_OUTPUT_PATH
        self.batch = []
        self.batch_size = Config.BATCH_SIZE
        self.last_flush_time = time.time()
        self.batch_timeout = Config.BATCH_TIMEOUT_SECONDS
        self.file_counter = 0
        
        # Create output directory
        import os
        os.makedirs(self.output_path, exist_ok=True)
        
        logger.info(f"LocalFileProducer initialized, output path: {self.output_path}")
    
    def put_record(self, data: Dict[Any, Any], partition_key: str = None):
        """Add record to batch"""
        self.batch.append(data)
        
        # Check if we should flush
        current_time = time.time()
        if (len(self.batch) >= self.batch_size or 
            current_time - self.last_flush_time >= self.batch_timeout):
            self.flush()
    
    def flush(self):
        """Write batch to JSON file"""
        if not self.batch:
            return
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.output_path}/batch_{timestamp}_{self.file_counter}.json"
            
            with open(filename, 'w') as f:
                json.dump(self.batch, f, indent=2)
            
            logger.info(f"Written {len(self.batch)} records to {filename}")
            
            self.batch = []
            self.last_flush_time = time.time()
            self.file_counter += 1
            
        except Exception as e:
            logger.error(f"Error writing batch to file: {str(e)}")
            self.batch = []
    
    def get_statistics(self) -> Dict[str, int]:
        """Get producer statistics"""
        return {
            'files_written': self.file_counter,
            'current_batch_size': len(self.batch)
        }
    
    def close(self):
        """Flush remaining records"""
        logger.info("Closing LocalFileProducer, flushing remaining records...")
        self.flush()


def create_producer():
    """Factory function to create appropriate producer based on configuration"""
    if Config.LOCAL_MODE:
        return LocalFileProducer()
    else:
        return KinesisProducer()

