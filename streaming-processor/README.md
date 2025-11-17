# PySpark Structured Streaming Processor

Real-time stream processing engine for stock market data with technical indicators and RL model integration.

## Features

- ✅ Reads from AWS Kinesis Data Streams or local files
- ✅ Technical indicators: RSI, MACD, Bollinger Bands, Moving Averages
- ✅ Windowing operations (tumbling and sliding windows)
- ✅ RL model inference for trading signals
- ✅ Rule-based strategy fallback
- ✅ Fault-tolerant with S3 checkpointing
- ✅ Watermark handling for late data
- ✅ Parquet output partitioned by symbol

## Prerequisites

- PySpark 3.4+
- AWS EMR cluster or local Spark installation
- Trained RL model (optional)

## Installation

### Local Development

```bash
cd streaming-processor
pip install -r requirements.txt
```

### On AWS EMR

The required packages will be installed via bootstrap actions or added as steps.

## Configuration

Set environment variables in `.env` file (project root):

```env
# AWS Configuration
AWS_REGION=us-east-1
KINESIS_STREAM_NAME=stock-market-stream
S3_BUCKET_NAME=stock-trading-data

# Spark Configuration
BATCH_INTERVAL_SECONDS=10
WATERMARK_DELAY=30 seconds

# Technical Indicators
RSI_PERIOD=14
MACD_FAST=12
MACD_SLOW=26
MACD_SIGNAL=9
BB_PERIOD=20
BB_STD_DEV=2

# RL Model
RL_MODEL_ENABLED=true
RL_MODEL_NAME=ppo_trading_model.zip
```

For local development:
```env
LOCAL_MODE=true
LOCAL_INPUT_PATH=./data/stream_output
LOCAL_OUTPUT_PATH=./data/processed
LOCAL_CHECKPOINT_PATH=./data/checkpoints
```

## Usage

### Run Locally (Standalone Spark)

```bash
# Start with local file input
python spark_streaming.py
```

### Submit to AWS EMR

```bash
# Using spark-submit
spark-submit \
  --packages org.apache.spark:spark-sql-kinesis_2.12:3.4.0 \
  --conf spark.sql.streaming.checkpointLocation=s3a://your-bucket/checkpoints \
  s3://your-bucket/scripts/spark_streaming.py
```

### Using AWS EMR Steps

```bash
aws emr add-steps \
  --cluster-id j-XXXXXXXXXXXXX \
  --steps Type=Spark,Name="Stock Streaming",ActionOnFailure=CONTINUE,Args=[
    --deploy-mode,cluster,
    --packages,org.apache.spark:spark-sql-kinesis_2.12:3.4.0,
    s3://your-bucket/scripts/spark_streaming.py
  ]
```

## Architecture

```
Kinesis Data Stream / Local Files
         ↓
   [Read Stream]
         ↓
   [Parse JSON Messages]
         ↓
   [Apply Watermark]
         ↓
   [Calculate Technical Indicators]
   - RSI
   - MACD
   - Bollinger Bands
   - Moving Averages
         ↓
   [Enrich Features for RL]
         ↓
   [RL Model Inference / Rule-Based Strategy]
         ↓
   [Write to S3/Local (Parquet)]
```

## Data Processing Flow

### 1. Message Parsing
- Reads JSON messages from Kinesis/files
- Parses based on message type (Trade/Quote/Bar)
- Converts timestamp strings to Spark timestamps

### 2. Technical Indicators

#### RSI (Relative Strength Index)
- Measures momentum on 0-100 scale
- Default period: 14 bars
- Oversold: < 30, Overbought: > 70

#### MACD (Moving Average Convergence Divergence)
- Trend-following momentum indicator
- Fast EMA (12) - Slow EMA (26) = MACD Line
- Signal Line: 9-period EMA of MACD
- Histogram: MACD - Signal

#### Bollinger Bands
- Volatility indicator
- Middle band: 20-period SMA
- Upper/Lower: ±2 standard deviations

#### Moving Averages
- 5-minute MA
- 15-minute MA
- 1-hour MA

### 3. Feature Engineering
- Price momentum (5-bar change)
- Volatility (20-bar rolling std)
- Volume ratio (current / MA)
- Bollinger Band position

