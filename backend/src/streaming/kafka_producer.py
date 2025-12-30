"""
Smart City Traffic - Kafka Producer
====================================

This script simulates real-time vehicle GPS events by:
- Reading historical taxi trip data
- Replaying trips as real-time GPS events
- Publishing to Kafka topic

Usage:
    python src/streaming/kafka_producer.py
    python src/streaming/kafka_producer.py --duration 60
    python src/streaming/kafka_producer.py --demo  # Without Kafka

Topics:
    - traffic-events: GPS position events (this producer)
"""

import os
import sys
from pathlib import Path
import json
import time
import random
import uuid
from datetime import datetime, timedelta
import argparse
import pandas as pd
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import centralized configuration
try:
    from src.config.spark_config import KAFKA_CONFIG, NYC_BOUNDS, MANHATTAN_BOUNDS, DATA_DIR
except ImportError:
    # Fallback if config not available
    KAFKA_CONFIG = {
        "bootstrap_servers": "localhost:9092",
        "topic_events": "traffic-events",
        "events_per_second": 500,
        "batch_size": 100,
    }
    NYC_BOUNDS = {"lat_min": 40.4774, "lat_max": 40.9176, "lon_min": -74.2591, "lon_max": -73.7004, "cell_size": 0.01}
    MANHATTAN_BOUNDS = {"lat_min": 40.70, "lat_max": 40.88, "lon_min": -74.02, "lon_max": -73.93}
    DATA_DIR = PROJECT_ROOT / "data"

# Configuration from centralized config
KAFKA_BOOTSTRAP_SERVERS = [KAFKA_CONFIG["bootstrap_servers"]]
KAFKA_TOPIC = KAFKA_CONFIG["topic_events"]  # Unified topic: 'traffic-events'

# Simulation settings
EVENTS_PER_SECOND = KAFKA_CONFIG.get("events_per_second", 500)
BATCH_SIZE = KAFKA_CONFIG.get("batch_size", 100)

# Data paths
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"


