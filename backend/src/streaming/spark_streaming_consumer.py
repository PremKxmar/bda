"""
============================================================
SMART CITY TRAFFIC - SPARK STRUCTURED STREAMING CONSUMER
============================================================
Consumes taxi trip events from Kafka using Spark Structured Streaming.
Makes real-time congestion predictions and writes results to HDFS.

Usage:
    python src/streaming/spark_streaming_consumer.py [--hdfs] [--cluster]
    
Options:
    --hdfs      Write output to HDFS instead of local files
    --cluster   Submit to Spark cluster instead of local mode
============================================================
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, window, count, avg, max as spark_max, min as spark_min,
    current_timestamp, lit, when, expr, to_timestamp, date_format,
    struct, to_json
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType,
    TimestampType, LongType
)
from pyspark.ml import PipelineModel

# Configuration
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPIC = 'taxi-trips'
HDFS_NAMENODE = 'hdfs://localhost:9000'
SPARK_MASTER_CLUSTER = 'spark://localhost:7077'

# Output paths
HDFS_OUTPUT_PATH = '/smart-city-traffic/data/streaming'
LOCAL_OUTPUT_PATH = str(Path(__file__).parent.parent.parent / 'data' / 'streaming')

# Checkpoint paths
HDFS_CHECKPOINT_PATH = '/smart-city-traffic/checkpoints/streaming'
LOCAL_CHECKPOINT_PATH = str(Path(__file__).parent.parent.parent / 'data' / 'checkpoints')


def get_taxi_event_schema():
    """Define schema for incoming Kafka taxi events."""
    return StructType([
        StructField("event_id", StringType(), True),
        StructField("event_time", StringType(), True),
        StructField("pickup_datetime", StringType(), True),
        StructField("dropoff_datetime", StringType(), True),
        StructField("pickup_lat", DoubleType(), True),
        StructField("pickup_lon", DoubleType(), True),
        StructField("dropoff_lat", DoubleType(), True),
        StructField("dropoff_lon", DoubleType(), True),
        StructField("trip_distance", DoubleType(), True),
        StructField("duration_minutes", DoubleType(), True),
        StructField("speed_mph", DoubleType(), True),
        StructField("passenger_count", IntegerType(), True),
        StructField("fare_amount", DoubleType(), True),
        StructField("cell_id", StringType(), True),
        StructField("cell_lat", IntegerType(), True),
        StructField("cell_lon", IntegerType(), True),
        StructField("hour", IntegerType(), True),
        StructField("day_of_week", IntegerType(), True),
        StructField("month", IntegerType(), True),
        StructField("year", IntegerType(), True),
        StructField("is_weekend", IntegerType(), True),
        StructField("is_rush_hour", IntegerType(), True),
        StructField("is_night", IntegerType(), True),
        StructField("is_manhattan", IntegerType(), True)
    ])


def create_spark_session(use_cluster=False, use_hdfs=False):
    """Create and configure Spark session for streaming."""
    
    # Windows workaround
    if os.name == 'nt':
        hadoop_home = r"C:\hadoop"
        os.environ['HADOOP_HOME'] = hadoop_home
        os.environ['hadoop.home.dir'] = hadoop_home
    
    app_name = "SmartCityTraffic-StreamingConsumer"
    
    builder = SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.streaming.checkpointLocation", LOCAL_CHECKPOINT_PATH) \
        .config("spark.streaming.stopGracefullyOnShutdown", "true") \
        .config("spark.sql.shuffle.partitions", "10") \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0")
    
    # Cluster or local mode
    if use_cluster:
        builder = builder.master(SPARK_MASTER_CLUSTER)
        print(f"  Mode: Cluster ({SPARK_MASTER_CLUSTER})")
    else:
        builder = builder.master("local[*]")
        builder = builder.config("spark.driver.memory", "2g")
        print("  Mode: Local")
    
    # HDFS configuration
    if use_hdfs:
        builder = builder \
            .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE) \
            .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
        print(f"  HDFS: {HDFS_NAMENODE}")
    
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    
    return spark


def load_ml_model(spark, use_hdfs=False):
    """Load the trained ML model for predictions."""
    try:
        if use_hdfs:
            model_path = f"{HDFS_NAMENODE}/smart-city-traffic/data/models/spark_congestion_model"
        else:
            model_path = str(Path(__file__).parent.parent.parent / 'models' / 'spark_congestion_model')
        
        print(f"  Loading model from: {model_path}")
        model = PipelineModel.load(model_path)
        print("  ✓ Model loaded successfully")
        return model
    except Exception as e:
        print(f"  ⚠ Could not load ML model: {e}")
        print("  → Predictions will use rule-based fallback")
        return None


def create_kafka_stream(spark):
    """Create a streaming DataFrame from Kafka."""
    
    print(f"\n📡 Connecting to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"   Topic: {KAFKA_TOPIC}")
    
    # Read from Kafka
    kafka_df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    # Parse JSON from Kafka value
    schema = get_taxi_event_schema()
    
    parsed_df = kafka_df \
        .select(
            col("key").cast("string").alias("kafka_key"),
            col("value").cast("string").alias("kafka_value"),
            col("timestamp").alias("kafka_timestamp")
        ) \
        .select(
            "kafka_key",
            "kafka_timestamp",
            from_json(col("kafka_value"), schema).alias("data")
        ) \
        .select(
            "kafka_key",
            "kafka_timestamp",
            "data.*"
        )
    
    return parsed_df


def add_congestion_prediction(df, model=None):
    """Add congestion predictions to the streaming DataFrame."""
    
    if model is not None:
        # Use ML model for predictions
        # Note: For streaming, we'd need to apply the model in batches
        # This is a simplified version
        predictions = model.transform(df)
        return predictions.withColumn(
            "congestion_level",
            when(col("prediction") == 0, "Low")
            .when(col("prediction") == 1, "Medium")
            .otherwise("High")
        )
    else:
        # Rule-based fallback when model not available
        return df.withColumn(
            "congestion_level",
            when(
                (col("is_rush_hour") == 1) & (col("is_manhattan") == 1),
                "High"
            ).when(
                (col("is_rush_hour") == 1) | (col("speed_mph") < 10),
                "Medium"
            ).otherwise("Low")
        ).withColumn(
            "prediction",
            when(col("congestion_level") == "Low", 0)
            .when(col("congestion_level") == "Medium", 1)
            .otherwise(2)
        )


def create_aggregations(df):
    """Create windowed aggregations for real-time analytics."""
    
    # Convert event_time to timestamp
    df_with_ts = df.withColumn(
        "event_timestamp",
        to_timestamp(col("event_time"))
    )
    
    # Aggregate by cell_id over 1-minute windows
    windowed_agg = df_with_ts \
        .withWatermark("event_timestamp", "2 minutes") \
        .groupBy(
            window(col("event_timestamp"), "1 minute"),
            col("cell_id"),
            col("cell_lat"),
            col("cell_lon")
        ) \
        .agg(
            count("*").alias("trip_count"),
            avg("speed_mph").alias("avg_speed"),
            avg("trip_distance").alias("avg_distance"),
            spark_max("speed_mph").alias("max_speed"),
            spark_min("speed_mph").alias("min_speed"),
            avg("fare_amount").alias("avg_fare")
        )
    
    # Add congestion level based on aggregates
    windowed_agg = windowed_agg.withColumn(
        "congestion_level",
        when(col("avg_speed") < 8, "High")
        .when(col("avg_speed") < 15, "Medium")
        .otherwise("Low")
    ).withColumn(
        "window_start", col("window.start")
    ).withColumn(
        "window_end", col("window.end")
    ).drop("window")
    
    return windowed_agg


def write_to_console(df, output_mode="append"):
    """Write streaming output to console for debugging."""
    return df \
        .writeStream \
        .outputMode(output_mode) \
        .format("console") \
        .option("truncate", False) \
        .option("numRows", 20) \
        .start()


def write_to_parquet(df, path, checkpoint_path, output_mode="append"):
    """Write streaming output to Parquet files."""
    return df \
        .writeStream \
        .outputMode(output_mode) \
        .format("parquet") \
        .option("path", path) \
        .option("checkpointLocation", checkpoint_path) \
        .partitionBy("cell_id") \
        .start()


def write_to_kafka(df, topic, checkpoint_path):
    """Write streaming output back to Kafka for downstream consumers."""
    
    # Convert to JSON for Kafka
    kafka_df = df.select(
        col("cell_id").alias("key"),
        to_json(struct("*")).alias("value")
    )
    
    return kafka_df \
        .writeStream \
        .outputMode("append") \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("topic", topic) \
        .option("checkpointLocation", checkpoint_path) \
        .start()


def process_batch(df, epoch_id, model=None):
    """Process each micro-batch (for foreachBatch)."""
    if df.count() > 0:
        # Add predictions
        predicted_df = add_congestion_prediction(df, model)
        
        # Show sample
        print(f"\n--- Batch {epoch_id} ---")
        predicted_df.select(
            "cell_id", "hour", "speed_mph", "congestion_level", "is_manhattan"
        ).show(10, truncate=False)


def main():
    parser = argparse.ArgumentParser(description='Spark Structured Streaming Consumer')
    parser.add_argument('--hdfs', action='store_true', help='Write output to HDFS')
    parser.add_argument('--cluster', action='store_true', help='Submit to Spark cluster')
    parser.add_argument('--output', choices=['console', 'parquet', 'kafka', 'all'], 
                        default='console', help='Output sink type')
    parser.add_argument('--duration', type=int, default=None, 
                        help='Duration in seconds (None=infinite)')
    
    args = parser.parse_args()
    
    print("""
