'use client'

import { CryptoStats as CryptoStatsType, StreamStats, SymbolInfo } from '@/lib/types'
import { formatCurrency, formatCompactNumber, formatNumber } from '@/lib/utils'
import { Activity, BarChart3, Clock, Zap, TrendingUp, TrendingDown } from 'lucide-react'

interface CryptoStatsProps {
  stats: CryptoStatsType
  streamStats: StreamStats
  symbolInfo: SymbolInfo
}

export default function CryptoStats({ stats, streamStats, symbolInfo }: CryptoStatsProps) {
  const timeSinceConnection = streamStats.connectionTime 
    ? Math.floor((Date.now() - streamStats.connectionTime) / 1000)
    : 0

  const formatUptime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    if (mins > 0) {
      return `${mins}m ${secs}s`
    }
    return `${secs}s`
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* 24h High */}
      <div className="stat-card">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="w-4 h-4 text-neon-green" />
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">24h High</span>
        </div>
        <div className="text-xl font-bold font-mono text-neon-green">
          {stats.high24h > 0 ? formatCurrency(stats.high24h) : '---'}
        </div>
      </div>

      {/* 24h Low */}
      <div className="stat-card">
        <div className="flex items-center gap-2 mb-2">
          <TrendingDown className="w-4 h-4 text-neon-red" />
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">24h Low</span>
        </div>
        <div className="text-xl font-bold font-mono text-neon-red">
          {stats.low24h < Infinity ? formatCurrency(stats.low24h) : '---'}
        </div>
      </div>

      {/* Volume */}
      <div className="stat-card">
        <div className="flex items-center gap-2 mb-2">
          <BarChart3 className="w-4 h-4 text-neon-purple" />
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Volume</span>
        </div>
        <div className="text-xl font-bold font-mono text-neon-purple">
          ${formatCompactNumber(stats.volume24h)}
        </div>
      </div>

      {/* Trade Count */}
      <div className="stat-card">
        <div className="flex items-center gap-2 mb-2">
          <Activity className="w-4 h-4 text-neon-cyan" />
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Trades</span>
        </div>
        <div className="text-xl font-bold font-mono text-neon-cyan">
          {formatNumber(stats.tradeCount, 0)}
        </div>
      </div>

      {/* Stream Stats Row */}
      <div className="col-span-2 md:col-span-4 stat-card">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-6">
            {/* Messages */}
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-neon-yellow" />
              <div>
                <p className="text-xs text-muted-foreground">Messages</p>
                <p className="font-mono font-bold text-neon-yellow">
                  {streamStats.messagesReceived.toLocaleString()}
                </p>
              </div>
            </div>

            {/* Trades Received */}
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-neon-magenta" />
              <div>
                <p className="text-xs text-muted-foreground">Trade Msgs</p>
                <p className="font-mono font-bold text-neon-magenta">
                  {streamStats.tradesReceived.toLocaleString()}
                </p>
              </div>
            </div>

            {/* Klines Received */}
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-neon-cyan" />
              <div>
                <p className="text-xs text-muted-foreground">Candle Msgs</p>
                <p className="font-mono font-bold text-neon-cyan">
                  {streamStats.klinesReceived.toLocaleString()}
                </p>
              </div>
            </div>

            {/* Uptime */}
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-neon-green" />
              <div>
                <p className="text-xs text-muted-foreground">Uptime</p>
                <p className="font-mono font-bold text-neon-green">
                  {formatUptime(timeSinceConnection)}
                </p>
              </div>
            </div>
          </div>

          {/* Connection indicator */}
          <div 
            className="px-3 py-1.5 rounded-full border text-xs font-semibold uppercase tracking-wider flex items-center gap-2"
            style={{ 
              backgroundColor: `${symbolInfo.color}15`,
              borderColor: `${symbolInfo.color}40`,
              color: symbolInfo.color
            }}
          >
            <span className="relative flex h-2 w-2">
              <span 
                className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                style={{ backgroundColor: symbolInfo.color }}
              />
              <span 
                className="relative inline-flex rounded-full h-2 w-2"
                style={{ backgroundColor: symbolInfo.color }}
              />
            </span>
            {symbolInfo.symbol}
          </div>
        </div>
      </div>
    </div>
  )
}





