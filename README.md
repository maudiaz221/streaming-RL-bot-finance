# Real-Time Stock Market Streaming Platform with Reinforcement Learning

A complete end-to-end real-time data streaming pipeline that captures live stock market data from Alpaca's WebSocket API, processes it using PySpark Structured Streaming on AWS, feeds it to a Reinforcement Learning trading model, and visualizes everything through a Next.js dashboard.

## 🏗️ Architecture

```
Alpaca WebSocket API (IEX)
         ↓
WebSocket Client (Python)
         ↓
Amazon Kinesis Data Streams
         ↓
PySpark Structured Streaming (EMR)
         ↓
Technical Indicators + Aggregations
         ↓
RL Model Inference (PPO)
         ↓
Amazon S3 (Parquet Storage)
         ↓
Next.js Dashboard (Real-time Visualization)
```

## 📁 Project Structure

```
streaming-RL-bot-finance/
├── alpaca-producer/        # WebSocket client for Alpaca → Kinesis
├── streaming-processor/    # PySpark Structured Streaming job
├── rl-model/               # Reinforcement Learning trading model
├── dashboard/              # Next.js real-time dashboard
├── infrastructure/         # AWS setup scripts
├── docs/                   # Documentation
└── README.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- AWS Account with configured CLI
- Alpaca Paper Trading Account (free)

### 1. Clone and Configure

```bash
# Clone the repository
cd streaming-RL-bot-finance

# Copy environment template
cp .env.example .env

# Edit .env with your Alpaca API keys and AWS credentials
```

### 2. Set Up Components

See [USAGE.md](docs/USAGE.md) for detailed setup instructions for each component.

## 📊 Features

### Data Ingestion
- Real-time WebSocket connection to Alpaca IEX feed
- Handles trades, quotes, and 1-minute bars
- Automatic reconnection with exponential backoff
- Batched Kinesis writes for efficiency

### Stream Processing
- PySpark Structured Streaming on AWS EMR
- Technical indicators: RSI, MACD, Bollinger Bands, Moving Averages
- Tumbling and sliding window aggregations
- Real-time anomaly detection
- Fault-tolerant with S3 checkpointing

### Reinforcement Learning
- PPO (Proximal Policy Optimization) trading agent
- State space: price, volume, technical indicators, portfolio
- Action space: HOLD, BUY, SELL
- Risk-adjusted rewards (Sharpe ratio)
- Model versioning with S3

### Dashboard
- Real-time candlestick charts (TradingView Lightweight Charts)
- Live technical indicators overlay
- RL trading signals visualization
- Portfolio simulation
- Multi-symbol tracking

## 📖 Documentation

- [USAGE.md](docs/USAGE.md) - Complete usage guide
- [LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) - Local testing without AWS
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - AWS deployment guide
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Detailed architecture

## 🔧 Technology Stack

- **Data Streaming**: Alpaca WebSocket API, Amazon Kinesis
- **Processing**: PySpark 3.4+, AWS EMR
- **ML/RL**: stable-baselines3 (PPO), OpenAI Gym
- **Storage**: Amazon S3 (Parquet)
- **Frontend**: Next.js 14, TradingView Charts, TailwindCSS
- **Infrastructure**: AWS Lambda/ECS, EMR, S3, Kinesis

## 💰 Cost Estimation

With proper configuration and using AWS free tier where possible:
- Kinesis: ~$30-50/month
- EMR (8 hours/day): ~$100-150/month
- S3: ~$5-10/month
- Lambda/ECS: ~$5-10/month
- **Total**: ~$140-220/month

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for cost optimization strategies.

## 📈 Performance Metrics

The platform is designed to handle:
- **4,096+ data points per second** (exceeds requirements)
- Sub-5 second end-to-end latency
- 20+ concurrent stock symbols
- Real-time technical indicator calculations

## 🔐 Security

- API keys stored in environment variables or AWS Secrets Manager
- IAM roles for service-to-service authentication
- No credentials committed to Git
- S3 encryption at rest

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

This project was created as an educational demonstration of real-time streaming architecture with ML/RL integration.

## 📧 Support

For issues and questions, please refer to the documentation in the `docs/` directory.

