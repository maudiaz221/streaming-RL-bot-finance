"""
Configuration for PySpark Structured Streaming
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class SparkConfig:
    """Spark streaming configuration"""
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # Kinesis Configuration
    KINESIS_STREAM_NAME = os.getenv('KINESIS_STREAM_NAME', 'stock-market-stream')
    KINESIS_ENDPOINT = f"https://kinesis.{AWS_REGION}.amazonaws.com"
    
    # S3 Configuration
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'stock-trading-data')
    S3_OUTPUT_PATH = f"s3a://{S3_BUCKET_NAME}/processed-data"
    S3_CHECKPOINT_PATH = f"s3a://{S3_BUCKET_NAME}/checkpoints"
    S3_MODEL_PATH = f"s3a://{S3_BUCKET_NAME}/models"
    
    # Local Mode (for development)
    LOCAL_MODE = os.getenv('LOCAL_MODE', 'false').lower() == 'true'
    LOCAL_INPUT_PATH = os.getenv('LOCAL_INPUT_PATH', './data/stream_output')
    LOCAL_OUTPUT_PATH = os.getenv('LOCAL_OUTPUT_PATH', './data/processed')
    LOCAL_CHECKPOINT_PATH = os.getenv('LOCAL_CHECKPOINT_PATH', './data/checkpoints')
    
    # Spark Configuration
    APP_NAME = "StockMarketStreaming"
    BATCH_INTERVAL_SECONDS = int(os.getenv('BATCH_INTERVAL_SECONDS', '10'))
    WATERMARK_DELAY = os.getenv('WATERMARK_DELAY', '30 seconds')
    
    # Window Configuration
    TUMBLING_WINDOW = os.getenv('TUMBLING_WINDOW', '1 minute')
    SLIDING_WINDOW_5MIN = os.getenv('SLIDING_WINDOW_5MIN', '5 minutes')
    SLIDING_WINDOW_15MIN = os.getenv('SLIDING_WINDOW_15MIN', '15 minutes')
    SLIDING_WINDOW_1HOUR = os.getenv('SLIDING_WINDOW_1HOUR', '1 hour')
    
    # Technical Indicators Configuration
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
    MACD_FAST = int(os.getenv('MACD_FAST', '12'))
    MACD_SLOW = int(os.getenv('MACD_SLOW', '26'))
    MACD_SIGNAL = int(os.getenv('MACD_SIGNAL', '9'))
    BB_PERIOD = int(os.getenv('BB_PERIOD', '20'))
    BB_STD_DEV = int(os.getenv('BB_STD_DEV', '2'))
    
    # RL Model Configuration
    RL_MODEL_ENABLED = os.getenv('RL_MODEL_ENABLED', 'true').lower() == 'true'
    RL_MODEL_NAME = os.getenv('RL_MODEL_NAME', 'ppo_trading_model.zip')
    
    @classmethod
    def get_output_path(cls):
        """Get output path based on mode"""
        return cls.LOCAL_OUTPUT_PATH if cls.LOCAL_MODE else cls.S3_OUTPUT_PATH
    
    @classmethod
    def get_checkpoint_path(cls):
        """Get checkpoint path based on mode"""
        return cls.LOCAL_CHECKPOINT_PATH if cls.LOCAL_MODE else cls.S3_CHECKPOINT_PATH
    
    @classmethod
    def get_model_path(cls):
        """Get model path"""
        if cls.LOCAL_MODE:
            return f"../rl-model/models/{cls.RL_MODEL_NAME}"
        else:
            return f"{cls.S3_MODEL_PATH}/{cls.RL_MODEL_NAME}"


if __name__ == "__main__":
    print("Spark Configuration Summary:")
    print(f"  - Local Mode: {SparkConfig.LOCAL_MODE}")
    print(f"  - AWS Region: {SparkConfig.AWS_REGION}")
    print(f"  - Kinesis Stream: {SparkConfig.KINESIS_STREAM_NAME}")
    print(f"  - S3 Bucket: {SparkConfig.S3_BUCKET_NAME}")
    print(f"  - Output Path: {SparkConfig.get_output_path()}")
    print(f"  - Checkpoint Path: {SparkConfig.get_checkpoint_path()}")
    print(f"  - Batch Interval: {SparkConfig.BATCH_INTERVAL_SECONDS}s")
    print(f"  - RL Model Enabled: {SparkConfig.RL_MODEL_ENABLED}")

