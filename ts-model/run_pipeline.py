import os
import subprocess
import sys
from pyspark.sql import SparkSession
import shutil

# Import pipeline components
# We need to add current directory to path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_preparation import process_s3_data
from train_model import train

def main():
    print("="*80)
    print("STARTING CRYPTO PREDICTION PIPELINE")
    print("="*80)

    # Configuration
    RAW_DATA_FILE = "ts-model/raw_data.json"
    PROCESSED_OUTPUT_DIR = "ts-model/processed_output"
    MODEL_OUTPUT = "ts-model/model.pkl"
    COLLECTION_DURATION = 60  # Collect for 60 seconds
    
    # 1. Data Collection
    print(f"\n[Step 1] Collecting data for {COLLECTION_DURATION} seconds...")
    
    # Remove existing raw data to ensure clean state
    if os.path.exists(RAW_DATA_FILE):
        os.remove(RAW_DATA_FILE)
        
    try:
        cmd = [
            sys.executable, 
            "ts-model/collect_data.py", 
            "--duration", str(COLLECTION_DURATION),
            "--output", RAW_DATA_FILE,
            "--bootstrap"
        ]
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Data collection failed: {e}")
        # Proceed if file exists, else exit
        if not os.path.exists(RAW_DATA_FILE):
            print("No raw data file. Exiting.")
            sys.exit(1)
            
    # Check if we have data
    if not os.path.exists(RAW_DATA_FILE) or os.path.getsize(RAW_DATA_FILE) == 0:
         print("Raw data file is empty. Exiting.")
         sys.exit(1)

    # 2. Data Preparation (PySpark)
    print(f"\n[Step 2] Processing data with PySpark...")
    
    # Initialize Spark
    spark = SparkSession.builder \
        .appName("CryptoPipeline") \
        .master("local[*]") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("ERROR")
    
    try:
        # Clean output dir if exists (Spark write mode 'overwrite' handles this but good to be clean)
        # However, data_preparation writes to specific files.
        # Let's let Spark handle it.
        
        symbol_counts, validation = process_s3_data(spark, RAW_DATA_FILE, PROCESSED_OUTPUT_DIR)
        
        print("\nData Prep Summary:")
        print(f"Total records: {validation['total_records']}")
        for sym, count in symbol_counts.items():
            print(f"  {sym}: {count}")
            
    except Exception as e:
        print(f"Data preparation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        spark.stop()

    # 3. Model Training
    print(f"\n[Step 3] Training Model...")
    try:
        train(PROCESSED_OUTPUT_DIR, MODEL_OUTPUT)
    except Exception as e:
        print(f"Model training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "="*80)
    print("PIPELINE COMPLETED SUCCESSFULLY")
    print(f"Model saved to {MODEL_OUTPUT}")
    print("="*80)

if __name__ == "__main__":
    main()

