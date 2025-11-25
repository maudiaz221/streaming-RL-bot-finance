# Dashboard Streaming Configuration

## Overview
The dashboard supports both **Mock Data** mode (for testing) and **Live WebSocket** mode (for real Alpaca data).

## Environment Variables

Edit `/workspaces/arqui/streaming-RL-bot-finance/dashboard/.env.local`:

```bash
# Alpaca API Credentials
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here

# WebSocket Configuration
ALPACA_WEBSOCKET_URL=wss://stream.data.alpaca.markets/v2/test
STOCK_SYMBOLS=FAKEPACA

# Streaming Configuration
STREAM_UPDATE_INTERVAL_MS=5000    # Update interval in milliseconds (5000 = 5 seconds)
USE_MOCK_DATA=true               # true = mock data, false = live WebSocket

# Public configuration (exposed to browser)
NEXT_PUBLIC_SYMBOLS=FAKEPACA,AAPL,GOOGL,TSLA,MSFT,NVDA
```

## Usage

### Testing with Mock Data (Recommended for Development)

1. Set `USE_MOCK_DATA=true` in `.env.local`
2. Adjust `STREAM_UPDATE_INTERVAL_MS` as needed (default: 5000ms = 5 seconds)
3. Run the dashboard:
   ```bash
   cd /workspaces/arqui/streaming-RL-bot-finance/dashboard
   npm run dev
   ```
4. Open browser to `http://localhost:3000`
5. You should see:
   - Mock price data updating every 5 seconds
   - Chart populating with candles
   - Connection status: "Connected"

### Using Live WebSocket Data

1. Set `USE_MOCK_DATA=false` in `.env.local`
2. Ensure your `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are correct
3. **Important**: Close any other WebSocket connections to avoid hitting Alpaca's connection limit (3 concurrent connections per account)
4. Run the dashboard:
   ```bash
   cd /workspaces/arqui/streaming-RL-bot-finance/dashboard
   npm run dev
   ```
5. The dashboard will connect to Alpaca and stream real trade data

## Testing the WebSocket Connection

Before using live data, test the WebSocket connection:

```bash
cd /workspaces/arqui/streaming-RL-bot-finance/dashboard
npx tsx test-websocket.ts
```

Expected output:
```
✅ WebSocket connection opened
✅ Authentication successful
✅ Subscription confirmed
📈 Trade #1: FAKEPACA @ $134.56 (size: 3)
...
✅ Test successful! Received 5 trades.
```

## Configuring Update Interval

The `STREAM_UPDATE_INTERVAL_MS` variable controls how frequently the dashboard receives updates:

- **1000** = 1 second (high frequency, more data points)
- **5000** = 5 seconds (default, balanced)
- **10000** = 10 seconds (low frequency, less data)

**Note**: This only controls the SSE broadcast interval. The actual WebSocket messages arrive continuously and are buffered.

## Chart Behavior

The chart displays candlestick data:
- **Time**: Unix timestamp (seconds)
- **Open**: First trade price in the interval
- **High**: Highest price (with small jitter for visibility)
- **Low**: Lowest price (with small jitter for visibility)
- **Close**: Latest trade price
- **Volume**: Trade size

For flat data (O=H=L=C), the frontend adds a small jitter (±$0.01) to ensure candles are visible.

## Troubleshooting

### Connection Limit Exceeded (406)
- **Cause**: Too many concurrent WebSocket connections to Alpaca
- **Solution**: 
  1. Kill all node processes: `pkill -f node`
  2. Wait 60 seconds for connections to timeout
  3. Retry

### Chart Not Updating
- **Check 1**: Open browser console (F12) and look for `[Dashboard] Received stock data:` logs
- **Check 2**: Verify SSE connection in Network tab (should see `/api/stream` with "EventStream" type)
- **Check 3**: Ensure `STREAM_UPDATE_INTERVAL_MS` is a valid number

### No Data Appearing
- **Mock Mode**: Check server logs for `[API Stream] Mock trade:` messages
- **Live Mode**: Run `test-websocket.ts` to verify connectivity
- **Chart**: Ensure you're viewing the FAKEPACA symbol (other symbols show "Data Not Available")

## Architecture

```
┌─────────────────┐
│   Alpaca API    │ (WebSocket)
└────────┬────────┘
         │
         │ trades (continuous)
         │
┌────────▼────────────────────────┐
│  Next.js API Route              │
│  /app/api/stream/route.ts       │
│  - Connects to Alpaca           │
│  - OR generates mock data       │
│  - Accumulates trades           │
└────────┬────────────────────────┘
         │
         │ Server-Sent Events (SSE)
         │ Every STREAM_UPDATE_INTERVAL_MS
         │
┌────────▼────────────────────────┐
│  Frontend (React)               │
│  /app/page.tsx                  │
│  - Receives trade data          │
│  - Updates chart state          │
│  - Renders candlestick chart    │
└─────────────────────────────────┘
```

## Files Modified

- `/app/api/stream/route.ts` - SSE endpoint with mock/live modes
- `/app/page.tsx` - Chart data management
- `/lib/use-alpaca-stream.ts` - React hook for SSE
- `/.env.local` - Configuration
- `/test-websocket.ts` - WebSocket test utility

