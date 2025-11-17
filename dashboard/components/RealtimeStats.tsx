'use client'

import { StockData, StreamStats } from '@/lib/types'
import { formatCurrency, formatNumber, formatPercent, getPriceChangeColor } from '@/lib/utils'
import { Activity, TrendingUp, BarChart3, Zap } from 'lucide-react'

interface RealtimeStatsProps {
  stockData: StockData
  streamStats: StreamStats
}

export default function RealtimeStats({ stockData, streamStats }: RealtimeStatsProps) {
  const priceChange = stockData.close - stockData.open
  const priceChangePct = stockData.open !== 0 ? (priceChange / stockData.open) * 100 : 0

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Current Price */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-medium text-gray-600">Current Price</span>
        </div>
        <div className="text-2xl font-bold">{formatCurrency(stockData.close)}</div>
        <div className={`text-sm ${getPriceChangeColor(priceChange)}`}>
          {priceChange >= 0 ? '+' : ''}{formatCurrency(priceChange)} ({formatPercent(priceChangePct)})
        </div>
      </div>

      {/* Volume */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center gap-2 mb-2">
          <BarChart3 className="w-4 h-4 text-purple-600" />
          <span className="text-sm font-medium text-gray-600">Volume</span>
        </div>
        <div className="text-2xl font-bold">{formatNumber(stockData.volume, 0)}</div>
        {stockData.indicators && (
          <div className="text-sm text-gray-600">
            Ratio: {formatNumber(stockData.indicators.volumeRatio, 2)}x
          </div>
        )}
      </div>

      {/* RSI */}
      {stockData.indicators && (
        <div className="bg-white rounded-lg border p-4">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-orange-600" />
            <span className="text-sm font-medium text-gray-600">RSI</span>
          </div>
          <div className="text-2xl font-bold">{formatNumber(stockData.indicators.rsi, 1)}</div>
          <div className="text-sm text-gray-600">
            {stockData.indicators.rsi < 30 && <span className="text-green-600">Oversold</span>}
            {stockData.indicators.rsi > 70 && <span className="text-red-600">Overbought</span>}
            {stockData.indicators.rsi >= 30 && stockData.indicators.rsi <= 70 && <span>Neutral</span>}
          </div>
        </div>
      )}

      {/* Stream Stats */}
      <div className="bg-white rounded-lg border p-4">
        <div className="flex items-center gap-2 mb-2">
          <Zap className="w-4 h-4 text-green-600" />
          <span className="text-sm font-medium text-gray-600">Stream Stats</span>
        </div>
        <div className="text-2xl font-bold">{streamStats.messagesPerSecond.toFixed(0)}/s</div>
        <div className="text-sm text-gray-600">
          Latency: {streamStats.latencyMs.toFixed(0)}ms
        </div>
      </div>

      {/* Technical Indicators Grid */}
      {stockData.indicators && (
        <>
          <div className="bg-white rounded-lg border p-4">
            <div className="text-sm font-medium text-gray-600 mb-2">MACD</div>
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>Line:</span>
                <span className="font-medium">{formatNumber(stockData.indicators.macdLine, 2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Signal:</span>
                <span className="font-medium">{formatNumber(stockData.indicators.macdSignal, 2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Histogram:</span>
                <span className={`font-medium ${getPriceChangeColor(stockData.indicators.macdHistogram)}`}>
                  {formatNumber(stockData.indicators.macdHistogram, 2)}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border p-4">
            <div className="text-sm font-medium text-gray-600 mb-2">Bollinger Bands</div>
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>Upper:</span>
                <span className="font-medium">{formatCurrency(stockData.indicators.bbUpper)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Middle:</span>
                <span className="font-medium">{formatCurrency(stockData.indicators.bbMiddle)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>Lower:</span>
                <span className="font-medium">{formatCurrency(stockData.indicators.bbLower)}</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg border p-4">
            <div className="text-sm font-medium text-gray-600 mb-2">Moving Averages</div>
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>5-min:</span>
                <span className="font-medium">{formatCurrency(stockData.indicators.ma5min)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>15-min:</span>
                <span className="font-medium">{formatCurrency(stockData.indicators.ma15min)}</span>
              </div>
              {stockData.indicators.ma1hour && (
                <div className="flex justify-between text-sm">
                  <span>1-hour:</span>
                  <span className="font-medium">{formatCurrency(stockData.indicators.ma1hour)}</span>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg border p-4">
            <div className="text-sm font-medium text-gray-600 mb-2">Volatility</div>
            <div className="text-2xl font-bold">{formatNumber(stockData.indicators.volatility, 2)}</div>
            <div className="text-sm text-gray-600 mt-2">
              {stockData.indicators.volatility > 3 && <span className="text-red-600">High Volatility</span>}
              {stockData.indicators.volatility <= 3 && stockData.indicators.volatility > 1 && <span className="text-orange-600">Medium Volatility</span>}
              {stockData.indicators.volatility <= 1 && <span className="text-green-600">Low Volatility</span>}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

