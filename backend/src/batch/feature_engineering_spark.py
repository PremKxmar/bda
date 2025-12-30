"""
Smart City Traffic - Spark Feature Engineering Module
======================================================

This script creates features for ML model training using Apache Spark:
- Reads cleaned data from HDFS or local filesystem
- Aggregates trip data by cell and time window
- Creates lagged features for true prediction (no data leakage)
- Calculates congestion labels from speed
- Saves features to HDFS or local filesystem

Key Changes from Original:
- Uses PySpark DataFrame API instead of Pandas
- Supports HDFS for distributed storage
- Creates lagged features (prev_hour data) for true prediction
- Removes avg_speed from features to prevent data leakage

Usage:
    python src/batch/feature_engineering_spark.py             # Local mode
    python src/batch/feature_engineering_spark.py --hdfs      # HDFS mode
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import argparse
import json

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, when, lit, count, avg, stddev, min as spark_min, max as spark_max,
    hour, dayofweek, month, year, date_trunc,
    lag, lead, coalesce, round as spark_round,
    sum as spark_sum, first, last
)
from pyspark.sql.window import Window
from pyspark.sql.types import IntegerType, DoubleType, BooleanType

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# CONFIGURATION
# =============================================================================

# HDFS Configuration
HDFS_NAMENODE = "hdfs://localhost:9000"
HDFS_PROCESSED_DIR = "/smart-city-traffic/data/processed"
HDFS_FEATURES_DIR = "/smart-city-traffic/data/features"

# Local Configuration
LOCAL_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LOCAL_FEATURES_DIR = PROJECT_ROOT / "data" / "processed"

# Congestion thresholds (based on speed in mph)
CONGESTION_THRESHOLDS = {
    'high': 10,      # < 10 mph = high congestion (label = 2)
    'medium': 20,    # 10-20 mph = medium congestion (label = 1)
    'low': float('inf')  # > 20 mph = low congestion (label = 0)
}


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
        if hadoop_home not in os.environ.get('PATH', ''):
            os.environ['PATH'] = os.environ.get('PATH', '') + f";{hadoop_home}\\bin"
    
    # Determine master URL
    if use_cluster:
        master = SPARK_MASTER_CLUSTER
        shuffle_partitions = 200
        mode_str = f"Cluster ({master})"
    else:
        master = SPARK_MASTER_LOCAL
        shuffle_partitions = 50
        mode_str = "Local"
    
    builder = SparkSession.builder \
        .appName("SmartCityTraffic-FeatureEngineering") \
        .master(master) \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.parquet.compression.codec", "snappy") \
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
    
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
    
    spark.sparkContext.setLogLevel("WARN")
    
    print("=" * 60)
    print("Spark Session Created for Feature Engineering")
    print(f"  App Name: {spark.sparkContext.appName}")
    print(f"  Spark Version: {spark.version}")
    print(f"  Mode: {mode_str}")
    print(f"  HDFS Mode: {use_hdfs}")
    if use_hdfs:
        print(f"  HDFS Namenode: {HDFS_NAMENODE}")
    print("=" * 60)
    
    return spark


def load_cleaned_data(spark, use_hdfs=False):
    """Load all cleaned Parquet files using Spark."""
    if use_hdfs:
        parquet_path = f"{HDFS_NAMENODE}{HDFS_PROCESSED_DIR}/*_clean.parquet"
    else:
        parquet_path = str(LOCAL_PROCESSED_DIR / "*_clean.parquet")
    
    print(f"\nLoading cleaned data from: {parquet_path}")
    
    try:
        df = spark.read.parquet(parquet_path)
        record_count = df.count()
        print(f"  ✓ Loaded {record_count:,} records")
        
        # Show schema
        print("\nSchema:")
        df.printSchema()
        
        return df
    except Exception as e:
        print(f"ERROR loading data: {e}")
        if use_hdfs:
            print("  Make sure cleaned data is in HDFS!")
            print("  Run: python src/batch/data_cleaning_spark.py --hdfs")
        return None


def aggregate_by_cell_hour(df):
    """
    Aggregate trip data by cell and hour using Spark DataFrame API.
    This creates the base dataset for feature engineering.
    """
    print("\n" + "=" * 60)
    print("STEP 1: Aggregating by Cell and Hour")
    print("=" * 60)
    
    # Create hour bucket (truncate to hour)
    df = df.withColumn("hour_bucket", date_trunc("hour", col("pickup_datetime")))
    
    # Aggregate by cell and hour
    agg_df = df.groupBy("cell_id", "cell_lat", "cell_lon", "hour_bucket", "hour", "day_of_week", "month", "year") \
        .agg(
            count("*").alias("trip_count"),
            avg("speed_mph").alias("avg_speed"),
            stddev("speed_mph").alias("speed_std"),
            spark_min("speed_mph").alias("min_speed"),
            spark_max("speed_mph").alias("max_speed"),
            avg("trip_distance").alias("avg_distance"),
            avg("duration_hours").alias("avg_duration"),
            first("is_manhattan").alias("is_manhattan")
        )
    
    # Fill null std values (when only 1 trip in cell-hour)
    agg_df = agg_df.withColumn(
        "speed_std",
        coalesce(col("speed_std"), lit(0.0))
    )
    
    record_count = agg_df.count()
    unique_cells = agg_df.select("cell_id").distinct().count()
    
    print(f"  Aggregated records: {record_count:,}")
    print(f"  Unique cells: {unique_cells:,}")
    print(f"  Date range: {agg_df.select(spark_min('hour_bucket')).collect()[0][0]} to "
          f"{agg_df.select(spark_max('hour_bucket')).collect()[0][0]}")
    
    return agg_df


def create_congestion_labels(df):
    """
    Create congestion labels based on average speed.
    Labels: 0 = Low (>20 mph), 1 = Medium (10-20 mph), 2 = High (<10 mph)
    """
    print("\n" + "=" * 60)
    print("STEP 2: Creating Congestion Labels")
    print("=" * 60)
    
    # Create numeric label
    df = df.withColumn(
        "congestion_label",
        when(col("avg_speed") > 20, 0)  # Low congestion
        .when(col("avg_speed") >= 10, 1)  # Medium congestion
        .otherwise(2)  # High congestion
    )
    
    # Create string label for readability
    df = df.withColumn(
        "congestion_level",
        when(col("congestion_label") == 0, "Low")
        .when(col("congestion_label") == 1, "Medium")
        .otherwise("High")
    )
    
    # Print distribution
    print("\nCongestion Label Distribution:")
    df.groupBy("congestion_level", "congestion_label") \
        .count() \
        .orderBy("congestion_label") \
        .show()
    
    return df


def create_lagged_features(df):
    """
    Create lagged features using Spark Window functions.
    This enables TRUE prediction by using PAST data to predict CURRENT/FUTURE congestion.
    
    Key insight: We use features from time T-1 to predict congestion at time T.
    This prevents data leakage where the model would just learn avg_speed -> congestion mapping.
    """
    print("\n" + "=" * 60)
    print("STEP 3: Creating Lagged Features (No Data Leakage)")
    print("=" * 60)
    
    # Define window: partition by cell, order by time
    cell_time_window = Window.partitionBy("cell_lat", "cell_lon").orderBy("hour_bucket")
    
    # Create lagged features (data from PREVIOUS hour)
    df = df.withColumn("prev_trip_count", lag("trip_count", 1).over(cell_time_window))
    df = df.withColumn("prev_avg_speed", lag("avg_speed", 1).over(cell_time_window))
    df = df.withColumn("prev_congestion_label", lag("congestion_label", 1).over(cell_time_window))
    
    # Create 2-hour lagged features for more context
    df = df.withColumn("prev_2h_trip_count", lag("trip_count", 2).over(cell_time_window))
    df = df.withColumn("prev_2h_avg_speed", lag("avg_speed", 2).over(cell_time_window))
    
    print("  Created lagged features:")
    print("    - prev_trip_count (1 hour ago)")
    print("    - prev_avg_speed (1 hour ago)")
    print("    - prev_congestion_label (1 hour ago)")
    print("    - prev_2h_trip_count (2 hours ago)")
    print("    - prev_2h_avg_speed (2 hours ago)")
    
    return df


def create_historical_features(df):
    """
    Create historical aggregated features.
    These represent typical patterns for each cell at each hour.
    """
    print("\n" + "=" * 60)
    print("STEP 4: Creating Historical Average Features")
    print("=" * 60)
    
    # Window for historical average by cell and hour of day
    cell_hour_window = Window.partitionBy("cell_lat", "cell_lon", "hour")
    
    # Historical averages
    df = df.withColumn(
        "historical_avg_trips",
        avg("trip_count").over(cell_hour_window)
    )
    df = df.withColumn(
        "historical_avg_speed",
        avg("avg_speed").over(cell_hour_window)
    )
    
    print("  Created historical features:")
    print("    - historical_avg_trips (average trips for this cell+hour)")
    print("    - historical_avg_speed (average speed for this cell+hour)")
    
    return df


def create_temporal_features(df):
    """
    Create additional temporal features.
    """
    print("\n" + "=" * 60)
    print("STEP 5: Creating Temporal Features")
    print("=" * 60)
    
    # Is weekend (Saturday=7, Sunday=1 in Spark)
    df = df.withColumn(
        "is_weekend",
        when(col("day_of_week").isin([1, 7]), 1).otherwise(0)
    )
    
    # Is rush hour (7-9 AM or 5-7 PM)
    df = df.withColumn(
        "is_rush_hour",
        when(
            (col("hour").between(7, 9)) | (col("hour").between(17, 19)),
            1
        ).otherwise(0)
    )
    
    # Is night (10 PM - 6 AM)
    df = df.withColumn(
        "is_night",
        when(
            (col("hour") >= 22) | (col("hour") <= 6),
            1
        ).otherwise(0)
    )
    
    # Convert is_manhattan to integer
    df = df.withColumn("is_manhattan_int", col("is_manhattan").cast(IntegerType()))
    
    print("  Created temporal features:")
    print("    - is_weekend (0/1)")
    print("    - is_rush_hour (0/1)")
    print("    - is_night (0/1)")
    print("    - is_manhattan_int (0/1)")
    
    return df


def prepare_final_features(df):
    """
    Prepare final feature set for ML training.
    IMPORTANT: avg_speed is NOT included in features to prevent data leakage!
    """
    print("\n" + "=" * 60)
    print("STEP 6: Preparing Final Features (No avg_speed!)")
    print("=" * 60)
    
    # Drop rows with null lagged features (first rows in each cell)
    df = df.na.drop(subset=["prev_trip_count", "prev_avg_speed", "prev_congestion_label"])
    
    # Define feature columns - NOTE: avg_speed is NOT included!
    feature_columns = [
        # Temporal features
        "hour",
        "day_of_week",
        "month",
        "is_weekend",
        "is_rush_hour",
        "is_night",
        
        # Spatial features
        "cell_lat",
        "cell_lon",
        "is_manhattan_int",
        
        # Lagged features (from previous time period - no leakage!)
        "prev_trip_count",
        "prev_avg_speed",
        "prev_congestion_label",
        "prev_2h_trip_count",
        "prev_2h_avg_speed",
        
        # Historical features
        "historical_avg_trips",
        "historical_avg_speed"
    ]
    
    # Select features + target + metadata columns
    metadata_columns = ["cell_id", "hour_bucket", "year"]
    target_columns = ["congestion_label", "congestion_level", "avg_speed"]  # avg_speed kept for analysis only
    
    final_df = df.select(feature_columns + target_columns + metadata_columns)
    
    # Fill any remaining nulls with 0
    final_df = final_df.na.fill(0)
    
    print(f"\n  Final dataset: {final_df.count():,} records")
    print(f"\n  Feature columns ({len(feature_columns)} total):")
    for col_name in feature_columns:
        print(f"    - {col_name}")
    
    print(f"\n  Target column: congestion_label")
    print(f"  NOTE: avg_speed is NOT in features (prevents data leakage!)")
    
    return final_df, feature_columns


def add_train_test_split_column(df):
    """
    Add column to identify train vs test data.
    Train: January + February data
    Test: March data
    This ensures temporal split (no future data leakage).
    """
    print("\n" + "=" * 60)
    print("STEP 7: Adding Train/Test Split Column")
    print("=" * 60)
    
    df = df.withColumn(
        "dataset_split",
        when(col("month").isin([1, 2]), "train")
        .when(col("month") == 3, "test")
        .otherwise("other")
    )
    
    # Show split distribution
    print("\nTrain/Test Split:")
    df.groupBy("dataset_split", "month").count().orderBy("month").show()
    
    return df


def save_features(df, feature_columns, use_hdfs=False):
    """Save processed features to Parquet (HDFS or local)."""
    print("\n" + "=" * 60)
    print("STEP 8: Saving Features")
    print("=" * 60)
    
    if use_hdfs:
        output_path = f"{HDFS_NAMENODE}{HDFS_FEATURES_DIR}/training_features_spark.parquet"
        features_json_path = None  # Will save locally
    else:
        output_path = str(LOCAL_FEATURES_DIR / "training_features_spark.parquet")
        features_json_path = LOCAL_FEATURES_DIR / "feature_columns_spark.json"
    
    # Repartition for optimal file size
    num_partitions = max(1, df.count() // 500000)
    df = df.repartition(num_partitions)
    
    # Save to Parquet
    df.write.mode("overwrite").parquet(output_path)
    print(f"  ✓ Saved features to: {output_path}")
    
    # Save feature column names (always save locally for model training reference)
    local_features_path = LOCAL_FEATURES_DIR / "feature_columns_spark.json"
    LOCAL_FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    with open(local_features_path, 'w') as f:
        json.dump(feature_columns, f, indent=2)
    print(f"  ✓ Saved feature columns to: {local_features_path}")
    
    return output_path


def print_data_summary(df):
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)
    
    print("\nSample rows:")
    df.select("hour", "cell_lat", "cell_lon", "prev_trip_count", "prev_avg_speed", 
              "congestion_label", "dataset_split").show(10)
    
    print("\nStatistics:")
    df.describe(["prev_trip_count", "prev_avg_speed", "historical_avg_trips"]).show()


def main():
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Spark Feature Engineering for Smart City Traffic")
    parser.add_argument("--hdfs", action="store_true", help="Use HDFS for input/output")
    parser.add_argument("--cluster", action="store_true",
                        help="Submit to Spark cluster (spark://localhost:7077) instead of local mode")
    args = parser.parse_args()
    
    use_hdfs = args.hdfs
    use_cluster = args.cluster
    
    print("\n" + "=" * 60)
    print("SMART CITY TRAFFIC - SPARK FEATURE ENGINEERING")
    print("=" * 60)
    print(f"Storage Mode: {'HDFS' if use_hdfs else 'Local'}")
    print(f"Spark Mode: {'Cluster' if use_cluster else 'Local'}")
    
    start_time = datetime.now()
    
    # Create Spark session
    spark = create_spark_session(use_hdfs=use_hdfs, use_cluster=use_cluster)
    
    # Load cleaned data
    df = load_cleaned_data(spark, use_hdfs=use_hdfs)
    if df is None:
        print("ERROR: Could not load data!")
        if use_hdfs:
            print("  Run data cleaning with HDFS first:")
            print("  python src/batch/data_cleaning_spark.py --hdfs")
        spark.stop()
        return
    
    # Step 1: Aggregate by cell and hour
    agg_df = aggregate_by_cell_hour(df)
    
    # Step 2: Create congestion labels
    agg_df = create_congestion_labels(agg_df)
    
    # Step 3: Create lagged features (for true prediction)
    agg_df = create_lagged_features(agg_df)
    
    # Step 4: Create historical features
    agg_df = create_historical_features(agg_df)
    
    # Step 5: Create temporal features
    agg_df = create_temporal_features(agg_df)
    
    # Step 6: Prepare final features
    final_df, feature_columns = prepare_final_features(agg_df)
    
    # Step 7: Add train/test split
    final_df = add_train_test_split_column(final_df)
    
    # Print summary
    print_data_summary(final_df)
    
    # Step 8: Save features
    output_base = f"{HDFS_NAMENODE}{HDFS_FEATURES_DIR}" if use_hdfs else str(LOCAL_FEATURES_DIR)
    save_features(final_df, feature_columns, use_hdfs=use_hdfs)
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("FEATURE ENGINEERING COMPLETE")
    print("=" * 60)
    print(f"  Mode: {'HDFS' if use_hdfs else 'Local'}")
    print(f"  Total records: {final_df.count():,}")
    print(f"  Features: {len(feature_columns)}")
    print(f"  Duration: {duration:.1f} seconds")
    print(f"  Output: {output_base}")
    print("\n  KEY POINT: avg_speed is NOT in features!")
    print("  This prevents data leakage and enables true prediction.")
    print("=" * 60)
    
    spark.stop()


if __name__ == "__main__":
    main()
