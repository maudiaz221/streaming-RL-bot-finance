# Stock Trading Dashboard

Real-time Next.js dashboard for visualizing stock market data and RL trading predictions.

## Features

- ✅ Real-time candlestick charts with TradingView Lightweight Charts
- ✅ Live technical indicators display
- ✅ RL trading signals visualization
- ✅ Multi-symbol tracking
- ✅ Streaming statistics
- ✅ Responsive design with TailwindCSS
- ✅ Mock data mode for development

## Prerequisites

- Node.js 18+
- npm or yarn

## Installation

```bash
cd dashboard
npm install
```

## Configuration

Create a `.env.local` file in the dashboard directory:

```env
AWS_REGION=us-east-1
S3_BUCKET_NAME=stock-trading-data
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

## Usage

### Development Mode (Mock Data)

```bash
npm run dev
```

Open http://localhost:3000

The dashboard will use simulated data by default, so you can develop without AWS setup.

### Production Build

```bash
npm run build
npm start
```

## Dashboard Pages

### Main Dashboard (`/`)
- Real-time stock price charts
- Live RL predictions with buy/sell/hold signals
- Current streaming statistics
- Technical indicators (RSI, MACD, Bollinger Bands)

## Components

### StockChart
Real-time candlestick chart using TradingView Lightweight Charts.

```tsx
import StockChart from '@/components/StockChart'

<StockChart 
  data={chartData} 
  symbol="AAPL" 
  height={500} 
/>
```

### TradingSignals
Display RL model predictions with confidence scores.

```tsx
import TradingSignals from '@/components/TradingSignals'

<TradingSignals 
  predictions={predictions} 
  symbol="AAPL" 
/>
```

### RealtimeStats
Grid of real-time statistics and technical indicators.

```tsx
import RealtimeStats from '@/components/RealtimeStats'

<RealtimeStats 
  stockData={stockData} 
  streamStats={streamStats} 
/>
```

## Connecting to Real Data

### Option 1: WebSocket Server (Recommended)

Create a WebSocket server that reads from S3/Kinesis and broadcasts to the dashboard:

```typescript
// lib/websocket.ts
import { io } from 'socket.io-client'

export function connectToDataStream(symbol: string) {
  const socket = io('ws://your-server:3001')
  
  socket.emit('subscribe', { symbols: [symbol] })
  
  socket.on('stockData', (data) => {
    // Handle incoming data
  })
  
  return socket
}
```

### Option 2: REST API with Polling

Query S3/DynamoDB periodically:

```typescript
// lib/api.ts
export async function fetchLatestData(symbol: string) {
  const response = await fetch(`/api/stocks/${symbol}`)
  return response.json()
}
```

### Option 3: AWS AppSync GraphQL

Use real-time GraphQL subscriptions:

```typescript
import { API, graphqlOperation } from 'aws-amplify'

const subscription = API.graphql(
  graphqlOperation(onStockUpdate)
).subscribe({
  next: ({ value }) => {
    // Handle update
  }
})
```

## Data Flow

```
AWS S3/Kinesis
     ↓
WebSocket Server / API
     ↓
Next.js Dashboard
     ↓
React Components
     ↓
TradingView Charts
```

## Customization

### Adding New Symbols

Edit `lib/mock-data.ts`:

```typescript
export const MOCK_SYMBOLS = [
  'AAPL', 'TSLA', 'NVDA', 'MSFT', 
  'YOUR_SYMBOL'
]
```

### Changing Update Frequency

In `app/page.tsx`, adjust the interval:

```typescript
const interval = setInterval(() => {
  // Update logic
}, 1000) // 1 second instead of 2
```

### Customizing Charts

Modify chart options in `components/StockChart.tsx`:

```typescript
const chart = createChart(chartContainerRef.current, {
  layout: {
    background: { color: '#1a1a1a' }, // Dark theme
    textColor: '#ffffff',
  },
  // ... more options
})
```

## Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### AWS Amplify

```bash
amplify init
amplify add hosting
amplify publish
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

Build and run:

```bash
docker build -t stock-dashboard .
docker run -p 3000:3000 stock-dashboard
```

## Performance Optimization

### 1. Enable React Server Components

Components without client interactions can be server components for better performance.

### 2. Optimize Chart Rendering

Limit chart data points:

```typescript
setChartData(prev => {
  const newData = [...prev, newPoint]
  return newData.slice(-200) // Keep last 200 points
})
```

### 3. Debounce Updates

```typescript
import { debounce } from 'lodash'

const debouncedUpdate = debounce(updateChart, 100)
```

### 4. Memoize Components

```typescript
import { memo } from 'react'

export default memo(StockChart)
```

## Troubleshooting

### Charts not rendering

**Solution:**
- Ensure `lightweight-charts` is installed
- Check browser console for errors
- Verify data format matches ChartData type

### WebSocket connection fails

**Solution:**
- Check CORS settings on server
- Verify WebSocket URL is correct
- Ensure server is running

### Slow performance

**Solution:**
- Reduce update frequency
- Limit number of data points
- Use React.memo for components
- Enable production build optimizations

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

MIT