### 4. RL Model Inference
- Uses trained PPO model
- Feature vector: [price, momentum, volatility, volume, RSI, MACD, BB position, MAs]
- Output: {0: HOLD, 1: BUY, 2: SELL}

### 5. Rule-Based Strategy (Fallback)
When RL model unavailable:
- BUY: RSI < 30 AND price < BB lower
- SELL: RSI > 70 AND price > BB upper
- HOLD: Otherwise

## Output Schema

Processed data in Parquet format with columns:

```
timestamp         (Timestamp)
S                 (String) - Symbol
o, h, l, c        (Double) - OHLC prices
v                 (Long) - Volume
ma_5min           (Double)
ma_15min          (Double)
ma_1hour          (Double)
rsi               (Double)
macd_line         (Double)
macd_signal       (Double)
macd_histogram    (Double)
bb_upper          (Double)
bb_middle         (Double)
bb_lower          (Double)
bb_width          (Double)
price_momentum    (Double)
volatility        (Double)
volume_ratio      (Double)
rl_action         (Integer) - 0=HOLD, 1=BUY, 2=SELL
rl_action_name    (String)
rl_confidence     (Double)
```

## Monitoring with Spark UI

### Access Spark UI

**Local:**
```
http://localhost:4040
```

**EMR (via SSH tunnel):**
```bash
ssh -i your-key.pem -L 8157:localhost:8088 hadoop@ec2-xxx-xxx-xxx-xxx.compute.amazonaws.com

# Then access:
http://localhost:8088   # YARN ResourceManager
http://localhost:8088/proxy/application_xxx_xxx/  # Spark UI
```

### Key Metrics to Monitor

1. **Streaming Tab**
   - Input Rate (records/sec)
   - Processing Rate (records/sec)
   - Batch Duration
   - Total Delay

2. **Jobs Tab**
   - Active/Completed jobs
   - Duration
   - Stages

3. **Stages Tab**
   - Task execution time
   - Shuffle read/write
   - GC time
   - Input/output

4. **Executors Tab**
   - Memory usage
   - Disk usage
   - Active tasks
   - Failed tasks

5. **SQL Tab**
   - Query plans
   - Physical plans

## Performance Tuning

### Memory Configuration

```bash
spark-submit \
  --driver-memory 4g \
  --executor-memory 8g \
  --executor-cores 4 \
  --conf spark.sql.shuffle.partitions=10 \
  spark_streaming.py
```

### Batch Interval Tuning

```env
# Shorter interval = lower latency, higher overhead
BATCH_INTERVAL_SECONDS=5

# Longer interval = higher throughput, higher latency
BATCH_INTERVAL_SECONDS=30
```

### Watermark Configuration

```env
# Allow 30 seconds for late-arriving data
WATERMARK_DELAY=30 seconds

# More lenient for very delayed data
WATERMARK_DELAY=2 minutes
```

## Troubleshooting

### Issue: Cannot connect to Kinesis

**Solution:**
- Verify IAM role has `kinesis:GetRecords`, `kinesis:GetShardIterator`, `kinesis:DescribeStream`
- Check security group allows outbound HTTPS
- Verify stream name and region

### Issue: High GC time in Spark UI

**Solution:**
- Increase executor memory
- Reduce batch interval
- Increase shuffle partitions
- Enable off-heap memory

### Issue: Watermark not advancing

**Solution:**
- Check data has valid timestamps
- Verify timestamp parsing is correct
- Ensure data is arriving consistently

### Issue: RL model predictions fail

**Solution:**
- Verify model file exists at specified path
- Check model was trained with correct feature set
- Review logs for specific error
- Fallback to rule-based strategy will activate automatically

## Testing

### Unit Tests

```bash
pytest tests/test_transformations.py
pytest tests/test_rl_inference.py
```

### Integration Test with Local Files

```bash
# 1. Generate sample data
python ../alpaca-producer/alpaca_websocket_client.py

# 2. Run processor in local mode
LOCAL_MODE=true python spark_streaming.py
```

## Best Practices

1. **Always use checkpointing** for fault tolerance
2. **Monitor Spark UI** regularly for performance bottlenecks
3. **Tune batch interval** based on latency requirements
4. **Partition output** by symbol for efficient queries
5. **Use watermarks** to handle late data gracefully
6. **Log important metrics** to CloudWatch for monitoring

## License

MIT

