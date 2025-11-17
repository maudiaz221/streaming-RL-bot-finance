# Quick Start Guide

Get the stock trading platform running in minutes!

## ⚡ Fast Local Setup (No AWS)

Perfect for testing with your Alpaca API keys:

### Step 1: Install Dependencies (5 minutes)

```bash
# Alpaca Producer
cd alpaca-producer
pip install -r requirements.txt

# Streaming Processor
cd ../streaming-processor
pip install -r requirements.txt

# RL Model (optional for now)
cd ../rl-model
pip install -r requirements.txt

# Dashboard
cd ../dashboard
npm install
```

### Step 2: Configure Environment

Your `.env` file already has Alpaca keys. Ensure it includes:

```env
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
LOCAL_MODE=true
```

### Step 3: Run the System (3 terminals)

**Terminal 1 - Start Alpaca Producer:**
```bash
cd alpaca-producer
LOCAL_MODE=true python alpaca_websocket_client.py
```

You should see:
```
✅ WebSocket connection opened
✅ Authentication successful!
Subscribing to 10 symbols...
✅ Subscription confirmed
```

**Terminal 2 - Start Stream Processor:**
```bash
cd streaming-processor
LOCAL_MODE=true python spark_streaming.py
```

You should see:
```
🚀 Starting Stock Market Streaming Application
✅ Spark session created
📊 Access Spark UI at: http://localhost:4040
```

**Terminal 3 - Start Dashboard:**
```bash
cd dashboard
npm run dev
```

You should see:
```
✓ Ready in 2.5s
- Local: http://localhost:3000
```

### Step 4: View Dashboard

Open **http://localhost:3000** in your browser!

You'll see:
- Real-time candlestick charts
- Technical indicators (RSI, MACD, Bollinger Bands)
- Trading signals
- Live streaming statistics

---

## 🎯 What You'll See

### During Market Hours (9:30 AM - 4:00 PM ET)
- **Real data** from Alpaca IEX feed
- High message rate (100+ messages/second)
- Active price movements

### Outside Market Hours
- Limited or no real data
- Use test mode instead (see below)

---

## 🧪 Test Mode (24/7 Data)

For testing anytime, use Alpaca's test stream:

```bash
# Edit .env
ALPACA_WEBSOCKET_URL=wss://stream.data.alpaca.markets/v2/test
STOCK_SYMBOLS=FAKEPACA

# Run producer
cd alpaca-producer
LOCAL_MODE=true python alpaca_websocket_client.py
```

---

## 📊 Monitor Performance

### Spark UI
- URL: http://localhost:4040
- Shows: Processing rates, batch durations, stages

### Producer Logs
Watch messages being received:
```bash
# In the producer terminal, you'll see:
Messages received: 1000 | Producer stats: {'total_records_sent': 950, ...}
```

### Dashboard Stats
Bottom of dashboard shows:
- Messages Received
- Messages/Second
- Average Latency

---

## 🛑 Stop Everything

Press `Ctrl+C` in each terminal to stop.

Or use:
```bash
pkill -f alpaca_websocket_client.py
pkill -f spark_streaming.py
# Ctrl+C in dashboard terminal
```

---

## 🎓 Train RL Model (Optional)

```bash
cd rl-model

# Generate and train on sample data (10 minutes)
python train_model.py --timesteps 10000

# Model saved to: ./models/ppo_trading_model.zip
```

---

## ☁️ AWS Deployment

When ready to deploy to AWS:

### 1. Setup AWS Infrastructure (10 minutes)

```bash
cd infrastructure

# Install
pip install -r requirements.txt

# Create Kinesis stream
python kinesis_setup.py --action create

# Create S3 bucket
python s3_setup.py --action create
```

### 2. Update .env

```env
LOCAL_MODE=false
AWS_REGION=us-east-1
KINESIS_STREAM_NAME=stock-market-stream
S3_BUCKET_NAME=stock-trading-data
```

### 3. Run Producer (now writes to Kinesis)

```bash
cd alpaca-producer
python alpaca_websocket_client.py
```

### 4. Submit Spark Job to EMR

See `docs/USAGE.md` for detailed EMR setup.

---

## 📚 Documentation

- **Complete Setup**: `docs/USAGE.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **AWS Setup**: `aws.md`
- **Alpaca Setup**: `alpaca.md`

---

## 🆘 Troubleshooting

### "unauthorized" error
- Check Alpaca API keys in `.env`
- Ensure using Paper Trading keys

### No data in dashboard
- Market hours? Try test mode
- Check producer is running
- Verify Spark job is processing

### Spark errors
- Ensure Java 11+ installed
- Check ports 4040 available
- Verify Python packages installed

### Dashboard blank
- Run `npm install` in dashboard folder
- Check browser console for errors
- Verify port 3000 is free

---

## ✅ Success Checklist

- [ ] Alpaca producer connects successfully
- [ ] Spark streaming job running
- [ ] Dashboard displays charts
- [ ] Real-time data updates visible
- [ ] Technical indicators calculated
- [ ] Trading signals appearing

---

## 🎉 What's Next?

1. **Monitor Spark UI** - Optimize performance
2. **Train Better RL Model** - More data, longer training
3. **Add More Symbols** - Edit `STOCK_SYMBOLS` in `.env`
4. **Deploy to AWS** - Production-ready setup
5. **Customize Dashboard** - Add your own indicators

---

## 💡 Quick Tips

- **Development**: Always use `LOCAL_MODE=true` first
- **Testing**: Use test stream (`FAKEPACA`) outside market hours
- **Performance**: Monitor Spark UI for bottlenecks
- **Cost**: Local mode = $0, AWS mode = ~$150-200/month
- **Data**: Stored in `./data/` folder in local mode

---

**You're all set! Happy trading! 🚀📈**

For detailed documentation, see `docs/USAGE.md`

