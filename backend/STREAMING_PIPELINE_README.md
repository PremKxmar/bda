# Smart City Traffic - Streaming & Cluster Pipeline

## Overview

This document describes the real-time streaming pipeline and distributed Spark cluster capabilities added to the Smart City Traffic system.

## Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                  SMART CITY TRAFFIC                     │
                    │              Real-Time Streaming Pipeline               │
                    └─────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────────────────────────┐
│   HDFS       │     │   KAFKA      │     │   SPARK CLUSTER                  │
│   (Storage)  │     │  (Streaming) │     │   (Processing)                   │
├──────────────┤     ├──────────────┤     ├──────────────────────────────────┤
│              │     │              │     │  ┌────────────┐                  │
│  Raw CSV     │────▶│ taxi-trips   │────▶│  │  Master    │ (port 8081)      │
│  (7GB)       │     │   topic      │     │  └─────┬──────┘                  │
│              │     │              │     │        │                         │
│  Parquet     │     │ traffic-     │◀────│  ┌─────┴──────┐                  │
│  (cleaned)   │     │ predictions  │     │  │  Worker 1  │ (port 8082)      │
│              │     │   topic      │     │  └────────────┘                  │
│  Features    │     │              │     │  ┌────────────┐                  │
│              │     │              │     │  │  Worker 2  │ (port 8083)      │
│  Models      │     │              │     │  └────────────┘                  │
└──────────────┘     └──────────────┘     └──────────────────────────────────┘
       │                    │                          │
       │                    │                          │
       ▼                    ▼                          ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │                         DASHBOARD (React)                               │
  │                    Real-time Congestion Visualization                   │
  └─────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Docker Services

| Service | Port | Description |
|---------|------|-------------|
| **namenode** | 9870, 9000 | HDFS NameNode (storage metadata) |
| **datanode** | 9864, 9866 | HDFS DataNode (actual data) |
| **zookeeper** | 2181 | Kafka coordination |
| **kafka** | 9092, 29092 | Message broker |
| **kafka-ui** | 8080 | Kafka web interface |
| **spark-master** | 8081, 7077 | Spark cluster master |
| **spark-worker-1** | 8082 | Spark worker node 1 |
| **spark-worker-2** | 8083 | Spark worker node 2 |

### 2. Streaming Components

| Component | File | Description |
|-----------|------|-------------|
| **Kafka Producer** | `src/streaming/kafka_streaming_producer.py` | Streams taxi events to Kafka |
| **Spark Consumer** | `src/streaming/spark_streaming_consumer.py` | Consumes from Kafka, makes predictions |
| **Spark Submit** | `src/batch/spark_submit.py` | Utility to submit jobs to cluster |

## Quick Start

### Step 1: Start All Services

```bash
cd backend

# Start everything (HDFS + Kafka + Spark Cluster)
docker-compose up -d

# Verify services
docker-compose ps
```

### Step 2: Upload Data to HDFS (if not already done)

```bash
python src/batch/hdfs_utils.py setup
python src/batch/hdfs_utils.py upload
python src/batch/hdfs_utils.py list
```

### Step 3: Run Batch Pipeline with HDFS

```bash
# Option A: Run all steps
python src/batch/spark_submit.py all --hdfs

# Option B: Run individual steps
python src/batch/data_cleaning_spark.py --hdfs
python src/batch/feature_engineering_spark.py --hdfs
python src/batch/model_training_spark.py --hdfs
```

### Step 4: Start Streaming Pipeline

**Terminal 1 - Start Kafka Producer:**
```bash
# Stream synthetic data
python src/streaming/kafka_streaming_producer.py --rate 50

# Or replay historical data from HDFS
python src/streaming/kafka_streaming_producer.py --hdfs --rate 100
```

**Terminal 2 - Start Spark Streaming Consumer:**
```bash
# Console output (for debugging)
python src/streaming/spark_streaming_consumer.py --output console

# Write to HDFS
python src/streaming/spark_streaming_consumer.py --hdfs --output parquet

# Write predictions back to Kafka
python src/streaming/spark_streaming_consumer.py --output kafka
```

## Detailed Usage

### Kafka Streaming Producer

```bash
python src/streaming/kafka_streaming_producer.py [OPTIONS]

Options:
  --hdfs          Load historical data from HDFS
  --rate RATE     Events per second (default: 100)
  --topic TOPIC   Kafka topic name (default: taxi-trips)
  --duration SEC  Run for N seconds (default: infinite)
  --synthetic     Force synthetic data generation
```

**Example Output:**
```
============================================================
SMART CITY TRAFFIC - KAFKA STREAMING PRODUCER
============================================================
✓ Connected to Kafka at localhost:9092
📊 Replaying historical data (46000 records)
📡 Streaming to Kafka topic: taxi-trips
⚡ Rate: 100 events/second

Press Ctrl+C to stop...

  Sent: 100 events | Rate: 99.8/s | Cell: 25_42 | Speed: 12.3 mph
  Sent: 200 events | Rate: 100.1/s | Cell: 18_38 | Speed: 8.7 mph
  ...
```

### Spark Streaming Consumer

```bash
python src/streaming/spark_streaming_consumer.py [OPTIONS]

Options:
  --hdfs          Write output to HDFS
  --cluster       Submit to Spark cluster
  --output TYPE   Output sink: console, parquet, kafka, all
  --duration SEC  Run for N seconds (default: infinite)
```

