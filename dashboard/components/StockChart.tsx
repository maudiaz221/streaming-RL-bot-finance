'use client'

import { useEffect, useRef } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickData } from 'lightweight-charts'
import { ChartData } from '@/lib/types'

interface StockChartProps {
  data: ChartData[]
  symbol: string
  height?: number
}

export default function StockChart({ data, symbol, height = 400 }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#e0e0e0',
      },
      timeScale: {
        borderColor: '#e0e0e0',
        timeVisible: true,
        secondsVisible: true,
      },
    })

    // Add candlestick series
    const series = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
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

  useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      const candlestickData: CandlestickData[] = data.map(d => ({
        time: d.time as any,
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
    <div className="w-full">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-lg font-semibold">{symbol}</h3>
        <div className="flex gap-2">
          <button className="px-3 py-1 text-sm rounded bg-gray-100 hover:bg-gray-200">1D</button>
          <button className="px-3 py-1 text-sm rounded bg-gray-100 hover:bg-gray-200">1W</button>
          <button className="px-3 py-1 text-sm rounded bg-gray-100 hover:bg-gray-200">1M</button>
        </div>
      </div>
      <div ref={chartContainerRef} className="border rounded-lg" />
    </div>
  )
}

