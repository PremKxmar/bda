"""
Smart City Traffic - Spark and Kafka Configuration
===================================================

Centralized configuration for Spark cluster, HDFS, and Kafka.
This module provides consistent settings across all scripts.

Usage:
    from config.spark_config import create_spark_session, KAFKA_CONFIG
"""

import os
from pathlib import Path

# =============================================================================
# FILE PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = Path(r"c:\sem6-real\bigdata\vscode")  # Local raw data location

# =============================================================================
# SPARK CONFIGURATION
# =============================================================================

SPARK_CONFIG = {
    # Master URLs
    "master_local": "local[*]",
    "master_cluster": "spark://localhost:7077",
    
    # Default memory settings
    "driver_memory": "2g",
    "executor_memory": "2g",
    
    # Shuffle partitions (lower for local, higher for cluster)
    "shuffle_partitions_local": 20,
    "shuffle_partitions_cluster": 200,
    
    # Other settings
    "parquet_compression": "snappy",
    "max_result_size": "1g",
}

# =============================================================================
# HDFS CONFIGURATION
# =============================================================================

HDFS_CONFIG = {
    "namenode": "hdfs://localhost:9000",
    "raw_dir": "/smart-city-traffic/data/raw",
    "processed_dir": "/smart-city-traffic/data/processed",
    "models_dir": "/smart-city-traffic/data/models",
    "streaming_dir": "/smart-city-traffic/data/streaming",
    "checkpoints_dir": "/smart-city-traffic/checkpoints",
}

# =============================================================================
# KAFKA CONFIGURATION
# =============================================================================

KAFKA_CONFIG = {
    # Broker settings
    "bootstrap_servers": "localhost:9092",
    "bootstrap_servers_docker": "kafka:29092",
    
    # Topic names (unified)
    "topic_events": "traffic-events",         # Producer -> Consumer
    "topic_predictions": "traffic-predictions", # Consumer -> API
    "topic_alerts": "traffic-alerts",          # High congestion alerts
    
    # Consumer settings
    "consumer_group": "traffic-consumer-group",
    "auto_offset_reset": "latest",
    
    # Producer settings
    "events_per_second": 500,
    "batch_size": 100,
}

# =============================================================================
# NYC GEOGRAPHIC BOUNDS
# =============================================================================

NYC_BOUNDS = {
    "lat_min": 40.4774,
    "lat_max": 40.9176,
    "lon_min": -74.2591,
    "lon_max": -73.7004,
    "cell_size": 0.01,  # Approximately 1km x 1km
}

