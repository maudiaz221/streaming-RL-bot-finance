# Binance Spark Processor

A real-time cryptocurrency data processing pipeline that streams kline (candlestick) data from Binance WebSocket, processes it with PySpark, and stores both raw and engineered features in S3.

## Architecture

```
Binance WebSocket → Message Queue → Spark Processor → S3 Storage
                                          ↓
                                   Feature Engineering
                                          ↓
                                   (raw & clean data)
```

## Features

- **Real-time WebSocket streaming** from Binance for multiple cryptocurrency pairs
- **PySpark batch processing** with feature engineering for time series analysis
- **S3 storage** with time-based partitioning (year/month/day/hour/minute)
- **Automatic reconnection** with exponential backoff
- **Docker containerization** for easy deployment
- **Volume-mounted logs** for persistent logging

## Data Structure

### Raw Data Structure
```
raw/
└── year=YYYY/
    └── month=MM/
        └── day=DD/
            └── hour=HH/
                └── minute=MM/
                    └── klines_YYYYMMDD_HHMMSS.parquet
```

### Processed Data Structure
```
clean/
└── year=YYYY/
    └── month=MM/
        └── day=DD/
            └── hour=HH/
                └── minute=MM/
                    └── klines_YYYYMMDD_HHMMSS.parquet
```

## Engineered Features

The processor generates the following features:

### Base Features
- timestamp, symbol, interval, exchange
- OHLC prices (open, high, low, close)
- volume, quote_volume
- number_of_trades
- taker_buy_volume, taker_buy_quote_volume

### Derived Features
- **Price Changes**: price_change, price_change_pct, log_return
- **Moving Averages**: ma_5, ma_10, ma_20
- **Volatility**: volatility_10 (10-period rolling std of returns)
- **Volume Metrics**: volume_ma_5, volume_change_pct
- **Momentum**: momentum_5, momentum_10
- **Spread**: hl_spread, hl_spread_pct

## Prerequisites

- Docker and Docker Compose
- AWS credentials with S3 access
- Access to Binance WebSocket API

## Configuration

1. Copy the example environment file:
```bash
cp .env.example ../.env
```

2. Edit `../.env` with your configuration:
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# S3 Configuration
S3_BUCKET=your_bucket_name_here
S3_RAW_PREFIX=raw
S3_CLEAN_PREFIX=clean

# Crypto Symbols (comma-separated)
CRYPTO_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT

# Binance Stream Types
BINANCE_STREAMS=kline_1m
```

## Local Development

### Build the Docker image:
```bash
docker build -t binance-spark-processor:latest .
```

### Run with Docker Compose:
```bash
docker-compose up -d
```

### View logs:
```bash
# Real-time logs
docker-compose logs -f

