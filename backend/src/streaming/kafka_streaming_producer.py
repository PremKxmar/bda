"""
============================================================
SMART CITY TRAFFIC - KAFKA STREAMING PRODUCER
============================================================
Reads taxi data from HDFS and streams to Kafka topic.
Simulates real-time taxi trip events.

Usage:
    python src/streaming/kafka_streaming_producer.py [--hdfs] [--rate RATE]
    
Options:
    --hdfs      Read data from HDFS instead of local files
    --rate      Events per second (default: 100)
    --topic     Kafka topic name (default: taxi-trips)
============================================================
"""

import json
import time
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import KafkaError
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Configuration
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
DEFAULT_TOPIC = 'taxi-trips'
DEFAULT_RATE = 100  # events per second

# NYC Geographic bounds
NYC_LAT_MIN = 40.4774
NYC_LAT_MAX = 40.9176
NYC_LON_MIN = -74.2591
NYC_LON_MAX = -73.7004

# Grid cell size
CELL_SIZE = 0.01


def create_kafka_producer():
    """Create and return a Kafka producer."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            batch_size=16384,
            linger_ms=10,
            buffer_memory=33554432
        )
        print(f"✓ Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
        return producer
    except KafkaError as e:
        print(f"✗ Failed to connect to Kafka: {e}")
        raise


def generate_cell_id(lat, lon):
    """Generate grid cell ID from coordinates."""
    cell_lat = int((lat - NYC_LAT_MIN) / CELL_SIZE)
    cell_lon = int((lon - NYC_LON_MIN) / CELL_SIZE)
    return f"{cell_lat}_{cell_lon}", cell_lat, cell_lon


def generate_synthetic_trip():
    """Generate a synthetic taxi trip event."""
    # Random pickup location in NYC
    pickup_lat = random.uniform(NYC_LAT_MIN, NYC_LAT_MAX)
    pickup_lon = random.uniform(NYC_LON_MIN, NYC_LON_MAX)
    
    # Random dropoff (within reasonable distance)
    dropoff_lat = pickup_lat + random.uniform(-0.05, 0.05)
    dropoff_lon = pickup_lon + random.uniform(-0.05, 0.05)
    
    # Clamp to NYC bounds
    dropoff_lat = max(NYC_LAT_MIN, min(NYC_LAT_MAX, dropoff_lat))
    dropoff_lon = max(NYC_LON_MIN, min(NYC_LON_MAX, dropoff_lon))
    
    # Trip details
    trip_distance = random.uniform(0.5, 15.0)
    duration_minutes = random.uniform(5, 60)
    speed_mph = (trip_distance / (duration_minutes / 60)) if duration_minutes > 0 else 10
    speed_mph = max(1, min(60, speed_mph))
    
    # Timestamps
    now = datetime.now()
    pickup_time = now - timedelta(minutes=duration_minutes)
    
    # Generate cell ID
    cell_id, cell_lat, cell_lon = generate_cell_id(pickup_lat, pickup_lon)
    
    # Time features
    hour = now.hour
    day_of_week = now.weekday() + 1
    is_weekend = 1 if day_of_week >= 6 else 0
    is_rush_hour = 1 if hour in [7, 8, 9, 17, 18, 19] else 0
    is_night = 1 if hour >= 22 or hour <= 5 else 0
    is_manhattan = 1 if (40.7 <= pickup_lat <= 40.82 and -74.02 <= pickup_lon <= -73.93) else 0
    
    return {
        'event_id': f"trip_{int(time.time()*1000)}_{random.randint(1000,9999)}",
        'event_time': now.isoformat(),
        'pickup_datetime': pickup_time.isoformat(),
        'dropoff_datetime': now.isoformat(),
        'pickup_lat': round(pickup_lat, 6),
        'pickup_lon': round(pickup_lon, 6),
        'dropoff_lat': round(dropoff_lat, 6),
        'dropoff_lon': round(dropoff_lon, 6),
        'trip_distance': round(trip_distance, 2),
        'duration_minutes': round(duration_minutes, 2),
        'speed_mph': round(speed_mph, 2),
        'passenger_count': random.randint(1, 4),
        'fare_amount': round(random.uniform(5, 100), 2),
        'cell_id': cell_id,
        'cell_lat': cell_lat,
        'cell_lon': cell_lon,
        'hour': hour,
        'day_of_week': day_of_week,
        'month': now.month,
        'year': now.year,
        'is_weekend': is_weekend,
        'is_rush_hour': is_rush_hour,
        'is_night': is_night,
        'is_manhattan': is_manhattan
    }


def load_historical_data_spark(use_hdfs=False):
    """Load historical data using Spark to replay as stream."""
    try:
        from pyspark.sql import SparkSession
        
        builder = SparkSession.builder \
            .appName("KafkaProducer-DataLoader") \
            .config("spark.driver.memory", "2g")
        
        if use_hdfs:
            builder = builder \
                .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:9000") \
                .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
        
        spark = builder.master("local[2]").getOrCreate()
        spark.sparkContext.setLogLevel("WARN")
        
        if use_hdfs:
            path = "hdfs://localhost:9000/smart-city-traffic/data/processed/*_clean.parquet"
        else:
            path = str(Path(__file__).parent.parent.parent / "data" / "processed" / "*_clean.parquet")
        
        print(f"Loading historical data from: {path}")
        df = spark.read.parquet(path)
        
        # Sample for streaming (don't load all 46M records)
        sample_df = df.sample(fraction=0.001, seed=42)
        data = sample_df.collect()
        
        spark.stop()
        
        print(f"✓ Loaded {len(data)} historical records for replay")
        return data
        
    except Exception as e:
        print(f"⚠ Could not load historical data: {e}")
        print("  Using synthetic data generation instead")
        return None


def replay_historical_trip(row):
    """Convert a historical Spark Row to Kafka event."""
    now = datetime.now()
    
    return {
        'event_id': f"replay_{int(time.time()*1000)}_{random.randint(1000,9999)}",
        'event_time': now.isoformat(),
        'pickup_datetime': str(row.pickup_datetime) if hasattr(row, 'pickup_datetime') else now.isoformat(),
        'dropoff_datetime': str(row.dropoff_datetime) if hasattr(row, 'dropoff_datetime') else now.isoformat(),
        'pickup_lat': float(row.pickup_lat),
        'pickup_lon': float(row.pickup_lon),
        'dropoff_lat': float(row.dropoff_lat),
        'dropoff_lon': float(row.dropoff_lon),
        'trip_distance': float(row.trip_distance),
        'duration_minutes': float(row.duration_hours * 60) if hasattr(row, 'duration_hours') else 10,
        'speed_mph': float(row.speed_mph),
        'passenger_count': int(row.passenger_count) if hasattr(row, 'passenger_count') else 1,
        'fare_amount': float(row.fare_amount) if hasattr(row, 'fare_amount') else 10.0,
        'cell_id': str(row.cell_id),
        'cell_lat': int(row.cell_lat),
        'cell_lon': int(row.cell_lon),
        'hour': now.hour,  # Use current time for streaming
        'day_of_week': now.weekday() + 1,
        'month': now.month,
        'year': now.year,
        'is_weekend': 1 if now.weekday() >= 5 else 0,
        'is_rush_hour': 1 if now.hour in [7, 8, 9, 17, 18, 19] else 0,
        'is_night': 1 if now.hour >= 22 or now.hour <= 5 else 0,
        'is_manhattan': 1 if hasattr(row, 'is_manhattan') and row.is_manhattan else 0
    }


def stream_to_kafka(producer, topic, rate, use_hdfs=False, duration_seconds=None):
    """Stream events to Kafka topic."""
    
    # Try to load historical data
    historical_data = load_historical_data_spark(use_hdfs)
    use_historical = historical_data is not None and len(historical_data) > 0
    
    if use_historical:
        print(f"\n📊 Replaying historical data ({len(historical_data)} records)")
    else:
        print(f"\n🔄 Generating synthetic taxi trips")
    
    print(f"📡 Streaming to Kafka topic: {topic}")
    print(f"⚡ Rate: {rate} events/second")
    if duration_seconds:
        print(f"⏱  Duration: {duration_seconds} seconds")
    print("\nPress Ctrl+C to stop...\n")
    
    interval = 1.0 / rate
    events_sent = 0
    errors = 0
    start_time = time.time()
    historical_index = 0
    
    try:
        while True:
            # Check duration limit
            if duration_seconds and (time.time() - start_time) >= duration_seconds:
                print(f"\n⏱  Duration limit reached ({duration_seconds}s)")
                break
            
            # Generate or replay event
            if use_historical:
                event = replay_historical_trip(historical_data[historical_index])
                historical_index = (historical_index + 1) % len(historical_data)
            else:
                event = generate_synthetic_trip()
            
            # Send to Kafka
            try:
                future = producer.send(
                    topic,
                    key=event['cell_id'],
                    value=event
                )
                # Don't wait for each message (async)
                events_sent += 1
                
                # Progress update every 100 events
                if events_sent % 100 == 0:
                    elapsed = time.time() - start_time
                    actual_rate = events_sent / elapsed if elapsed > 0 else 0
                    print(f"  Sent: {events_sent:,} events | Rate: {actual_rate:.1f}/s | "
                          f"Cell: {event['cell_id']} | Speed: {event['speed_mph']:.1f} mph")
                
            except KafkaError as e:
                errors += 1
                if errors <= 5:
                    print(f"  ⚠ Kafka error: {e}")
            
            # Rate limiting
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping producer...")
    
    finally:
        # Flush remaining messages
        producer.flush()
        
        elapsed = time.time() - start_time
        print(f"""
