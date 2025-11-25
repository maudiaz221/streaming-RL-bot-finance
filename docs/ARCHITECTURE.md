# System Architecture

## Overview

This document describes the architecture of the Real-Time Stock Market Streaming Platform with Reinforcement Learning.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Sources                                 │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ WebSocket (WSS)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Alpaca Market Data API                            │
│  wss://stream.data.alpaca.markets/v2/iex                           │
│                                                                       │
│  Channels: Trades, Quotes, Bars (1-min OHLCV)                      │
│  Symbols: AAPL, TSLA, NVDA, MSFT, GOOGL, etc.                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ Real-time Stream
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              WebSocket Client (Python)                               │
│  • alpaca_websocket_client.py                                       │
│  • Handles authentication & subscriptions                            │
│  • Batches messages for efficiency                                   │
│  • Auto-reconnection with exponential backoff                        │
│  • Deployment: ECS Fargate / EC2 / Local                           │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ Batched Records
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│           Amazon Kinesis Data Streams                                │
│  • Stream: stock-market-stream                                       │
│  • Shards: 1-2 (configurable)                                       │
│  • Retention: 24-168 hours                                           │
│  • Throughput: 4,096+ messages/sec                                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ Stream Processing
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│        PySpark Structured Streaming (EMR / Local)                   │
│  • spark_streaming.py                                                │
│  • Reads from Kinesis using spark-sql-kinesis connector             │
│  • Processing:                                                       │
│    - Parse JSON messages                                             │
│    - Apply watermarks for late data                                  │
│    - Calculate technical indicators                                  │
│    - Windowing operations (tumbling & sliding)                       │
│    - RL model inference                                              │
│  • Checkpointing to S3 for fault tolerance                          │
└─────────────────────────────────────────────────────────────────────┘
                    │                           │
                    │                           │
       Technical Indicators            RL Model Inference
                    │                           │
                    ▼                           ▼
┌──────────────────────────────────┐  ┌────────────────────────────┐
│  Technical Indicators Module      │  │   RL Model (PPO)          │
│  • RSI (14-period)                │  │   • Input: 13 features     │
│  • MACD (12, 26, 9)              │  │   • Output: BUY/SELL/HOLD │
│  • Bollinger Bands (20, 2σ)      │  │   • Confidence scores     │
│  • Moving Averages (5m, 15m, 1h) │  │   • Trained model from S3 │
│  • Volatility & Volume ratios    │  └────────────────────────────┘
└──────────────────────────────────┘
                    │
                    │ Processed Data
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Amazon S3                                       │
│  Bucket: stock-trading-data                                         │
│  • processed-data/  (Parquet, partitioned by symbol)               │
│  • checkpoints/     (Spark streaming state)                         │
│  • models/          (Trained RL models)                             │
│  • raw-data/        (Backups)                                       │
│  • logs/            (Application logs)                              │
└─────────────────────────────────────────────────────────────────────┘
                    │
                    │ Query / Read
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Next.js Dashboard (React)                               │
│  • Real-time candlestick charts (TradingView Lightweight Charts)    │
│  • Live technical indicators display                                 │
│  • RL trading signals visualization                                  │
│  • Multi-symbol tracking                                             │
│  • Streaming statistics                                              │
│  • Deployment: Vercel / AWS Amplify / Self-hosted                   │
└─────────────────────────────────────────────────────────────────────┘
                    │
                    │ Display
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         End User                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Ingestion Layer

**Component**: Alpaca WebSocket Client

**Responsibilities**:
- Establish and maintain WebSocket connection to Alpaca
- Authenticate using API keys
- Subscribe to real-time market data (trades, quotes, bars)
- Batch messages for efficient Kinesis writes
- Handle connection failures and reconnection

**Technology**:
- Python 3.11
- `websocket-client` library
- `boto3` for AWS SDK

**Deployment Options**:
- **ECS Fargate**: Recommended for production (containerized, auto-scaling)
- **EC2**: Long-running instance
- **Local**: Development and testing

**Data Flow**:
```
Alpaca API → WebSocket Client → Batch (100 messages / 5 seconds) → Kinesis
```

---

### 2. Stream Ingestion Layer

**Component**: Amazon Kinesis Data Streams

**Responsibilities**:
- Receive and buffer streaming data
- Provide ordered, durable stream processing
- Enable multiple consumers (Spark, potential others)

**Configuration**:
- **Stream Name**: `stock-market-stream`
- **Shards**: 1-2 (1 shard = 1 MB/sec in, 2 MB/sec out)
- **Retention**: 24 hours (default), configurable up to 168 hours
- **Encryption**: KMS encryption at rest

**Throughput**:
- Designed for 4,096+ messages per second
- Each message: ~500 bytes (JSON)
- Total: ~2 MB/sec sustained

---

### 3. Stream Processing Layer

**Component**: PySpark Structured Streaming

**Responsibilities**:
- Read from Kinesis in micro-batches
- Parse and validate JSON messages
- Calculate technical indicators in real-time
- Apply windowing operations
- Execute RL model inference
- Write results to S3
- Maintain fault-tolerant checkpoints