**Example Output:**
```
============================================================
SMART CITY TRAFFIC - SPARK STRUCTURED STREAMING
============================================================

🔧 Creating Spark Session...
  Mode: Local
📥 Creating Kafka Stream...
📡 Connecting to Kafka: localhost:9092
   Topic: taxi-trips

🚀 STREAMING STARTED
   Queries running: 1

-------------------------------------------
Batch: 0
-------------------------------------------
+-------+--------+--------+----------+---------+----------------+
|cell_id|cell_lat|cell_lon|trip_count|avg_speed|congestion_level|
+-------+--------+--------+----------+---------+----------------+
|25_42  |25      |42      |15        |11.2     |Medium          |
|18_38  |18      |38      |8         |6.5      |High            |
|30_45  |30      |45      |22        |18.3     |Low             |
+-------+--------+--------+----------+---------+----------------+
```

### Spark Cluster Mode

```bash
# Submit batch jobs to Spark cluster
python src/batch/spark_submit.py clean --cluster --hdfs
python src/batch/spark_submit.py features --cluster --hdfs
python src/batch/spark_submit.py train --cluster --hdfs

# Or run all at once
python src/batch/spark_submit.py all --cluster --hdfs
```

## Web UIs

Access these dashboards in your browser:

| Service | URL | Description |
|---------|-----|-------------|
| **HDFS NameNode** | http://localhost:9870 | File system browser |
| **Kafka UI** | http://localhost:8080 | Topics, messages, consumers |
| **Spark Master** | http://localhost:8081 | Cluster overview, running apps |
| **Spark Worker 1** | http://localhost:8082 | Worker status |
| **Spark Worker 2** | http://localhost:8083 | Worker status |
| **Application** | http://localhost:3000 | Traffic dashboard |

## Data Flow

### Batch Processing (Daily/Hourly)
```
Raw CSV (HDFS) → Data Cleaning → Feature Engineering → Model Training → Model (HDFS)
```

### Stream Processing (Real-time)
```
Kafka Producer → taxi-trips topic → Spark Streaming → Predictions → traffic-predictions topic
                                                   ↓
                                             HDFS (archived)
```

## Kafka Topics

| Topic | Description | Message Format |
|-------|-------------|----------------|
| `taxi-trips` | Raw taxi trip events | JSON with trip details |
| `traffic-predictions` | Aggregated predictions | JSON with cell congestion |

**Sample Message (taxi-trips):**
```json
{
  "event_id": "trip_1735562400000_1234",
  "event_time": "2025-12-30T10:00:00",
  "pickup_lat": 40.7580,
  "pickup_lon": -73.9855,
  "cell_id": "28_45",
  "speed_mph": 12.5,
  "is_rush_hour": 1,
  "is_manhattan": 1
}
```

**Sample Message (traffic-predictions):**
```json
{
  "window_start": "2025-12-30T10:00:00",
  "window_end": "2025-12-30T10:01:00",
  "cell_id": "28_45",
  "trip_count": 25,
  "avg_speed": 8.5,
  "congestion_level": "High"
}
```

## Troubleshooting

### Kafka Connection Issues
```bash
# Check if Kafka is running
docker logs kafka

# List topics
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 --list

# Create topic manually if needed
docker exec -it kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic taxi-trips --partitions 3 --replication-factor 1
```

### Spark Cluster Issues
```bash
# Check Spark master logs
docker logs spark-master

# Check worker logs
docker logs spark-worker-1
docker logs spark-worker-2

# Verify cluster is up
curl http://localhost:8081/json
```

### HDFS Issues
```bash
# Check HDFS health
docker exec namenode hdfs dfsadmin -report

# Safe mode issues
docker exec namenode hdfs dfsadmin -safemode leave
```

## Performance Tuning

### Kafka Producer
- Adjust `--rate` based on your network capacity
- Use `batch_size` and `linger_ms` for better throughput

### Spark Streaming
- Tune `processingTime` trigger for latency vs throughput
- Adjust `spark.sql.shuffle.partitions` for parallelism
- Use watermarking for late data handling

### Spark Cluster
- Scale workers by adding more `spark-worker-N` services
- Adjust `SPARK_WORKER_MEMORY` and `SPARK_WORKER_CORES`

## Files Structure

```
backend/
├── docker-compose.yml          # All services (HDFS, Kafka, Spark)
├── src/
│   ├── batch/
│   │   ├── data_cleaning_spark.py      # With --hdfs flag
│   │   ├── feature_engineering_spark.py # With --hdfs flag
│   │   ├── model_training_spark.py     # With --hdfs flag
│   │   ├── hdfs_utils.py               # HDFS utilities
│   │   └── spark_submit.py             # Cluster submit utility
│   └── streaming/
│       ├── kafka_streaming_producer.py  # Streams to Kafka
│       └── spark_streaming_consumer.py  # Consumes from Kafka
└── STREAMING_PIPELINE_README.md        # This file
```

## Next Steps

1. **Add Airflow** - Orchestrate batch and streaming jobs
2. **Add MLflow** - Track model versions and experiments
3. **Add Grafana** - Monitor pipeline metrics
4. **Add Delta Lake** - ACID transactions on data lake
