#!/bin/bash

# Setup script for dashboard .env.local

echo "🔧 Dashboard Environment Setup"
echo "==============================="
echo ""

# Check if alpaca-producer .env exists
PRODUCER_ENV="/workspaces/arqui/streaming-RL-bot-finance/alpaca-producer/.env"

if [ -f "$PRODUCER_ENV" ]; then
  echo "✅ Found Alpaca credentials in alpaca-producer/.env"
  echo "📋 Copying credentials to dashboard/.env.local..."
  
  # Extract credentials from producer .env
  ALPACA_API_KEY=$(grep "^ALPACA_API_KEY=" "$PRODUCER_ENV" | cut -d '=' -f2-)
  ALPACA_SECRET_KEY=$(grep "^ALPACA_SECRET_KEY=" "$PRODUCER_ENV" | cut -d '=' -f2-)
  
  # Create .env.local in dashboard
  cat > .env.local << ENV
# Alpaca API Credentials (copied from alpaca-producer/.env)
ALPACA_API_KEY=$ALPACA_API_KEY
ALPACA_SECRET_KEY=$ALPACA_SECRET_KEY

# Alpaca WebSocket URL (use test stream for development)
# Production: wss://stream.data.alpaca.markets/v2/iex
# Test: wss://stream.data.alpaca.markets/v2/test
ALPACA_WEBSOCKET_URL=wss://stream.data.alpaca.markets/v2/test

# Symbols to track (comma-separated)
STOCK_SYMBOLS=FAKEPACA,AAPL,GOOGL,TSLA,MSFT,NVDA

# Next.js public variables (exposed to browser)
NEXT_PUBLIC_STOCK_SYMBOLS=FAKEPACA,AAPL,GOOGL,TSLA,MSFT,NVDA
ENV

  echo ""
  echo "✅ Successfully created .env.local"
  echo ""
  echo "📝 Configuration:"
  echo "   - Using Alpaca test stream (FAKEPACA)"
  echo "   - Tracking symbols: FAKEPACA, AAPL, GOOGL, TSLA, MSFT, NVDA"
  echo ""
  echo "🚀 Next steps:"
  echo "   1. npm install"
  echo "   2. npm run dev"
  echo "   3. Open http://localhost:3000"
  echo ""
  
else
  echo "❌ Could not find alpaca-producer/.env"
  echo ""
  echo "📝 Please create .env.local manually:"
  echo "   cp .env.local.example .env.local"
  echo "   # Then edit .env.local with your API keys"
  echo ""
fi
