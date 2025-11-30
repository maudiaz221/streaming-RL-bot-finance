"""
Example usage of the crypto time series data preparation pipeline.

This script demonstrates how to process raw JSON kline data and generate
CSV files with engineered features ready for time series modeling.
"""

from pyspark.sql import SparkSession
from data_preparation import process_s3_data

def main():
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("CryptoTimeSeriesDataPrep") \
        .master("local[*]") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    
    # Set log level
    spark.sparkContext.setLogLevel("WARN")
    
    print("\n" + "=" * 80)
    print("Crypto Time Series Data Preparation Pipeline")
    print("=" * 80)
    
    # ===================================================================
    # CONFIGURATION - Update these paths for your use case
    # ===================================================================
    
    # For S3:
    # input_path = "s3://your-bucket/raw-data/*.json"
    # output_path = "s3://your-bucket/processed-data"
    
    # For local testing:
    input_path = "batch_20251125_224845_4.json"  # Single file or pattern like "*.json"
    output_path = "processed_output"
    
    # ===================================================================
    # PROCESS DATA
    # ===================================================================
    
    try:
        symbol_counts, validation = process_s3_data(spark, input_path, output_path)
        
        # Print summary
        print("\n" + "=" * 80)
        print("PROCESSING COMPLETE!")
        print("=" * 80)
        
        print(f"\n📊 Records processed per symbol:")
        for symbol, count in symbol_counts.items():
            print(f"   {symbol}: {count:,} records")
        
        print(f"\n✅ Data Quality:")
        print(f"   Total records: {validation['total_records']:,}")
        print(f"   Duplicate timestamps: {validation['duplicate_timestamps']}")
        print(f"   Invalid prices: {validation['invalid_prices']}")
        
        if validation['duplicate_timestamps'] > 0:
            print(f"\n⚠️  Warning: Found duplicate timestamps!")
        
        if validation['invalid_prices'] > 0:
            print(f"\n⚠️  Warning: Found invalid prices!")
        
        print(f"\n📁 Output location: {output_path}/")
        print(f"   Files: {', '.join([f'{s}.csv/' for s in symbol_counts.keys()])}")
        
        print("\n" + "=" * 80)
        print("CSV files are ready for time series modeling!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

