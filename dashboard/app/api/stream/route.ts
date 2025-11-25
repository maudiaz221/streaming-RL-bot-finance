/**
 * API Route for Server-Sent Events (SSE) streaming from Alpaca WebSocket
 * This route connects to Alpaca's WebSocket API and streams data to the frontend
 */

import { NextRequest } from 'next/server'
import { AlpacaWebSocketClient, AlpacaMessage } from '@/lib/alpaca-websocket'

// Disable response caching and use Node.js runtime
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'
export const maxDuration = 300 // Allow up to 5 minutes for streaming

// Singleton WebSocket client instance
let alpacaClient: AlpacaWebSocketClient | null = null
let clientCount = 0

// OHLC candle data structure for proper candlestick rendering
interface CandleData {
  [symbol: string]: {
    open: number
    high: number
    low: number
    close: number
    volume: number
    timestamp: string
  }
}

const latestCandles: CandleData = {}

function getOrCreateAlpacaClient(): AlpacaWebSocketClient {
  if (!alpacaClient || !alpacaClient.isConnected()) {
    const apiKey = process.env.ALPACA_API_KEY
    const secretKey = process.env.ALPACA_SECRET_KEY
    const wsUrl = process.env.ALPACA_WEBSOCKET_URL || 'wss://stream.data.alpaca.markets/v2/test'
    const symbols = (process.env.STOCK_SYMBOLS || 'FAKEPACA').split(',').map(s => s.trim())

    if (!apiKey || !secretKey) {
      throw new Error('Alpaca API credentials not configured. Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env.local')
    }

    console.log('[API Stream] Creating new Alpaca WebSocket client')
    console.log(`[API Stream] WebSocket URL: ${wsUrl}`)
    console.log(`[API Stream] Symbols: ${symbols.join(', ')}`)

    alpacaClient = new AlpacaWebSocketClient(apiKey, secretKey, wsUrl, symbols)
    
    // Set up message handler - ONLY process trades (like alpaca-producer)
    alpacaClient.onMessage((msg: AlpacaMessage) => {
      // Only process trade messages (T === 't')
      if (msg.T === 't') {
        const symbol = msg.S
        const price = msg.p || 0
        
        // Build OHLC candle from trades
        if (!latestCandles[symbol]) {
          latestCandles[symbol] = {
            open: price,
            high: price,
            low: price,
            close: price,
            volume: msg.s || 0,
            timestamp: msg.t || new Date().toISOString()
          }
        } else {
          // Update existing candle
          latestCandles[symbol].high = Math.max(latestCandles[symbol].high, price)
          latestCandles[symbol].low = Math.min(latestCandles[symbol].low, price)
          latestCandles[symbol].close = price
          latestCandles[symbol].volume += msg.s || 0
          latestCandles[symbol].timestamp = msg.t || new Date().toISOString()
        }
        
        console.log(`[API Stream] Trade received: ${symbol} @ $${msg.p}`)
      }
    })
  }

  return alpacaClient
}

export async function GET(req: NextRequest) {
  console.log('[API Stream] New SSE connection request')

  try {
    // Configuration
    const useMockData = process.env.USE_MOCK_DATA === 'true'
    const updateIntervalMs = parseInt(process.env.STREAM_UPDATE_INTERVAL_MS || '5000', 10)
    
    console.log(`[API Stream] Configuration:`)
    console.log(`  - Mock Data: ${useMockData}`)
    console.log(`  - Update Interval: ${updateIntervalMs}ms (${updateIntervalMs/1000}s)`)

    if (!useMockData) {
      // Get or create the WebSocket client
      const client = getOrCreateAlpacaClient()
      clientCount++

      if (!client.isConnected()) {
        console.log('[API Stream] Connecting to Alpaca WebSocket...')
        await client.connect()
        console.log('[API Stream] Successfully connected to Alpaca')
      }
    } else {
      console.log('[API Stream] Using MOCK DATA mode')
    }

    // Create a readable stream for SSE
    const stream = new ReadableStream({
      start(controller) {
        console.log(`[API Stream] SSE stream started (${clientCount} active clients)`)

        // Send initial connection message
        const encoder = new TextEncoder()
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({
          type: 'connected',
          timestamp: new Date().toISOString(),
          message: useMockData ? 'Connected to Mock Data Stream' : 'Connected to Alpaca WebSocket stream'
        })}\n\n`))

        // Mock data state (persists across intervals)
        let mockPrice = 105.0
        let mockTrend = 1 // 1 for uptrend, -1 for downtrend
        
        // Set up periodic data sending
        const interval = setInterval(() => {
          try {
            if (useMockData) {
              // Generate PROPER OHLC candle with visible body
              const openPrice = mockPrice
              
              // Generate realistic price movement during the interval
              const priceChange = (Math.random() * 2.0 - 1.0) + (mockTrend * 0.3)
              const closePrice = parseFloat((openPrice + priceChange).toFixed(2))
              
              // High and Low should extend beyond Open/Close for realistic wicks
              const highPrice = Math.max(openPrice, closePrice) + Math.random() * 0.5
              const lowPrice = Math.min(openPrice, closePrice) - Math.random() * 0.5
              
              // Update price for next candle
              mockPrice = closePrice
              
              // Keep price in reasonable range (100-115)
              if (mockPrice > 115) {
                mockPrice = 115
                mockTrend = -1
              } else if (mockPrice < 100) {
                mockPrice = 100
                mockTrend = 1
              }
              
              // Occasionally change trend (every ~10% of updates)
              if (Math.random() > 0.9) {
                mockTrend *= -1
              }
              
              // Create proper OHLC candle
              latestCandles['FAKEPACA'] = {
                open: parseFloat(openPrice.toFixed(2)),
                high: parseFloat(highPrice.toFixed(2)),
                low: parseFloat(lowPrice.toFixed(2)),
                close: parseFloat(closePrice.toFixed(2)),
                volume: Math.floor(Math.random() * 1000) + 100,
                timestamp: new Date().toISOString()
              }
              
              const direction = closePrice > openPrice ? '🟢' : '🔴'
              console.log(`[API Stream] ${direction} Mock candle: FAKEPACA O:$${openPrice.toFixed(2)} H:$${highPrice.toFixed(2)} L:$${lowPrice.toFixed(2)} C:$${closePrice.toFixed(2)}`)
            }

            // Send latest candles
            const data = {
              type: 'update',
              timestamp: new Date().toISOString(),
              candles: latestCandles
            }
            
            controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`))
          } catch (error) {
            console.error('[API Stream] Error sending data:', error)
          }
        }, updateIntervalMs)

        // Handle client disconnect
        req.signal.addEventListener('abort', () => {
          console.log('[API Stream] Client disconnected')
          clearInterval(interval)
          clientCount--
          
          // If no more clients, optionally disconnect the WebSocket
          // (Keep it connected for now to maintain the stream)
          if (clientCount === 0) {
            console.log('[API Stream] No more clients connected')
            // Optionally: alpacaClient?.disconnect()
          }

          try {
            controller.close()
          } catch (error) {
            // Controller already closed
          }
        })
      },
      cancel() {
        console.log('[API Stream] Stream cancelled')
        clientCount--
      }
    })

    // Return SSE response
    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no', // Disable buffering in nginx
      },
    })
  } catch (error) {
    console.error('[API Stream] Error setting up stream:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Failed to connect to Alpaca WebSocket',
        message: error instanceof Error ? error.message : 'Unknown error'
      }),
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    )
  }
}