# Check logs directory
tail -f logs/app.log
```

### Stop the container:
```bash
docker-compose down
```

## EC2 Instance Selection

### Choosing the Right Instance Type

Your EC2 instance size directly impacts Spark performance and the metrics you'll collect.

#### Minimum Requirements
- **At least 2 vCPUs**: Spark needs 1 core for driver + 1+ for executors
- **At least 4GB RAM**: Spark is memory-intensive

#### Recommended Instance Types

| Instance Type | vCPUs | RAM | Cost/Hour | Best For | Notes |
|--------------|-------|-----|-----------|----------|-------|
| **t3.medium** | 2 | 4GB | $0.04 | Testing only | ⚠️ May struggle with window functions |
| **t3.large** | 2 | 8GB | $0.08 | Light workload | Better than t3.medium, limited parallelism |
| **t3.xlarge** ⭐ | 4 | 16GB | $0.17 | **Recommended start** | Good balance, 3 executor cores |
| **m5.large** | 2 | 8GB | $0.10 | Consistent perf | Better CPU than t3, but only 2 cores |
| **m5.xlarge** ⭐ | 4 | 16GB | $0.19 | **Production ready** | Excellent balance |
| **m5.2xlarge** | 8 | 32GB | $0.38 | Heavy workload | Best for many symbols/high throughput |
| **c5.xlarge** | 4 | 8GB | $0.17 | Compute-heavy | Good CPU, less memory |
| **c5.2xlarge** | 8 | 16GB | $0.34 | CPU-intensive | Optimize for computation |

💡 **Recommendation**: Start with **t3.xlarge** or **m5.xlarge** for meaningful metrics at reasonable cost.

### How Cores Affect Performance

Your Spark config uses `SPARK_MASTER=local[*]` which utilizes **all available cores**:

#### 2 vCPUs (t3.medium, m5.large):
```
Driver: 1 core
Executors: 1 core
Parallelism: 1 task at a time (sequential)
Window functions: Processed one symbol at a time
⚠️ Bottleneck with 3+ symbols
```

#### 4 vCPUs (t3.xlarge, m5.xlarge) - **Recommended**:
```
Driver: 1 core
Executors: 3 cores
Parallelism: 3 tasks simultaneously
Window functions: All 3 symbols processed in parallel
✅ Sweet spot for default workload (BTCUSDT, ETHUSDT, BNBUSDT)
```

#### 8 vCPUs (m5.2xlarge, c5.2xlarge):
```
Driver: 1 core
Executors: 7 cores
Parallelism: 7 tasks simultaneously
Window functions: Fast parallel processing
✅ Good if adding more symbols (>5)
```

### Optimizing Spark Configuration by Instance Size

Add these to your `.env` file based on your EC2 instance:

#### For t3.medium / m5.large (2 vCPUs) - Budget Option
```bash
SPARK_MASTER=local[2]
# Note: Consider upgrading if processing >2 symbols
```

#### For t3.xlarge / m5.xlarge (4 vCPUs) - **Recommended**
```bash
SPARK_MASTER=local[4]
# Or use local[*] to automatically use all cores
```

#### For m5.2xlarge (8 vCPUs) - High Performance
```bash
SPARK_MASTER=local[8]
# Can handle 5+ symbols efficiently
```

### Memory Considerations

Spark memory usage scales with:
- Number of symbols being processed
- Window sizes (5, 10, 20 periods in your config)
- Batch sizes

**General guidelines:**
- **4GB RAM**: Minimum, may see spills with 3+ symbols
- **8GB RAM**: Comfortable for 3-5 symbols
- **16GB RAM**: Recommended, no spills, good GC performance
- **32GB RAM**: Excellent for 10+ symbols or larger windows

### Cost vs Performance Trade-off

**Monthly costs (24/7 operation):**
- t3.medium: ~$30/month (not recommended)
- t3.xlarge: ~$125/month ⭐ (recommended starting point)
- m5.xlarge: ~$140/month ⭐ (best balance)
- m5.2xlarge: ~$280/month (if you need the power)

💡 **Pro tip**: Use **On-Demand** for testing, then switch to **Reserved Instances** (up to 72% savings) or **Spot Instances** (up to 90% savings) for long-term deployment.

### Testing Your Instance Choice

After deploying, use Spark UI to verify your instance is appropriate:

**Good signs:**
- ✅ GC Time < 10% of Executor Run Time
- ✅ Shuffle Spill (Memory/Disk) near zero
- ✅ Scheduler Delay < 100ms
- ✅ All executor cores utilized

**Signs you need to upgrade:**
- ❌ High Shuffle Spill (>100MB)
- ❌ GC Time > 15% of Executor Run Time
- ❌ High Scheduler Delay (>500ms)
- ❌ Tasks queuing (waiting for cores)

---

## EC2 Deployment

### 1. Prepare EC2 Instance

SSH into your EC2 instance:
```bash
ssh -i your-key.pem ec2-user@your-ec2-ip
```

Install Docker:
```bash
# Amazon Linux 2023
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes to take effect
exit
```

### 2. Deploy Using Docker Image

#### Option A: Build on EC2
```bash
# Clone or copy your application
mkdir -p ~/binance-spark-processor
cd ~/binance-spark-processor

# Copy files (use scp or git clone)
# ... copy all application files ...

# Create .env file
nano .env
# ... paste your configuration ...

# Build and run
docker-compose up -d
```

#### Option B: Pull from Docker Registry (Recommended)

**Push image from local machine:**
```bash
# Build and tag
docker build -t binance-spark-processor:latest .

# Tag for your registry (Docker Hub example)
docker tag binance-spark-processor:latest your-dockerhub-username/binance-spark-processor:latest

# Push to registry
docker push your-dockerhub-username/binance-spark-processor:latest
```

**Pull and run on EC2:**
```bash
# Create directory
mkdir -p ~/binance-spark-processor
cd ~/binance-spark-processor

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  binance-spark-processor:
    image: your-dockerhub-username/binance-spark-processor:latest
    container_name: binance-spark-processor
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF

