"""
AWS S3 bucket setup script
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


def create_s3_bucket(
    bucket_name: str,
    region: str = 'us-east-1',
    enable_versioning: bool = False,
    enable_encryption: bool = True
):
    """
    Create an S3 bucket with proper configuration
    
    Args:
        bucket_name: Name of the bucket
        region: AWS region
        enable_versioning: Enable versioning
        enable_encryption: Enable server-side encryption
    """
    try:
        s3 = boto3.client('s3', region_name=region)
        
        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket '{bucket_name}' already exists")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != '404':
                raise
        
        # Create bucket
        logger.info(f"Creating S3 bucket: {bucket_name}")
        logger.info(f"  Region: {region}")
        
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        
        logger.info("✅ Bucket created successfully")
        
        # Enable versioning
        if enable_versioning:
            logger.info("Enabling versioning...")
            s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            logger.info("✅ Versioning enabled")
        
        # Enable encryption
        if enable_encryption:
            logger.info("Enabling server-side encryption...")
            s3.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    'Rules': [{
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }]
                }
            )
            logger.info("✅ Encryption enabled")
        
        # Block public access
        logger.info("Configuring public access block...")
        s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True
            }
        )
        logger.info("✅ Public access blocked")
        
        return bucket_name
        
    except Exception as e:
        logger.error(f"❌ Failed to create bucket: {e}")
        sys.exit(1)


def create_folder_structure(bucket_name: str, region: str = 'us-east-1'):
    """Create folder structure in S3 bucket"""
    folders = [
        'processed-data/',
        'checkpoints/',
        'models/',
        'raw-data/',
        'logs/'
    ]
    
    try:
        s3 = boto3.client('s3', region_name=region)
        
        logger.info(f"Creating folder structure in {bucket_name}...")
        
        for folder in folders:
            s3.put_object(Bucket=bucket_name, Key=folder)
            logger.info(f"  Created: {folder}")
        
        logger.info("✅ Folder structure created")
        
    except Exception as e:
        logger.error(f"❌ Failed to create folders: {e}")


def setup_lifecycle_policy(bucket_name: str, region: str = 'us-east-1'):
    """Setup lifecycle policy for cost optimization"""
    try:
        s3 = boto3.client('s3', region_name=region)
        
        logger.info("Setting up lifecycle policy...")
        
        lifecycle_config = {
            'Rules': [
                {
                    'Id': 'MoveOldDataToIA',
                    'Status': 'Enabled',
                    'Filter': {'Prefix': 'processed-data/'},
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'STANDARD_IA'
                        },
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER'
                        }
                    ]
                },
                {
                    'Id': 'DeleteOldLogs',
                    'Status': 'Enabled',
                    'Filter': {'Prefix': 'logs/'},
                    'Expiration': {'Days': 30}
                }
            ]
        }
        
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_config
        )
        
        logger.info("✅ Lifecycle policy configured")
        logger.info("  - Data > 30 days moved to Infrequent Access")
        logger.info("  - Data > 90 days moved to Glacier")
        logger.info("  - Logs deleted after 30 days")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup lifecycle policy: {e}")


def delete_bucket(bucket_name: str, region: str = 'us-east-1', force: bool = False):
    """Delete an S3 bucket"""
    try:
        s3 = boto3.client('s3', region_name=region)
        s3_resource = boto3.resource('s3', region_name=region)
        bucket = s3_resource.Bucket(bucket_name)
        
        if force:
            logger.warning(f"Emptying bucket {bucket_name}...")
            bucket.objects.all().delete()
            bucket.object_versions.all().delete()
        
        logger.warning(f"Deleting bucket: {bucket_name}")
        s3.delete_bucket(Bucket=bucket_name)
        
        logger.info("✅ Bucket deleted")
        
    except Exception as e:
        logger.error(f"❌ Failed to delete bucket: {e}")


def list_buckets(region: str = 'us-east-1'):
    """List all S3 buckets"""
    try:
        s3 = boto3.client('s3', region_name=region)
        
        response = s3.list_buckets()
        buckets = response['Buckets']
        
        if not buckets:
            logger.info("No buckets found")
            return
        
        logger.info(f"Found {len(buckets)} bucket(s):")
        for bucket in buckets:
            name = bucket['Name']
            created = bucket['CreationDate'].strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"  - {name} (Created: {created})")
        
    except Exception as e:
        logger.error(f"❌ Failed to list buckets: {e}")


def main():
    parser = argparse.ArgumentParser(description='Manage AWS S3 Buckets')
    parser.add_argument('--action', choices=['create', 'delete', 'list', 'create-folders', 'setup-lifecycle'],
                       default='create', help='Action to perform')
    parser.add_argument('--bucket-name', default='stock-trading-data',
                       help='Bucket name')
    parser.add_argument('--region', default='us-east-1',
                       help='AWS region')
    parser.add_argument('--versioning', action='store_true',
                       help='Enable versioning')
    parser.add_argument('--no-encryption', action='store_true',
                       help='Disable encryption')
    parser.add_argument('--force', action='store_true',
                       help='Force delete (empty bucket first)')
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("AWS S3 Bucket Management")
    logger.info("=" * 70)
    
    if args.action == 'create':
        create_s3_bucket(
            args.bucket_name,
            args.region,
            enable_versioning=args.versioning,
            enable_encryption=not args.no_encryption
        )
        create_folder_structure(args.bucket_name, args.region)
    elif args.action == 'delete':
        confirm = input(f"Are you sure you want to delete '{args.bucket_name}'? (yes/no): ")
        if confirm.lower() == 'yes':
            delete_bucket(args.bucket_name, args.region, args.force)
        else:
            logger.info("Deletion cancelled")
    elif args.action == 'list':
        list_buckets(args.region)
    elif args.action == 'create-folders':
        create_folder_structure(args.bucket_name, args.region)
    elif args.action == 'setup-lifecycle':
        setup_lifecycle_policy(args.bucket_name, args.region)


if __name__ == "__main__":
    main()

