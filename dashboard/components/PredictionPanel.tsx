'use client'

import { useEffect, useState } from 'react'
import { ArrowUp, ArrowDown, Activity, Target } from 'lucide-react'

interface Metrics {
  mae: number
  rmse: number
  last_trained: string
  accuracy_direction: number
  total_predictions: number
}

interface PredictionData {
  symbol: string
  current_price: number
  predicted_price: number
  predicted_return: number
  timestamp: string
  confidence: string
  status?: string
  metrics?: Metrics
}

export default function PredictionPanel({ symbol }: { symbol: string }) {
  const [data, setData] = useState<PredictionData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchPrediction = async () => {
      try {
        // Fetch via Next.js API proxy to avoid client-side CORS/network issues
        const res = await fetch(`/api/predict/${symbol}`)
        if (!res.ok) throw new Error('Failed to fetch prediction')
        const json = await res.json()
        setData(json)
        setError(null)
      } catch (err) {
        console.error(err)
        setError('Prediction unavailable')
      } finally {
        setLoading(false)
      }
    }

    // Initial fetch
    fetchPrediction()

    // Poll every 10 seconds
    const interval = setInterval(fetchPrediction, 10000)
    return () => clearInterval(interval)
  }, [symbol])

  if (loading) return <div className="glass-card p-4 animate-pulse min-h-[160px]"></div>
  
  if (error || data?.status === 'waiting_for_data') {
    return (
      <div className="glass-card p-4 flex flex-col items-center justify-center text-muted-foreground min-h-[160px]">
        <Activity className="w-8 h-8 mb-2 opacity-50" />
        <span className="text-sm">{error || "Gathering data for prediction..."}</span>
      </div>
    )
  }

  if (!data) return null

  const isBullish = data.predicted_return > 0
  const colorClass = isBullish ? 'text-neon-green' : 'text-neon-red'
  const Icon = isBullish ? ArrowUp : ArrowDown

  return (
    <div className="glass-card p-6 relative overflow-hidden group h-full flex flex-col justify-between">
      <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
        <Icon className={`w-24 h-24 ${colorClass}`} />
      </div>
      
      <div>
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-neon-cyan" />
          AI Forecast (1m)
        </h3>

        <div className="grid grid-cols-2 gap-4 mb-6">
          <div>
            <p className="text-xs text-muted-foreground mb-1">Target Price</p>
            <p className={`text-2xl font-mono font-bold ${colorClass}`}>
              ${data.predicted_price.toFixed(2)}
            </p>
          </div>
          
          <div>
            <p className="text-xs text-muted-foreground mb-1">Expected Return</p>
            <div className={`flex items-center gap-1 font-mono font-bold ${colorClass}`}>
              <Icon className="w-4 h-4" />
              {Math.abs(data.predicted_return).toFixed(3)}%
            </div>
          </div>
        </div>
      </div>

      {data.metrics && (
        <div className="pt-4 border-t border-white/5">
           <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-neon-purple">
              <Target className="w-3 h-3" />
              <span>Live Model Performance</span>
           </div>
           
           <div className="grid grid-cols-3 gap-2">
              <div className="bg-card/50 p-2 rounded border border-white/5">
                 <p className="text-[10px] text-muted-foreground">Accuracy</p>
                 <p className="text-sm font-mono text-foreground">
                    {data.metrics.accuracy_direction.toFixed(1)}%
                 </p>
              </div>
              <div className="bg-card/50 p-2 rounded border border-white/5">
                 <p className="text-[10px] text-muted-foreground">Total Preds</p>
                 <p className="text-sm font-mono text-foreground">
                    {data.metrics.total_predictions}
                 </p>
              </div>
              <div className="bg-card/50 p-2 rounded border border-white/5">
                 <p className="text-[10px] text-muted-foreground">Status</p>
                 <p className="text-sm font-mono text-green-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                    Live
                 </p>
              </div>
           </div>
        </div>
      )}
      
      <div className="mt-4 text-[10px] text-muted-foreground font-mono flex justify-between">
        <span>RF Model v1.0</span>
        <span>Updated: {new Date(data.timestamp).toLocaleTimeString()}</span>
      </div>
    </div>
  )
}