# Create .env file
nano .env
# ... paste your configuration ...

# Pull and run
docker-compose pull
docker-compose up -d
```

#### Option C: Use ECR (Elastic Container Registry) - Recommended for Production

**Step 1: Push Image to ECR (from your local machine)**

The repository includes a push script that handles building and pushing to ECR:

```bash
# Make script executable
chmod +x push_to_ecr.sh

# Push with 'latest' tag
./push_to_ecr.sh

# Or push with a specific version tag
./push_to_ecr.sh v1.0.0
```

The script will:
- Authenticate with AWS ECR
- Build the Docker image for linux/amd64 platform
- Tag and push to your ECR repository
- Display next steps for EC2 deployment

**Step 2: Deploy on EC2**

SSH into your EC2 instance and follow these steps:

```bash
# Create application directory
mkdir -p ~/binance-spark-processor
cd ~/binance-spark-processor

# Create necessary directories
mkdir -p logs

# Configure AWS credentials on EC2 (if not already done)
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 164332231571.dkr.ecr.us-east-1.amazonaws.com

# Create docker-compose.yml for ECR deployment
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  binance-spark-processor:
    image: 164332231571.dkr.ecr.us-east-1.amazonaws.com/arquitectura/spark-processing:latest
    container_name: binance-spark-processor
    env_file:
      - .env
    ports:
      # Spark UI - Web interface for monitoring jobs, stages, and metrics
      - "4040:4040"
    volumes:
      # Persist logs and Spark event logs on EC2 host
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - binance-network
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"
    healthcheck:
      test: ["CMD", "pgrep", "-f", "python main.py"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s

networks:
  binance-network:
    driver: bridge
EOF

# Create .env file with your configuration
cat > .env << 'EOF'
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# S3 Configuration
S3_BUCKET=your_bucket_name_here
S3_RAW_PREFIX=raw
S3_CLEAN_PREFIX=clean

# Crypto Symbols (comma-separated)
CRYPTO_SYMBOLS=BTCUSDT,ETHUSDT,BNBUSDT

# Binance Stream Types
BINANCE_STREAMS=kline_1m
EOF

# Edit .env with your actual values
nano .env

# Pull the latest image
docker-compose pull

# Start the application
docker-compose up -d

# View logs in real-time
docker-compose logs -f
```

**Step 3: Verify Deployment and Logs**

```bash
# Check container status
docker-compose ps

# View real-time logs from Docker
docker-compose logs -f

# View application logs from the mounted volume (persisted on EC2)
tail -f logs/app.log

# Check all log files in the logs directory
ls -lh logs/

# Search for errors in logs
grep -i error logs/app.log

# Check resource usage
docker stats binance-spark-processor
```

### 3. Monitor on EC2

```bash
# View real-time Docker logs
docker-compose logs -f

# View application logs (persisted in mounted volume)
tail -f logs/app.log

# View all logs in the logs directory
ls -lh logs/
tail -f logs/*.log

# Check container status
docker-compose ps

# Check container health
docker inspect binance-spark-processor | grep -A 10 Health

# Check resource usage
docker stats binance-spark-processor

# Monitor S3 uploads (verify data is being written)
aws s3 ls s3://your-bucket-name/raw/ --recursive --human-readable | tail -20
```

### 4. Update/Redeploy Application

When you make changes and want to deploy a new version:

**From your local machine:**
```bash
# Build and push new version
./push_to_ecr.sh v1.0.1

# Or update latest
./push_to_ecr.sh latest
```

**On EC2:**
```bash
cd ~/binance-spark-processor

# Stop current container
docker-compose down

# Login to ECR (if session expired)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 164332231571.dkr.ecr.us-east-1.amazonaws.com

# Pull latest image
docker-compose pull

# Start with new image
docker-compose up -d

# Verify it's running
docker-compose ps
docker-compose logs -f
```

### 5. Log Management on EC2

The application writes logs to the `./logs` directory on your EC2 instance, which persists even if the container is removed.

**Log file structure:**
```
~/binance-spark-processor/logs/
├── app.log              # Main application logs
└── [other log files]    # Any additional log files from the application
```

**Useful log commands:**
```bash
# View real-time logs
tail -f logs/app.log

# View last 100 lines
tail -n 100 logs/app.log

# Search for errors
grep -i "error" logs/app.log

# Search for specific symbol
grep "BTCUSDT" logs/app.log

# View logs from specific time period
grep "2024-01-15" logs/app.log

# Rotate logs if they get too large
# (Docker already handles this with max-size: 50m, max-file: 5)
# But you can manually archive old logs:
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

**Set up log rotation (optional):**
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/binance-spark

# Add this content:
/home/ec2-user/binance-spark-processor/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    missingok
    copytruncate
}

# Test logrotate
sudo logrotate -f /etc/logrotate.d/binance-spark
```

### 6. Manage the Application

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View logs
docker-compose logs -f

# Update to new version
docker-compose pull
docker-compose up -d

# Remove container and volumes (clean slate)
docker-compose down -v

# View container processes
docker-compose top

# Execute command inside running container
docker-compose exec binance-spark-processor bash
```

---

## Quick Reference: ECR Deployment

### From Local Machine
```bash
# 1. Make script executable
chmod +x push_to_ecr.sh

# 2. Push to ECR
./push_to_ecr.sh                # Push with 'latest' tag
./push_to_ecr.sh v1.0.0         # Push with specific version
```

### On EC2 Instance
```bash
# Initial Setup
mkdir -p ~/binance-spark-processor && cd ~/binance-spark-processor
mkdir -p logs

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 164332231571.dkr.ecr.us-east-1.amazonaws.com

# Create docker-compose.yml and .env (see detailed instructions above)

# Deploy
docker-compose pull && docker-compose up -d

# Monitor
docker-compose logs -f               # View Docker logs
tail -f logs/app.log                # View application logs
docker stats binance-spark-processor # Check resources

# Access Spark UI (configure security group first!)
# http://YOUR-EC2-IP:4040
```

### Common Operations
```bash
# Update to new version
docker-compose down
docker-compose pull
docker-compose up -d

# View logs
docker-compose logs -f              # Docker logs
tail -f logs/app.log               # Application logs
grep "ERROR" logs/app.log          # Search for errors

# Check health
docker-compose ps
docker inspect binance-spark-processor | grep -A 10 Health

# Clean restart
docker-compose down -v
docker-compose up -d
```

---

## Spark UI - Performance Monitoring

The application includes the **Spark Web UI** for comprehensive performance monitoring and analysis.

### Accessing Spark UI

#### On Local Development
If running locally with docker-compose:
```
http://localhost:4040
```

#### On EC2 Instance
1. **Configure EC2 Security Group** to allow inbound traffic on port 4040:
   - Go to EC2 Console → Security Groups
   - Select your instance's security group
   - Add Inbound Rule:
     - Type: Custom TCP
     - Port: 4040
     - Source: Your IP (or 0.0.0.0/0 for public access - not recommended for production)

2. **Access the UI** from your browser:
   ```
   http://YOUR-EC2-PUBLIC-IP:4040
   ```
   Replace `YOUR-EC2-PUBLIC-IP` with your EC2 instance's public IP address

3. **Find your EC2 Public IP**:
   ```bash
   # On EC2 instance
   curl http://checkip.amazonaws.com

   # Or from AWS Console
   # EC2 → Instances → Select your instance → Public IPv4 address
   ```

### Available Metrics and Tabs

The Spark UI provides all the performance metrics you need for your architecture analysis:

#### 1. **Jobs Tab** - Job Execution Times
- **Duration**: Total time for each job to complete
- **Stages**: Number of stages per job
- **Tasks**: Number of tasks across all stages
- **Job Timeline**: Visual timeline showing when jobs ran
- **Job Details**: Click any job to see detailed stage information

**What to monitor:**
- Job duration trends over time
- Failed jobs or tasks
- Job submission delays

#### 2. **Stages Tab** - Stage-Level Performance
For each stage, you can see:

**Timing Metrics:**
- **Duration**: Total stage execution time
- **Scheduler Delay**: Time waiting for resources to become available
- **Task Deserialization Time**: Time to deserialize task data
- **GC Time**: Garbage collection time (high GC time indicates memory pressure)
- **Result Serialization Time**: Time to serialize task results
- **Getting Result Time**: Time to fetch results from executors

**Shuffle Metrics (Critical for Performance):**
- **Shuffle Read Size/Records**: Data read from shuffle (join, reduceByKey operations)
- **Shuffle Write Size/Records**: Data written to shuffle
- **Shuffle Spill (Memory)**: Data spilled from memory to disk during shuffle
- **Shuffle Spill (Disk)**: Total disk space used for spills

**I/O Metrics:**
- **Input Size/Records**: Data read from source (S3, files)
- **Output Size/Records**: Data written to destination
- **Bytes Read/Written**: Total I/O operations

**What to monitor:**
- Stages with high shuffle read/write (bottlenecks)
- High spill indicates insufficient memory
- GC time > 10% of task time indicates memory issues
- High scheduler delay indicates resource contention

#### 3. **Storage Tab** - Data Caching
- RDD/DataFrame persistence levels
- Memory used by cached data
- Fraction cached vs spilled to disk

**What to monitor:**
- Cache hit rates
- Memory usage by cached datasets

#### 4. **Environment Tab** - Configuration
Critical for comparing architectures:
- **Spark Properties**: All Spark configuration settings
- **System Properties**: JVM settings, Java version
- **Classpath Entries**: Libraries and dependencies
- **Runtime Information**: Scala version, Java version

**What to export for comparison:**
- `spark.executor.memory`
- `spark.executor.cores`
- `spark.driver.memory`
- `spark.sql.adaptive.enabled`
- `spark.sql.shuffle.partitions`
- All custom configurations

#### 5. **Executors Tab** - Resource Usage
Per executor metrics:
- **RDD Blocks**: Number of cached RDD blocks
- **Storage Memory**: Memory used for caching
- **Disk Used**: Disk space used
- **Cores**: Number of cores allocated
- **Active/Failed/Complete Tasks**: Task statistics
- **Input/Output/Shuffle Read/Write**: I/O metrics per executor
- **GC Time**: Garbage collection time per executor

**What to monitor:**
- Executor memory usage vs allocation
- Uneven task distribution across executors
- High GC time on specific executors

#### 6. **SQL Tab** - Query Performance (If using Spark SQL)
- **Query Duration**: Total execution time
- **Query Plan**: Physical and logical execution plans
- **DAG Visualization**: Visual representation of query execution
- **Metrics per Operation**: Rows processed, data size, time spent

### Key Performance Indicators to Track

Based on your requirements, monitor these specific metrics:

1. **Job Execution Time** (`Jobs` tab):
   - Total duration per job
   - Trends over time

2. **Shuffle Operations** (`Stages` tab → Shuffle Read/Write):
   - Shuffle read/write size
   - Time spent in shuffle operations
   - Operations that trigger shuffles: `join`, `reduceByKey`, `groupByKey`, `repartition`

3. **I/O Operations** (`Stages` tab → Input/Output):
   - Input bytes read from S3
   - Output bytes written to S3
   - Number of records processed

4. **Resource Utilization** (`Stages` tab, `Executors` tab):
   - **Scheduler Delay**: Time waiting for resources
   - **Executor Run Time**: Actual computation time
   - **GC Time**: Garbage collection time
   - **Rule of thumb**: GC Time should be < 10% of Executor Run Time

5. **Spill Metrics** (`Stages` tab):
   - **Shuffle Spill (Memory)**: Data that couldn't fit in memory during shuffle
   - **Shuffle Spill (Disk)**: Data written to disk
   - **High spill = performance degradation** → increase `spark.executor.memory`

6. **Environment Configuration** (`Environment` tab):
   - Export all configurations for architecture comparison
   - Document resource allocations (cores, memory)

### Exporting Metrics

#### Save Spark Event Logs
Event logs are automatically saved to `/app/logs/spark-events/` and are accessible on your EC2 instance at `~/binance-spark-processor/logs/spark-events/`.

```bash
# On EC2, view Spark event logs
ls -lh logs/spark-events/

# Download event logs for offline analysis
scp -i your-key.pem ec2-user@YOUR-EC2-IP:~/binance-spark-processor/logs/spark-events/* ./local-analysis/
```

#### Screenshot Key Metrics
For reports and comparisons:
1. Take screenshots of Jobs, Stages, and Executors tabs
2. Export environment configuration
3. Document specific job timings and shuffle metrics

#### Use Spark History Server (Optional)
For persistent access to completed jobs:

```bash
# On EC2, start Spark History Server
docker exec -it binance-spark-processor bash
$SPARK_HOME/sbin/start-history-server.sh

# Access at http://YOUR-EC2-IP:18080
```

### Troubleshooting Spark UI Access

```bash
# Verify Spark UI is running inside container
docker exec binance-spark-processor curl -s http://localhost:4040 | head -20

# Check if port is exposed
docker port binance-spark-processor

# Check EC2 security group allows port 4040
# AWS Console → EC2 → Security Groups → Check Inbound Rules

# Check application logs for Spark UI URL
docker-compose logs | grep "Spark UI"
tail -f logs/app.log | grep "Spark UI"
```

### Performance Analysis Workflow

1. **Start your application** on EC2
2. **Open Spark UI** at `http://YOUR-EC2-IP:4040`
3. **Run your workload** and let data flow through the pipeline
4. **Monitor in real-time**:
   - Jobs tab: Track job submissions and completion
   - Stages tab: Identify slow stages
   - Executors tab: Monitor resource usage
5. **After workload completes**:
   - Review job timeline
   - Analyze shuffle operations
   - Check for spills and GC pressure
   - Export metrics and configurations
6. **Compare architectures**:
   - Save configurations from Environment tab
   - Document key metrics (job time, shuffle time, I/O, spills)
   - Create performance comparison charts

### Metrics Collection Template

For comparing different architectures, collect these metrics from Spark UI:

| Metric Category | Metric Name | Where to Find | Unit |
|----------------|-------------|---------------|------|
| **Job Execution** | Total Job Duration | Jobs tab → Duration | seconds |
| **Job Execution** | Number of Stages | Jobs tab → Stages | count |
| **Job Execution** | Number of Tasks | Jobs tab → Tasks | count |
| **Shuffle Performance** | Shuffle Read Size | Stages tab → Shuffle Read | MB/GB |
| **Shuffle Performance** | Shuffle Write Size | Stages tab → Shuffle Write | MB/GB |
| **Shuffle Performance** | Shuffle Read Time | Stages tab → Shuffle Read Time | seconds |
| **Shuffle Performance** | Shuffle Write Time | Stages tab → Shuffle Write Time | seconds |
| **I/O Operations** | Input Bytes | Stages tab → Input Size | MB/GB |
| **I/O Operations** | Output Bytes | Stages tab → Output Size | MB/GB |
| **I/O Operations** | Input Records | Stages tab → Input Records | count |
| **Resource Timing** | Scheduler Delay | Stages tab → Scheduler Delay | milliseconds |
| **Resource Timing** | Executor Run Time | Stages tab → Task Time | seconds |
| **Resource Timing** | GC Time | Stages tab → GC Time | seconds |
| **Resource Timing** | GC Time % | (GC Time / Executor Run Time) × 100 | percentage |
| **Memory Spill** | Shuffle Spill (Memory) | Stages tab → Shuffle Spill (Memory) | MB/GB |
| **Memory Spill** | Shuffle Spill (Disk) | Stages tab → Shuffle Spill (Disk) | MB/GB |
| **Environment** | Executor Memory | Environment tab → spark.executor.memory | GB |
| **Environment** | Executor Cores | Environment tab → spark.executor.cores | count |
| **Environment** | Driver Memory | Environment tab → spark.driver.memory | GB |
| **Environment** | Shuffle Partitions | Environment tab → spark.sql.shuffle.partitions | count |

**Example CSV format for collecting metrics:**
```csv
Architecture,Job_Duration_sec,Stages,Tasks,Shuffle_Read_MB,Shuffle_Write_MB,Scheduler_Delay_ms,Executor_Runtime_sec,GC_Time_sec,GC_Time_pct,Spill_Memory_MB,Spill_Disk_MB,Executor_Memory_GB,Executor_Cores
EC2_t3.medium,45.2,3,150,250,180,850,42.5,2.1,4.94,50,120,4,2
EMR_m5.xlarge,28.7,3,150,250,180,320,27.8,1.2,4.32,15,30,8,4
Glue_2_DPU,35.1,3,150,250,180,480,33.9,1.8,5.31,25,60,8,4
```

---

## Volume Mounts

The application uses volume mounts for persistent logging:

```yaml
volumes:
  - ./logs:/app/logs
```

This allows you to:
- Access logs from the host machine
- Persist logs even if the container is removed
- Monitor logs using standard tools (tail, grep, etc.)

## Testing

Test individual components:

```bash
# Test configuration
docker-compose run --rm binance-spark-processor python config.py

# Test WebSocket client
docker-compose run --rm binance-spark-processor python websocket_client.py

# Test Spark processor
docker-compose run --rm binance-spark-processor python spark_processor.py
```

## Troubleshooting

### ECR Authentication Issues
```bash
# Check if AWS CLI is configured
aws sts get-caller-identity

# Re-authenticate with ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 164332231571.dkr.ecr.us-east-1.amazonaws.com

# Verify ECR repository exists
aws ecr describe-repositories --region us-east-1

# Check ECR login expiration (ECR tokens expire after 12 hours)
# If you get "no basic auth credentials" error, re-run the login command above
```

### ECR Image Pull Issues on EC2
```bash
# Ensure EC2 instance has proper IAM role with ECR permissions
# Required permissions: ecr:GetAuthorizationToken, ecr:BatchGetImage, ecr:GetDownloadUrlForLayer

# Check if image exists in ECR
aws ecr list-images --repository-name arquitectura/spark-processing --region us-east-1

# Force pull latest image
docker-compose pull --ignore-pull-failures
docker-compose up -d --force-recreate

# Check Docker daemon logs
sudo journalctl -u docker -n 50
```

### Container Won't Start
```bash
# Check logs
docker-compose logs

# Check detailed container logs
docker logs binance-spark-processor --tail 100

# Check configuration
docker-compose config

# Validate environment variables
docker-compose run --rm binance-spark-processor python config.py

# Check if container is running
docker ps -a | grep binance-spark-processor

# Check exit code
docker inspect binance-spark-processor --format='{{.State.ExitCode}}'
```

### AWS/S3 Issues
```bash
# Test AWS credentials inside container
docker-compose exec binance-spark-processor aws sts get-caller-identity

# Test S3 access
docker-compose exec binance-spark-processor aws s3 ls s3://your-bucket-name/

# Verify EC2 IAM role has S3 permissions
aws iam get-role --role-name your-ec2-role-name

# Test boto3 connection
docker-compose run --rm binance-spark-processor python -c "import boto3; print(boto3.client('s3').list_buckets())"
```

### Spark Issues
```bash
# Check Java installation
docker-compose run --rm binance-spark-processor java -version

# Check Spark environment
docker-compose run --rm binance-spark-processor env | grep SPARK

# Test Spark session creation
docker-compose run --rm binance-spark-processor python -c "from pyspark.sql import SparkSession; spark = SparkSession.builder.getOrCreate(); print(spark.version)"
```

### WebSocket Connection Issues
```bash
# Test WebSocket connection
docker-compose run --rm binance-spark-processor python -c "import websocket; ws = websocket.create_connection('wss://stream.binance.com:9443/ws/btcusdt@kline_1m'); print('Connected'); ws.close()"

# Check network connectivity from EC2
ping stream.binance.com

# Check if security group allows outbound HTTPS (port 443)
```

### Logs Not Appearing
```bash
# Check if logs directory exists and has proper permissions
ls -la logs/

# Create logs directory if missing
mkdir -p logs
chmod 755 logs

# Check volume mounts
docker inspect binance-spark-processor | grep -A 10 Mounts

# Check if application is writing logs
docker-compose exec binance-spark-processor ls -la /app/logs/
```

### High Memory/CPU Usage
```bash
# Check resource usage
docker stats binance-spark-processor

# Limit resources in docker-compose.yml (add under service):
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G

# Restart with new limits
docker-compose down
docker-compose up -d
```

## Performance Tuning

### Spark Configuration
Adjust Spark settings in `.env`:
```bash
# Use all available cores
SPARK_MASTER=local[*]

# Or specify number of cores
SPARK_MASTER=local[4]
```

### Resource Limits
Add resource limits to `docker-compose.yml`:
```yaml
services:
  binance-spark-processor:
    # ... other settings ...
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

## Project Structure

```
binance-spark-processor/
├── config.py                 # Configuration management
├── websocket_client.py       # Binance WebSocket client
├── spark_processor.py        # PySpark processing with feature engineering
├── s3_writer.py             # S3 writer with time-based partitioning
├── main.py                  # Main orchestrator
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── .dockerignore          # Docker ignore patterns
├── .env.example           # Example environment variables
├── push_to_ecr.sh        # ECR push script
└── logs/                 # Application logs (volume mount)
```

## License

MIT

## Support

For issues and questions, please open an issue on the repository.
