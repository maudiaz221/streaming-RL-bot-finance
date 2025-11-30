'use client'

import { useEffect, useRef, useState } from 'react'
import { CryptoStats, SymbolInfo } from '@/lib/types'
import { formatCurrency, formatPercent } from '@/lib/utils'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface PriceDisplayProps {
  stats: CryptoStats
  symbolInfo: SymbolInfo
}

export default function PriceDisplay({ stats, symbolInfo }: PriceDisplayProps) {
  const [flashClass, setFlashClass] = useState('')
  const prevPriceRef = useRef(stats.price)

  useEffect(() => {
    if (stats.price !== prevPriceRef.current) {
      if (stats.price > prevPriceRef.current) {
        setFlashClass('price-flash-up')
      } else if (stats.price < prevPriceRef.current) {
        setFlashClass('price-flash-down')
      }
      prevPriceRef.current = stats.price

      const timer = setTimeout(() => setFlashClass(''), 300)
      return () => clearTimeout(timer)
    }
  }, [stats.price])

  const isPositive = stats.priceChange >= 0
  const PriceIcon = stats.priceChange > 0 ? TrendingUp : stats.priceChange < 0 ? TrendingDown : Minus

  return (
    <div className="glass-card p-6 relative overflow-hidden">
      {/* Coin icon background decoration */}
      <div 
        className="absolute -right-8 -top-8 text-9xl opacity-5 font-bold select-none"
        style={{ color: symbolInfo.color }}
      >
        {symbolInfo.icon}
      </div>

      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div 
          className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl font-bold"
          style={{ 
            backgroundColor: `${symbolInfo.color}20`,
            boxShadow: `0 0 20px ${symbolInfo.glowColor}`
          }}
        >
          {symbolInfo.icon}
        </div>
        <div>
          <h2 className="text-xl font-bold text-foreground">{symbolInfo.name}</h2>
          <p className="text-sm text-muted-foreground font-mono">{symbolInfo.symbol}</p>
        </div>
        
        {/* Live indicator */}
        <div className="ml-auto flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neon-green opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-neon-green"></span>
          </span>
          <span className="text-xs text-neon-green font-semibold uppercase tracking-wider">Live</span>
        </div>
      </div>

      {/* Main price */}
      <div className={`rounded-lg p-4 mb-4 transition-colors ${flashClass}`}>
        <div 
          className="text-5xl md:text-6xl font-bold font-mono tracking-tight"
          style={{ 
            color: symbolInfo.color,
            textShadow: `0 0 30px ${symbolInfo.glowColor}`
          }}
        >
          {stats.price > 0 ? formatCurrency(stats.price) : '---'}
        </div>
      </div>

      {/* Price change */}
      <div className="flex items-center gap-4">
        <div 
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
            isPositive 
              ? 'bg-neon-green/10 border-neon-green/30 text-neon-green' 
              : 'bg-neon-red/10 border-neon-red/30 text-neon-red'
          }`}
        >
          <PriceIcon className="w-5 h-5" />
          <span className="font-bold font-mono">
            {formatPercent(stats.priceChangePercent)}
          </span>
        </div>
        
        <div className={`font-mono text-lg ${isPositive ? 'text-neon-green' : 'text-neon-red'}`}>
          {isPositive ? '+' : ''}{formatCurrency(stats.priceChange)}
        </div>
      </div>

      {/* Mini stats */}
      <div className="grid grid-cols-3 gap-4 mt-6 pt-4 border-t border-card-border">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">24h High</p>
          <p className="font-mono text-sm text-neon-green">
            {stats.high24h > 0 ? formatCurrency(stats.high24h) : '---'}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">24h Low</p>
          <p className="font-mono text-sm text-neon-red">
            {stats.low24h < Infinity ? formatCurrency(stats.low24h) : '---'}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Trades</p>
          <p className="font-mono text-sm text-neon-cyan">
            {stats.tradeCount.toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  )
}





