# 📖 Complete Guide: Reading from Kinesis on EMR

## 🎯 Quick Start

### Prerequisites
1. ✅ Kinesis stream created and receiving data
2. ✅ EMR cluster running with Spark
3. ✅ S3 bucket for output and checkpoints
4. ✅ IAM roles configured correctly

---

## 📊 Method 1: Using the Simple Reader (`kinesis_reader_emr.py`)

### Step 1: Set Environment Variables

```bash
export EMR_CLUSTER_ID="j-XXXXXXXXXXXXX"
export KINESIS_STREAM_NAME="stock-market-stream"
export S3_BUCKET="your-bucket-name"
export AWS_REGION="us-east-1"
```

### Step 2: Upload Code to S3

```bash
aws s3 cp kinesis_reader_emr.py s3://${S3_BUCKET}/spark/code/
```

### Step 3: Submit to EMR

```bash
aws emr add-steps \
  --cluster-id ${EMR_CLUSTER_ID} \
  --steps Type=Spark,Name="Kinesis-Reader",\
ActionOnFailure=CONTINUE,\
Args=[\
--deploy-mode,cluster,\
--packages,org.apache.spark:spark-sql-kinesis_2.12:3.3.0,\
s3://${S3_BUCKET}/spark/code/kinesis_reader_emr.py\
]
```

### Step 4: Check Output

```bash
# List processed data
aws s3 ls s3://${S3_BUCKET}/processed/ --recursive

# View a sample file
aws s3 cp s3://${S3_BUCKET}/processed/trades/symbol=AAPL/part-00000.parquet - | parquet-tools show -
```

---

## 🔥 Method 2: Using the Full Processor (`spark_streaming.py`)

Your existing code already supports Kinesis! Just set:

```bash
export LOCAL_MODE=false
export KINESIS_STREAM_NAME="stock-market-stream"
export S3_BUCKET="your-bucket-name"
export AWS_REGION="us-east-1"
```

### Upload All Code

```bash
# Upload main script
aws s3 cp spark_streaming.py s3://${S3_BUCKET}/spark/code/

# Upload dependencies
aws s3 cp alpaca_data_transformations.py s3://${S3_BUCKET}/spark/code/
aws s3 cp rl_model_inference.py s3://${S3_BUCKET}/spark/code/
aws s3 cp config.py s3://${S3_BUCKET}/spark/code/
```

### Submit with All Dependencies

```bash
aws emr add-steps \
  --cluster-id ${EMR_CLUSTER_ID} \
  --steps Type=Spark,Name="Stock-Market-Processor",\
ActionOnFailure=CONTINUE,\
Args=[\
--deploy-mode,cluster,\
--packages,org.apache.spark:spark-sql-kinesis_2.12:3.3.0,\
--py-files,s3://${S3_BUCKET}/spark/code/alpaca_data_transformations.py,\
--py-files,s3://${S3_BUCKET}/spark/code/rl_model_inference.py,\
--py-files,s3://${S3_BUCKET}/spark/code/config.py,\
s3://${S3_BUCKET}/spark/code/spark_streaming.py\
]
```

---

## 💻 Method 3: Direct spark-submit on EMR Master Node

### SSH into EMR Master

```bash
ssh -i your-key.pem hadoop@ec2-xx-xx-xx-xx.compute.amazonaws.com
```

### Run Spark Submit

```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kinesis_2.12:3.3.0 \
  --conf spark.sql.streaming.schemaInference=true \
  --conf spark.executor.memory=4g \
  --conf spark.executor.cores=2 \
  --conf spark.dynamicAllocation.enabled=true \
  kinesis_reader_emr.py
```

---

## 🎨 Method 4: Using foreachBatch for Complex Processing

For more control, process each micro-batch:

```python
def process_batch(batch_df, batch_id):
    """Custom processing logic for each batch"""
    
    if batch_df.count() > 0:
        print(f"Processing batch {batch_id} with {batch_df.count()} records")
        
        # Parse JSON
        parsed_df = batch_df.selectExpr("CAST(data AS STRING) as json_str")
        
        # Your custom processing here
        # Example: Calculate aggregations
        result = parsed_df.selectExpr(
            "get_json_object(json_str, '$.S') as symbol",
            "get_json_object(json_str, '$.p') as price"
        ).groupBy("symbol").agg(
            avg("price").alias("avg_price"),
            count("*").alias("count")
        )
        
        # Write to S3
        result.write \
            .mode("append") \
            .parquet(f"s3://your-bucket/processed/batch_{batch_id}")

# Read from Kinesis
kinesis_df = spark.readStream \
    .format("kinesis") \
    .option("streamName", "stock-market-stream") \
    .option("region", "us-east-1") \
    .option("initialPosition", "TRIM_HORIZON") \
    .load()

# Process using foreachBatch
query = kinesis_df.writeStream \
    .foreachBatch(process_batch) \
    .outputMode("append") \
    .option("checkpointLocation", "s3://your-bucket/checkpoints") \
    .start()

query.awaitTermination()
```

---

## 🔧 Configuration Options

### Kinesis Reader Options

```python
spark.readStream \
    .format("kinesis") \
    .option("streamName", "your-stream")              # Required
    .option("region", "us-east-1")                    # Required
    .option("initialPosition", "TRIM_HORIZON")        # LATEST, TRIM_HORIZON, or AT_TIMESTAMP
    .option("kinesis.executor.maxFetchTimeInMs", 1000) # Fetch interval
    .option("kinesis.executor.maxFetchRecordsPerShard", 10000) # Records per fetch
    .option("kinesis.executor.maxRecordPerRead", 100000) # Total records per read
    .load()
```

