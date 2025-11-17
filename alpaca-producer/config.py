"""
Configuration management for Alpaca WebSocket Producer
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    """Configuration class for application settings"""
    
    # Alpaca Configuration
    ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
    ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
    ALPACA_WEBSOCKET_URL = os.getenv(
        'ALPACA_WEBSOCKET_URL',
        'wss://stream.data.alpaca.markets/v2/iex'
    )
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # Kinesis Configuration
    KINESIS_STREAM_NAME = os.getenv('KINESIS_STREAM_NAME', 'stock-market-stream')
    
    # Stock Symbols Configuration
    STOCK_SYMBOLS_RAW = os.getenv(
        'STOCK_SYMBOLS',
        'AAPL,TSLA,NVDA,MSFT,GOOGL,AMZN,META,SPY,QQQ,AMD'
    )
    STOCK_SYMBOLS = [s.strip() for s in STOCK_SYMBOLS_RAW.split(',') if s.strip()]
    
    # Local Development Mode
    LOCAL_MODE = os.getenv('LOCAL_MODE', 'false').lower() == 'true'
    LOCAL_OUTPUT_PATH = os.getenv('LOCAL_OUTPUT_PATH', './data/stream_output')
    
    # Batch Configuration for Kinesis
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))
    BATCH_TIMEOUT_SECONDS = int(os.getenv('BATCH_TIMEOUT_SECONDS', '5'))
    
    # Reconnection Configuration
    MAX_RECONNECT_ATTEMPTS = int(os.getenv('MAX_RECONNECT_ATTEMPTS', '5'))
    RECONNECT_BACKOFF_BASE = int(os.getenv('RECONNECT_BACKOFF_BASE', '2'))
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.ALPACA_API_KEY:
            errors.append("ALPACA_API_KEY is required")
        if not cls.ALPACA_SECRET_KEY:
            errors.append("ALPACA_SECRET_KEY is required")
        
        if not cls.LOCAL_MODE:
            if not cls.AWS_REGION:
                errors.append("AWS_REGION is required when not in LOCAL_MODE")
            if not cls.KINESIS_STREAM_NAME:
                errors.append("KINESIS_STREAM_NAME is required when not in LOCAL_MODE")
        
        if not cls.STOCK_SYMBOLS:
            errors.append("STOCK_SYMBOLS must contain at least one symbol")
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True


if __name__ == "__main__":
    # Test configuration
    try:
        Config.validate()
        print("✅ Configuration validated successfully!")
        print(f"\nConfiguration Summary:")
        print(f"  - Alpaca URL: {Config.ALPACA_WEBSOCKET_URL}")
        print(f"  - Stock Symbols: {', '.join(Config.STOCK_SYMBOLS)}")
        print(f"  - AWS Region: {Config.AWS_REGION}")
        print(f"  - Kinesis Stream: {Config.KINESIS_STREAM_NAME}")
        print(f"  - Local Mode: {Config.LOCAL_MODE}")
    except ValueError as e:
        print(f"❌ Configuration validation failed:")
        print(e)

