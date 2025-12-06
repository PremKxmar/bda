"""
Smart City Traffic - HDFS Utilities
====================================

This script provides utilities for working with Hadoop HDFS:
- Upload local data to HDFS
- Download data from HDFS
- List HDFS directories
- Clean up HDFS data

Usage:
    python src/batch/hdfs_utils.py upload
    python src/batch/hdfs_utils.py download
    python src/batch/hdfs_utils.py list
"""

import os
import sys
from pathlib import Path
import subprocess
import argparse

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
HDFS_NAMENODE = "hdfs://localhost:9000"
HDFS_DATA_DIR = "/smart-city-traffic/data"
LOCAL_DATA_DIR = PROJECT_ROOT / "data"


def run_hdfs_command(cmd, check=True):
    """Run an HDFS command and return output."""
    full_cmd = f"hdfs dfs {cmd}"
    print(f"Running: {full_cmd}")
    
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
        if result.stderr:
            print(f"STDERR: {result.stderr}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return False


def create_hdfs_directories():
    """Create necessary HDFS directories."""
    print("\n" + "=" * 60)
    print("Creating HDFS directories")
    print("=" * 60)
    
    directories = [
        f"{HDFS_DATA_DIR}",
        f"{HDFS_DATA_DIR}/raw",
        f"{HDFS_DATA_DIR}/processed",
        f"{HDFS_DATA_DIR}/models",
        f"{HDFS_DATA_DIR}/features"
    ]
    
    for dir_path in directories:
        run_hdfs_command(f"-mkdir -p {dir_path}", check=False)
    
    print("✓ HDFS directories created")


def upload_to_hdfs():
    """Upload local data to HDFS."""
    print("\n" + "=" * 60)
    print("Uploading data to HDFS")
    print("=" * 60)
    
    # Create directories first
    create_hdfs_directories()
    
    # Upload raw CSV files
    raw_dir = PROJECT_ROOT.parent
    csv_files = list(raw_dir.glob("yellow_tripdata_*.csv"))
    
    if csv_files:
        print(f"\nUploading {len(csv_files)} CSV files to HDFS...")
        for csv_file in csv_files:
            hdfs_path = f"{HDFS_DATA_DIR}/raw/{csv_file.name}"
            run_hdfs_command(f"-put -f {csv_file} {hdfs_path}")
            print(f"  ✓ Uploaded: {csv_file.name}")
    
    # Upload processed parquet files
    processed_dir = LOCAL_DATA_DIR / "processed"
    parquet_files = list(processed_dir.glob("*.parquet"))
    
    if parquet_files:
        print(f"\nUploading {len(parquet_files)} Parquet files to HDFS...")
        for pq_file in parquet_files:
            hdfs_path = f"{HDFS_DATA_DIR}/processed/{pq_file.name}"
            run_hdfs_command(f"-put -f {pq_file} {hdfs_path}")
            print(f"  ✓ Uploaded: {pq_file.name}")
    
    # Upload models
    models_dir = PROJECT_ROOT / "models"
    if models_dir.exists():
        print(f"\nUploading models to HDFS...")
        hdfs_models_path = f"{HDFS_DATA_DIR}/models"
        run_hdfs_command(f"-put -f {models_dir}/* {hdfs_models_path}/", check=False)
        print(f"  ✓ Uploaded models")
    
    print("\n✓ Upload complete!")


def download_from_hdfs():
    """Download data from HDFS to local."""
    print("\n" + "=" * 60)
    print("Downloading data from HDFS")
    print("=" * 60)
    
    # Create local directories
    (LOCAL_DATA_DIR / "processed").mkdir(parents=True, exist_ok=True)
    
    # Download processed data
    hdfs_processed = f"{HDFS_DATA_DIR}/processed/*"
    local_processed = LOCAL_DATA_DIR / "processed"
    
    run_hdfs_command(f"-get {hdfs_processed} {local_processed}/", check=False)
    
    print("\n✓ Download complete!")


def list_hdfs_contents():
    """List contents of HDFS directories."""
    print("\n" + "=" * 60)
    print("HDFS Directory Contents")
    print("=" * 60)
    
    print("\n--- Raw Data ---")
    run_hdfs_command(f"-ls {HDFS_DATA_DIR}/raw", check=False)
    
    print("\n--- Processed Data ---")
    run_hdfs_command(f"-ls {HDFS_DATA_DIR}/processed", check=False)
    
    print("\n--- Models ---")
    run_hdfs_command(f"-ls {HDFS_DATA_DIR}/models", check=False)
    
    print("\n--- Storage Usage ---")
    run_hdfs_command(f"-du -h {HDFS_DATA_DIR}", check=False)


def clean_hdfs():
    """Clean HDFS directories."""
    print("\n" + "=" * 60)
    print("Cleaning HDFS directories")
    print("=" * 60)
    
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
    
    print("\n--- HDFS Report ---")
    result = subprocess.run("hdfs dfsadmin -report", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout[:2000])  # Print first 2000 chars
        print("\n✓ HDFS is healthy")
    else:
        print(f"✗ HDFS health check failed: {result.stderr}")


def main():
    parser = argparse.ArgumentParser(description="HDFS Utilities for Smart City Traffic")
    parser.add_argument(
        "action",
        choices=["upload", "download", "list", "clean", "health", "setup"],
        help="Action to perform"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("SMART CITY TRAFFIC - HDFS UTILITIES")
    print("=" * 60)
    print(f"HDFS Namenode: {HDFS_NAMENODE}")
    print(f"HDFS Data Dir: {HDFS_DATA_DIR}")
    print(f"Local Data Dir: {LOCAL_DATA_DIR}")
    
    if args.action == "upload":
        upload_to_hdfs()
    elif args.action == "download":
        download_from_hdfs()
    elif args.action == "list":
        list_hdfs_contents()
    elif args.action == "clean":
        clean_hdfs()
    elif args.action == "health":
        check_hdfs_health()
    elif args.action == "setup":
        create_hdfs_directories()
        print("\n✓ HDFS setup complete!")


if __name__ == "__main__":
    main()
