"""
Smart City Traffic - Spark Data Cleaning Module
================================================

This script cleans the raw NYC Taxi data using Apache Spark:
- Reads data from HDFS or local filesystem
- Removes invalid coordinates
- Filters outliers in speed/distance
- Handles missing values
- Saves cleaned data as Parquet to HDFS or local

Usage:
    python src/batch/data_cleaning_spark.py             # Local mode
    python src/batch/data_cleaning_spark.py --hdfs      # HDFS mode
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import argparse

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, unix_timestamp, round as spark_round,
    hour, dayofweek, month, year, to_timestamp,
    lit, count, avg, min as spark_min, max as spark_max
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    IntegerType, TimestampType
)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# CONFIGURATION
# =============================================================================

# HDFS Configuration
HDFS_NAMENODE = "hdfs://localhost:9000"
HDFS_RAW_DIR = "/smart-city-traffic/data/raw"
HDFS_PROCESSED_DIR = "/smart-city-traffic/data/processed"

# Local Configuration
LOCAL_RAW_DIR = Path(r"c:\sem6-real\bigdata\vscode")
LOCAL_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# NYC Geographic bounds
NYC_LAT_MIN = 40.4774
NYC_LAT_MAX = 40.9176
NYC_LON_MIN = -74.2591
NYC_LON_MAX = -73.7004

# Grid cell size (approximately 1km x 1km)
CELL_SIZE = 0.01

# Global flag for HDFS mode
USE_HDFS = False

# Spark cluster configuration
SPARK_MASTER_LOCAL = "local[*]"
SPARK_MASTER_CLUSTER = "spark://localhost:7077"


def create_spark_session(use_hdfs=False, use_cluster=False):
    """
    Create and configure Spark session.
    
    Args:
        use_hdfs: If True, configure HDFS as default filesystem
        use_cluster: If True, connect to Spark cluster; else local mode
    """
    import os
    
    # Windows workaround: Set Hadoop home for winutils.exe
    if os.name == 'nt':  # Windows
        hadoop_home = r"C:\hadoop"
        os.environ['HADOOP_HOME'] = hadoop_home
        os.environ['hadoop.home.dir'] = hadoop_home
        # Add to PATH if not present
        if hadoop_home not in os.environ.get('PATH', ''):
            os.environ['PATH'] = os.environ.get('PATH', '') + f";{hadoop_home}\\bin"
    
    # Determine master URL
    if use_cluster:
        master = SPARK_MASTER_CLUSTER
        shuffle_partitions = 200  # More partitions for cluster
        mode_str = f"Cluster ({master})"
    else:
        master = SPARK_MASTER_LOCAL
        shuffle_partitions = 20  # Fewer partitions for local
        mode_str = "Local"
    
    builder = SparkSession.builder \
        .appName("SmartCityTraffic-DataCleaning") \
        .master(master) \
        .config("spark.driver.memory", "2g") \
        .config("spark.executor.memory", "2g") \
        .config("spark.sql.parquet.compression.codec", "snappy") \
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions)) \
        .config("spark.driver.maxResultSize", "1g")
    
    # Add HDFS configuration if using HDFS
    if use_hdfs:
        builder = builder \
            .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE) \
            .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
    
    # Add cluster-specific configs
    if use_cluster:
        builder = builder \
            .config("spark.submit.deployMode", "client") \
            .config("spark.dynamicAllocation.enabled", "false")
    
    spark = builder.getOrCreate()
    
    # Set log level
    spark.sparkContext.setLogLevel("WARN")
    
    print("=" * 60)
    print("Spark Session Created")
    print(f"  App Name: {spark.sparkContext.appName}")
    print(f"  Spark Version: {spark.version}")
    print(f"  Mode: {mode_str}")
    print(f"  HDFS Mode: {use_hdfs}")
    if use_hdfs:
        print(f"  HDFS Namenode: {HDFS_NAMENODE}")
    print("=" * 60)
    
    return spark


def get_taxi_files_local():
    """Find all taxi CSV files in the local raw data directory."""
    files = list(LOCAL_RAW_DIR.glob('yellow_tripdata_*.csv'))
    print(f"\nFound {len(files)} taxi data files (local):")
    for f in files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  - {f.name}: {size_mb:.2f} MB")
    return [str(f) for f in files]


def get_taxi_files_hdfs(spark):
    """Find all taxi CSV files in HDFS."""
    print(f"\nLooking for taxi data files in HDFS: {HDFS_RAW_DIR}")
    
    # Use Spark to list HDFS directory
    hadoop_conf = spark.sparkContext._jsc.hadoopConfiguration()
    fs = spark.sparkContext._jvm.org.apache.hadoop.fs.FileSystem.get(
        spark.sparkContext._jvm.java.net.URI(HDFS_NAMENODE),
        hadoop_conf
    )
    
    path = spark.sparkContext._jvm.org.apache.hadoop.fs.Path(HDFS_RAW_DIR)
    
    files = []
    try:
        file_statuses = fs.listStatus(path)
        for status in file_statuses:
            file_path = str(status.getPath())
            if "yellow_tripdata" in file_path:
                files.append(file_path)
                print(f"  - {file_path}")
    except Exception as e:
        print(f"  Error listing HDFS: {e}")
        print(f"  Make sure data is uploaded to HDFS first!")
    
    print(f"\nFound {len(files)} taxi data files in HDFS")
    return files


def load_raw_data(spark, file_path, use_hdfs=False):
    """Load raw CSV data into Spark DataFrame."""
    print(f"\nLoading: {file_path}")
    
    # Define schema for NYC Taxi data (2015-2016 format)
    schema = StructType([
        StructField("VendorID", IntegerType(), True),
        StructField("tpep_pickup_datetime", StringType(), True),
        StructField("tpep_dropoff_datetime", StringType(), True),
        StructField("passenger_count", IntegerType(), True),
        StructField("trip_distance", DoubleType(), True),
        StructField("pickup_longitude", DoubleType(), True),
        StructField("pickup_latitude", DoubleType(), True),
        StructField("RatecodeID", IntegerType(), True),
        StructField("store_and_fwd_flag", StringType(), True),
        StructField("dropoff_longitude", DoubleType(), True),
        StructField("dropoff_latitude", DoubleType(), True),
        StructField("payment_type", IntegerType(), True),
        StructField("fare_amount", DoubleType(), True),
        StructField("extra", DoubleType(), True),
        StructField("mta_tax", DoubleType(), True),
        StructField("tip_amount", DoubleType(), True),
        StructField("tolls_amount", DoubleType(), True),
        StructField("improvement_surcharge", DoubleType(), True),
        StructField("total_amount", DoubleType(), True)
    ])
    
    # Read CSV with schema
    df = spark.read \
        .option("header", "true") \
        .option("mode", "DROPMALFORMED") \
        .schema(schema) \
        .csv(file_path)
    
    initial_count = df.count()
    print(f"  Loaded {initial_count:,} rows")
    
    return df


def clean_and_transform(df):
    """Apply cleaning transformations using Spark DataFrame API."""
    print("\nApplying cleaning transformations...")
    
    # Step 1: Rename columns to standard names
    df = df.withColumnRenamed("tpep_pickup_datetime", "pickup_datetime") \
           .withColumnRenamed("tpep_dropoff_datetime", "dropoff_datetime") \
           .withColumnRenamed("pickup_longitude", "pickup_lon") \
           .withColumnRenamed("pickup_latitude", "pickup_lat") \
           .withColumnRenamed("dropoff_longitude", "dropoff_lon") \
           .withColumnRenamed("dropoff_latitude", "dropoff_lat")
    
    # Step 2: Convert datetime strings to timestamps
    df = df.withColumn("pickup_datetime", to_timestamp(col("pickup_datetime"), "yyyy-MM-dd HH:mm:ss")) \
           .withColumn("dropoff_datetime", to_timestamp(col("dropoff_datetime"), "yyyy-MM-dd HH:mm:ss"))
    
    # Step 3: Filter invalid coordinates (within NYC bounds)
    df = df.filter(
        (col("pickup_lat").between(NYC_LAT_MIN, NYC_LAT_MAX)) &
        (col("pickup_lon").between(NYC_LON_MIN, NYC_LON_MAX)) &
        (col("dropoff_lat").between(NYC_LAT_MIN, NYC_LAT_MAX)) &
        (col("dropoff_lon").between(NYC_LON_MIN, NYC_LON_MAX))
    )
    print(f"  After coordinate filter: {df.count():,} rows")
    
    # Step 4: Calculate trip duration in hours
    df = df.withColumn(
        "duration_seconds",
        unix_timestamp(col("dropoff_datetime")) - unix_timestamp(col("pickup_datetime"))
    )
    df = df.withColumn("duration_hours", col("duration_seconds") / 3600.0)
    
    # Step 5: Filter invalid durations (between 1 minute and 3 hours)
    df = df.filter(
        (col("duration_seconds") >= 60) &  # At least 1 minute
        (col("duration_seconds") <= 10800)  # At most 3 hours
    )
    print(f"  After duration filter: {df.count():,} rows")
    
    # Step 6: Filter invalid distances (between 0.1 and 100 miles)
    df = df.filter(
        (col("trip_distance") >= 0.1) &
        (col("trip_distance") <= 100)
    )
    print(f"  After distance filter: {df.count():,} rows")
    
    # Step 7: Calculate speed in mph
    df = df.withColumn(
        "speed_mph",
        spark_round(col("trip_distance") / col("duration_hours"), 2)
    )
    
    # Step 8: Filter unrealistic speeds (between 1 and 60 mph)
    df = df.filter(
        (col("speed_mph") >= 1) &
        (col("speed_mph") <= 60)
    )
    print(f"  After speed filter: {df.count():,} rows")
    
    # Step 9: Create grid cell indices
    df = df.withColumn(
        "cell_lat",
        ((col("pickup_lat") - lit(NYC_LAT_MIN)) / lit(CELL_SIZE)).cast(IntegerType())
    )
    df = df.withColumn(
        "cell_lon",
        ((col("pickup_lon") - lit(NYC_LON_MIN)) / lit(CELL_SIZE)).cast(IntegerType())
    )
    df = df.withColumn(
        "cell_id",
        concat_ws("_", lit("cell"), col("cell_lat"), col("cell_lon"))
    )
    
    # Step 10: Extract temporal features
    df = df.withColumn("hour", hour(col("pickup_datetime"))) \
           .withColumn("day_of_week", dayofweek(col("pickup_datetime"))) \
           .withColumn("month", month(col("pickup_datetime"))) \
           .withColumn("year", year(col("pickup_datetime")))
    
    # Step 11: Create is_manhattan flag (approximate bounds)
    df = df.withColumn(
        "is_manhattan",
        when(
            (col("pickup_lat").between(40.70, 40.88)) &
            (col("pickup_lon").between(-74.02, -73.93)),
            True
        ).otherwise(False)
    )
    
    # Step 12: Select final columns
    final_columns = [
        "pickup_datetime", "dropoff_datetime",
        "pickup_lat", "pickup_lon",
        "dropoff_lat", "dropoff_lon",
        "trip_distance", "duration_hours", "speed_mph",
        "passenger_count", "fare_amount", "total_amount",
        "cell_id", "cell_lat", "cell_lon",
        "hour", "day_of_week", "month", "year",
        "is_manhattan"
    ]
    
    df = df.select(final_columns)
    
    return df


# Need to import concat_ws
from pyspark.sql.functions import concat_ws


def print_statistics(df, label):
    """Print statistics about the DataFrame."""
    print(f"\n{label} Statistics:")
    print(f"  Total records: {df.count():,}")
    print(f"  Unique cells: {df.select('cell_id').distinct().count():,}")
    
    # Speed statistics
    speed_stats = df.agg(
        spark_min("speed_mph").alias("min_speed"),
        spark_max("speed_mph").alias("max_speed"),
        avg("speed_mph").alias("avg_speed")
    ).collect()[0]
    
    print(f"  Speed (mph): min={speed_stats['min_speed']:.1f}, "
          f"max={speed_stats['max_speed']:.1f}, avg={speed_stats['avg_speed']:.1f}")
    
    # Trips per hour distribution
    print("\n  Trips by hour (sample):")
    hour_counts = df.groupBy("hour").count().orderBy("hour").collect()
    for row in hour_counts[:6]:
        print(f"    Hour {row['hour']:02d}: {row['count']:,}")


def save_to_parquet(df, output_path, use_hdfs=False):
    """Save DataFrame to Parquet format (HDFS or local)."""
    print(f"\nSaving to: {output_path}")
    
    # Repartition for optimal file sizes (aim for ~128MB per partition)
    num_partitions = max(1, df.count() // 500000)
    df = df.repartition(num_partitions)
    
    # Save as Parquet with snappy compression
    df.write \
        .mode("overwrite") \
        .parquet(output_path)
    
    print(f"  ✓ Saved successfully!")


def main():
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Spark Data Cleaning for Smart City Traffic")
    parser.add_argument("--hdfs", action="store_true", help="Use HDFS for input/output")
    parser.add_argument("--cluster", action="store_true", 
                        help="Submit to Spark cluster (spark://localhost:7077) instead of local mode")
    args = parser.parse_args()
    
    use_hdfs = args.hdfs
    use_cluster = args.cluster
    
    print("\n" + "=" * 60)
    print("SMART CITY TRAFFIC - SPARK DATA CLEANING")
    print("=" * 60)
    print(f"Storage Mode: {'HDFS' if use_hdfs else 'Local'}")
    print(f"Spark Mode: {'Cluster' if use_cluster else 'Local'}")
    
    start_time = datetime.now()
    
    # Create Spark session
    spark = create_spark_session(use_hdfs=use_hdfs, use_cluster=use_cluster)
    
    # Get taxi files based on mode
    if use_hdfs:
        taxi_files = get_taxi_files_hdfs(spark)
        output_base = f"{HDFS_NAMENODE}{HDFS_PROCESSED_DIR}"
    else:
        taxi_files = get_taxi_files_local()
        output_base = str(LOCAL_PROCESSED_DIR)
        # Ensure local output directory exists
        LOCAL_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    if not taxi_files:
        print("ERROR: No taxi data files found!")
        if use_hdfs:
            print("  Make sure to upload data to HDFS first:")
            print("  python src/batch/hdfs_utils.py upload")
        spark.stop()
        return
    
    # Process each file
    total_records = 0
    for file_path in taxi_files:
        print(f"\n{'=' * 60}")
        file_name = file_path.split("/")[-1] if "/" in file_path else file_path.split("\\")[-1]
        print(f"Processing: {file_name}")
        print("=" * 60)
        
        # Load raw data
        df = load_raw_data(spark, file_path, use_hdfs)
        
        # Clean and transform
        df_clean = clean_and_transform(df)
        
        # Print statistics
        print_statistics(df_clean, "Cleaned Data")
        
        # Generate output path
        # Extract base name without extension
        base_name = file_name.replace(".csv", "").replace(".parquet", "")
        output_name = f"{base_name}_clean.parquet"
        
        if use_hdfs:
            output_path = f"{output_base}/{output_name}"
        else:
            output_path = str(LOCAL_PROCESSED_DIR / output_name)
        
        # Save to Parquet
        save_to_parquet(df_clean, output_path, use_hdfs)
        
        total_records += df_clean.count()
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("CLEANING COMPLETE")
    print("=" * 60)
    print(f"  Mode: {'HDFS' if use_hdfs else 'Local'}")
    print(f"  Files processed: {len(taxi_files)}")
    print(f"  Total records: {total_records:,}")
    print(f"  Duration: {duration:.1f} seconds")
    print(f"  Output directory: {output_base}")
    print("=" * 60)
    
    # Stop Spark session
    spark.stop()


if __name__ == "__main__":
    main()
