#!/bin/bash
cd "$(dirname "$0")"
export LOCAL_MODE=true
export CRYPTO_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT
export BINANCE_STREAMS=trade,kline_1m
./venv/bin/python binance_websocket_client.py

