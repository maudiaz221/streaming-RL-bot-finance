# Real-Time Stock Market Data Streaming Platform with Reinforcement Learning

## Project Overview
Build a complete real-time data streaming pipeline that captures live stock market data from **Alpaca's WebSocket API**, processes it using PySpark Structured Streaming on AWS, feeds it to a Reinforcement Learning model, and visualizes everything through a Next.js dashboard.

## Core Requirements

### 1. Data Ingestion Layer - Alpaca WebSocket Streaming
- **Objective**: Capture real-time stock market data using Alpaca's WebSocket API
- **Alpaca Market Data Streaming**:
  - **Primary WebSocket URL**: `wss://stream.data.alpaca.markets/v2/iex` (FREE - IEX data feed)
  - **Premium WebSocket URL**: `wss://stream.data.alpaca.markets/v2/sip` (paid - consolidated SIP data)
  - **Test WebSocket URL**: `wss://stream.data.alpaca.markets/v2/test` (use "FAKEPACA" symbol for testing)
  - **Account Updates URL**: `wss://paper-api.alpaca.markets/stream` (for trade/order updates)
  
- **Free Tier Capabilities**:
  - IEX data source provides real-time market data for ALL US stocks
  - 1 concurrent WebSocket connection allowed
  - Access to trades, quotes, and 1-minute bars
  - No credit card required for paper trading account
  
- **Available Data Channels**:
  - **Trades** (`trades`): Real-time trade execution data
    ```json
    {"T":"t","S":"AAPL","i":96921,"x":"D","p":126.55,"s":1,"t":"2021-02-22T15:51:44.208Z","c":["@","I"],"z":"C"}
    ```
    - `T`: message type (t=trade)
    - `S`: symbol
    - `p`: price
    - `s`: size (shares)
    - `t`: timestamp
    - `x`: exchange code
    
  - **Quotes** (`quotes`): Best bid/ask prices with sizes
    ```json
    {"T":"q","S":"AMD","bx":"U","bp":87.66,"bs":1,"ax":"Q","ap":87.68,"as":4,"t":"2021-02-22T15:51:45.335Z","c":["R"],"z":"C"}
    ```
    - `bp`: bid price
    - `bs`: bid size
    - `ap`: ask price
    - `as`: ask size
    
  - **Bars** (`bars`): Aggregated 1-minute OHLCV data
    ```json
    {"T":"b","S":"SPY","o":387.98,"h":388.0,"l":387.97,"c":388.0,"v":49,"t":"2021-02-22T19:15:00Z","n":1,"vw":387.99}
    ```
    - `o`: open, `h`: high, `l`: low, `c`: close
    - `v`: volume
    - `vw`: volume-weighted average price
    
  - **Trade Updates** (`trade_updates`): Account order fills, cancellations (from paper-api endpoint)

- **WebSocket Authentication Flow**:
  ```python
  # 1. Connect to WebSocket
  ws = websocket.WebSocketApp("wss://stream.data.alpaca.markets/v2/iex")
  
  # 2. Send authentication message
  auth_msg = {
      "action": "auth",
      "key": "YOUR_API_KEY",
      "secret": "YOUR_SECRET_KEY"
  }
  
  # 3. Receive authentication response
  {"T":"success","msg":"authenticated"}
  
  # 4. Subscribe to data channels
  subscribe_msg = {
      "action": "subscribe",
      "trades": ["AAPL", "TSLA", "NVDA"],
      "quotes": ["SPY", "QQQ"],
      "bars": ["MSFT", "GOOGL"]
  }
  
  # 5. Receive subscription confirmation
  {"T":"subscription","trades":["AAPL","TSLA","NVDA"],"quotes":["SPY","QQQ"],"bars":["MSFT","GOOGL"]}
  ```

- **Data Volume Requirements**:
  - Must handle at least **4,096 data points per second** (as per project requirements)
  - Strategy to achieve this:
    - Subscribe to 20+ high-volume stocks (AAPL, TSLA, NVDA, SPY, QQQ, etc.)
    - Enable all three channels: trades, quotes, bars
    - During market hours, high-volume stocks generate thousands of updates per minute
    - Each stock can produce 100+ trades/quotes per second during active trading
  - Test endpoint: Use "FAKEPACA" symbol on test stream for consistent data generation

