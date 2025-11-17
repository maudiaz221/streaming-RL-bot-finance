'use client'

import { useState, useEffect } from 'react'
import StockChart from '@/components/StockChart'
import TradingSignals from '@/components/TradingSignals'
import RealtimeStats from '@/components/RealtimeStats'
import { StockData, RLPrediction, StreamStats, ChartData } from '@/lib/types'
import { generateMockStockData, MOCK_SYMBOLS } from '@/lib/mock-data'

export default function Home() {
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL')
  const [stockData, setStockData] = useState<StockData | null>(null)
  const [predictions, setPredictions] = useState<RLPrediction[]>([])
  const [chartData, setChartData] = useState<ChartData[]>([])
  const [streamStats, setStreamStats] = useState<StreamStats>({
    messagesReceived: 0,
    messagesPerSecond: 0,
    latencyMs: 25,
    lastUpdate: new Date().toISOString(),
  })

  // Simulate real-time data updates
  useEffect(() => {
    const interval = setInterval(() => {
      const newData = generateMockStockData(selectedSymbol)
      setStockData(newData)

      // Update predictions
      if (newData.prediction) {
        setPredictions(prev => [...prev, newData.prediction!].slice(-50))
      }

      // Update chart data
      setChartData(prev => {
        const newChartData = [...prev, {
          time: Math.floor(new Date().getTime() / 1000),
          open: newData.open,
          high: newData.high,
          low: newData.low,
          close: newData.close,
          volume: newData.volume,
        }]
        return newChartData.slice(-100) // Keep last 100 points
      })

      // Update stream stats
      setStreamStats(prev => ({
        messagesReceived: prev.messagesReceived + 1,
        messagesPerSecond: Math.floor(Math.random() * 50) + 20,
        latencyMs: Math.floor(Math.random() * 30) + 10,
        lastUpdate: new Date().toISOString(),
      }))
    }, 2000) // Update every 2 seconds

    return () => clearInterval(interval)
  }, [selectedSymbol])

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
                Live market data with RL-powered trading signals
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
                ● Live
              </span>
            </div>
          </div>

          {/* Symbol Selector */}
          <div className="flex gap-2 flex-wrap">
            {MOCK_SYMBOLS.map(symbol => (
              <button
                key={symbol}
                onClick={() => setSelectedSymbol(symbol)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  selectedSymbol === symbol
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {symbol}
              </button>
            ))}
          </div>
        </div>

        {/* Real-time Stats */}
        {stockData && (
          <RealtimeStats stockData={stockData} streamStats={streamStats} />
        )}

        {/* Main Content Grid */}
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

        {/* Footer Info */}
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

        {/* Notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            <strong>Note:</strong> This dashboard is currently using simulated data. 
            To connect to live data, configure AWS credentials and run the Alpaca WebSocket producer.
            See the documentation for setup instructions.
          </p>
        </div>
      </div>
    </main>
  )
}

