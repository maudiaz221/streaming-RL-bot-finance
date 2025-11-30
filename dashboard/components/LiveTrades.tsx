'use client'

import { ProcessedTrade, SymbolInfo } from '@/lib/types'
import { formatCurrency, formatNumber, formatTime } from '@/lib/utils'
import { ArrowUpRight, ArrowDownRight } from 'lucide-react'

interface LiveTradesProps {
  trades: ProcessedTrade[]
  symbolInfo: SymbolInfo
  maxTrades?: number
}

export default function LiveTrades({ trades, symbolInfo, maxTrades = 20 }: LiveTradesProps) {
  const displayTrades = trades.slice(0, maxTrades)

  return (
    <div className="glass-card p-4 h-full flex flex-col min-h-[400px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-foreground">Live Trades</h3>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neon-magenta opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-neon-magenta"></span>
          </span>
          <span className="text-xs text-muted-foreground">
            {trades.length} trades
          </span>
        </div>
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-4 gap-2 text-xs text-muted-foreground uppercase tracking-wider pb-2 border-b border-card-border">
        <span>Time</span>
        <span className="text-right">Price</span>
        <span className="text-right">Amount</span>
        <span className="text-right">Side</span>
      </div>

      {/* Trades list */}
      <div className="flex-1 overflow-y-auto mt-2 space-y-1">
        {displayTrades.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
            Waiting for trades...
          </div>
        ) : (
          displayTrades.map((trade, index) => {
            const isBuy = !trade.isBuyerMaker
            return (
              <div 
                key={trade.id} 
                className={`trade-row grid grid-cols-4 gap-2 py-2 px-2 rounded text-sm font-mono ${
                  index === 0 ? 'bg-card/50' : ''
                }`}
                style={{ 
                  animationDelay: `${index * 20}ms`,
                  opacity: 1 - (index * 0.03),
                }}
              >
                <span className="text-muted-foreground text-xs">
                  {formatTime(trade.time)}
                </span>
                <span 
                  className={`text-right font-medium ${
                    isBuy ? 'text-neon-green' : 'text-neon-red'
                  }`}
                >
                  {formatCurrency(trade.price)}
                </span>
                <span className="text-right text-foreground/80">
                  {formatNumber(trade.quantity, 4)}
                </span>
                <span className="text-right">
                  {isBuy ? (
                    <span className="inline-flex items-center gap-1 text-neon-green">
                      <ArrowUpRight className="w-3 h-3" />
                      <span className="text-xs">BUY</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-neon-red">
                      <ArrowDownRight className="w-3 h-3" />
                      <span className="text-xs">SELL</span>
                    </span>
                  )}
                </span>
              </div>
            )
          })
        )}
      </div>

      {/* Trade volume indicator */}
      {trades.length > 0 && (
        <div className="mt-3 pt-3 border-t border-card-border">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Buy/Sell Ratio</span>
            <div className="flex items-center gap-2">
              {(() => {
                const buyCount = trades.filter(t => !t.isBuyerMaker).length
                const sellCount = trades.filter(t => t.isBuyerMaker).length
                const total = buyCount + sellCount
                const buyPercent = total > 0 ? (buyCount / total) * 100 : 50
                
                return (
                  <>
                    <span className="text-neon-green">{buyPercent.toFixed(0)}%</span>
                    <div className="w-20 h-2 rounded-full overflow-hidden bg-neon-red/30">
                      <div 
                        className="h-full bg-neon-green transition-all duration-300"
                        style={{ width: `${buyPercent}%` }}
                      />
                    </div>
                    <span className="text-neon-red">{(100 - buyPercent).toFixed(0)}%</span>
                  </>
                )
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}