- **Alpaca Account Setup**:
  - Sign up free at: https://alpaca.markets/
  - Create API keys from dashboard (Paper Trading)
  - No credit card required for IEX data access
  - Free tier includes unlimited IEX streaming data

### 2. AWS Streaming Architecture
**Required AWS Services**:
- **Amazon Kinesis Data Streams**: Primary streaming ingestion service
- **AWS Lambda**: Python WebSocket client that connects to Alpaca and pushes to Kinesis
- **Amazon S3**: For data persistence and checkpointing
- **AWS Glue**: For data cataloging (optional but recommended)
- **Amazon EMR or EC2**: For running PySpark Structured Streaming jobs
- **AWS IAM**: For proper permissions management

**Updated Architecture Flow**:
```
Alpaca WebSocket API 
    ↓
Lambda (WebSocket Client) → Kinesis Data Stream → PySpark on EMR → S3 (Storage)
                                                         ↓
                                                    RL Model
                                                         ↓
                                                  Next.js Dashboard
```

**Lambda WebSocket Client Design**:
- Lambda function runs continuously (or triggered by EventBridge every 1 minute)
- Establishes WebSocket connection to Alpaca
- Authenticates and subscribes to symbols
- Receives real-time market data
- Batches messages and pushes to Kinesis Data Streams
- Handles reconnection logic for fault tolerance
- Note: For long-running WebSocket connections, consider EC2 or ECS instead of Lambda

**Alternative: EC2/ECS WebSocket Client** (Recommended):
- Deploy a Docker container on ECS Fargate or EC2
- Long-running Python process maintains persistent WebSocket connection
- More suitable for continuous streaming than Lambda
- Better for maintaining WebSocket connection state

### 3. PySpark Structured Streaming Processing
**Requirements**:
- Use PySpark Structured Streaming (NOT Kafka, use Kinesis instead)
- Read from Kinesis Data Streams using the Kinesis connector
- **Data Schema for Alpaca Trades**:
  ```python
  from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType
  
  trade_schema = StructType([
      StructField("T", StringType()),      # message type
      StructField("S", StringType()),      # symbol
      StructField("p", DoubleType()),      # price
      StructField("s", LongType()),        # size
      StructField("t", StringType()),      # timestamp
      StructField("x", StringType()),      # exchange
  ])
  ```

- **Real-Time Transformations**:
  - Parse JSON messages from Kinesis
  - Calculate streaming statistics per symbol: min, max, mean, variance, standard deviation
  - Create price range buckets for continuous values
  - Calculate moving averages (5-min, 15-min, 1-hour windows)
  - Detect anomalies or outliers (sudden price spikes)
  - Compute technical indicators: RSI, MACD, Bollinger Bands
  - Consider using online unsupervised learning: STREAM-LOF, OLOF, or DBSCAN for anomaly detection
  
- **Windowing Operations**:
  - Implement tumbling windows (e.g., 1-minute aggregations matching Alpaca bars)
  - Implement sliding windows for moving averages
  - Use watermarks for handling late-arriving data (important for real-time stock data)
  - Group by symbol for per-stock analytics
  
- **Output Modes**:
  - Write streaming statistics to S3 in Parquet format (partitioned by date and symbol)
  - Write real-time metrics to a temporary storage for dashboard consumption
  - Checkpoint streaming state to S3 for fault tolerance
  - Consider writing to DynamoDB for low-latency dashboard queries

### 4. Reinforcement Learning Model
**Requirements**:
- **Model Type**: Trading RL agent using DQN, Q-Learning, PPO, or A3C
- **Trading Environment**:
  - State space: [current_price, volume, bid_ask_spread, RSI, MACD, moving_averages, portfolio_value, position]
  - Action space: {0: HOLD, 1: BUY, 2: SELL}
  - Reward function: Portfolio returns, Sharpe ratio, or profit/loss
  
- **Training Phase**:
  - Collect sufficient historical data from the stream (save to S3)
  - Train initial RL model on batch data using historical trades
  - Model should learn optimal buy/sell/hold actions based on market features
  - Use libraries: stable-baselines3, Ray RLlib, or TensorFlow
  
- **Inference Phase**:
  - Load trained model from S3
  - Make real-time predictions on incoming streaming data from PySpark
  - Output: Trading signals (buy/sell/hold) with confidence scores and Q-values
  
