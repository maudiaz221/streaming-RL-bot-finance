'use client'

import { useState } from 'react'
import PriceDisplay from '@/components/PriceDisplay'
import CryptoChart from '@/components/CryptoChart'
import CryptoStats from '@/components/CryptoStats'
import LiveTrades from '@/components/LiveTrades'
import PredictionPanel from '@/components/PredictionPanel'
import { useBinanceStream } from '@/lib/binance-stream-context'
import { CRYPTO_SYMBOLS, SYMBOL_INFO, CryptoSymbol } from '@/lib/types'
import { Wifi, WifiOff, RefreshCw } from 'lucide-react'

export default function Home() {
  const [selectedSymbol, setSelectedSymbol] = useState<CryptoSymbol>('BTCUSDT')
  
  // Get stream data for selected symbol (data is cached across tab switches)
  const { 
    trades, 
    candles, 
    stats, 
    connectionStatus, 
    streamStats, 
    error, 
    reconnect 
  } = useBinanceStream(selectedSymbol)

  const symbolInfo = SYMBOL_INFO[selectedSymbol]

  return (
    <main className="min-h-screen p-4 md:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <header className="glass-card p-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            {/* Title */}
            <div>
              <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-neon-cyan via-neon-magenta to-neon-purple bg-clip-text text-transparent">
                Crypto Dashboard
              </h1>
              <p className="text-muted-foreground mt-1">
                Real-time market data from Binance WebSocket
              </p>
            </div>

            {/* Connection Status */}
            <div className="flex items-center gap-3">
              {connectionStatus === 'connected' && (
                <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-neon-green/10 border border-neon-green/30">
                  <Wifi className="w-4 h-4 text-neon-green" />
                  <span className="text-sm font-semibold text-neon-green">Connected</span>
                </div>
              )}
              {connectionStatus === 'connecting' && (
                <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-neon-yellow/10 border border-neon-yellow/30">
                  <RefreshCw className="w-4 h-4 text-neon-yellow animate-spin" />
                  <span className="text-sm font-semibold text-neon-yellow">Connecting...</span>
                </div>
              )}
              {(connectionStatus === 'disconnected' || connectionStatus === 'error') && (
                <button 
                  onClick={reconnect}
                  className="flex items-center gap-2 px-4 py-2 rounded-full bg-neon-red/10 border border-neon-red/30 hover:bg-neon-red/20 transition-colors"
                >
                  <WifiOff className="w-4 h-4 text-neon-red" />
                  <span className="text-sm font-semibold text-neon-red">Reconnect</span>
                </button>
              )}
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mt-4 p-3 rounded-lg bg-neon-red/10 border border-neon-red/30 text-sm text-neon-red">
              ⚠️ {error}
            </div>
          )}

          {/* Coin Tabs */}
          <div className="mt-6 flex gap-2 border-b border-card-border">
            {CRYPTO_SYMBOLS.map((symbol) => {
              const info = SYMBOL_INFO[symbol]
              const isActive = selectedSymbol === symbol
              
              return (
                <button
                  key={symbol}
                  onClick={() => setSelectedSymbol(symbol)}
                  className={`
                    relative px-6 py-3 font-mono font-semibold text-sm uppercase tracking-wider
                    transition-all duration-300 border-b-2
                    ${isActive 
                      ? 'text-foreground border-current' 
                      : 'text-muted-foreground border-transparent hover:text-foreground hover:border-muted'
                    }
                  `}
                  style={isActive ? { 
                    color: info.color,
                    textShadow: `0 0 20px ${info.glowColor}`,
                  } : undefined}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-lg">{info.icon}</span>
                    <span>{info.name}</span>
                  </span>
                  
                  {/* Active indicator glow */}
                  {isActive && (
                    <span 
                      className="absolute bottom-0 left-0 right-0 h-0.5 blur-sm"
                      style={{ backgroundColor: info.color }}
                    />
                  )}
                </button>
              )
            })}
          </div>
        </header>

        {/* Price Display */}
        <PriceDisplay stats={stats} symbolInfo={symbolInfo} />

        {/* Stats Grid */}
        <CryptoStats stats={stats} streamStats={streamStats} symbolInfo={symbolInfo} />

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chart - 2/3 width on large screens */}
          <div className="lg:col-span-2">
            <CryptoChart data={candles} symbolInfo={symbolInfo} height={450} />
          </div>

          {/* Live Trades - 1/3 width on large screens */}
          <div className="lg:col-span-1 flex flex-col gap-6">
            <div className="h-auto">
               <PredictionPanel symbol={selectedSymbol} />
            </div>
            <div className="flex-1 min-h-[400px]">
               <LiveTrades trades={trades} symbolInfo={symbolInfo} />
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="glass-card p-4 mt-12">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-6">
              <span>
                Data source: <span className="text-neon-cyan font-semibold">Binance WebSocket</span>
              </span>
              <span>
                Stream: <span className="text-neon-magenta font-mono">{selectedSymbol.toLowerCase()}@trade</span>
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs">
                Built with Next.js + TradingView Lightweight Charts
              </span>
            </div>
          </div>
        </footer>

      </div>
    </main>
  )
}