============================================================
SMART CITY TRAFFIC - SPARK STRUCTURED STREAMING
============================================================
""")
    
    # Create Spark session
    print("🔧 Creating Spark Session...")
    spark = create_spark_session(use_cluster=args.cluster, use_hdfs=args.hdfs)
    
    print(f"""
============================================================
Spark Session Created
  App Name: {spark.sparkContext.appName}
  Spark Version: {spark.version}
  Master: {spark.sparkContext.master}
============================================================
""")
    
    # Load ML model (optional)
    model = load_ml_model(spark, use_hdfs=args.hdfs)
    
    # Create Kafka stream
    print("\n📥 Creating Kafka Stream...")
    stream_df = create_kafka_stream(spark)
    
    # Add predictions
    predicted_df = add_congestion_prediction(stream_df, model=None)  # Use rule-based for streaming
    
    # Create aggregations
    agg_df = create_aggregations(predicted_df)
    
    # Set up output paths
    if args.hdfs:
        output_path = f"{HDFS_NAMENODE}{HDFS_OUTPUT_PATH}"
        checkpoint_base = f"{HDFS_NAMENODE}{HDFS_CHECKPOINT_PATH}"
    else:
        output_path = LOCAL_OUTPUT_PATH
        checkpoint_base = LOCAL_CHECKPOINT_PATH
        # Create local directories
        os.makedirs(output_path, exist_ok=True)
        os.makedirs(checkpoint_base, exist_ok=True)
    
    print(f"\n📤 Output Configuration:")
    print(f"   Path: {output_path}")
    print(f"   Checkpoint: {checkpoint_base}")
    print(f"   Mode: {args.output}")
    
    # Start streaming queries
    queries = []
    
    if args.output in ['console', 'all']:
        print("\n🖥  Starting Console Output...")
        console_query = agg_df \
            .writeStream \
            .outputMode("update") \
            .format("console") \
            .option("truncate", False) \
            .option("numRows", 10) \
            .trigger(processingTime="10 seconds") \
            .start()
        queries.append(console_query)
    
    if args.output in ['parquet', 'all']:
        print("\n💾 Starting Parquet Output...")
        parquet_query = predicted_df \
            .writeStream \
            .outputMode("append") \
            .format("parquet") \
            .option("path", f"{output_path}/raw_events") \
            .option("checkpointLocation", f"{checkpoint_base}/raw_events") \
            .trigger(processingTime="30 seconds") \
            .start()
        queries.append(parquet_query)
        
        # Also write aggregations
        agg_parquet_query = agg_df \
            .writeStream \
            .outputMode("update") \
            .format("parquet") \
            .option("path", f"{output_path}/aggregations") \
            .option("checkpointLocation", f"{checkpoint_base}/aggregations") \
            .trigger(processingTime="60 seconds") \
            .start()
        queries.append(agg_parquet_query)
    
    if args.output in ['kafka', 'all']:
        print("\n📡 Starting Kafka Output...")
        kafka_query = write_to_kafka(
            agg_df, 
            "traffic-predictions",
            f"{checkpoint_base}/kafka_output"
        )
        queries.append(kafka_query)
    
    print(f"""
============================================================
🚀 STREAMING STARTED
============================================================
   Queries running: {len(queries)}
   Press Ctrl+C to stop...
============================================================
""")
    
    # Wait for queries
    try:
        if args.duration:
            # Run for specified duration
            import time
            time.sleep(args.duration)
            print(f"\n⏱  Duration limit reached ({args.duration}s)")
        else:
            # Run indefinitely
            for query in queries:
                query.awaitTermination()
    
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping streaming...")
    
    finally:
        # Stop all queries
        for query in queries:
            query.stop()
        
        spark.stop()
        print("\n✓ Streaming stopped gracefully")


if __name__ == "__main__":
    main()
