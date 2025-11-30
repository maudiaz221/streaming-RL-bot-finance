"""
Binance WebSocket Client with queue-based message passing
"""
import json
import time
import logging
import websocket
from typing import List, Callable, Optional
from threading import Thread
from queue import Queue
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)


class BinanceWebSocketClient:
    """
    WebSocket client for Binance real-time market data streaming.
    Handles subscriptions, reconnection, and queue-based message passing to Spark processor.
    """
    
    def __init__(
        self,
        websocket_url: str = None,
        symbols: List[str] = None,
        streams: List[str] = None,
        message_queue: Optional[Queue] = None
    ):
        # Configuration
        self.websocket_url = websocket_url or Config.BINANCE_WEBSOCKET_URL
        self.symbols = symbols or Config.CRYPTO_SYMBOLS
        self.streams = streams or Config.BINANCE_STREAMS
        self.message_queue = message_queue or Queue()
        
        # Build combined stream URL
        self.stream_url = self._build_stream_url()
        
        # WebSocket instance
        self.ws = None
        
        # Reconnection settings
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = Config.MAX_RECONNECT_ATTEMPTS
        self.reconnect_backoff_base = Config.RECONNECT_BACKOFF_BASE
        self.should_reconnect = True
        
        # Statistics
        self.messages_received = 0
        self.kline_messages_sent = 0
        self.kline_in_progress_skipped = 0
        self.last_message_time = None
        
        logger.info(f"BinanceWebSocketClient initialized")
        logger.info(f"Tracking {len(self.symbols)} symbols: {', '.join(self.symbols[:5])}...")
        logger.info(f"Streams: {', '.join(self.streams)}")
    
    def _build_stream_url(self) -> str:
        """Build the combined WebSocket stream URL for all symbols and streams"""
        # Binance uses lowercase symbols
        symbol_streams = []
        for symbol in self.symbols:
            symbol_lower = symbol.lower()
            for stream in self.streams:
                # Format: btcusdt@kline_1m
                symbol_streams.append(f"{symbol_lower}@{stream}")
        
        # Combined stream URL format
        combined_streams = '/'.join(symbol_streams)
        
        if len(symbol_streams) == 1:
            # Single stream: wss://stream.binance.com:9443/ws/<stream>
            return f"{self.websocket_url}/{symbol_streams[0]}"
        else:
            # Multiple streams: wss://stream.binance.com:9443/stream?streams=...
            return f"{self.websocket_url.replace('/ws', '/stream')}?streams={combined_streams}"
    
    def on_open(self, ws):
        """Handle WebSocket connection opened"""
        logger.info("✅ WebSocket connection opened")
        logger.info(f"🔗 Connected to: {self.stream_url}")
        self.reconnect_attempts = 0
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            # Parse message
            data = json.loads(message)
            
            # Binance sends data in different formats depending on single/multi stream
            if "stream" in data:
                # Multi-stream format
                stream_name = data["stream"]
                msg_data = data["data"]
                msg_data["stream"] = stream_name
            else:
                # Single stream format
                msg_data = data
            
            # Process the message
            self._process_message(msg_data)
            
            self.messages_received += 1
            self.last_message_time = time.time()
            
            # Log statistics every 100 messages
            if self.messages_received % 100 == 0:
                logger.info(
                    f"📊 Total messages: {self.messages_received} | "
                    f"In-progress skipped: {self.kline_in_progress_skipped} | "
                    f"Closed candles sent: {self.kline_messages_sent} | "
                    f"Queue size: {self.message_queue.qsize()}"
                )
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {message[:100]}... Error: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _process_message(self, msg: dict):
        """Process a single message from Binance and add to queue"""
        # Determine message type based on event type
        event_type = msg.get("e")  # e.g., "kline"
        symbol = msg.get("s", msg.get("symbol", "unknown"))
        
        # FILTER: Only process kline events
        if event_type != "kline":
            return
        
        # FILTER: Only send CLOSED candles (x: true), ignore in-progress candles
        kline_data = msg.get("k", {})
        is_closed = kline_data.get("x", False)
        
        if not is_closed:
            # Skip in-progress candles
            self.kline_in_progress_skipped += 1
            return
        
        # Add metadata
        msg["received_at"] = time.time()
        msg["client_timestamp"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        # Normalize message structure for consistency
        normalized_msg = {
            "event_type": event_type,
            "symbol": symbol,
            "exchange": "binance",
            "data": msg,
            "received_at": msg["received_at"],
            "client_timestamp": msg["client_timestamp"]
        }
        
        # Add to queue for processing
        self.message_queue.put(normalized_msg)
        
        # Increment kline counter
        self.kline_messages_sent += 1
        
        # Log every closed candle sent
        logger.info(
            f"📊 Closed candle #{self.kline_messages_sent}: {symbol} | "
            f"O:{kline_data.get('o')} H:{kline_data.get('h')} "
            f"L:{kline_data.get('l')} C:{kline_data.get('c')} | "
            f"V:{kline_data.get('v')}"
        )
    
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"❌ WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection closed"""
        logger.warning(
            f"⚠️  WebSocket connection closed "
            f"(code: {close_status_code}, message: {close_msg})"
        )
        
        # Attempt reconnection if enabled
        if self.should_reconnect and self.reconnect_attempts < self.max_reconnect_attempts:
            self._reconnect()
        else:
            logger.info("Not reconnecting (max attempts reached or reconnection disabled)")
    
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
        logger.info(f"Connecting to Binance WebSocket...")
        logger.info(f"Stream URL: {self.stream_url[:100]}...")
        
        # Create WebSocket app
        self.ws = websocket.WebSocketApp(
            self.stream_url,
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
        """Stop the WebSocket client"""
        logger.info("Stopping WebSocket client...")
        self.should_reconnect = False
        
        if self.ws:
            self.ws.close()
        
        logger.info(
            f"✅ Client stopped. Total messages: {self.messages_received} | "
            f"In-progress skipped: {self.kline_in_progress_skipped} | "
            f"Closed candles sent: {self.kline_messages_sent}"
        )
    
    def get_queue(self) -> Queue:
        """Get the message queue for consuming messages"""
        return self.message_queue


if __name__ == "__main__":
    # Test WebSocket client
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        Config.validate()
        client = BinanceWebSocketClient()
        
        logger.info("Starting Binance WebSocket client test...")
        logger.info("Press Ctrl+C to stop")
        
        # Start client in background
        client.start()
        
        # Monitor queue
        while True:
            time.sleep(1)
            if not client.message_queue.empty():
                msg = client.message_queue.get()
                logger.info(f"Received from queue: {msg['symbol']}")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt received")
        client.stop()
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise

