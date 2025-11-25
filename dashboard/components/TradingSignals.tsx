'use client'

import { RLPrediction } from '@/lib/types'
import { getActionColor, formatTimestamp } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface TradingSignalsProps {
  predictions: RLPrediction[]
  symbol: string
}

export default function TradingSignals({ predictions, symbol }: TradingSignalsProps) {
  const latestPrediction = predictions[predictions.length - 1]

  const getActionIcon = (action: string) => {
    switch (action.toUpperCase()) {
      case 'BUY':
        return <TrendingUp className="w-5 h-5" />
      case 'SELL':
        return <TrendingDown className="w-5 h-5" />
      default:
        return <Minus className="w-5 h-5" />
    }
  }

  return (
    <div className="bg-white rounded-lg border p-4">
      <h3 className="text-lg font-semibold mb-4">Trading Signals - {symbol}</h3>
      
      {latestPrediction && (
        <div className={`mb-4 p-4 rounded-lg border-2 ${getActionColor(latestPrediction.actionName)}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              {getActionIcon(latestPrediction.actionName)}
              <span className="text-2xl font-bold">{latestPrediction.actionName}</span>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-600">Confidence</div>
              <div className="text-xl font-semibold">
                {(latestPrediction.confidence * 100).toFixed(1)}%
              </div>
            </div>
          </div>
          <div className="text-sm text-gray-600">
            {formatTimestamp(latestPrediction.timestamp)}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h4 className="text-sm font-medium text-gray-600">Recent Signals</h4>
        <div className="max-h-64 overflow-y-auto space-y-2">
          {predictions.slice(-10).reverse().map((prediction, idx) => (
            <div
              key={idx}
              className={`flex items-center justify-between p-2 rounded border ${getActionColor(prediction.actionName)}`}
            >
              <div className="flex items-center gap-2">
                {getActionIcon(prediction.actionName)}
                <span className="font-medium">{prediction.actionName}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm">
                  {(prediction.confidence * 100).toFixed(0)}%
                </span>
                <span className="text-xs text-gray-600">
                  {formatTimestamp(prediction.timestamp)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}




