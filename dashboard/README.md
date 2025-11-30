# Binance Crypto Dashboard

Real-time cryptocurrency trading dashboard with live Binance WebSocket data and a cyberpunk aesthetic.

## Features

- Real-time candlestick charts with TradingView Lightweight Charts
- Live trade feed with buy/sell indicators
- Multi-coin support (BTC, ETH, BNB)
- Cyberpunk dark theme with neon accents
- Direct Binance WebSocket connection (no backend required)
- Responsive design with TailwindCSS

## Coins Tracked

- **BTCUSDT** - Bitcoin
- **ETHUSDT** - Ethereum  
- **BNBUSDT** - BNB

## Prerequisites

- Node.js 18+
- npm or yarn

## Installation

```bash
cd dashboard
npm install
```

## Usage

### Development Mode

```bash
npm run dev
```

Open http://localhost:3000

The dashboard will automatically connect to Binance's public WebSocket and start streaming live market data.

### Production Build

```bash
npm run build
npm start
```

## Architecture

```
┌─────────────────────────┐
│   Binance WebSocket     │
│   (Public Streams)      │
└───────────┬─────────────┘
            │
            │ wss://stream.binance.com:9443/stream
            │ btcusdt@trade, btcusdt@kline_1m
            │
┌───────────▼─────────────┐
│   Browser (React)       │
│   - Direct WebSocket    │
│   - useBinanceStream    │
└───────────┬─────────────┘
            │
┌───────────▼─────────────┐
│   Components            │
│   - PriceDisplay        │
│   - CryptoChart         │
│   - LiveTrades          │
│   - CryptoStats         │
└─────────────────────────┘
```

## Components

### PriceDisplay
Large animated price display with 24h change percentage.

### CryptoChart
Real-time candlestick chart using TradingView Lightweight Charts with neon styling.

### LiveTrades
Scrolling live trade feed showing individual trades with buy/sell indicators.

### CryptoStats
Grid of real-time statistics including 24h high/low, volume, and stream stats.

## Binance WebSocket Streams

The dashboard subscribes to:
- `{symbol}@trade` - Individual trades for live ticker
- `{symbol}@kline_1m` - 1-minute candles for chart

## Theme Customization

The cyberpunk theme is defined in:
- `app/globals.css` - CSS variables and effects
- `tailwind.config.js` - Extended color palette

Key colors:
- `--neon-cyan` - Primary accent
- `--neon-magenta` - Secondary accent
- `--neon-green` - Positive/Buy
- `--neon-red` - Negative/Sell

## Deployment

### Vercel (Recommended)

```bash
npm i -g vercel
vercel
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

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

MIT