**Technology**:
- PySpark 3.4+
- Kinesis connector: `spark-sql-kinesis_2.12:3.4.0`
- Python libraries: pandas, numpy

**Deployment**:
- **AWS EMR**: Recommended for production
- **Local Spark**: Development and testing

**Processing Pipeline**:
```
1. Read from Kinesis
2. Parse JSON (trades, quotes, bars)
3. Apply watermark (handle late data)
4. Calculate indicators per symbol:
   - RSI (rolling 14 bars)
   - MACD (EMA 12, 26, signal 9)
   - Bollinger Bands (20-period, 2σ)
   - Moving Averages (5min, 15min, 1hour)
   - Volatility (20-bar rolling std)
5. Windowing:
   - Tumbling: 1-minute aggregations
   - Sliding: 5-min, 15-min, 1-hour
6. Enrich features for RL
7. RL inference (pandas UDF)
8. Write to S3 (Parquet, partitioned by symbol)
9. Checkpoint state
```

**Batch Interval**: 10 seconds (configurable)
**Watermark**: 30 seconds (handle late arrivals)

---

### 4. Machine Learning Layer

**Component**: Reinforcement Learning Model (PPO)

**Responsibilities**:
- Learn optimal trading strategy from historical data
- Make real-time trading decisions
- Provide confidence scores for signals

**Architecture**:

**Training**:
- **Environment**: Custom Gym environment (StockTradingEnv)
- **Algorithm**: PPO (Proximal Policy Optimization)
- **Framework**: stable-baselines3
- **State Space**: 13 features
  - Price, momentum, volatility, volume ratio
  - RSI, MACD, Bollinger Band position
  - Moving averages
  - Portfolio state (cash, shares)
- **Action Space**: Discrete {0: HOLD, 1: BUY, 2: SELL}
- **Reward**: Portfolio change + Sharpe ratio bonus - penalties

**Inference**:
- Loaded from S3 in Spark job
- Executed via pandas UDF for batch predictions
- Fallback to rule-based strategy if model unavailable

**Training Data**:
- Historical bars with calculated indicators
- Minimum 10,000 samples recommended
- Train/test split: 80/20

---

### 5. Storage Layer

**Component**: Amazon S3

**Responsibilities**:
- Store processed streaming data
- Maintain Spark checkpoints
- Version RL models
- Archive raw data
- Store application logs

**Bucket Structure**:
```
s3://stock-trading-data/
├── processed-data/
│   ├── S=AAPL/
│   │   └── date=2024-01-15/
│   │       └── part-00000.parquet
│   ├── S=TSLA/
│   └── ...
├── checkpoints/
│   └── bar_processing/
│       └── offsets/
├── models/
│   ├── ppo_trading_model.zip
│   └── best_model.zip
├── raw-data/
└── logs/
```

**Optimizations**:
- **Format**: Parquet (columnar, compressed)
- **Partitioning**: By symbol (S=) for efficient queries
- **Lifecycle Policies**:
  - Standard → Standard-IA (30 days)
  - Standard-IA → Glacier (90 days)
  - Delete logs (30 days)

---

### 6. Visualization Layer

**Component**: Next.js Dashboard

**Responsibilities**:
- Display real-time candlestick charts
- Show technical indicators
- Visualize RL predictions and trading signals
- Track multiple symbols
- Display streaming statistics

**Technology**:
- Next.js 14 (React 18)
- TradingView Lightweight Charts
- Recharts for statistics
- TailwindCSS for styling
- TypeScript

**Data Connection Options**:
1. **WebSocket Server** (Recommended): Bridge between S3/Kinesis and dashboard
2. **REST API with Polling**: Query S3/DynamoDB periodically
3. **AWS AppSync**: Real-time GraphQL subscriptions
4. **Mock Data**: Development mode

**Pages**:
- `/` - Main dashboard with charts and signals
- `/analytics` - Historical performance (future)
- `/model` - RL model metrics (future)

---

## Data Flow

### Real-Time Data Path

```
Market Event
    ↓ (<100ms)
Alpaca API
    ↓ (WebSocket, <50ms)
WebSocket Client
    ↓ (Batch, <5s)
Kinesis Stream
    ↓ (Micro-batch, 10s interval)
PySpark Streaming
    ↓ (Processing, <2s)
Technical Indicators + RL Inference
    ↓ (Write, <1s)
S3 (Parquet)
    ↓ (Query, <500ms)
Dashboard
    ↓
User
```

**Total Latency**: ~20-30 seconds end-to-end

### Batch Data Path (Training)

```
Historical Data (CSV/API)
    ↓
Data Preparation Script
    ↓
Training DataFrame
    ↓
RL Model Training (PPO)
    ↓ (30-60 minutes)
Trained Model (.zip)
    ↓
S3 Storage
    ↓
PySpark Streaming (Inference)
```

---

## Fault Tolerance

### Alpaca Producer
- **Reconnection**: Exponential backoff (max 5 attempts)
- **State Recovery**: Re-subscribe to symbols on reconnect
- **Monitoring**: Log connection status, alert on failures

