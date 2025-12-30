"""
============================================================
SMART CITY TRAFFIC - SPARK CLUSTER SUBMIT UTILITY
============================================================
Submit Spark jobs to the cluster or run locally.

Usage:
    python src/batch/spark_submit.py <job_name> [--cluster] [--hdfs]
    
Jobs:
    clean       - Run data cleaning
    features    - Run feature engineering  
    train       - Run model training
    all         - Run complete pipeline
============================================================
"""

import argparse
import subprocess
import os
import sys
from pathlib import Path

# Configuration
SPARK_MASTER_LOCAL = "local[*]"
SPARK_MASTER_CLUSTER = "spark://localhost:7077"
HDFS_NAMENODE = "hdfs://localhost:9000"

# Job scripts
JOBS = {
    "clean": "src/batch/data_cleaning_spark.py",
    "features": "src/batch/feature_engineering_spark.py",
    "train": "src/batch/model_training_spark.py"
}

# Spark submit configuration
SPARK_SUBMIT_CONF = {
    "local": {
        "driver_memory": "2g",
        "executor_memory": "2g",
        "executor_cores": "2"
    },
    "cluster": {
        "driver_memory": "2g",
        "executor_memory": "2g",
        "executor_cores": "2",
        "num_executors": "2"
    }
}


def get_spark_submit_path():
    """Find spark-submit executable."""
    # Check common locations
    possible_paths = [
        "spark-submit",  # In PATH
        r"C:\spark\bin\spark-submit.cmd",
        r"C:\Program Files\Spark\bin\spark-submit.cmd",
        "/opt/spark/bin/spark-submit",
        "/usr/local/spark/bin/spark-submit"
    ]
    
    for path in possible_paths:
        try:
            result = subprocess.run([path, "--version"], capture_output=True, text=True)
            if result.returncode == 0 or "version" in result.stderr.lower():
                return path
        except FileNotFoundError:
            continue
    
    # If not found, try using pyspark directly
    print("⚠ spark-submit not found, using pyspark directly")
    return None


def run_with_pyspark(job_script, use_hdfs=False):
    """Run job using pyspark directly (local mode)."""
    cmd = [sys.executable, job_script]
    if use_hdfs:
        cmd.append("--hdfs")
    
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd)


def run_with_spark_submit(job_script, use_cluster=False, use_hdfs=False):
    """Run job using spark-submit."""
    spark_submit = get_spark_submit_path()
    
    if spark_submit is None:
        return run_with_pyspark(job_script, use_hdfs)
    
    mode = "cluster" if use_cluster else "local"
    conf = SPARK_SUBMIT_CONF[mode]
    
    cmd = [
        spark_submit,
        "--master", SPARK_MASTER_CLUSTER if use_cluster else SPARK_MASTER_LOCAL,
        "--driver-memory", conf["driver_memory"],
        "--executor-memory", conf["executor_memory"],
        "--executor-cores", conf["executor_cores"],
    ]
    
    if use_cluster:
        cmd.extend(["--num-executors", conf["num_executors"]])
        cmd.extend(["--deploy-mode", "client"])  # or "cluster" for standalone
    
    # Add HDFS configuration
    if use_hdfs:
        cmd.extend([
            "--conf", f"spark.hadoop.fs.defaultFS={HDFS_NAMENODE}",
            "--conf", "spark.hadoop.dfs.client.use.datanode.hostname=true"
        ])
    
    # Add the job script
    cmd.append(job_script)
    
    # Add script arguments
    if use_hdfs:
        cmd.append("--hdfs")
    
    print(f"\n{'='*60}")
    print(f"SPARK SUBMIT")
    print(f"{'='*60}")
    print(f"Master: {SPARK_MASTER_CLUSTER if use_cluster else SPARK_MASTER_LOCAL}")
    print(f"Script: {job_script}")
    print(f"HDFS: {use_hdfs}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    
    return subprocess.run(cmd)


def run_pipeline(jobs_to_run, use_cluster=False, use_hdfs=False):
    """Run multiple jobs in sequence."""
    backend_dir = Path(__file__).parent.parent.parent
    
    for job_name in jobs_to_run:
        if job_name not in JOBS:
            print(f"⚠ Unknown job: {job_name}")
            continue
        
        job_script = str(backend_dir / JOBS[job_name])
        
        print(f"\n{'#'*60}")
        print(f"# RUNNING: {job_name.upper()}")
        print(f"{'#'*60}")
        
        result = run_with_spark_submit(job_script, use_cluster, use_hdfs)
        
        if result.returncode != 0:
            print(f"\n✗ Job '{job_name}' failed with exit code {result.returncode}")
            return result.returncode
        
        print(f"\n✓ Job '{job_name}' completed successfully")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description='Spark Job Submit Utility')
    parser.add_argument('job', choices=['clean', 'features', 'train', 'all'],
                        help='Job to run')
    parser.add_argument('--cluster', action='store_true', 
                        help='Submit to Spark cluster')
    parser.add_argument('--hdfs', action='store_true',
                        help='Use HDFS for data storage')
    
    args = parser.parse_args()
    
    print("""
============================================================
SMART CITY TRAFFIC - SPARK JOB SUBMIT
============================================================
""")
    
    if args.job == 'all':
        jobs = ['clean', 'features', 'train']
    else:
        jobs = [args.job]
    
    exit_code = run_pipeline(jobs, args.cluster, args.hdfs)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