- **Integration**:
  - PySpark streaming job calls the RL model for inference on each batch
  - Can use pandas UDF or direct Python model loading
  - Store predictions alongside raw data in S3
  - Send predictions to Next.js dashboard via API or real-time stream

### 5. Next.js Dashboard
**Requirements**:
- **Real-Time Visualization**:
  - Live stock price charts (candlestick or line charts) showing Alpaca trade/quote data
  - Multi-symbol ticker display
  - Streaming statistics display (mean, variance, min, max per symbol)
  - Real-time technical indicators visualization (RSI, MACD overlays)
  - RL model predictions and confidence scores
  - Trading signals visualization (buy/sell/hold indicators with timing)
  - Portfolio simulation showing hypothetical trades based on RL predictions
  
- **Technologies to Use**:
  - Next.js 14+ (App Router)
  - React Server Components where appropriate
  - Chart libraries: 
    - TradingView Lightweight Charts (recommended for stock charts)
    - Recharts or Chart.js for statistics
  - WebSocket or Server-Sent Events (SSE) for real-time updates
  - TailwindCSS for styling
  - shadcn/ui for UI components
  
- **Dashboard Pages**:
  - **Main Dashboard**: 
    - Real-time price charts for subscribed symbols
    - Live RL predictions with buy/sell/hold signals
    - Current streaming statistics
  - **Analytics Page**: 
    - Historical performance metrics
    - Backtesting results visualization
  - **Model Performance Page**: 
    - RL model accuracy, reward curves
    - Trade win rate, Sharpe ratio
  - **Settings Page**:
    - Symbol selection for tracking
    - Model configuration
  
- **Data Connection Options**:
  - **Option A**: Connect directly to Kinesis Data Streams using AWS SDK
  - **Option B**: Create Lambda API endpoints that query S3/DynamoDB
  - **Option C**: Use AWS AppSync for real-time GraphQL subscriptions
  - **Option D**: Implement custom WebSocket server that reads from Kinesis/S3
  - Recommended: Use AWS AppSync or custom WebSocket server for true real-time experience