### Initial Position Options

| Option | Description |
|--------|-------------|
| `LATEST` | Start from newest records (default) |
| `TRIM_HORIZON` | Start from oldest available records |
| `AT_TIMESTAMP` | Start from specific timestamp |

---

## 📊 Monitoring Your Job

### Check EMR Step Status

```bash
aws emr list-steps --cluster-id ${EMR_CLUSTER_ID}
```

### View Step Details

```bash
aws emr describe-step --cluster-id ${EMR_CLUSTER_ID} --step-id s-XXXXXXXXXXXXX
```

### Access Spark UI

1. Enable SSH tunnel:
```bash
ssh -i your-key.pem -N -L 8157:localhost:8088 hadoop@master-node
```

2. Open browser: `http://localhost:8157`

### CloudWatch Logs

```bash
aws logs tail /aws/emr/${EMR_CLUSTER_ID}/step/s-XXXXXXXXXXXXX --follow
```

---

## 🐛 Troubleshooting

### Issue: "Stream not found"

**Solution:** Verify stream exists and IAM role has permissions:

```bash
aws kinesis describe-stream --stream-name stock-market-stream
```

### Issue: "Access Denied to S3"

**Solution:** Add S3 permissions to EMR service role:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject"
  ],
  "Resource": "arn:aws:s3:::your-bucket/*"
}
```

### Issue: "Package not found: spark-sql-kinesis"

**Solution:** Use correct Spark version package:

| Spark Version | Package |
|---------------|---------|
| 3.3.x | `org.apache.spark:spark-sql-kinesis_2.12:3.3.0` |
| 3.4.x | `org.apache.spark:spark-sql-kinesis_2.12:3.4.0` |
| 3.5.x | `org.apache.spark:spark-sql-kinesis_2.12:3.5.0` |

### Issue: Data lag / slow processing

**Solution:** Increase parallelism:

```python
spark.conf.set("spark.sql.shuffle.partitions", 200)
spark.conf.set("spark.executor.instances", 10)
```

---

## 💰 Cost Optimization

### 1. Use Spot Instances for Task Nodes

Save 70% on compute:

```bash
aws emr create-cluster \
  --instance-groups \
    InstanceGroupType=MASTER,InstanceType=m5.xlarge,InstanceCount=1 \
    InstanceGroupType=CORE,InstanceType=m5.xlarge,InstanceCount=2 \
    InstanceGroupType=TASK,InstanceType=m5.xlarge,InstanceCount=3,BidPrice=0.05
```

### 2. Auto-terminate Cluster After Job

```bash
--auto-terminate
```

### 3. Use Smaller Shards

Reduce Kinesis cost by using appropriate shard count:

```bash
aws kinesis update-shard-count \
  --stream-name stock-market-stream \
  --target-shard-count 1
```

---

## 📈 Performance Tuning

### For High Throughput

```python
spark.conf.set("spark.sql.shuffle.partitions", 200)
spark.conf.set("spark.streaming.kafka.consumer.cache.maxCapacity", 1000)
spark.conf.set("spark.executor.memory", "8g")
spark.conf.set("spark.executor.cores", 4)
```

### For Low Latency

```python
# Reduce trigger interval
.trigger(processingTime="1 second")

# Increase fetch frequency
.option("kinesis.executor.maxFetchTimeInMs", 500)
```

---

## 🎯 Complete Example: End-to-End Flow

```bash
#!/bin/bash

# 1. Create Kinesis stream
aws kinesis create-stream \
  --stream-name stock-market-stream \
  --shard-count 2

# 2. Start producer (feeding data to Kinesis)
python alpaca_websocket_client.py

# 3. Create EMR cluster
EMR_CLUSTER_ID=$(aws emr create-cluster \
  --name "Stock-Processor" \
  --release-label emr-6.10.0 \
  --applications Name=Spark \
  --instance-type m5.xlarge \
  --instance-count 3 \
  --use-default-roles \
  --query 'ClusterId' \
  --output text)

echo "EMR Cluster: ${EMR_CLUSTER_ID}"

# 4. Wait for cluster to be ready
aws emr wait cluster-running --cluster-id ${EMR_CLUSTER_ID}

# 5. Upload code
aws s3 cp kinesis_reader_emr.py s3://my-bucket/spark/

# 6. Submit job
aws emr add-steps \
  --cluster-id ${EMR_CLUSTER_ID} \
  --steps Type=Spark,Name="Reader",\
Args=[--packages,org.apache.spark:spark-sql-kinesis_2.12:3.3.0,\
s3://my-bucket/spark/kinesis_reader_emr.py]

# 7. Monitor output
watch -n 5 'aws s3 ls s3://my-bucket/processed/ --recursive | tail -20'
```

---

## 📚 Additional Resources

- [AWS EMR Spark Documentation](https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark.html)
- [Spark Kinesis Integration](https://spark.apache.org/docs/latest/structured-streaming-kinesis-integration.html)
- [Kinesis Best Practices](https://docs.aws.amazon.com/streams/latest/dev/best-practices.html)

---

## ✅ Checklist Before Production

- [ ] IAM roles configured with least privilege
- [ ] S3 lifecycle policies for old data
- [ ] CloudWatch alarms for failures
- [ ] EMR auto-scaling configured
- [ ] Spot instances for cost savings
- [ ] Monitoring dashboard setup
- [ ] Backup strategy for checkpoints
- [ ] Error handling and retry logic
- [ ] Data validation in place
- [ ] Performance testing completed