class TaxiSimulator:
    """Simulates taxi GPS events from historical data."""
    
    def __init__(self):
        self.producer = None
        self.df = None
        self.events_sent = 0
        self.start_time = None
    
    def connect_kafka(self):
        """Connect to Kafka broker."""
        print("Connecting to Kafka...")
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                batch_size=16384,
                linger_ms=10
            )
            print(f"Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return True
        except NoBrokersAvailable:
            print("ERROR: Could not connect to Kafka!")
            print("Make sure Kafka is running: docker-compose up -d")
            return False
    
    def load_data(self):
        """Load processed trip data."""
        # Try to load cleaned parquet files (correct naming convention)
        parquet_files = list(PROCESSED_DATA_DIR.glob('*_clean.parquet'))
        
        if parquet_files:
            print(f"Loading from {len(parquet_files)} parquet files...")
            dfs = []
            for f in parquet_files[:1]:  # Load just one file for simulation
                df = pd.read_parquet(f)
                dfs.append(df)
            self.df = pd.concat(dfs, ignore_index=True)
        else:
            # Fall back to raw CSV
            csv_files = list(Path(r"c:\sem6-real\bigdata\vscode").glob('yellow_tripdata_*.csv'))
            if csv_files:
                print(f"Loading sample from {csv_files[0].name}...")
                self.df = pd.read_csv(csv_files[0], nrows=100000)
                self.df = self._standardize_columns(self.df)
            else:
                print("ERROR: No data files found!")
                return False
        
        print(f"Loaded {len(self.df):,} trips for simulation")
        return True
    
    def _standardize_columns(self, df):
        """Standardize column names."""
        rename_map = {
            'tpep_pickup_datetime': 'pickup_datetime',
            'pickup_longitude': 'pickup_lon',
            'pickup_latitude': 'pickup_lat',
            'dropoff_longitude': 'dropoff_lon',
            'dropoff_latitude': 'dropoff_lat'
        }
        
        for old, new in rename_map.items():
            if old in df.columns:
                df = df.rename(columns={old: new})
        
        return df
    
    def generate_event(self, row):
        """Generate a GPS event from a trip row.
        
        This event schema matches the consumer's expected format,
        including temporal features for ML predictions.
        """
        # Generate unique vehicle ID
        vehicle_id = f"taxi_{random.randint(10000, 99999)}"
        
        # Get coordinates
        lat = row.get('pickup_lat', row.get('cell_center_lat', 40.75))
        lon = row.get('pickup_lon', row.get('cell_center_lon', -73.98))
        
        # Calculate speed (with some randomization)
        base_speed = row.get('speed_mph', random.uniform(10, 30))
        speed = max(0, base_speed + random.uniform(-5, 5))
        
        # Get cell info (compute if not available)
        cell_size = NYC_BOUNDS.get("cell_size", 0.01)
        cell_lat = int((lat - NYC_BOUNDS["lat_min"]) / cell_size)
        cell_lon = int((lon - NYC_BOUNDS["lon_min"]) / cell_size)
        cell_id = row.get('cell_id', f"cell_{cell_lat}_{cell_lon}")
        
        # Temporal features (use current time for simulation)
        now = datetime.utcnow()
        current_hour = row.get('hour', now.hour)
        current_dow = row.get('day_of_week', now.weekday() + 1)  # 1-7 for Sun-Sat
        
        # Derive boolean features
        is_weekend = 1 if current_dow in [1, 7] else 0  # 1=Sunday, 7=Saturday
        is_rush_hour = 1 if current_hour in [7, 8, 9, 17, 18, 19] else 0
        is_night = 1 if current_hour in [22, 23, 0, 1, 2, 3, 4, 5] else 0
        is_manhattan = 1 if (
            MANHATTAN_BOUNDS["lat_min"] <= lat <= MANHATTAN_BOUNDS["lat_max"] and
            MANHATTAN_BOUNDS["lon_min"] <= lon <= MANHATTAN_BOUNDS["lon_max"]
        ) else 0
        
        # Create event with unified schema
        event = {
            # Event metadata
            'event_id': f"evt_{uuid.uuid4().hex[:12]}",
            'timestamp': now.isoformat() + 'Z',
            'vehicle_id': vehicle_id,
            
            # Location
            'latitude': float(lat),
            'longitude': float(lon),
            'cell_id': cell_id,
            'cell_lat': cell_lat,
            'cell_lon': cell_lon,
            
            # Trip info
            'speed': round(float(speed), 2),
            'heading': random.randint(0, 359),
            'trip_id': f"trip_{uuid.uuid4().hex[:8]}",
            
            # Temporal features (for ML predictions)
            'hour': current_hour,
            'day_of_week': current_dow,
            'is_weekend': is_weekend,
            'is_rush_hour': is_rush_hour,
            'is_night': is_night,
            'is_manhattan': is_manhattan,
        }
        
        return event
    
    def send_event(self, event):
        """Send event to Kafka."""
        try:
            future = self.producer.send(
                KAFKA_TOPIC,
                key=event['vehicle_id'],
                value=event
            )
            return True
        except Exception as e:
            print(f"Error sending event: {e}")
            return False
    
    def run_simulation(self, duration_seconds=60):
        """Run the simulation for specified duration."""
        print(f"\n{'='*60}")
        print("STARTING TRAFFIC SIMULATION")
        print(f"{'='*60}")
        print(f"Topic: {KAFKA_TOPIC}")
        print(f"Target rate: {EVENTS_PER_SECOND} events/second")
        print(f"Duration: {duration_seconds} seconds")
        print(f"{'='*60}\n")
        
        self.start_time = time.time()
        self.events_sent = 0
        
        # Sample trips for simulation
        sample_size = min(len(self.df), EVENTS_PER_SECOND * duration_seconds)
        sample_df = self.df.sample(n=sample_size, replace=True)
        
        batch = []
        last_report_time = time.time()
        events_since_report = 0
        
        try:
            for idx, row in sample_df.iterrows():
                # Generate and send event
                event = self.generate_event(row)
                self.send_event(event)
                self.events_sent += 1
                events_since_report += 1
                
                # Rate limiting
                elapsed = time.time() - self.start_time
                expected_events = elapsed * EVENTS_PER_SECOND
                
                if self.events_sent > expected_events:
                    sleep_time = (self.events_sent - expected_events) / EVENTS_PER_SECOND
                    time.sleep(sleep_time)
                
                # Progress report every 5 seconds
                if time.time() - last_report_time >= 5:
                    actual_rate = events_since_report / (time.time() - last_report_time)
                    print(f"  [{elapsed:.0f}s] Events sent: {self.events_sent:,} | Rate: {actual_rate:.0f}/s")
                    last_report_time = time.time()
                    events_since_report = 0
                
                # Check duration
                if elapsed >= duration_seconds:
                    break
            
            # Flush remaining messages
            self.producer.flush()
            
        except KeyboardInterrupt:
            print("\n\nSimulation interrupted by user")
        
        # Final report
        total_time = time.time() - self.start_time
        avg_rate = self.events_sent / total_time
        
        print(f"\n{'='*60}")
        print("SIMULATION COMPLETE")
        print(f"{'='*60}")
        print(f"Total events sent: {self.events_sent:,}")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Average rate: {avg_rate:.0f} events/second")
        print(f"{'='*60}")
    
    def close(self):
        """Close Kafka producer."""
        if self.producer:
            self.producer.close()
            print("Kafka producer closed")


def run_demo_mode():
    """Run in demo mode without Kafka (prints events to console)."""
    print("\n" + "="*60)
    print("RUNNING IN DEMO MODE (No Kafka)")
    print("="*60)
    
    # Load sample data
    csv_files = list(Path(r"c:\sem6-real\bigdata\vscode").glob('yellow_tripdata_*.csv'))
    if not csv_files:
        print("No data files found!")
        return
    
    print(f"Loading sample from {csv_files[0].name}...")
    df = pd.read_csv(csv_files[0], nrows=1000)
    
    # Generate sample events
    print("\nSample GPS Events:")
    print("-"*60)
    
    for i in range(10):
        row = df.iloc[random.randint(0, len(df)-1)]
        
        # Extract coordinates (handle different column names)
        lat_col = 'pickup_latitude' if 'pickup_latitude' in df.columns else 'Start_Lat'
        lon_col = 'pickup_longitude' if 'pickup_longitude' in df.columns else 'Start_Lon'
        
        if lat_col in df.columns and lon_col in df.columns:
            lat = row[lat_col]
            lon = row[lon_col]
        else:
            lat = 40.75 + random.uniform(-0.05, 0.05)
            lon = -73.98 + random.uniform(-0.05, 0.05)
        
        event = {
            'vehicle_id': f"taxi_{random.randint(10000, 99999)}",
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'latitude': float(lat),
            'longitude': float(lon),
            'speed': round(random.uniform(5, 35), 2),
            'heading': random.randint(0, 359)
        }
        
        print(json.dumps(event, indent=2))
        print("-"*60)
        time.sleep(0.5)


def main():
    """Main execution function."""
    print("="*60)
    print("SMART CITY TRAFFIC - KAFKA PRODUCER")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    simulator = TaxiSimulator()
    
    # Try to connect to Kafka
    if simulator.connect_kafka():
        # Load data
        if simulator.load_data():
            # Run simulation
            simulator.run_simulation(duration_seconds=300)  # 5 minutes
        simulator.close()
    else:
        print("\nKafka not available. Running in demo mode...")
        run_demo_mode()
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
