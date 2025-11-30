"""
Main orchestrator for Binance Spark Processor
Coordinates WebSocket client, Spark processor, and S3 writer
"""
import logging
import logging.handlers
import signal
import sys
import time
import os
from queue import Queue, Empty
from threading import Thread, Event
from datetime import datetime, timezone
from config import Config
from websocket_client import BinanceWebSocketClient
from spark_processor import SparkProcessor
from s3_writer import S3Writer

# Configure logging to write to both console and file
log_dir = "/app/logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "app.log")

# Create formatters and handlers
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_formatter)

# File handler with rotation
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=50 * 1024 * 1024,  # 50 MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(log_formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)


class BinanceSparkOrchestrator:
    """
    Main orchestrator that coordinates:
    1. WebSocket client receiving kline data
    2. Writing raw data to S3
    3. Processing data with Spark
    4. Writing processed data to S3
    """
    
    def __init__(self):
        """Initialize all components"""
        logger.info("=" * 80)
        logger.info("Initializing Binance Spark Processor")
        logger.info("=" * 80)
        
        # Validate configuration
        Config.validate()
        
        # Create message queue for WebSocket -> Processor communication
        self.message_queue = Queue()
        
        # Initialize components
        self.ws_client = BinanceWebSocketClient(message_queue=self.message_queue)
        self.spark_processor = SparkProcessor()
        self.s3_writer = S3Writer()
        
        # Control flags
        self.shutdown_event = Event()
        self.ws_thread = None
        self.processor_thread = None
        
        # Statistics
        self.total_raw_written = 0
        self.total_processed_written = 0
        self.start_time = time.time()
        
        logger.info("✅ All components initialized successfully")
    
    def process_messages(self):
        """
        Process messages from the queue:
        1. Group messages by minute timestamp
        2. Write raw data to S3 (all symbols for that minute)
        3. Process with Spark
        4. Write processed data to S3 (all symbols for that minute)
        """
        logger.info("Starting message processor thread...")
        
        # Dictionary to batch messages by minute: {minute_timestamp: [messages]}
        minute_batches = {}
        last_check_time = time.time()
        check_interval = 5  # Check every 5 seconds
        
        while not self.shutdown_event.is_set():
            try:
                # Try to get message from queue with timeout
                try:
                    message = self.message_queue.get(timeout=1)
                    
                    # Extract timestamp and round to minute
                    kline_data = message.get('data', {}).get('k', {})
                    kline_start_time = int(kline_data.get('t', 0))
                    timestamp = datetime.fromtimestamp(kline_start_time / 1000, tz=timezone.utc)
                    # Round to minute (strip seconds)
                    minute_key = timestamp.replace(second=0, microsecond=0)
                    
                    # Add to appropriate minute batch
                    if minute_key not in minute_batches:
                        minute_batches[minute_key] = []
                    minute_batches[minute_key].append(message)
                    
                    logger.info(f"Added {message.get('symbol')} to minute batch {minute_key}")
                    
                except Empty:
                    # No message available
                    pass
                
                # Periodically check if any minute batches are complete and ready to process
                current_time = time.time()
                if current_time - last_check_time >= check_interval:
                    self._check_and_process_complete_batches(minute_batches)
                    last_check_time = current_time
            
            except Exception as e:
                logger.error(f"Error in message processor: {e}")
                import traceback
                traceback.print_exc()
        
        # Process remaining messages before shutdown
        if minute_batches:
            logger.info("Processing remaining minute batches before shutdown...")
            for minute_key, batch in minute_batches.items():
                self._process_minute_batch(minute_key, batch)
        
        logger.info("Message processor thread stopped")
    
    def _check_and_process_complete_batches(self, minute_batches: dict):
        """
        Check which minute batches are complete and ready to process.
        A batch is complete if we've moved past that minute (i.e., all symbols have reported).
        
        Args:
            minute_batches: Dictionary of {minute_timestamp: [messages]}
        """
        current_time = datetime.now(tz=timezone.utc).replace(second=0, microsecond=0)
        
        # Process batches that are at least 2 minutes old (to ensure all symbols have reported)
        completed_minutes = []
        for minute_key in list(minute_batches.keys()):
            # If the minute is at least 90 seconds old, consider it complete
            age_seconds = (current_time - minute_key).total_seconds()
            if age_seconds >= 90:
                completed_minutes.append(minute_key)
        
        # Process and remove completed batches
        for minute_key in completed_minutes:
            batch = minute_batches.pop(minute_key)
            logger.info(f"Processing completed minute batch: {minute_key} ({len(batch)} symbols)")
            self._process_minute_batch(minute_key, batch)
    
    def _process_minute_batch(self, minute_timestamp: datetime, batch: list):
        """
        Process a complete minute batch (all symbols for one minute).
        
        Args:
            minute_timestamp: The minute these klines belong to
            batch: List of kline messages for this minute
        """
        if not batch:
            return
        
        try:
            logger.info(f"Processing minute batch: {minute_timestamp} with {len(batch)} symbols")
            
            # Step 1: Write raw data to S3 (single parquet file with all symbols)
            self.s3_writer.write_raw_kline_batch_by_minute(batch, minute_timestamp)
            self.total_raw_written += len(batch)
            
            # Step 2: Process with Spark (batch processing)
            processed_data = self.spark_processor.process_kline_batch(batch)
            
            # Step 3: Write processed data to S3 (single parquet file with all symbols)
            self.s3_writer.write_processed_kline_batch_by_minute(processed_data, minute_timestamp)
            self.total_processed_written += len(processed_data)
            
            logger.info(
                f"✅ Minute batch processed: {minute_timestamp} | "
                f"{len(batch)} raw → {len(processed_data)} processed"
            )
            
        except Exception as e:
            logger.error(f"Error processing minute batch {minute_timestamp}: {e}")
            import traceback
            traceback.print_exc()
    def start(self):
        """Start all components"""
        logger.info("=" * 80)
        logger.info("Starting Binance Spark Processor")
        logger.info("=" * 80)
        
        # Start WebSocket client
        logger.info("Starting WebSocket client...")
        self.ws_thread = self.ws_client.start()
        
        # Start message processor
        logger.info("Starting message processor...")
        self.processor_thread = Thread(target=self.process_messages, daemon=True)
        self.processor_thread.start()
        
        logger.info("✅ All components started successfully")
        logger.info("=" * 80)
        logger.info("System is running. Press Ctrl+C to stop.")
        logger.info("=" * 80)
    
    def stop(self):
        """Stop all components gracefully"""
        logger.info("=" * 80)
        logger.info("Shutting down Binance Spark Processor...")
        logger.info("=" * 80)
        
        # Signal shutdown
        self.shutdown_event.set()
        
        # Stop WebSocket client
        logger.info("Stopping WebSocket client...")
        self.ws_client.stop()
        
        # Wait for processor thread to finish
        if self.processor_thread and self.processor_thread.is_alive():
            logger.info("Waiting for message processor to finish...")
            self.processor_thread.join(timeout=10)
        
        # Stop Spark processor
        logger.info("Stopping Spark processor...")
        self.spark_processor.stop()
        
        # Print final statistics
        elapsed_time = time.time() - self.start_time
        logger.info("=" * 80)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 80)
        logger.info(f"  Runtime: {elapsed_time:.2f} seconds")
        logger.info(f"  Raw klines written: {self.total_raw_written}")
        logger.info(f"  Processed klines written: {self.total_processed_written}")
        logger.info(f"  Messages remaining in queue: {self.message_queue.qsize()}")
        logger.info("=" * 80)
        logger.info("✅ Shutdown complete")
        logger.info("=" * 80)
    
    def run(self):
        """Run the orchestrator (blocking)"""
        self.start()
        
        try:
            # Keep main thread alive
            while not self.shutdown_event.is_set():
                time.sleep(1)
                
                # Log status every 60 seconds
                if int(time.time()) % 60 == 0:
                    elapsed = time.time() - self.start_time
                    logger.info(
                        f"📊 Status - Runtime: {elapsed:.0f}s | "
                        f"Raw: {self.total_raw_written} | "
                        f"Processed: {self.total_processed_written} | "
                        f"Queue: {self.message_queue.qsize()}"
                    )
        
        except KeyboardInterrupt:
            logger.info("\n⚠️  Keyboard interrupt received")
        
        finally:
            self.stop()


def signal_handler(signum, _frame):
    """Handle termination signals"""
    logger.info(f"\n⚠️  Received signal {signum}")
    sys.exit(0)


def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and run orchestrator
        orchestrator = BinanceSparkOrchestrator()
        orchestrator.run()
    
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