============================================================
STREAMING SUMMARY
============================================================
  Events sent: {events_sent:,}
  Errors: {errors}
  Duration: {elapsed:.1f} seconds
  Actual rate: {events_sent/elapsed:.1f} events/second
  Topic: {topic}
============================================================
""")


def main():
    parser = argparse.ArgumentParser(description='Kafka Streaming Producer for Taxi Data')
    parser.add_argument('--hdfs', action='store_true', help='Load data from HDFS')
    parser.add_argument('--rate', type=int, default=DEFAULT_RATE, help='Events per second')
    parser.add_argument('--topic', type=str, default=DEFAULT_TOPIC, help='Kafka topic name')
    parser.add_argument('--duration', type=int, default=None, help='Duration in seconds (None=infinite)')
    parser.add_argument('--synthetic', action='store_true', help='Use synthetic data only')
    
    args = parser.parse_args()
    
    print("""
============================================================
SMART CITY TRAFFIC - KAFKA STREAMING PRODUCER
============================================================
""")
    
    # Create Kafka producer
    producer = create_kafka_producer()
    
    # Start streaming
    if args.synthetic:
        # Force synthetic mode
        stream_to_kafka(producer, args.topic, args.rate, use_hdfs=False, duration_seconds=args.duration)
    else:
        stream_to_kafka(producer, args.topic, args.rate, use_hdfs=args.hdfs, duration_seconds=args.duration)
    
    producer.close()


if __name__ == "__main__":
    main()
