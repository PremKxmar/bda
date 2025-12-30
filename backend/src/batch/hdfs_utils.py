"""
Smart City Traffic - HDFS Utilities
====================================

This script provides utilities for working with Hadoop HDFS:
- Upload local data to HDFS using PySpark
- Download data from HDFS
- List HDFS directories
- Clean up HDFS data

Usage:
    python src/batch/hdfs_utils.py upload
    python src/batch/hdfs_utils.py download
    python src/batch/hdfs_utils.py list
    python src/batch/hdfs_utils.py health
"""

import os
import sys
from pathlib import Path
import subprocess
import argparse

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration - HDFS paths
HDFS_NAMENODE = "hdfs://localhost:9000"
HDFS_DATA_DIR = "/smart-city-traffic/data"
HDFS_RAW_DIR = f"{HDFS_DATA_DIR}/raw"
HDFS_PROCESSED_DIR = f"{HDFS_DATA_DIR}/processed"
HDFS_FEATURES_DIR = f"{HDFS_DATA_DIR}/features"
HDFS_MODELS_DIR = f"{HDFS_DATA_DIR}/models"

# Local paths
LOCAL_DATA_DIR = PROJECT_ROOT / "data"
LOCAL_RAW_DIR = Path(r"c:\sem6-real\bigdata\vscode")  # Where raw CSV files are
LOCAL_PROCESSED_DIR = LOCAL_DATA_DIR / "processed"
LOCAL_MODELS_DIR = PROJECT_ROOT / "models"


def get_hdfs_uri(path):
    """Get full HDFS URI for a path."""
    return f"{HDFS_NAMENODE}{path}"


def run_hdfs_command(cmd, check=True):
    """Run an HDFS command using docker exec to namenode container."""
    # Use docker exec to run HDFS commands inside the namenode container
    full_cmd = f'docker exec namenode hdfs dfs {cmd}'
    print(f"Running: hdfs dfs {cmd}")
    
    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr and "WARN" not in result.stderr:
            print(f"STDERR: {result.stderr}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return False


def check_docker_running():
    """Check if Docker and HDFS containers are running."""
    try:
        result = subprocess.run(
            'docker ps --filter "name=namenode" --format "{{.Names}}"',
            shell=True,
            capture_output=True,
            text=True
        )
        if "namenode" in result.stdout:
            print("✓ HDFS namenode container is running")
            return True
        else:
            print("✗ HDFS namenode container is NOT running")
            print("  Run: docker-compose up -d namenode datanode")
            return False
    except Exception as e:
        print(f"✗ Docker check failed: {e}")
        return False


def create_hdfs_directories():
    """Create necessary HDFS directories."""
    print("\n" + "=" * 60)
    print("Creating HDFS directories")
    print("=" * 60)
    
    directories = [
        HDFS_DATA_DIR,
        HDFS_RAW_DIR,
        HDFS_PROCESSED_DIR,
        HDFS_FEATURES_DIR,
        HDFS_MODELS_DIR
    ]
    
    for dir_path in directories:
        run_hdfs_command(f"-mkdir -p {dir_path}", check=False)
    
    print("✓ HDFS directories created")


def upload_with_spark():
    """Upload data to HDFS using PySpark (handles large files better)."""
    from pyspark.sql import SparkSession
    
    print("\n" + "=" * 60)
    print("Uploading data to HDFS using Spark")
    print("=" * 60)
    
    # Create Spark session with HDFS config
    spark = SparkSession.builder \
        .appName("HDFS-Upload") \
        .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE) \
        .master("local[*]") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    # Upload raw CSV files
    csv_files = list(LOCAL_RAW_DIR.glob("yellow_tripdata_*.csv"))
    
    if csv_files:
        print(f"\nUploading {len(csv_files)} CSV files to HDFS...")
        for csv_file in csv_files:
            print(f"  Reading: {csv_file.name}...")
            df = spark.read.option("header", "true").csv(str(csv_file))
            
            hdfs_path = f"{HDFS_NAMENODE}{HDFS_RAW_DIR}/{csv_file.stem}"
            print(f"  Writing to: {hdfs_path}")
            df.write.mode("overwrite").option("header", "true").csv(hdfs_path)
            print(f"  ✓ Uploaded: {csv_file.name} ({df.count():,} rows)")
    else:
        print("  No CSV files found in", LOCAL_RAW_DIR)
    
    # Upload processed parquet files
    parquet_dirs = [d for d in LOCAL_PROCESSED_DIR.iterdir() if d.is_dir() and "parquet" in d.name]
    
    if parquet_dirs:
        print(f"\nUploading {len(parquet_dirs)} Parquet directories to HDFS...")
        for pq_dir in parquet_dirs:
            print(f"  Reading: {pq_dir.name}...")
            df = spark.read.parquet(str(pq_dir))
            
            hdfs_path = f"{HDFS_NAMENODE}{HDFS_PROCESSED_DIR}/{pq_dir.name}"
            print(f"  Writing to: {hdfs_path}")
            df.write.mode("overwrite").parquet(hdfs_path)
            print(f"  ✓ Uploaded: {pq_dir.name} ({df.count():,} rows)")
    
    # Upload single parquet files
    parquet_files = list(LOCAL_PROCESSED_DIR.glob("*.parquet"))
    parquet_files = [f for f in parquet_files if f.is_file()]
    
    if parquet_files:
        print(f"\nUploading {len(parquet_files)} Parquet files to HDFS...")
        for pq_file in parquet_files:
            print(f"  Reading: {pq_file.name}...")
            df = spark.read.parquet(str(pq_file))
            
            hdfs_path = f"{HDFS_NAMENODE}{HDFS_PROCESSED_DIR}/{pq_file.stem}"
            print(f"  Writing to: {hdfs_path}")
            df.write.mode("overwrite").parquet(hdfs_path)
            print(f"  ✓ Uploaded: {pq_file.name}")
    
    spark.stop()
    print("\n✓ Spark upload complete!")


