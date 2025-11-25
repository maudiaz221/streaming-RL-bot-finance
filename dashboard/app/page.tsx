'use client'

import { useState, useEffect } from 'react'
import StockChart from '@/components/StockChart'
import TradingSignals from '@/components/TradingSignals'
import RealtimeStats from '@/components/RealtimeStats'
import { RLPrediction, ChartData } from '@/lib/types'
import { useAlpacaStream } from '@/lib/use-alpaca-stream'

// Available symbols (from environment or default)
const AVAILABLE_SYMBOLS = (process.env.NEXT_PUBLIC_STOCK_SYMBOLS || 'FAKEPACA,AAPL,GOOGL,TSLA,MSFT,NVDA').split(',')

export default function Home() {
  const [selectedSymbol, setSelectedSymbol] = useState(AVAILABLE_SYMBOLS[0])
  const [predictions, setPredictions] = useState<RLPrediction[]>([])
  const [chartData, setChartData] = useState<ChartData[]>([])

  // Use the Alpaca WebSocket stream
  const { stockData, streamStats, connectionStatus, error, reconnect } = useAlpacaStream(selectedSymbol)

  // Update chart data when new stock data arrives
  useEffect(() => {
    if (stockData) {
      console.log('[Dashboard] Received stock data:', stockData)
      
      setChartData(prev => {
        // Use OHLC data directly from backend (already has proper candle structure)
        const newPoint = {
          time: Math.floor(new Date().getTime() / 1000),
          open: stockData.open,
          high: stockData.high,
          low: stockData.low,
          close: stockData.close,
          volume: stockData.volume,
        }
        
        console.log('[Dashboard] Adding chart point:', newPoint)
        const newChartData = [...prev, newPoint]
        console.log('[Dashboard] Total chart points:', newChartData.length)
        
        return newChartData.slice(-100) // Keep last 100 points
      })

      // Generate mock predictions for now (replace with real RL model later)
      if (Math.random() > 0.7) { // Occasionally generate predictions
        const priceChange = stockData.close - stockData.open
        let action = 0 // HOLD
        if (priceChange > 0.5) action = 1 // BUY
        if (priceChange < -0.5) action = 2 // SELL

        const prediction: RLPrediction = {
          action,
          actionName: ['HOLD', 'BUY', 'SELL'][action],
          confidence: 0.6 + Math.random() * 0.3,
          timestamp: stockData.timestamp,
        }
        setPredictions(prev => [...prev, prediction].slice(-50))
      }
    }
  }, [stockData])

  return (
    <main className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-lg border p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Real-Time Stock Trading Dashboard
              </h1>
              <p className="text-gray-600 mt-1">
                Live market data from Alpaca WebSocket
              </p>
            </div>
            <div className="flex items-center gap-2">
              {connectionStatus === 'connected' && (
                <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium flex items-center gap-1">
                  <span className="w-2 h-2 bg-green-600 rounded-full animate-pulse"></span>
                  Live
                </span>
              )}
              {connectionStatus === 'connecting' && (
                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                  Connecting...
                </span>
              )}
              {connectionStatus === 'error' && (
                <button 
                  onClick={reconnect}
                  className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm font-medium hover:bg-red-200"
                >
                  Reconnect
                </button>
              )}
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
              ⚠️ {error}
            </div>
          )}

          {/* Symbol Selector */}
          <div className="flex gap-2 flex-wrap">
            {AVAILABLE_SYMBOLS.map(symbol => (
              <button
                key={symbol}
                onClick={() => setSelectedSymbol(symbol.trim())}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  selectedSymbol === symbol.trim()
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {symbol.trim()}
              </button>
            ))}
          </div>
        </div>

        {/* Data Availability Notice */}
        {selectedSymbol !== 'FAKEPACA' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800">
              <strong>⚠️ Data Not Available:</strong> Live data is currently only available for FAKEPACA (test stream). 
              Other symbols require market hours and may incur data fees.
            </p>
          </div>
        )}

        {/* Real-time Stats */}
        {stockData && selectedSymbol === 'FAKEPACA' && (
          <RealtimeStats stockData={stockData} streamStats={streamStats} />
        )}

        {/* Main Content Grid */}
        {selectedSymbol === 'FAKEPACA' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chart Section - 2/3 width */}
            <div className="lg:col-span-2 bg-white rounded-lg border p-6">
              <StockChart data={chartData} symbol={selectedSymbol} height={500} />
            </div>

            {/* Signals Section - 1/3 width */}
            <div className="lg:col-span-1">
              {predictions.length > 0 && (
                <TradingSignals predictions={predictions} symbol={selectedSymbol} />
              )}
            </div>
          </div>
        )}

        {/* Footer Info */}
        {selectedSymbol === 'FAKEPACA' && (
          <div className="bg-white rounded-lg border p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-sm text-gray-600">Messages Received</div>
                <div className="text-2xl font-bold text-gray-900">
                  {streamStats.messagesReceived.toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Messages/Second</div>
                <div className="text-2xl font-bold text-gray-900">
                  {streamStats.messagesPerSecond}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Average Latency</div>
                <div className="text-2xl font-bold text-gray-900">
                  {streamStats.latencyMs}ms
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Connection Info */}
        <div className={`border rounded-lg p-4 ${
          connectionStatus === 'connected' 
            ? 'bg-green-50 border-green-200' 
            : 'bg-blue-50 border-blue-200'
        }`}>
          <p className={`text-sm ${
            connectionStatus === 'connected' ? 'text-green-800' : 'text-blue-800'
          }`}>
            {connectionStatus === 'connected' ? (
              <>
                <strong>✅ Connected:</strong> Receiving live data from Alpaca WebSocket API
              </>
            ) : (
              <>
                <strong>📡 Setup Required:</strong> Configure your Alpaca API credentials in{' '}
                <code className="px-1 py-0.5 bg-white rounded">.env.local</code> to see live data.
                Copy <code className="px-1 py-0.5 bg-white rounded">.env.local.example</code> and add your API keys.
              </>
            )}
          </p>
        </div>
      </div>
    </main>
  )
}




