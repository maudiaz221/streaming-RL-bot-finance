"""
Alpaca WebSocket Client with automatic reconnection and Kinesis integration
"""
import json
import time
import logging
import websocket
from typing import List, Callable, Optional
from threading import Thread
from config import Config
from kinesis_producer import create_producer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlpacaWebSocketClient:
    """
    WebSocket client for Alpaca real-time market data streaming.
    Handles authentication, subscriptions, reconnection, and data forwarding to Kinesis.
    """
    
    def __init__(
        self,
        api_key: str = None,
        secret_key: str = None,
        websocket_url: str = None,
        symbols: List[str] = None,
        on_message_callback: Optional[Callable] = None
    ):
        # Configuration
        self.api_key = api_key or Config.ALPACA_API_KEY
        self.secret_key = secret_key or Config.ALPACA_SECRET_KEY
        self.websocket_url = websocket_url or Config.ALPACA_WEBSOCKET_URL
        self.symbols = symbols or Config.STOCK_SYMBOLS
        self.on_message_callback = on_message_callback
        
        # WebSocket instance
        self.ws = None
        self.is_authenticated = False
        self.is_subscribed = False
        
        # Reconnection settings
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = Config.MAX_RECONNECT_ATTEMPTS
        self.reconnect_backoff_base = Config.RECONNECT_BACKOFF_BASE
        self.should_reconnect = True
        
        # Statistics
        self.messages_received = 0
        self.last_message_time = None
        
        # Kinesis/File producer
        self.producer = create_producer()
        
        logger.info(f"AlpacaWebSocketClient initialized")
        logger.info(f"Tracking {len(self.symbols)} symbols: {', '.join(self.symbols[:5])}...")
    
    def on_open(self, ws):
        """Handle WebSocket connection opened"""
        logger.info("✅ WebSocket connection opened")
        self.reconnect_attempts = 0
        
        # Send authentication message
        auth_message = {
            "action": "auth",
            "key": self.api_key,
            "secret": self.secret_key
        }
        
        logger.info("Sending authentication...")
        ws.send(json.dumps(auth_message))
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            # Parse message
            data = json.loads(message)
            
            # Handle array of messages (Alpaca sends messages in arrays)
            if isinstance(data, list):
                for msg in data:
                    self._process_single_message(msg)
            else:
                self._process_single_message(data)
            
            self.messages_received += 1
            self.last_message_time = time.time()
            
            # Log statistics every 1000 messages
            if self.messages_received % 1000 == 0:
                stats = self.producer.get_statistics()
                logger.info(
                    f"Messages received: {self.messages_received} | "
                    f"Producer stats: {stats}"
                )
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {message[:100]}... Error: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _process_single_message(self, msg: dict):
        """Process a single message from Alpaca"""
        msg_type = msg.get("T")
        
        if msg_type == "success":
            # Authentication successful
            if msg.get("msg") == "authenticated":
                logger.info("✅ Authentication successful!")
                self.is_authenticated = True
                self._subscribe_to_symbols()
        
        elif msg_type == "subscription":
            # Subscription confirmation
            logger.info(f"✅ Subscription confirmed: {msg}")
            self.is_subscribed = True
        
        elif msg_type == "error":
            # Error message
            logger.error(f"❌ Error from Alpaca: {msg.get('msg')}")
        
        elif msg_type in ["t", "q", "b"]:
            # Market data: t=trade, q=quote, b=bar
            symbol = msg.get("S")
            
            # Add metadata
            msg["received_at"] = time.time()
            msg["client_timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            # Send to Kinesis/File
            partition_key = symbol if symbol else "unknown"
            self.producer.put_record(msg, partition_key=partition_key)
            
            # Call custom callback if provided
            if self.on_message_callback:
                self.on_message_callback(msg)
            
            # Debug logging for first few messages
            if self.messages_received < 10:
                logger.debug(f"Received {msg_type}: {json.dumps(msg)[:200]}")
        
        else:
            # Unknown message type
            logger.debug(f"Unknown message type '{msg_type}': {msg}")
    
    def _subscribe_to_symbols(self):
        """Subscribe to market data for configured symbols"""
        if not self.is_authenticated:
            logger.warning("Cannot subscribe: not authenticated yet")
            return
        
        # Subscribe to trades, quotes, and bars for all symbols
        subscribe_message = {
            "action": "subscribe",
            "trades": self.symbols,
            "quotes": self.symbols,
            "bars": self.symbols
        }
        
        logger.info(f"Subscribing to {len(self.symbols)} symbols...")
        logger.debug(f"Subscribe message: {subscribe_message}")
        
        self.ws.send(json.dumps(subscribe_message))
    
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"❌ WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed"""
        logger.warning(
            f"⚠️  WebSocket connection closed "
            f"(code: {close_status_code}, message: {close_msg})"
        )
        
        self.is_authenticated = False
        self.is_subscribed = False
        
        # Attempt reconnection if enabled
        if self.should_reconnect and self.reconnect_attempts < self.max_reconnect_attempts:
            self._reconnect()
        else:
            logger.info("Not reconnecting (max attempts reached or reconnection disabled)")
            self.producer.close()
    
    def _reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        self.reconnect_attempts += 1
        backoff_time = self.reconnect_backoff_base ** self.reconnect_attempts
        
        logger.info(
            f"🔄 Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} "
            f"in {backoff_time} seconds..."
        )
        
        time.sleep(backoff_time)
        self.connect()
    
    def connect(self):
        """Establish WebSocket connection"""
        logger.info(f"Connecting to {self.websocket_url}...")
        
        # Create WebSocket app
        self.ws = websocket.WebSocketApp(
            self.websocket_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Run forever (blocking call)
        self.ws.run_forever()
    
    def start(self):
        """Start the WebSocket client in a separate thread"""
        thread = Thread(target=self.connect, daemon=True)
        thread.start()
        logger.info("WebSocket client started in background thread")
        return thread
    
    def stop(self):
        """Stop the WebSocket client and close producer"""
        logger.info("Stopping WebSocket client...")
        self.should_reconnect = False
        
        if self.ws:
            self.ws.close()
        
        # Close producer (flush remaining data)
        self.producer.close()
        
        logger.info(f"✅ Client stopped. Total messages received: {self.messages_received}")


def main():
    """Main function to run the Alpaca WebSocket client"""
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
    
    # Create and start client
    client = AlpacaWebSocketClient()
    
    try:
        logger.info("Starting Alpaca WebSocket client...")
        logger.info(f"Press Ctrl+C to stop")
        
        # Run client (blocking)
        client.connect()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt received")
        client.stop()
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        client.stop()
        raise


if __name__ == "__main__":
    main()