### Kinesis
- **Durability**: Data replicated across 3 AZs
- **Retention**: 24-168 hours for replay
- **Monitoring**: CloudWatch metrics for throughput and errors

### Spark Streaming
- **Checkpointing**: Write-ahead logs to S3
- **Exactly-once**: Kinesis offsets tracked per batch
- **Restartability**: Resume from last checkpoint on failure
- **Watermarks**: Handle late-arriving data gracefully

### S3
- **Durability**: 99.999999999% (11 nines)
- **Versioning**: Optional, for critical data
- **Replication**: Cross-region replication (optional)

---

## Scalability

### Horizontal Scaling

| Component | Scaling Method | Max Throughput |
|-----------|---------------|----------------|
| WebSocket Producer | Multiple instances (different symbols) | 10,000+ msg/sec |
| Kinesis | Add shards | 1 MB/sec per shard |
| Spark | Add worker nodes | Linear with nodes |
| S3 | Automatic | 5,500 PUT/sec per prefix |
| Dashboard | CDN + serverless | Unlimited reads |

### Vertical Scaling

- **Spark Executors**: Increase memory (8GB → 16GB)
- **Kinesis Shards**: On-demand mode (auto-scales)
- **EC2 Instances**: Larger instance types

### Cost Optimization

- Use Spot Instances for EMR
- Enable S3 lifecycle policies
- Use on-demand Kinesis for variable workloads
- Archive old data to Glacier

---

## Security

### Authentication & Authorization
- **AWS**: IAM roles for service-to-service
- **Alpaca**: API keys in environment variables or AWS Secrets Manager
- **Dashboard**: AWS Cognito (future enhancement)

### Encryption
- **In Transit**: TLS 1.2+ (WebSocket, HTTPS)
- **At Rest**: 
  - Kinesis: KMS encryption
  - S3: SSE-S3 or SSE-KMS
  - EMR: EBS encryption

### Network Security
- **VPC**: Deploy EMR in private subnets
- **Security Groups**: Restrict access by IP/port
- **NAT Gateway**: Outbound internet access for private subnets

### Data Privacy
- No PII collected
- Market data is public information
- API keys never logged or committed

---

## Monitoring & Logging

### CloudWatch Metrics

**Kinesis**:
- IncomingRecords
- IncomingBytes
- GetRecords.Latency

**EMR/Spark**:
- Batch Duration
- Processing Rate
- Input Rate
- Total Delay

**Custom Metrics**:
- Messages received per symbol
- RL prediction accuracy
- Trading signal counts

### Logging

**Application Logs**:
- Producer: WebSocket events, Kinesis writes
- Spark: Processing errors, checkpoint info
- RL: Prediction scores, fallback events

**AWS Logs**:
- CloudWatch Logs for Lambda/ECS
- EMR logs in S3
- VPC Flow Logs (optional)

### Alerting

- Kinesis throughput exceeded
- Spark job failures
- High latency (>60s)
- Model inference errors
- Cost anomalies

---

## Performance Characteristics

### Latency
- **WebSocket to Kinesis**: <5 seconds
- **Kinesis to S3**: 10-20 seconds
- **End-to-end**: 20-30 seconds

### Throughput
- **Design Target**: 4,096 messages/sec
- **Actual Capacity**: 10,000+ messages/sec
- **Per Symbol**: 200+ updates/sec during market hours

### Resource Usage
- **WebSocket Producer**: 512 MB RAM, minimal CPU
- **Spark (local)**: 4 GB RAM, 2 cores
- **Spark (EMR)**: m5.xlarge (4 vCPU, 16 GB) per node
- **Dashboard**: 512 MB RAM (Node.js)

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Data Source | Alpaca Markets API | Real-time market data |
| Ingestion | Python, websocket-client | WebSocket client |
| Streaming | AWS Kinesis | Data buffering |
| Processing | PySpark 3.4+ | Stream processing |
| ML/RL | stable-baselines3, PPO | Trading decisions |
| Storage | Amazon S3 (Parquet) | Data lake |
| Visualization | Next.js 14, TypeScript | Dashboard |
| Infrastructure | AWS (Kinesis, S3, EMR) | Cloud platform |

---

## Future Enhancements

1. **Multi-Model Ensemble**: Combine multiple RL models
2. **Real-Time Backtesting**: Simulate trades in real-time
3. **Advanced Indicators**: Ichimoku, Fibonacci, etc.
4. **Sentiment Analysis**: Integrate news/social media
5. **Portfolio Management**: Track actual portfolio
6. **Alerting System**: SMS/email for trade signals
7. **API Gateway**: REST API for external access
8. **Mobile App**: React Native dashboard

---

## Conclusion

This architecture provides:
- ✅ Real-time streaming (<30s latency)
- ✅ Fault-tolerant and scalable
- ✅ ML-powered trading signals
- ✅ Comprehensive technical analysis
- ✅ Production-ready deployment
- ✅ Cost-effective (~$150-200/month)




