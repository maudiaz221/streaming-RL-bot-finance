import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { symbol: string } }
) {
  const symbol = params.symbol
  
  try {
    // Use environment variable for API URL if set, otherwise fallback to localhost
    // In Docker Compose, this will be "http://api:8000"
    const apiUrl = process.env.API_URL || 'http://127.0.0.1:8000';
    
    const res = await fetch(`${apiUrl}/predict/${symbol}`, {
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
        'Connection': 'keep-alive'
      },
    })

    if (!res.ok) {
      return NextResponse.json(
        { error: `API Error: ${res.statusText}` },
        { status: res.status }
      )
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Proxy Error:', error)
    return NextResponse.json(
      { error: 'Failed to connect to prediction service' },
      { status: 503 }
    )
  }
}

