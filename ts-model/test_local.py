"""
Test script to process local JSON file and create CSV output
"""

from pyspark.sql import SparkSession
from data_preparation import process_s3_data
import os

# Initialize Spark session for local testing
spark = SparkSession.builder \
    .appName("CryptoDataPrepLocalTest") \
    .master("local[*]") \
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
    .config("spark.driver.memory", "2g") \
    .getOrCreate()

# Set log level to reduce noise
spark.sparkContext.setLogLevel("WARN")

print("\n" + "=" * 80)
print("Testing Crypto Time Series Data Preparation Pipeline")
print("=" * 80)

# Define paths
input_path = "batch_20251125_224845_4.json"
output_path = "output"

# Create output directory if it doesn't exist
os.makedirs(output_path, exist_ok=True)

print(f"\nInput file: {input_path}")
print(f"Output directory: {output_path}")

# Process the data
try:
    symbol_counts, validation = process_s3_data(spark, input_path, output_path)
    
    print("\n" + "=" * 80)
    print("PROCESSING SUMMARY")
    print("=" * 80)
    
    print(f"\n✓ Records per symbol:")
    for symbol, count in symbol_counts.items():
        print(f"  • {symbol}: {count:,} records")
    
    print(f"\n✓ Validation Report:")
    print(f"  • Total records: {validation['total_records']:,}")
    print(f"  • Duplicate timestamps: {validation['duplicate_timestamps']}")
    print(f"  • Invalid prices: {validation['invalid_prices']}")
    
    print(f"\n✓ Null counts in critical columns:")
    for col, count in validation['null_counts'].items():
        print(f"  • {col}: {count}")
    
    print(f"\n✓ Time ranges:")
    for symbol, time_range in validation['time_ranges'].items():
        print(f"  • {symbol}:")
        print(f"    - First: {time_range['first']}")
        print(f"    - Last: {time_range['last']}")
    
    print("\n" + "=" * 80)
    print("✓ SUCCESS! CSV files generated in ts-model/output/")
    print("=" * 80 + "\n")
    
except Exception as e:
    print(f"\n✗ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    
finally:
    spark.stop()