# Manhattan approximate bounds
MANHATTAN_BOUNDS = {
    "lat_min": 40.70,
    "lat_max": 40.88,
    "lon_min": -74.02,
    "lon_max": -73.93,
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def setup_windows_hadoop():
    """Set up Hadoop environment for Windows."""
    if os.name == 'nt':  # Windows
        hadoop_home = r"C:\hadoop"
        os.environ['HADOOP_HOME'] = hadoop_home
        os.environ['hadoop.home.dir'] = hadoop_home
        if hadoop_home not in os.environ.get('PATH', ''):
            os.environ['PATH'] = os.environ.get('PATH', '') + f";{hadoop_home}\\bin"


def create_spark_session(
    app_name: str,
    use_cluster: bool = False,
    use_hdfs: bool = False,
    driver_memory: str = None,
    executor_memory: str = None,
    enable_kafka: bool = False
):
    """
    Create and configure a Spark session.
    
    Args:
        app_name: Name of the Spark application
        use_cluster: If True, connect to Spark cluster; else local mode
        use_hdfs: If True, configure HDFS as default filesystem
        driver_memory: Override default driver memory (e.g., "4g")
        executor_memory: Override default executor memory (e.g., "4g")
        enable_kafka: If True, add Kafka Spark SQL package
        
    Returns:
        SparkSession: Configured Spark session
    """
    from pyspark.sql import SparkSession
    
    # Windows setup
    setup_windows_hadoop()
    
    # Determine master
    if use_cluster:
        master = SPARK_CONFIG["master_cluster"]
        shuffle_partitions = SPARK_CONFIG["shuffle_partitions_cluster"]
        mode_str = f"Cluster ({master})"
    else:
        master = SPARK_CONFIG["master_local"]
        shuffle_partitions = SPARK_CONFIG["shuffle_partitions_local"]
        mode_str = "Local"
    
    # Memory settings
    driver_mem = driver_memory or SPARK_CONFIG["driver_memory"]
    executor_mem = executor_memory or SPARK_CONFIG["executor_memory"]
    
    # Build session
    builder = SparkSession.builder \
        .appName(app_name) \
        .master(master) \
        .config("spark.driver.memory", driver_mem) \
        .config("spark.executor.memory", executor_mem) \
        .config("spark.sql.parquet.compression.codec", SPARK_CONFIG["parquet_compression"]) \
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions)) \
        .config("spark.driver.maxResultSize", SPARK_CONFIG["max_result_size"])
    
    # HDFS configuration
    if use_hdfs:
        builder = builder \
            .config("spark.hadoop.fs.defaultFS", HDFS_CONFIG["namenode"]) \
            .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
    
    # Kafka configuration (for Spark Structured Streaming)
    if enable_kafka:
        # Use Spark 3.5.0 compatible Kafka package
        builder = builder \
            .config("spark.jars.packages", 
                    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0")
    
    # Add extra configs for cluster mode
    if use_cluster:
        builder = builder \
            .config("spark.submit.deployMode", "client") \
            .config("spark.dynamicAllocation.enabled", "false")
    
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    
    # Print session info
    print("=" * 60)
    print("Spark Session Created")
    print(f"  App Name: {app_name}")
    print(f"  Spark Version: {spark.version}")
    print(f"  Mode: {mode_str}")
    print(f"  Driver Memory: {driver_mem}")
    print(f"  Executor Memory: {executor_mem}")
    if use_hdfs:
        print(f"  HDFS: {HDFS_CONFIG['namenode']}")
    if enable_kafka:
        print(f"  Kafka: {KAFKA_CONFIG['bootstrap_servers']}")
    print("=" * 60)
    
    return spark


def get_kafka_bootstrap_servers(use_docker_internal: bool = False) -> str:
    """
    Get Kafka bootstrap servers URL.
    
    Args:
        use_docker_internal: If True, return Docker internal network address
        
    Returns:
        Bootstrap servers connection string
    """
    if use_docker_internal:
        return KAFKA_CONFIG["bootstrap_servers_docker"]
    return KAFKA_CONFIG["bootstrap_servers"]


def get_hdfs_path(path_type: str) -> str:
    """
    Get full HDFS path for a given path type.
    
    Args:
        path_type: One of 'raw', 'processed', 'models', 'streaming', 'checkpoints'
        
    Returns:
        Full HDFS path (e.g., hdfs://localhost:9000/smart-city-traffic/data/raw)
    """
    path_map = {
        "raw": HDFS_CONFIG["raw_dir"],
        "processed": HDFS_CONFIG["processed_dir"],
        "models": HDFS_CONFIG["models_dir"],
        "streaming": HDFS_CONFIG["streaming_dir"],
        "checkpoints": HDFS_CONFIG["checkpoints_dir"],
    }
    
    if path_type not in path_map:
        raise ValueError(f"Unknown path type: {path_type}. Choose from {list(path_map.keys())}")
    
    return f"{HDFS_CONFIG['namenode']}{path_map[path_type]}"


# =============================================================================
# STREAMING EVENT SCHEMA
# =============================================================================

def get_traffic_event_schema():
    """
    Get the unified schema for traffic events (Kafka messages).
    
    This schema is used by both the Kafka producer and Spark Structured Streaming consumer.
    """
    from pyspark.sql.types import (
        StructType, StructField, StringType, DoubleType, IntegerType
    )
    
    return StructType([
        # Event metadata
        StructField("event_id", StringType(), True),
        StructField("timestamp", StringType(), True),
        StructField("vehicle_id", StringType(), True),
        
        # Location
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("cell_id", StringType(), True),
        StructField("cell_lat", IntegerType(), True),
        StructField("cell_lon", IntegerType(), True),
        
        # Trip info
        StructField("speed", DoubleType(), True),
        StructField("heading", IntegerType(), True),
        StructField("trip_id", StringType(), True),
        
        # Temporal features
        StructField("hour", IntegerType(), True),
        StructField("day_of_week", IntegerType(), True),
        StructField("is_weekend", IntegerType(), True),
        StructField("is_rush_hour", IntegerType(), True),
        StructField("is_night", IntegerType(), True),
        StructField("is_manhattan", IntegerType(), True),
    ])


if __name__ == "__main__":
    # Test configuration
    print("Smart City Traffic - Configuration Test")
    print("=" * 60)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Data Directory: {DATA_DIR}")
    print(f"Models Directory: {MODELS_DIR}")
    print()
    print("Spark Config:", SPARK_CONFIG)
    print()
    print("HDFS Config:", HDFS_CONFIG)
    print()
    print("Kafka Config:", KAFKA_CONFIG)
