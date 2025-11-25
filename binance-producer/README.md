# Alpaca WebSocket Producer

Real-time WebSocket client that connects to Alpaca's market data stream and forwards data to AWS Kinesis or local files.

## Features

- ✅ Real-time WebSocket connection to Alpaca IEX feed
- ✅ Automatic authentication and subscription management
- ✅ Batched Kinesis writes for efficiency
- ✅ Automatic reconnection with exponential backoff
- ✅ Local development mode (writes to files instead of Kinesis)
- ✅ Comprehensive logging and statistics
- ✅ Docker support for ECS/container deployment

## Quick Start

### Prerequisites
- Python 3.11+
- Alpaca API keys (in `.env` file in project root)
- AWS credentials (for Kinesis mode)

### Installation

```bash
cd alpaca-producer
pip install -r requirements.txt
```

### Configuration

The application reads from the `.env` file in the project root. Required variables:

```env
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
STOCK_SYMBOLS=AAPL,TSLA,NVDA,MSFT,SPY,QQQ
```

For AWS/Kinesis mode:
```env
LOCAL_MODE=false
AWS_REGION=us-east-1
KINESIS_STREAM_NAME=stock-market-stream
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
```

For local development:
```env
LOCAL_MODE=true
LOCAL_OUTPUT_PATH=./data/stream_output
```

### Usage

#### Run Locally (Python)
```bash
python alpaca_websocket_client.py
```

#### Test Configuration
```bash
python config.py
```

#### Run with Docker
```bash
# Build image
docker build -t alpaca-producer .

# Run container
docker run --env-file ../.env alpaca-producer
```

#### Deploy to AWS ECS
See the infrastructure setup scripts in `../infrastructure/`

## Architecture

```
Alpaca WebSocket API (wss://stream.data.alpaca.markets/v2/iex)
         ↓
   [Authentication]
         ↓
   [Subscribe to Symbols]
         ↓
   [Receive Messages]
         ↓
   [Batch Messages]
         ↓
Amazon Kinesis / Local Files
```

## Data Flow

1. **Connection**: Establish WebSocket connection to Alpaca
2. **Authentication**: Send API credentials
3. **Subscription**: Subscribe to trades, quotes, and bars for configured symbols
4. **Reception**: Receive real-time market data
5. **Batching**: Batch messages for efficient writes
6. **Forwarding**: Send to Kinesis (or local files in development mode)

## Message Types

The client subscribes to three types of market data:

### Trades (`t`)
```json
{
  "T": "t",
  "S": "AAPL",
  "p": 150.25,
  "s": 100,
  "t": "2024-01-15T10:30:00.123Z",
  "x": "D"
}
```

### Quotes (`q`)
```json
{
  "T": "q",
  "S": "AAPL",
  "bp": 150.20,
  "bs": 100,
  "ap": 150.25,
  "as": 50,
  "t": "2024-01-15T10:30:00.123Z"
}
```

### Bars (`b`)
```json
{
  "T": "b",
  "S": "AAPL",
  "o": 150.00,
  "h": 150.50,
  "l": 149.75,
  "c": 150.25,
  "v": 10000,
  "t": "2024-01-15T10:30:00Z"
}
```

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `ALPACA_API_KEY` | Alpaca API key | Required |
| `ALPACA_SECRET_KEY` | Alpaca secret key | Required |
| `ALPACA_WEBSOCKET_URL` | WebSocket endpoint | `wss://stream.data.alpaca.markets/v2/iex` |
| `STOCK_SYMBOLS` | Comma-separated symbols | `AAPL,TSLA,...` |
| `LOCAL_MODE` | Use local files instead of Kinesis | `false` |
| `KINESIS_STREAM_NAME` | Kinesis stream name | `stock-market-stream` |
| `BATCH_SIZE` | Records per batch | `100` |
| `BATCH_TIMEOUT_SECONDS` | Max seconds before flush | `5` |
| `MAX_RECONNECT_ATTEMPTS` | Max reconnection tries | `5` |

## Monitoring

The client logs statistics every 1000 messages:
- Total messages received
- Records sent to Kinesis/files
- Batches sent
- Failed records

## Error Handling

- **Authentication failures**: Logs error and exits
- **Connection drops**: Automatic reconnection with exponential backoff
- **Kinesis errors**: Logs failed records, continues processing
- **Invalid messages**: Logs and skips

## Development

### Local Testing (No AWS)

Set `LOCAL_MODE=true` in `.env`:

```bash
LOCAL_MODE=true
LOCAL_OUTPUT_PATH=./data/stream_output
python alpaca_websocket_client.py
```

Data will be written to JSON files in `./data/stream_output/`

### Using Test Stream

For 24/7 testing without market hours:

```env
ALPACA_WEBSOCKET_URL=wss://stream.data.alpaca.markets/v2/test
STOCK_SYMBOLS=FAKEPACA
```

## Troubleshooting

### "unauthorized" error
- Verify API keys are correct
- Ensure using Paper Trading keys
- Check for whitespace in `.env`

### "connection limit exceeded"
- Close other WebSocket connections
- Free tier allows 1 concurrent connection

### No data received
- Check market hours (9:30 AM - 4:00 PM ET)
- Use test stream with "FAKEPACA" for 24/7 data
- Verify symbols are valid

### Kinesis permission errors
- Check IAM role has `kinesis:PutRecord` and `kinesis:PutRecords`
- Verify stream name is correct
- Ensure AWS credentials are valid

## Performance

- Handles 4,096+ messages per second
- Batches up to 500 records per Kinesis API call
- Sub-second latency from Alpaca to Kinesis

## License

MIT


