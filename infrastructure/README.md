# Infrastructure Setup Scripts

Python scripts for setting up AWS infrastructure for the stock trading platform.

## Prerequisites

- Python 3.9+
- AWS CLI configured with credentials
- Appropriate IAM permissions

## Installation

```bash
cd infrastructure
pip install -r requirements.txt
```

## AWS Credentials

Ensure you have AWS credentials configured:

```bash
aws configure
```

Or set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

## Usage

### Create Kinesis Data Stream

```bash
# Create stream with 1 shard
python kinesis_setup.py --action create --stream-name stock-market-stream

# Create with multiple shards for higher throughput
python kinesis_setup.py --action create --stream-name stock-market-stream --shards 2

# Update retention period
python kinesis_setup.py --action update-retention --stream-name stock-market-stream --retention-hours 48

# Enable encryption
python kinesis_setup.py --action enable-encryption --stream-name stock-market-stream

# List all streams
python kinesis_setup.py --action list

# Delete stream
python kinesis_setup.py --action delete --stream-name stock-market-stream
```

### Create S3 Bucket

```bash
# Create bucket with default settings
python s3_setup.py --action create --bucket-name stock-trading-data

# Create with versioning enabled
python s3_setup.py --action create --bucket-name stock-trading-data --versioning

# Create folders in bucket
python s3_setup.py --action create-folders --bucket-name stock-trading-data

# Setup lifecycle policy
python s3_setup.py --action setup-lifecycle --bucket-name stock-trading-data

# List all buckets
python s3_setup.py --action list

# Delete bucket (force empty first)
python s3_setup.py --action delete --bucket-name stock-trading-data --force
```

## Complete Setup

Run all setup commands in order:

```bash
#!/bin/bash

# Set variables
STREAM_NAME="stock-market-stream"
BUCKET_NAME="stock-trading-data"
REGION="us-east-1"

echo "Setting up AWS infrastructure..."

# 1. Create Kinesis stream
echo "Creating Kinesis stream..."
python kinesis_setup.py --action create --stream-name $STREAM_NAME --region $REGION --shards 1

# 2. Create S3 bucket
echo "Creating S3 bucket..."
python s3_setup.py --action create --bucket-name $BUCKET_NAME --region $REGION

# 3. Create folder structure
echo "Creating folder structure..."
python s3_setup.py --action create-folders --bucket-name $BUCKET_NAME --region $REGION

# 4. Setup lifecycle policies
echo "Setting up lifecycle policies..."
python s3_setup.py --action setup-lifecycle --bucket-name $BUCKET_NAME --region $REGION

echo "✅ Infrastructure setup complete!"
echo "Kinesis Stream: $STREAM_NAME"
echo "S3 Bucket: $BUCKET_NAME"
```

Save as `setup_all.sh` and run:

```bash
chmod +x setup_all.sh
./setup_all.sh
```

## S3 Folder Structure

The setup creates the following folder structure:

```
s3://stock-trading-data/
├── processed-data/     # Processed streaming data (Parquet)
├── checkpoints/        # Spark streaming checkpoints
├── models/             # Trained RL models
├── raw-data/           # Raw data backups
└── logs/               # Application logs
```

## Cost Considerations

### Kinesis Data Streams
- **On-demand**: ~$0.015 per shard-hour + $0.013 per million PUT payload units
- **Provisioned**: ~$0.015 per shard-hour
- **Example**: 1 shard running 24/7 = ~$11/month

### S3 Storage
- **Standard**: $0.023 per GB/month
- **Standard-IA**: $0.0125 per GB/month (after 30 days)
- **Glacier**: $0.004 per GB/month (after 90 days)
- **Example**: 100GB/month = ~$2.30/month (with lifecycle policies)

### Data Transfer
- **In**: Free
- **Out**: $0.09 per GB (to internet)

## Security Best Practices

1. **Enable Encryption**
   - Kinesis: KMS encryption for data at rest
   - S3: Server-side encryption (AES-256)

2. **Access Control**
   - Use IAM roles instead of access keys where possible
   - Follow principle of least privilege
   - Enable MFA for sensitive operations

3. **Monitoring**
   - Enable CloudWatch logging
   - Set up billing alerts
   - Monitor API calls with CloudTrail

4. **Data Retention**
   - Kinesis: 24-168 hours
   - S3: Use lifecycle policies to archive old data

## Cleanup

To remove all created resources:

```bash
# Delete Kinesis stream
python kinesis_setup.py --action delete --stream-name stock-market-stream

# Delete S3 bucket (force removes all objects)
python s3_setup.py --action delete --bucket-name stock-trading-data --force
```

**Warning**: This will permanently delete all data!

## Troubleshooting

### Permission Denied Errors

Ensure your IAM user/role has these permissions:
- `kinesis:CreateStream`
- `kinesis:DeleteStream`
- `kinesis:DescribeStream`
- `s3:CreateBucket`
- `s3:DeleteBucket`
- `s3:PutObject`
- `s3:PutBucketPolicy`

### Stream Already Exists

If stream exists, the script will skip creation. To recreate:
1. Delete existing stream
2. Wait for deletion to complete (~1 minute)
3. Run create command again

### Bucket Name Already Taken

S3 bucket names are globally unique. If your chosen name is taken:
1. Choose a different name (add unique suffix)
2. Update `.env` file with new bucket name

## Next Steps

After infrastructure setup:
1. Update `.env` file with created resource names
2. Run Alpaca WebSocket producer
3. Submit PySpark streaming job to EMR
4. Deploy Next.js dashboard

## License

MIT




