import type { Metadata } from 'next'
import { JetBrains_Mono } from 'next/font/google'
import './globals.css'
import { BinanceStreamProvider } from '@/lib/binance-stream-context'

const jetbrainsMono = JetBrains_Mono({ 
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Binance Crypto Dashboard | Real-Time Trading',
  description: 'Real-time cryptocurrency trading dashboard with live Binance WebSocket data',
  icons: {
    icon: 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📊</text></svg>',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${jetbrainsMono.variable} font-mono cyber-grid scan-lines`}>
        <div className="noise-overlay" />
        <BinanceStreamProvider>
          {children}
        </BinanceStreamProvider>
      </body>
    </html>
  )
}
