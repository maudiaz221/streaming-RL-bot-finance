"""
Configuration management for Binance Spark Processor
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
if not env_path.exists():
    env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Configuration class for application settings"""
    
    # Binance Configuration
    BINANCE_WEBSOCKET_URL = os.getenv(
        'BINANCE_WEBSOCKET_URL',
        'wss://stream.binance.com:9443/ws'
    )
    
    # Crypto Symbols Configuration
    CRYPTO_SYMBOLS_RAW = os.getenv(
        'CRYPTO_SYMBOLS',
        'BTCUSDT,ETHUSDT,BNBUSDT'
    )
    CRYPTO_SYMBOLS = [s.strip().upper() for s in CRYPTO_SYMBOLS_RAW.split(',') if s.strip()]
    
    # Binance Stream Types (kline_1m for 1-minute candles)
    BINANCE_STREAMS_RAW = os.getenv(
        'BINANCE_STREAMS',
        'kline_1m'
    )
    BINANCE_STREAMS = [s.strip() for s in BINANCE_STREAMS_RAW.split(',') if s.strip()]
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # S3 Configuration
    S3_BUCKET = os.getenv('S3_BUCKET')
    S3_RAW_PREFIX = os.getenv('S3_RAW_PREFIX', 'raw')
    S3_CLEAN_PREFIX = os.getenv('S3_CLEAN_PREFIX', 'clean')
    
    # Spark Configuration
    SPARK_MASTER = os.getenv('SPARK_MASTER', 'local[*]')
    SPARK_APP_NAME = os.getenv('SPARK_APP_NAME', 'BinanceSparkProcessor')
    
    # Reconnection Configuration
    MAX_RECONNECT_ATTEMPTS = int(os.getenv('MAX_RECONNECT_ATTEMPTS', '5'))
    RECONNECT_BACKOFF_BASE = int(os.getenv('RECONNECT_BACKOFF_BASE', '2'))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.BINANCE_WEBSOCKET_URL:
            errors.append("BINANCE_WEBSOCKET_URL is required")
        
        if not cls.CRYPTO_SYMBOLS:
            errors.append("CRYPTO_SYMBOLS must contain at least one symbol")
        
        if not cls.BINANCE_STREAMS:
            errors.append("BINANCE_STREAMS must contain at least one stream type")
        
        if not cls.AWS_REGION:
            errors.append("AWS_REGION is required")
        
        if not cls.S3_BUCKET:
            errors.append("S3_BUCKET is required")
        
        if not cls.AWS_ACCESS_KEY_ID or not cls.AWS_SECRET_ACCESS_KEY:
            errors.append("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True
    
    @classmethod
    def get_s3_raw_path(cls, symbol: str, timestamp) -> str:
        """Generate S3 path for raw data with time partitioning"""
        year = timestamp.strftime('%Y')
        month = timestamp.strftime('%m')
        day = timestamp.strftime('%d')
        hour = timestamp.strftime('%H')
        minute = timestamp.strftime('%M')
        
        return f"{cls.S3_RAW_PREFIX}/year={year}/month={month}/day={day}/hour={hour}/minute={minute}"
    
    @classmethod
    def get_s3_clean_path(cls, symbol: str, timestamp) -> str:
        """Generate S3 path for processed data with time partitioning"""
        year = timestamp.strftime('%Y')
        month = timestamp.strftime('%m')
        day = timestamp.strftime('%d')
        hour = timestamp.strftime('%H')
        minute = timestamp.strftime('%M')
        
        return f"{cls.S3_CLEAN_PREFIX}/year={year}/month={month}/day={day}/hour={hour}/minute={minute}"


if __name__ == "__main__":
    # Test configuration
    try:
        Config.validate()
        print("✅ Configuration validated successfully!")
        print(f"\nConfiguration Summary:")
        print(f"  - Binance WebSocket URL: {Config.BINANCE_WEBSOCKET_URL}")
        print(f"  - Crypto Symbols: {', '.join(Config.CRYPTO_SYMBOLS)}")
        print(f"  - Stream Types: {', '.join(Config.BINANCE_STREAMS)}")
        print(f"  - AWS Region: {Config.AWS_REGION}")
        print(f"  - S3 Bucket: {Config.S3_BUCKET}")
        print(f"  - S3 Raw Prefix: {Config.S3_RAW_PREFIX}")
        print(f"  - S3 Clean Prefix: {Config.S3_CLEAN_PREFIX}")
        print(f"  - Spark Master: {Config.SPARK_MASTER}")
    except ValueError as e:
        print(f"❌ Configuration validation failed:")
        print(e)