### 6. Performance Monitoring with Spark UI
**Requirements**:
- Access Spark UI during execution (http://localhost:4040 or via SSH tunnel for EMR)
- **Capture and analyze these 6+ metrics**:
  1. **Job Execution Time**: Total time for each streaming batch
  2. **Shuffle Operations**: Time spent in shuffle operations (joins, reduceByKey, groupBy)
  3. **I/O Operations**: Disk read/write times per stage (Kinesis reads, S3 writes)
  4. **Scheduler Delay**: Time waiting for resources
  5. **Executor Runtime**: Actual computation time
  6. **GC Time**: Garbage collection overhead
  7. **Spill (Memory/Disk)**: Memory overflow to disk (indicates RAM issues)
  8. **Environment Variables**: Document Spark configuration used
  9. **Streaming Batch Processing Rate**: Batches processed per second
  10. **Input Rate**: Records per second from Kinesis

- Take screenshots from Spark UI for your report
- Compare performance across: Local execution, Google Colab, AWS EMR
- Document how streaming performance changes with different batch intervals

### 7. Fault Tolerance & Reliability
- Implement checkpointing in PySpark Structured Streaming to S3
- Handle exactly-once semantics for data processing
- Implement retry logic for Alpaca WebSocket connection
- Handle late-arriving data with watermarks
- Graceful error handling for network failures
- Alpaca reconnection strategy in Lambda/EC2 client
- Monitor Alpaca rate limits and connection status

## Technical Implementation Details

### Code Structure
```
project-root/
├── alpaca-producer/        # WebSocket client for Alpaca
│   ├── alpaca_websocket_client.py
│   ├── kinesis_producer.py
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile          # For ECS deployment
├── lambda-alternative/     # If using Lambda instead of EC2
│   ├── lambda_handler.py
│   └── requirements.txt
├── streaming-processor/    # PySpark Structured Streaming job
│   ├── spark_streaming.py
│   ├── alpaca_data_transformations.py
│   ├── rl_model_inference.py
│   └── requirements.txt
├── rl-model/               # Reinforcement Learning model
│   ├── train_model.py
│   ├── trading_environment.py
│   ├── model.py
│   └── requirements.txt
├── dashboard/              # Next.js application
│   ├── app/
│   │   ├── page.tsx       # Main dashboard
│   │   ├── analytics/
│   │   └── model/
│   ├── components/
│   │   ├── StockChart.tsx
│   │   ├── TradingSignals.tsx
│   │   └── RealtimeStats.tsx
│   ├── lib/
│   │   ├── websocket.ts
│   │   └── aws-client.ts
│   └── public/
├── infrastructure/         # AWS setup scripts
│   ├── kinesis_setup.py
│   ├── emr_cluster.py
│   ├── iam_roles.py
│   └── ecs_fargate_setup.py
└── docs/
    ├── aws_setup_guide.md
    └── alpaca_setup.md
```

### Alpaca WebSocket Client Implementation (Python)
```python
import websocket
import json
import boto3

class AlpacaWebSocketClient:
    def __init__(self, api_key, secret_key, kinesis_stream):
        self.api_key = api_key
        self.secret_key = secret_key
        self.kinesis = boto3.client('kinesis')
        self.stream_name = kinesis_stream
        self.ws = None
        
    def on_open(self, ws):
        # Authenticate
        auth = {
            "action": "auth",
            "key": self.api_key,
            "secret": self.secret_key
        }
        ws.send(json.dumps(auth))
        
    def on_message(self, ws, message):
        data = json.loads(message)
        
        # Check for successful authentication
        if data[0].get("T") == "success" and data[0].get("msg") == "authenticated":
            # Subscribe to symbols
            subscribe = {
                "action": "subscribe",
                "trades": ["AAPL", "TSLA", "NVDA", "SPY"],
                "quotes": ["AAPL", "TSLA"],
                "bars": ["SPY", "QQQ"]
            }
            ws.send(json.dumps(subscribe))
        else:
            # Push to Kinesis
            self.kinesis.put_record(
                StreamName=self.stream_name,
                Data=json.dumps(data),
                PartitionKey=data[0].get("S", "unknown")
            )
    
    def on_error(self, ws, error):
        print(f"Error: {error}")
        
    def on_close(self, ws, close_status_code, close_msg):
        print("Connection closed")
        
    def connect(self):
        self.ws = websocket.WebSocketApp(
            "wss://stream.data.alpaca.markets/v2/iex",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever()
```

### PySpark Kinesis Reading Code
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Initialize Spark with Kinesis support
spark = SparkSession.builder \
    .appName("AlpacaStreamProcessing") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kinesis_2.12:3.4.0") \
    .getOrCreate()

# Read from Kinesis
kinesis_df = spark \
    .readStream \
    .format("kinesis") \
    .option("streamName", "stock-market-stream") \
    .option("region", "us-east-1") \
    .option("initialPosition", "TRIM_HORIZON") \
    .load()

# Parse JSON from Kinesis
parsed_df = kinesis_df.select(
    from_json(col("data").cast("string"), alpaca_schema).alias("parsed")
).select("parsed.*")

# Apply transformations and windowing
# ... (continue with aggregations, RL inference, etc.)
```

### RL Model Specifications
- **Framework**: stable-baselines3 or Ray RLlib
- **State Features**: 
  - Price features: current_price, price_change, volatility
  - Technical indicators: RSI, MACD, Moving Averages
  - Market features: volume, bid_ask_spread
  - Position features: current_position, cash_balance
- **Action Space**: Discrete {HOLD=0, BUY=1, SELL=2}
- **Reward Function**: 
  ```python
  reward = (portfolio_value_t - portfolio_value_t-1) / portfolio_value_t-1
  # Or use Sharpe ratio for risk-adjusted returns
  ```
- Model checkpoints saved to S3 for versioning

### Next.js Real-Time Integration
- Use `websocket` or `socket.io-client` for WebSocket connections
- Implement reconnection logic
- Use React Query for data fetching and caching
- TradingView Lightweight Charts for professional stock visualizations
- Display latency metrics (data timestamp vs display timestamp)

## Deliverables Expected from Cursor

1. **Alpaca WebSocket Client (Python)**
   - Complete WebSocket client connecting to Alpaca IEX stream
   - Authentication and subscription logic
   - Kinesis producer integration
   - Error handling and reconnection
   - Alternative: Lambda function or ECS Dockerfile

2. **PySpark Structured Streaming Application**
   - Complete streaming job reading from Kinesis
   - Alpaca data schema parsing
   - Real-time transformations and technical indicators
   - Windowing operations (tumbling and sliding)
   - RL model inference integration
   - S3 output with checkpointing

3. **RL Trading Model**
   - Training script using historical Alpaca data
   - Trading environment implementation
   - Model architecture (DQN or PPO recommended)
   - Inference wrapper for PySpark integration
   - Model serialization to S3

4. **Next.js Dashboard**
   - Multi-page dashboard application
   - Real-time stock price charts using TradingView Lightweight Charts
   - Live statistics and technical indicators
   - RL predictions visualization
   - WebSocket or SSE connection to data source
   - Responsive design with TailwindCSS

5. **Infrastructure Setup Scripts**
   - Python scripts to create Kinesis streams
   - ECS Fargate task definition for Alpaca client
   - EMR cluster launch script with Spark configuration
   - IAM roles and policies
   - S3 bucket creation and lifecycle policies

6. **Comprehensive AWS Setup Guide (CRITICAL)**
   - Step-by-step AWS console instructions
   - Alpaca account setup and API key generation
   - Kinesis stream configuration
   - ECS/Lambda deployment for WebSocket client
   - EMR cluster setup and Spark job submission
   - IAM permissions for all services
   - Spark UI access via SSH tunnel
   - Cost estimation and optimization
   - Testing and troubleshooting

7. **Documentation**
   - README with architecture diagram
   - Alpaca API integration guide
   - Local development setup
   - AWS deployment guide
   - Dashboard user guide
   - Troubleshooting common issues

## Performance Comparison Requirement
Test the application on at least TWO platforms:
- Local machine (Spark Standalone)
- AWS EMR
- Google Colab (optional)

Document 6+ metrics from Spark UI with screenshots for each platform.

## Alpaca-Specific Notes

### Free Tier Limitations
- 1 concurrent WebSocket connection
- IEX data only (not full SIP consolidated feed)
- IEX represents ~2-3% of market volume
- Sufficient for development and paper trading
- For production, consider upgrading to SIP feed

### Symbols to Use for Testing
- High liquidity stocks: AAPL, MSFT, TSLA, NVDA, GOOGL, AMZN
- ETFs: SPY, QQQ, IWM (higher message volume)
- Test symbol: "FAKEPACA" on test stream

### Message Rate Expectations
- During market hours (9:30 AM - 4:00 PM ET):
  - High-volume stocks: 50-200 messages/second/symbol
  - 20 symbols × 100 msg/sec = 2,000 msg/sec baseline
  - Can scale to 5,000+ messages/second during volatile periods
- Easily meets 4,096 data points/second requirement

### WebSocket Reliability
- Implement heartbeat/ping-pong mechanism
- Handle reconnection with exponential backoff
- Maintain subscription state for reconnection
- Monitor connection status and alert on failures

## Additional Constraints
- Python 3.9+
- PySpark 3.4+ with Kinesis connector
- Node.js 18+ for Next.js
- All AWS resources in the same region (us-east-1 recommended)
- Proper logging throughout (CloudWatch for AWS components)
- Unit tests for critical functions
- Follow PEP 8 for Python
- Follow Next.js and React best practices
- Environment variables for all secrets (never commit API keys)

## Expected Output Format
1. All source code files with proper structure
2. `AWS_SETUP_GUIDE.md` with detailed console instructions
3. `ALPACA_SETUP.md` with Alpaca account and API setup
4. `README.md` with architecture overview and setup
5. Requirements.txt for each Python component
6. package.json for Next.js
7. Dockerfile for Alpaca WebSocket client (ECS)
8. Spark configuration files
9. Environment variable templates (.env.example)

## Critical Success Criteria
1. Successfully connect to Alpaca WebSocket and receive real-time data
2. Stream data through Kinesis to PySpark with <5 second latency
3. Process streaming data with PySpark and calculate technical indicators
4. Train RL model on historical data and make real-time predictions
5. Display live data and predictions on Next.js dashboard
6. Document Spark UI metrics across platforms
7. Complete end-to-end pipeline works without manual intervention
8. Proper error handling and fault tolerance throughout
9. Clear documentation for setup and deployment
10. Cost-effective architecture (stay within AWS free tier where possible)