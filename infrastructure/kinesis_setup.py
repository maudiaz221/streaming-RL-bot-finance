"""
AWS Kinesis Data Stream setup script
"""
import boto3
import argparse
import logging
import sys
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_kinesis_stream(
    stream_name: str,
    shard_count: int = 1,
    region: str = 'us-east-1'
):
    """
    Create a Kinesis Data Stream
    
    Args:
        stream_name: Name of the stream
        shard_count: Number of shards
        region: AWS region
    """
    try:
        kinesis = boto3.client('kinesis', region_name=region)
        
        # Check if stream already exists
        try:
            response = kinesis.describe_stream(StreamName=stream_name)
            logger.info(f"Stream '{stream_name}' already exists")
            logger.info(f"Status: {response['StreamDescription']['StreamStatus']}")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Create stream
        logger.info(f"Creating Kinesis stream: {stream_name}")
        logger.info(f"  Region: {region}")
        logger.info(f"  Shards: {shard_count}")
        
        kinesis.create_stream(
            StreamName=stream_name,
            ShardCount=shard_count
        )
        
        logger.info("✅ Stream creation initiated")
        logger.info("Waiting for stream to become active...")
        
        # Wait for stream to be active
        waiter = kinesis.get_waiter('stream_exists')
        waiter.wait(StreamName=stream_name)
        
        # Get stream details
        response = kinesis.describe_stream(StreamName=stream_name)
        stream_arn = response['StreamDescription']['StreamARN']
        
        logger.info("✅ Stream is now active!")
        logger.info(f"Stream ARN: {stream_arn}")
        logger.info(f"Retention period: 24 hours (default)")
        
        return stream_arn
        
    except Exception as e:
        logger.error(f"❌ Failed to create stream: {e}")
        sys.exit(1)


def update_retention_period(
    stream_name: str,
    retention_hours: int = 24,
    region: str = 'us-east-1'
):
    """Update stream retention period"""
    try:
        kinesis = boto3.client('kinesis', region_name=region)
        
        logger.info(f"Updating retention period to {retention_hours} hours...")
        
        kinesis.increase_stream_retention_period(
            StreamName=stream_name,
            RetentionPeriodHours=retention_hours
        )
        
        logger.info("✅ Retention period updated")
        
    except Exception as e:
        logger.error(f"❌ Failed to update retention: {e}")


def enable_encryption(
    stream_name: str,
    kms_key_id: str = 'alias/aws/kinesis',
    region: str = 'us-east-1'
):
    """Enable server-side encryption"""
    try:
        kinesis = boto3.client('kinesis', region_name=region)
        
        logger.info(f"Enabling encryption with key: {kms_key_id}")
        
        kinesis.start_stream_encryption(
            StreamName=stream_name,
            EncryptionType='KMS',
            KeyId=kms_key_id
        )
        
        logger.info("✅ Encryption enabled")
        
    except Exception as e:
        logger.error(f"❌ Failed to enable encryption: {e}")


def delete_stream(stream_name: str, region: str = 'us-east-1'):
    """Delete a Kinesis stream"""
    try:
        kinesis = boto3.client('kinesis', region_name=region)
        
        logger.warning(f"Deleting stream: {stream_name}")
        
        kinesis.delete_stream(
            StreamName=stream_name,
            EnforceConsumerDeletion=True
        )
        
        logger.info("✅ Stream deletion initiated")
        
    except Exception as e:
        logger.error(f"❌ Failed to delete stream: {e}")


def list_streams(region: str = 'us-east-1'):
    """List all Kinesis streams"""
    try:
        kinesis = boto3.client('kinesis', region_name=region)
        
        response = kinesis.list_streams()
        streams = response['StreamNames']
        
        if not streams:
            logger.info("No streams found")
            return
        
        logger.info(f"Found {len(streams)} stream(s):")
        for stream in streams:
            # Get stream details
            desc = kinesis.describe_stream(StreamName=stream)
            status = desc['StreamDescription']['StreamStatus']
            shards = len(desc['StreamDescription']['Shards'])
            
            logger.info(f"  - {stream} (Status: {status}, Shards: {shards})")
        
    except Exception as e:
        logger.error(f"❌ Failed to list streams: {e}")


def main():
    parser = argparse.ArgumentParser(description='Manage AWS Kinesis Data Streams')
    parser.add_argument('--action', choices=['create', 'delete', 'list', 'update-retention', 'enable-encryption'],
                       default='create', help='Action to perform')
    parser.add_argument('--stream-name', default='stock-market-stream',
                       help='Stream name')
    parser.add_argument('--shards', type=int, default=1,
                       help='Number of shards (for create)')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region')
    parser.add_argument('--retention-hours', type=int, default=24,
                       help='Retention period in hours')
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("AWS Kinesis Stream Management")
    logger.info("=" * 70)
    
    if args.action == 'create':
        create_kinesis_stream(args.stream_name, args.shards, args.region)
    elif args.action == 'delete':
        confirm = input(f"Are you sure you want to delete '{args.stream_name}'? (yes/no): ")
        if confirm.lower() == 'yes':
            delete_stream(args.stream_name, args.region)
        else:
            logger.info("Deletion cancelled")
    elif args.action == 'list':
        list_streams(args.region)
    elif args.action == 'update-retention':
        update_retention_period(args.stream_name, args.retention_hours, args.region)
    elif args.action == 'enable-encryption':
        enable_encryption(args.stream_name, region=args.region)


if __name__ == "__main__":
    main()

