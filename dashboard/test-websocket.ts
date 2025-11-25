#!/usr/bin/env tsx
/**
 * WebSocket Connection Test Script
 * Tests Alpaca WebSocket connectivity and data reception
 */

import WebSocket from 'ws';
import * as fs from 'fs';
import * as path from 'path';

// Read environment variables from .env.local
const envPath = path.join(__dirname, '.env.local');
const env: Record<string, string> = {};

try {
  const envContent = fs.readFileSync(envPath, 'utf-8');
  envContent.split('\n').forEach(line => {
    const match = line.match(/^([^=#]+)=(.*)$/);
    if (match) {
      const key = match[1].trim();
      const value = match[2].trim().replace(/^["']|["']$/g, '');
      env[key] = value;
    }
  });
} catch (e) {
  console.error('❌ Could not read .env.local file');
  process.exit(1);
}

const API_KEY = env.ALPACA_API_KEY;
const SECRET_KEY = env.ALPACA_SECRET_KEY;
const WS_URL = env.ALPACA_WEBSOCKET_URL || 'wss://stream.data.alpaca.markets/v2/test';
const SYMBOLS = (env.STOCK_SYMBOLS || 'FAKEPACA').split(',').map(s => s.trim());

if (!API_KEY || !SECRET_KEY) {
  console.error('❌ Missing ALPACA_API_KEY or ALPACA_SECRET_KEY in .env.local');
  process.exit(1);
}

console.log('🔌 WebSocket Connection Test');
console.log('━'.repeat(60));
console.log(`📡 URL: ${WS_URL}`);
console.log(`📊 Symbols: ${SYMBOLS.join(', ')}`);
console.log('━'.repeat(60));

const ws = new WebSocket(WS_URL);
let messageCount = 0;
let tradeCount = 0;

ws.on('open', () => {
  console.log('✅ WebSocket connection opened');
  console.log('🔐 Sending authentication...');
  
  ws.send(JSON.stringify({
    action: 'auth',
    key: API_KEY,
    secret: SECRET_KEY,
  }));
});

ws.on('message', (data: WebSocket.Data) => {
  const messages = JSON.parse(data.toString());
  
  if (Array.isArray(messages)) {
    messages.forEach((msg: any) => {
      messageCount++;
      
      if (msg.T === 'success' && msg.msg === 'connected') {
        console.log('✅ Connected to Alpaca');
      }
      
      if (msg.T === 'success' && msg.msg === 'authenticated') {
        console.log('✅ Authentication successful');
        console.log('📡 Subscribing to symbols...');
        
        ws.send(JSON.stringify({
          action: 'subscribe',
          trades: SYMBOLS,
          quotes: [],
          bars: [],
        }));
      }
      
      if (msg.T === 'subscription') {
        console.log('✅ Subscription confirmed');
        console.log('⏳ Waiting for trade data...');
      }
      
      if (msg.T === 't') {
        tradeCount++;
        console.log(`📈 Trade #${tradeCount}: ${msg.S} @ $${msg.p} (size: ${msg.s}) - ${msg.t}`);
        
        if (tradeCount >= 5) {
          console.log('━'.repeat(60));
          console.log('✅ Test successful! Received 5 trades.');
          console.log(`📊 Total messages: ${messageCount}`);
          console.log('━'.repeat(60));
          ws.close();
          process.exit(0);
        }
      }
      
      if (msg.T === 'error') {
        console.error(`❌ Error: ${msg.msg} (code: ${msg.code})`);
        process.exit(1);
      }
    });
  }
});

ws.on('error', (err: Error) => {
  console.error('❌ WebSocket error:', err.message);
  process.exit(1);
});

ws.on('close', () => {
  console.log('🔌 WebSocket connection closed');
});

// Timeout after 30 seconds
setTimeout(() => {
  console.log('⏱️  Timeout: No trades received in 30 seconds');
  console.log(`📊 Total messages received: ${messageCount}`);
  ws.close();
  process.exit(1);
}, 30000);