def upload_to_hdfs():
    """Upload local data to HDFS using docker cp and hdfs put."""
    print("\n" + "=" * 60)
    print("Uploading data to HDFS")
    print("=" * 60)
    
    if not check_docker_running():
        return
    
    # Create directories first
    create_hdfs_directories()
    
    # Upload raw CSV files using docker cp + hdfs put
    csv_files = list(LOCAL_RAW_DIR.glob("yellow_tripdata_*.csv"))
    
    if csv_files:
        print(f"\nUploading {len(csv_files)} CSV files to HDFS...")
        for csv_file in csv_files:
            # Copy file to container
            print(f"  Copying {csv_file.name} to container...")
            copy_cmd = f'docker cp "{csv_file}" namenode:/tmp/{csv_file.name}'
            subprocess.run(copy_cmd, shell=True, check=False)
            
            # Put to HDFS
            hdfs_path = f"{HDFS_RAW_DIR}/{csv_file.name}"
            run_hdfs_command(f"-put -f /tmp/{csv_file.name} {hdfs_path}", check=False)
            
            # Clean up
            subprocess.run(f'docker exec namenode rm /tmp/{csv_file.name}', shell=True, check=False)
            print(f"  ✓ Uploaded: {csv_file.name}")
    else:
        print(f"  No CSV files found in {LOCAL_RAW_DIR}")
    
    print("\n✓ Upload complete!")


def download_from_hdfs():
    """Download data from HDFS to local."""
    print("\n" + "=" * 60)
    print("Downloading data from HDFS")
    print("=" * 60)
    
    if not check_docker_running():
        return
    
    # Create local directories
    LOCAL_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download processed data
    hdfs_processed = f"{HDFS_PROCESSED_DIR}/*"
    
    run_hdfs_command(f"-get {hdfs_processed} /tmp/", check=False)
    subprocess.run(f'docker cp namenode:/tmp/processed {LOCAL_PROCESSED_DIR}/', shell=True, check=False)
    
    print("\n✓ Download complete!")


def list_hdfs_contents():
    """List contents of HDFS directories."""
    print("\n" + "=" * 60)
    print("HDFS Directory Contents")
    print("=" * 60)
    
    if not check_docker_running():
        return
    
    print("\n--- Root Directory ---")
    run_hdfs_command(f"-ls {HDFS_DATA_DIR}", check=False)
    
    print("\n--- Raw Data ---")
    run_hdfs_command(f"-ls {HDFS_RAW_DIR}", check=False)
    
    print("\n--- Processed Data ---")
    run_hdfs_command(f"-ls {HDFS_PROCESSED_DIR}", check=False)
    
    print("\n--- Features ---")
    run_hdfs_command(f"-ls {HDFS_FEATURES_DIR}", check=False)
    
    print("\n--- Models ---")
    run_hdfs_command(f"-ls {HDFS_MODELS_DIR}", check=False)
    
    print("\n--- Storage Usage ---")
    run_hdfs_command(f"-du -h {HDFS_DATA_DIR}", check=False)


def clean_hdfs():
    """Clean HDFS directories."""
    print("\n" + "=" * 60)
    print("Cleaning HDFS directories")
    print("=" * 60)
    
    if not check_docker_running():
        return
    
    confirm = input("Are you sure you want to delete all HDFS data? (yes/no): ")
    if confirm.lower() == 'yes':
        run_hdfs_command(f"-rm -r {HDFS_DATA_DIR}", check=False)
        print("✓ HDFS data deleted")
    else:
        print("Cancelled")


def check_hdfs_health():
    """Check HDFS health status."""
    print("\n" + "=" * 60)
    print("HDFS Health Check")
    print("=" * 60)
    
    if not check_docker_running():
        return
    
    print("\n--- HDFS Report ---")
    result = subprocess.run(
        'docker exec namenode hdfs dfsadmin -report',
        shell=True, 
        capture_output=True, 
        text=True
    )
    if result.returncode == 0:
        print(result.stdout[:2000])  # Print first 2000 chars
        print("\n✓ HDFS is healthy")
    else:
        print(f"✗ HDFS health check failed: {result.stderr}")


def main():
    parser = argparse.ArgumentParser(description="HDFS Utilities for Smart City Traffic")
    parser.add_argument(
        "action",
        choices=["upload", "upload-spark", "download", "list", "clean", "health", "setup"],
        help="Action to perform"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("SMART CITY TRAFFIC - HDFS UTILITIES")
    print("=" * 60)
    print(f"HDFS Namenode: {HDFS_NAMENODE}")
    print(f"HDFS Data Dir: {HDFS_DATA_DIR}")
    print(f"Local Raw Dir: {LOCAL_RAW_DIR}")
    print(f"Local Processed Dir: {LOCAL_PROCESSED_DIR}")
    
    if args.action == "upload":
        upload_to_hdfs()
    elif args.action == "upload-spark":
        upload_with_spark()
    elif args.action == "download":
        download_from_hdfs()
    elif args.action == "list":
        list_hdfs_contents()
    elif args.action == "clean":
        clean_hdfs()
    elif args.action == "health":
        check_hdfs_health()
    elif args.action == "setup":
        if check_docker_running():
            create_hdfs_directories()
            print("\n✓ HDFS setup complete!")


if __name__ == "__main__":
    main()
