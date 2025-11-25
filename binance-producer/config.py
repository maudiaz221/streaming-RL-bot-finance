"""
Configuration management for Binance WebSocket Producer
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
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
    
    # Binance Stream Types (trade, kline_1m, kline_5m, ticker, depth, aggTrade)
    BINANCE_STREAMS_RAW = os.getenv(
        'BINANCE_STREAMS',
        'trade,kline_1m'
    )
    BINANCE_STREAMS = [s.strip() for s in BINANCE_STREAMS_RAW.split(',') if s.strip()]
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # Kinesis Configuration
    KINESIS_STREAM_NAME = os.getenv('KINESIS_STREAM_NAME', 'crypto-market-stream')
    
    # Local Development Mode
    LOCAL_MODE = os.getenv('LOCAL_MODE', 'false').lower() == 'true'
    LOCAL_OUTPUT_PATH = os.getenv('LOCAL_OUTPUT_PATH', './data/stream_output')
    
    # Batch Configuration for Kinesis
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
    BATCH_TIMEOUT_SECONDS = int(os.getenv('BATCH_TIMEOUT_SECONDS', '1'))
    
    # Reconnection Configuration
    MAX_RECONNECT_ATTEMPTS = int(os.getenv('MAX_RECONNECT_ATTEMPTS', '5'))
    RECONNECT_BACKOFF_BASE = int(os.getenv('RECONNECT_BACKOFF_BASE', '2'))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        # Binance doesn't require API keys for public data streams
        if not cls.BINANCE_WEBSOCKET_URL:
            errors.append("BINANCE_WEBSOCKET_URL is required")
        
        if not cls.CRYPTO_SYMBOLS:
            errors.append("CRYPTO_SYMBOLS must contain at least one symbol")
        
        if not cls.BINANCE_STREAMS:
            errors.append("BINANCE_STREAMS must contain at least one stream type")
        
        if not cls.LOCAL_MODE:
            if not cls.AWS_REGION:
                errors.append("AWS_REGION is required when not in LOCAL_MODE")
            if not cls.KINESIS_STREAM_NAME:
                errors.append("KINESIS_STREAM_NAME is required when not in LOCAL_MODE")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True


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
        print(f"  - Kinesis Stream: {Config.KINESIS_STREAM_NAME}")
        print(f"  - Local Mode: {Config.LOCAL_MODE}")
    except ValueError as e:
        print(f"❌ Configuration validation failed:")
        print(e)


