"""
Smart City Traffic - Kafka to API Bridge
=========================================

This module provides real-time updates from Kafka to the Flask API.
It consumes predictions from the 'traffic-predictions' topic and
updates the API's traffic_state in real-time.

Usage:
    # Start as standalone process
    python src/streaming/kafka_api_bridge.py
    
    # Or import and use in API
    from streaming.kafka_api_bridge import KafkaTrafficConsumer
    
Topics:
    Input: traffic-predictions (from spark_streaming_consumer.py)
"""

import json
import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Callable, Optional
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import centralized configuration
try:
    from src.config.spark_config import KAFKA_CONFIG
    KAFKA_BOOTSTRAP_SERVERS = KAFKA_CONFIG["bootstrap_servers"]
    KAFKA_TOPIC_PREDICTIONS = KAFKA_CONFIG["topic_predictions"]
    KAFKA_CONSUMER_GROUP = KAFKA_CONFIG.get("consumer_group", "traffic-api-consumer")
except ImportError:
    KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
    KAFKA_TOPIC_PREDICTIONS = "traffic-predictions"
    KAFKA_CONSUMER_GROUP = "traffic-api-consumer"


class KafkaTrafficConsumer:
    """
    Consumer that bridges Kafka traffic predictions to the Flask API.
    
    This class runs in a background thread and updates a shared traffic state
    dictionary whenever new predictions arrive from Kafka.
    """
    
    def __init__(
        self, 
        traffic_state: Dict,
        on_update_callback: Optional[Callable] = None,
        bootstrap_servers: str = None,
        topic: str = None,
        consumer_group: str = None
    ):
        """
        Initialize the Kafka consumer.
        
        Args:
            traffic_state: Shared dictionary to update with traffic data
            on_update_callback: Optional callback function called after updates
            bootstrap_servers: Kafka broker address
            topic: Kafka topic to consume from
            consumer_group: Kafka consumer group ID
        """
        self.traffic_state = traffic_state
        self.on_update_callback = on_update_callback
        self.bootstrap_servers = bootstrap_servers or KAFKA_BOOTSTRAP_SERVERS
        self.topic = topic or KAFKA_TOPIC_PREDICTIONS
        self.consumer_group = consumer_group or KAFKA_CONSUMER_GROUP
        
        self.consumer = None
        self.running = False
        self.thread = None
        self.messages_processed = 0
        self.last_update = None
        self.connected = False
        
    def connect(self) -> bool:
        """
        Connect to Kafka broker.
        
        Returns:
            True if connected successfully, False otherwise
        """
        print(f"Connecting to Kafka: {self.bootstrap_servers}")
        print(f"Topic: {self.topic}")
        
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                consumer_timeout_ms=1000  # 1 second timeout for polling
            )
            self.connected = True
            print(f"✓ Connected to Kafka successfully")
            return True
        except NoBrokersAvailable:
            print(f"✗ Could not connect to Kafka at {self.bootstrap_servers}")
            print("  Make sure Kafka is running: docker-compose up -d")
            self.connected = False
            return False
        except Exception as e:
            print(f"✗ Kafka connection error: {e}")
            self.connected = False
            return False
    
    def process_message(self, message) -> None:
        """
        Process a single Kafka message and update traffic state.
        
        Args:
            message: Kafka message with traffic prediction data
        """
        try:
            data = message.value
            
            # Extract cell_id (might be the key or in the value)
            cell_id = data.get('cell_id', message.key.decode('utf-8') if message.key else None)
            
            if not cell_id:
                return
            
            # Update traffic state with prediction data
            self.traffic_state[cell_id] = {
                'cell_id': cell_id,
                'latitude': data.get('cell_lat', 0) * 0.01 + 40.4855,  # Convert back to coords
                'longitude': data.get('cell_lon', 0) * 0.01 - 74.2567,
                'congestion_index': self._level_to_index(data.get('congestion_level', 'Medium')),
                'congestion_level': data.get('congestion_level', 'medium').lower(),
                'vehicle_count': int(data.get('trip_count', 0)),
                'avg_speed': round(float(data.get('avg_speed', 20)), 1),
                'max_speed': round(float(data.get('max_speed', 30)), 1),
                'min_speed': round(float(data.get('min_speed', 5)), 1),
                'last_update': datetime.utcnow().isoformat(),
                'source': 'kafka_stream'
            }
            
            self.messages_processed += 1
            self.last_update = datetime.utcnow()
            
        except Exception as e:
            print(f"Error processing Kafka message: {e}")
    
    def _level_to_index(self, level: str) -> float:
        """Convert congestion level to index value."""
        level = level.lower() if level else 'medium'
        if level == 'low':
            return 0.3
        elif level == 'high':
            return 0.85
        else:
            return 0.55
    
    def run(self) -> None:
        """
        Main consumer loop. Runs until stop() is called.
        """
        print(f"\n📡 Starting Kafka consumer loop...")
        print(f"   Topic: {self.topic}")
        print(f"   Group: {self.consumer_group}")
        
        self.running = True
        
        while self.running:
            try:
                # Poll for messages
                for message in self.consumer:
                    if not self.running:
                        break
                    
                    self.process_message(message)
                    
                    # Call update callback if provided
                    if self.on_update_callback and self.messages_processed % 10 == 0:
                        self.on_update_callback({
                            'type': 'kafka_update',
                            'messages_processed': self.messages_processed,
                            'cells_updated': len(self.traffic_state),
                            'timestamp': datetime.utcnow().isoformat()
                        })
                        
            except Exception as e:
                if self.running:
                    print(f"Kafka consumer error: {e}")
                    time.sleep(1)  # Brief pause before retry
        
        print("Kafka consumer stopped")
    
    def start_background(self) -> bool:
        """
        Start the consumer in a background thread.
        
        Returns:
            True if started successfully
        """
        if not self.connected and not self.connect():
            return False
        
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        print("✓ Kafka consumer started in background thread")
        return True
    
    def stop(self) -> None:
        """Stop the consumer."""
        self.running = False
        if self.consumer:
            self.consumer.close()
            print("Kafka consumer closed")
    
    def get_stats(self) -> Dict:
        """Get consumer statistics."""
        return {
            'connected': self.connected,
            'running': self.running,
            'messages_processed': self.messages_processed,
            'cells_in_state': len(self.traffic_state),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'topic': self.topic,
            'consumer_group': self.consumer_group
        }


def main():
    """Standalone test of the Kafka consumer."""
    print("=" * 60)
    print("SMART CITY TRAFFIC - KAFKA API BRIDGE TEST")
    print("=" * 60)
    
    # Shared traffic state (in real app, this comes from the API)
    traffic_state = {}
    
    # Create consumer
    consumer = KafkaTrafficConsumer(
        traffic_state=traffic_state,
        on_update_callback=lambda msg: print(f"  Update: {msg}")
    )
    
    # Connect and run
    if consumer.connect():
        try:
            print("\nListening for messages (Ctrl+C to stop)...\n")
            consumer.run()
        except KeyboardInterrupt:
            print("\n\nStopping...")
        finally:
            consumer.stop()
    else:
        print("\nFailed to connect to Kafka.")
        print("Make sure Docker services are running:")
        print("  cd backend && docker-compose up -d")
    
    # Print final stats
    print(f"\nFinal stats: {consumer.get_stats()}")
    print(f"Cells in state: {len(traffic_state)}")


if __name__ == "__main__":
    main()
