'use client'

import { useEffect, useRef } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickData, ColorType, Time } from 'lightweight-charts'
import { ChartData, SymbolInfo } from '@/lib/types'

interface CryptoChartProps {
  data: ChartData[]
  symbolInfo: SymbolInfo
  height?: number
}

export default function CryptoChart({ data, symbolInfo, height = 400 }: CryptoChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    // Cyberpunk chart theme
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: 'rgba(255, 255, 255, 0.6)',
        fontFamily: 'JetBrains Mono, monospace',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.03)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.03)' },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: 'rgba(0, 255, 255, 0.3)',
          width: 1,
          style: 2,
          labelBackgroundColor: '#0a0a0f',
        },
        horzLine: {
          color: 'rgba(0, 255, 255, 0.3)',
          width: 1,
          style: 2,
          labelBackgroundColor: '#0a0a0f',
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: number) => {
          const date = new Date(time * 1000)
          return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: false 
          })
        },
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
      },
      handleScale: {
        mouseWheel: true,
        pinch: true,
      },
    })

    // Neon candlestick colors
    const series = chart.addCandlestickSeries({
      upColor: '#00ff88',
      downColor: '#ff0066',
      borderVisible: false,
      wickUpColor: '#00ff88',
      wickDownColor: '#ff0066',
    })

    chartRef.current = chart
    seriesRef.current = series

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [height])

  // Update data
  useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      const candlestickData: CandlestickData<Time>[] = data.map(d => ({
        time: d.time as Time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))

      seriesRef.current.setData(candlestickData)
      
      if (chartRef.current) {
        chartRef.current.timeScale().fitContent()
      }
    }
  }, [data])

  return (
    <div className="glass-card p-4 relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-foreground">Price Chart</h3>
          <span className="text-xs px-2 py-1 rounded bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30">
            1m
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm bg-neon-green"></span>
            Bullish
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm bg-neon-red"></span>
            Bearish
          </span>
        </div>
      </div>

      {/* Chart container */}
      <div 
        ref={chartContainerRef} 
        className="rounded-lg overflow-hidden"
        style={{ 
          background: 'linear-gradient(180deg, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.1) 100%)',
        }}
      />

      {/* Glow effect at bottom */}
      <div 
        className="absolute bottom-0 left-0 right-0 h-1 opacity-50"
        style={{ 
          background: `linear-gradient(90deg, transparent, ${symbolInfo.color}, transparent)`,
        }}
      />

      {/* Data count indicator */}
      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>{data.length} candles loaded</span>
        {data.length > 0 && (
          <span>
            Last update: {new Date(data[data.length - 1].time * 1000).toLocaleTimeString()}
          </span>
        )}
      </div>
    </div>
  )
}





