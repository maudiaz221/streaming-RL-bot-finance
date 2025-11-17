# Alpaca Account & API Setup Guide

## Overview
This guide walks you through setting up an Alpaca account and obtaining API credentials for real-time stock market data streaming.

---

## 1. Create Alpaca Account

### Step 1: Sign Up
1. Go to https://alpaca.markets/
2. Click "Get Started" or "Sign Up"
3. Choose **"Paper Trading Only"** (No real money required)
4. Fill in your information:
   - Email address
   - Password
   - Accept terms and conditions
5. Verify your email address

**Note**: You do NOT need to provide any financial information, bank accounts, or credit cards for paper trading and IEX market data access.

---

## 2. Generate API Keys

### Step 1: Access Dashboard
1. Log in to https://app.alpaca.markets/
2. You'll be in the Paper Trading environment by default

### Step 2: Generate API Credentials
1. Navigate to "API Keys" in the left sidebar
2. Click "Generate New Key" or "View" if keys already exist
3. You'll receive:
   - **API Key ID** (looks like: `PKxxxxxxxxxxxxxxxxxx`)
   - **Secret Key** (looks like: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
   
⚠️ **IMPORTANT**: 
- Copy and save both keys immediately
- The Secret Key is only shown ONCE
- Store them securely (password manager, AWS Secrets Manager, etc.)
- Never commit these to Git or share publicly

### Step 3: Key Types
Alpaca provides two sets of keys:
- **Paper Trading Keys**: For testing with virtual money (what we'll use)
- **Live Trading Keys**: For real money trading (not needed for this project)

Make sure you're using **Paper Trading Keys** for this project.

---

## 3. Understanding Your Subscription

### Free Tier Includes:
- ✅ Unlimited IEX real-time market data streaming
- ✅ Access to trades, quotes, and 1-minute bars
- ✅ All US stocks and ETFs
- ✅ 1 concurrent WebSocket connection
- ✅ Historical data (bars, trades, quotes)
- ✅ Paper trading capabilities

### IEX Data vs SIP Data:
- **IEX (Free)**: Data from IEX exchange only (~2-3% of market volume)
- **SIP (Paid)**: Consolidated data from all exchanges (100% of market volume)

For this project, **IEX data is sufficient** and completely free.

---

## 4. Test Your API Keys

### Using Python:
```python
import requests

API_KEY = "YOUR_API_KEY_ID"
SECRET_KEY = "YOUR_SECRET_KEY"

# Test REST API
url = "https://paper-api.alpaca.markets/v2/account"
headers = {
    "APCA-API-KEY-ID": API_KEY,
    "APCA-API-SECRET-KEY": SECRET_KEY
}

response = requests.get(url, headers=headers)
print(response.json())
# Should return your paper trading account info
```

### Using WebSocket (Test Stream):
```python
import websocket
import json

def on_message(ws, message):
    print(f"Received: {message}")

def on_open(ws):
    # Authenticate
    auth = {
        "action": "auth",
        "key": "YOUR_API_KEY_ID",
        "secret": "YOUR_SECRET_KEY"
    }
    ws.send(json.dumps(auth))
    
    # Subscribe to test data
    subscribe = {
        "action": "subscribe",
        "trades": ["FAKEPACA"],
        "quotes": ["FAKEPACA"],
        "bars": ["FAKEPACA"]
    }
    ws.send(json.dumps(subscribe))

# Connect to test stream
ws = websocket.WebSocketApp(
    "wss://stream.data.alpaca.markets/v2/test",
    on_open=on_open,
    on_message=on_message
)
ws.run_forever()
```

---

## 5. WebSocket Endpoints Reference

### Market Data Streaming:
```
# IEX Real-time (FREE)
wss://stream.data.alpaca.markets/v2/iex

# SIP Real-time (Paid subscription required)
wss://stream.data.alpaca.markets/v2/sip

# Test Stream (Fake data for testing)
wss://stream.data.alpaca.markets/v2/test
```

### Account/Trading Updates:
```
# Paper Trading
wss://paper-api.alpaca.markets/stream

# Live Trading (not needed for this project)
wss://api.alpaca.markets/stream
```

---

## 6. Rate Limits & Connection Limits

### WebSocket Streaming:
- **Concurrent Connections**: 1 per subscription tier
- **Message Rate**: Unlimited (real-time as market generates)
- **Symbols**: Unlimited subscriptions within a single connection

### REST API:
- **Rate Limit**: 200 requests per minute per API key
- Sufficient for historical data fetching and account management

---

## 7. Available Symbols

### High-Volume Stocks (Good for Testing):
```python
symbols = [
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "TSLA",   # Tesla
    "NVDA",   # NVIDIA
    "GOOGL",  # Google
    "AMZN",   # Amazon
    "META",   # Meta
    "SPY",    # S&P 500 ETF
    "QQQ",    # NASDAQ ETF
]
```

### Test Symbol:
- Use `"FAKEPACA"` on the test stream for consistent data generation

---

## 8. Store API Keys Securely

### Option 1: Environment Variables (Local Development)
```bash
# .env file (DO NOT COMMIT TO GIT)
ALPACA_API_KEY=PKxxxxxxxxxxxxxxxxxx
ALPACA_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxx
```

### Option 2: AWS Secrets Manager (Production)
```bash
aws secretsmanager create-secret \
    --name alpaca/api-credentials \
    --secret-string '{"api_key":"PKxxx","secret_key":"xxx"}'
```

Then retrieve in your code:
```python
import boto3
import json

client = boto3.client('secretsmanager')
response = client.get_secret_value(SecretId='alpaca/api-credentials')
secrets = json.loads(response['SecretString'])

API_KEY = secrets['api_key']
SECRET_KEY = secrets['secret_key']
```

### Option 3: AWS Systems Manager Parameter Store
```bash
aws ssm put-parameter \
    --name /alpaca/api-key \
    --value "PKxxx" \
    --type SecureString

aws ssm put-parameter \
    --name /alpaca/secret-key \
    --value "xxx" \
    --type SecureString
```

---

## 9. Python Libraries

### Install Required Libraries:
```bash
pip install alpaca-trade-api websocket-client boto3
```

### Import in Your Code:
```python
import alpaca_trade_api as tradeapi
import websocket
```

### Official Alpaca Python SDK:
```python
from alpaca_trade_api import REST, Stream

# REST API client
api = REST(
    key_id='YOUR_API_KEY',
    secret_key='YOUR_SECRET_KEY',
    base_url='https://paper-api.alpaca.markets'
)

# Get account info
account = api.get_account()
print(account)

# Stream client (async)
stream = Stream(
    key_id='YOUR_API_KEY',
    secret_key='YOUR_SECRET_KEY',
    base_url='https://stream.data.alpaca.markets',
    data_feed='iex'
)

@stream.on_bar('AAPL')
async def on_bar(bar):
    print(f"Bar received: {bar}")

stream.run()
```

---

## 10. Documentation Resources

### Official Alpaca Documentation:
- **Main Docs**: https://docs.alpaca.markets/
- **WebSocket Streaming**: https://docs.alpaca.markets/docs/websocket-streaming
- **Market Data API**: https://docs.alpaca.markets/docs/about-market-data-api
- **Real-time Stock Data**: https://docs.alpaca.markets/docs/real-time-stock-pricing-data
- **Python SDK**: https://github.com/alpacahq/alpaca-trade-api-python

### API References:
- REST API: https://docs.alpaca.markets/reference/
- WebSocket Spec: https://docs.alpaca.markets/docs/streaming-market-data

---

## 11. Common Issues & Troubleshooting

### Issue 1: "unauthorized" message
**Cause**: Invalid API keys or wrong endpoint
**Solution**: 
- Verify you're using Paper Trading keys
- Check for typos in API key and secret
- Ensure you're connecting to the correct endpoint

### Issue 2: "connection limit exceeded"
**Cause**: Multiple WebSocket connections active
**Solution**:
- Close other connections
- Only maintain 1 active connection on free tier
- Check for zombie connections

### Issue 3: No data received after subscribing
**Cause**: Market is closed or symbol doesn't exist
**Solution**:
- Check market hours (9:30 AM - 4:00 PM ET, Mon-Fri)
- Use test stream with "FAKEPACA" for 24/7 data
- Verify symbol spelling

### Issue 4: "403 Forbidden" on WebSocket
**Cause**: Subscription doesn't include requested data feed
**Solution**:
- Use `iex` feed (free) instead of `sip` feed (paid)
- Change WebSocket URL to IEX endpoint

---

## 12. Best Practices

1. **Never hardcode API keys** - Use environment variables or secret management
2. **Implement reconnection logic** - WebSocket connections can drop
3. **Handle market hours** - Real data only flows during trading hours
4. **Use test stream for development** - Avoid hitting rate limits during testing
5. **Monitor connection status** - Implement heartbeat/ping-pong
6. **Batch Kinesis writes** - Don't send individual messages (expensive and slow)
7. **Log authentication events** - Track successful/failed auth attempts
8. **Set up alerts** - Notify when WebSocket disconnects unexpectedly

---

## 13. Quick Start Checklist

- [ ] Created Alpaca paper trading account
- [ ] Generated API keys (saved securely)
- [ ] Tested API keys with REST endpoint
- [ ] Tested WebSocket connection to test stream
- [ ] Stored API keys in AWS Secrets Manager or environment variables
- [ ] Installed required Python libraries
- [ ] Reviewed Alpaca documentation
- [ ] Identified stocks to track (20+ high-volume symbols)
- [ ] Verified market hours for live data testing

---

## 14. Cost Summary

| Item | Cost |
|------|------|
| Paper Trading Account | **FREE** |
| IEX Real-time Market Data | **FREE** |
| WebSocket Streaming (IEX) | **FREE** |
| Historical Data (IEX) | **FREE** |
| API Calls (REST) | **FREE** |
| **Total Monthly Cost** | **$0.00** |

**Optional Paid Upgrades** (NOT needed for this project):
- SIP Consolidated Feed: $99-$199/month
- Unlimited API calls: Higher tier plans
- Multiple concurrent connections: Higher tier plans

---

## Next Steps

After completing this setup:
1. Move to the AWS Setup Guide to configure cloud infrastructure
2. Implement the Alpaca WebSocket client (Lambda or ECS)
3. Test end-to-end data flow: Alpaca → Kinesis → PySpark
4. Begin building the RL model and dashboard

**Your Alpaca setup is now complete!** 🎉