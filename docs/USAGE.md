# Complete Usage Guide

This guide walks you through the complete setup and usage of the Real-Time Stock Market Streaming Platform with Reinforcement Learning.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Component Setup](#component-setup)
4. [Running the System](#running-the-system)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts
- [ ] AWS Account (with billing enabled)
- [ ] Alpaca Paper Trading Account (free)

### Software Requirements
- [ ] Python 3.11+
- [ ] Node.js 18+
- [ ] AWS CLI configured
- [ ] Git

### Knowledge Requirements
- Basic Python programming
- Basic AWS understanding
- Command line familiarity

---

## Initial Setup

### 1. Clone Repository

```bash
cd /path/to/your/workspace
# Repository already cloned at /workspaces/arqui/streaming-RL-bot-finance
cd streaming-RL-bot-finance
```

### 2. Configure Environment Variables

The project includes a `.env` file in the root. Ensure it contains:

```env
# Alpaca API Credentials (you have these)
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_SECRET_KEY=your_alpaca_secret_key
ALPACA_WEBSOCKET_URL=wss://stream.data.alpaca.markets/v2/iex

# AWS Configuration (you'll configure these)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Kinesis Configuration
KINESIS_STREAM_NAME=stock-market-stream

# S3 Configuration
S3_BUCKET_NAME=stock-trading-data

# Stock Symbols to Track
STOCK_SYMBOLS=AAPL,TSLA,NVDA,MSFT,GOOGL,AMZN,META,SPY,QQQ,AMD

# Local Development (optional)
LOCAL_MODE=false
```

---

## Component Setup

### Component 1: AWS Infrastructure

**What it does**: Sets up Kinesis and S3 for data streaming and storage.

**Setup Time**: 5-10 minutes

```bash
cd infrastructure

# Install dependencies
pip install -r requirements.txt

# Create Kinesis stream
python kinesis_setup.py --action create --stream-name stock-market-stream --region us-east-1

# Create S3 bucket
python s3_setup.py --action create --bucket-name stock-trading-data --region us-east-1

# Verify
python kinesis_setup.py --action list
python s3_setup.py --action list
```

**Expected Output**:
```
✅ Stream is now active!
Stream ARN: arn:aws:kinesis:us-east-1:xxxxx:stream/stock-market-stream

✅ Bucket created successfully
✅ Folder structure created
```

---

### Component 2: Alpaca WebSocket Producer

**What it does**: Connects to Alpaca's real-time market data and streams to Kinesis.

**Setup Time**: 2-3 minutes

```bash
cd ../alpaca-producer

# Install dependencies
pip install -r requirements.txt

# Test configuration
python config.py

# Test with local mode (writes to files instead of Kinesis)
LOCAL_MODE=true python alpaca_websocket_client.py
```

**Expected Output**:
```
✅ WebSocket connection opened
Sending authentication...
✅ Authentication successful!
Subscribing to 10 symbols...
✅ Subscription confirmed
Messages received: 100 | Producer stats: {...}
```

**To stop**: Press `Ctrl+C`

---

### Component 3: PySpark Streaming Processor

**What it does**: Processes streaming data, calculates technical indicators, runs RL model inference.

**Setup Time**: 5 minutes (local) / 15-20 minutes (EMR)

#### Local Development Mode

```bash
cd ../streaming-processor

# Install dependencies
pip install -r requirements.txt

# Test configuration
python config.py

# Run in local mode (reads from files)
LOCAL_MODE=true python spark_streaming.py
```

#### AWS EMR Mode

```bash
# Upload script to S3
aws s3 cp spark_streaming.py s3://stock-trading-data/scripts/
aws s3 cp alpaca_data_transformations.py s3://stock-trading-data/scripts/
aws s3 cp rl_model_inference.py s3://stock-trading-data/scripts/
aws s3 cp config.py s3://stock-trading-data/scripts/

# Submit Spark job (you'll do this via EMR console or CLI)
# See AWS setup guide for detailed EMR instructions
```

**Expected Output**:
```
🚀 Starting Stock Market Streaming Application
✅ Spark session created: StockMarketStreaming
📥 Reading from Kinesis stream: stock-market-stream
🔧 Processing streaming data...
✅ Streaming query started successfully!
📊 Access Spark UI at: http://localhost:4040
```

---

### Component 4: RL Trading Model

**What it does**: Trains a reinforcement learning model for trading decisions.

**Setup Time**: 30-60 minutes (training time)

```bash
cd ../rl-model

# Install dependencies
pip install -r requirements.txt

# Option A: Train on synthetic data (for testing)
python train_model.py --timesteps 10000

# Option B: Train on real data
python train_model.py \
  --data-path ../data/processed \
  --symbol AAPL \
  --timesteps 100000 \
  --save-path ./models \
  --model-name ppo_aapl_model

# Monitor training with TensorBoard
tensorboard --logdir ./models/tensorboard
```

**Expected Output**:
```
Creating training environment with 8000 samples
Creating PPO model...
Starting training for 100000 timesteps...
✅ Training completed in 1234.56 seconds
✅ Model saved to ./models/ppo_aapl_model.zip

Training Set Performance:
  avg_total_return: 523.15
  avg_return_pct: 5.23
  avg_sharpe_ratio: 1.85
```

---

### Component 5: Next.js Dashboard

**What it does**: Visualizes real-time data and trading signals.

**Setup Time**: 3-5 minutes

```bash
cd ../dashboard

# Install dependencies
npm install

# Run in development mode (uses mock data)
npm run dev
```

Open http://localhost:3000

**Expected Output**:
```
- Local: http://localhost:3000
✓ Ready in 2.5s
```

---

## Running the System

### End-to-End Local Testing (No AWS Required)

Perfect for development and testing:

```bash
# Terminal 1: Run producer in local mode
cd alpaca-producer
LOCAL_MODE=true python alpaca_websocket_client.py

# Terminal 2: Run Spark processor in local mode
cd streaming-processor
LOCAL_MODE=true python spark_streaming.py

# Terminal 3: Run dashboard
cd dashboard
npm run dev
```

Visit http://localhost:3000 to see the dashboard with real Alpaca data!

---

### Production Deployment on AWS

#### Step 1: Start WebSocket Producer

Option A: Run on EC2/ECS (Recommended for 24/7 operation)
```bash
# Build Docker image
cd alpaca-producer
docker build -t alpaca-producer .

# Run container
docker run -d \
  --env-file ../.env \
  --name alpaca-producer \
  alpaca-producer
```

Option B: Run locally and keep running
```bash
cd alpaca-producer
nohup python alpaca_websocket_client.py > producer.log 2>&1 &
```

#### Step 2: Submit Spark Job to EMR

```bash
# Via AWS CLI
aws emr add-steps \
  --cluster-id j-XXXXXXXXXXXXX \
  --steps Type=Spark,Name="StockStreaming",ActionOnFailure=CONTINUE,Args=[
    --packages,org.apache.spark:spark-sql-kinesis_2.12:3.4.0,
    s3://stock-trading-data/scripts/spark_streaming.py
  ]
```

#### Step 3: Deploy Dashboard

```bash
cd dashboard

# Option A: Deploy to Vercel
vercel

# Option B: Build and run
npm run build
npm start
```

---

## Monitoring

### Monitor Alpaca Producer

```bash
# Check logs
tail -f producer.log

# Check Kinesis metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kinesis \
  --metric-name IncomingRecords \
  --dimensions Name=StreamName,Value=stock-market-stream \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T01:00:00Z \
  --period 300 \
  --statistics Sum
```

### Monitor Spark Streaming

```bash
# Access Spark UI
# Local: http://localhost:4040
# EMR: Setup SSH tunnel first

# Check processed data in S3
aws s3 ls s3://stock-trading-data/processed-data/ --recursive
```

### Monitor Dashboard

```bash
# Check Next.js logs
npm run dev

# Production monitoring
pm2 start npm --name "dashboard" -- start
pm2 logs dashboard
```

---

## Troubleshooting

### Issue: Alpaca WebSocket won't connect

**Symptoms**:
```
❌ WebSocket error: unauthorized
```

**Solution**:
1. Verify API keys in `.env` are correct
2. Ensure using Paper Trading keys (not Live)
3. Check for extra spaces in `.env` file
4. Try test endpoint: `wss://stream.data.alpaca.markets/v2/test`

---

### Issue: No data in Kinesis

**Symptoms**:
```
Messages received: 0
```

**Solution**:
1. Check market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
2. Use test stream with "FAKEPACA" symbol for 24/7 data
3. Verify IAM permissions for Kinesis
4. Check CloudWatch logs for errors

---

### Issue: Spark job fails

**Symptoms**:
```
❌ Error in streaming application
```

**Solution**:
1. Check Spark UI for specific error
2. Verify Kinesis stream exists and is active
3. Ensure S3 bucket is accessible
4. Check IAM role has necessary permissions
5. Verify packages are included: `spark-sql-kinesis_2.12:3.4.0`

---

### Issue: RL model predictions fail

**Symptoms**:
```
RL model prediction failed. Using rule-based strategy.
```

**Solution**:
1. Verify model file exists at specified path
2. Check model was trained with correct features
3. Ensure stable-baselines3 is installed
4. Review logs for specific error
5. Fallback rule-based strategy will activate automatically

---

### Issue: Dashboard shows "No data"

**Symptoms**:
Dashboard loads but shows no charts or signals

**Solution**:
1. Verify WebSocket/API endpoint is configured
2. Check browser console for errors
3. Ensure backend services are running
4. Use mock data mode for development: Dashboard uses mock data by default

---

## Quick Reference Commands

### Start Everything (Local)
```bash
# Terminal 1
cd alpaca-producer && LOCAL_MODE=true python alpaca_websocket_client.py

# Terminal 2
cd streaming-processor && LOCAL_MODE=true python spark_streaming.py

# Terminal 3
cd dashboard && npm run dev
```

### Stop Everything
```bash
# Stop processes
pkill -f alpaca_websocket_client.py
pkill -f spark_streaming.py
# Ctrl+C in dashboard terminal
```

### Check Status
```bash
# Kinesis
aws kinesis describe-stream --stream-name stock-market-stream

# S3
aws s3 ls s3://stock-trading-data/

# Processes
ps aux | grep python
```

### Clean Up
```bash
# Delete AWS resources
python infrastructure/kinesis_setup.py --action delete --stream-name stock-market-stream
python infrastructure/s3_setup.py --action delete --bucket-name stock-trading-data --force

# Clean local data
rm -rf data/
rm -rf rl-model/models/
rm -rf streaming-processor/checkpoints/
```

---

## Next Steps

1. **Optimize Performance**: Monitor Spark UI metrics and tune configurations
2. **Enhance RL Model**: Train on more data, try different algorithms
3. **Add More Symbols**: Update `STOCK_SYMBOLS` in `.env`
4. **Deploy to Production**: Use ECS for producer, EMR for processing
5. **Add Monitoring**: Set up CloudWatch alarms
6. **Implement Backtesting**: Test trading strategies on historical data

---

## Support

For issues and questions:
1. Check component-specific README files
2. Review AWS setup guide: `aws.md`
3. Review Alpaca setup guide: `alpaca.md`
4. Check project requirements: `prompt.md`

---

## Summary

You now have a complete real-time stock trading platform with:
- ✅ Live market data streaming from Alpaca
- ✅ Real-time processing with PySpark
- ✅ Technical indicators (RSI, MACD, Bollinger Bands)
- ✅ RL-powered trading signals
- ✅ Beautiful Next.js dashboard
- ✅ AWS-ready architecture

**Congratulations!** 🎉

