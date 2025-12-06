# 🏙️ Smart City Real-Time Traffic Simulation & Predictive Analytics

> A Distributed Big Data Pipeline with Hadoop, Spark, and Machine Learning

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Spark](https://img.shields.io/badge/Apache%20Spark-3.5-orange.svg)
![Scala](https://img.shields.io/badge/Scala-2.12-red.svg)
![Hadoop](https://img.shields.io/badge/Hadoop-3.2-yellow.svg)
![Kafka](https://img.shields.io/badge/Apache%20Kafka-3.6-purple.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 📋 Project Overview

This project simulates and predicts city traffic in near-real-time using a complete big data pipeline. It processes **7+ GB of NYC Taxi trip data** (46+ million trips) featuring:

- **Distributed Storage** with Hadoop HDFS
- **Batch Processing** with Apache Spark (Python & Scala)
- **Machine Learning** with Spark MLlib
- **Real-time Streaming** via Apache Kafka
- **Interactive Dashboard** for visualization

## 🎯 Technical Requirements Satisfied

| Requirement | Implementation |
|------------|----------------|
| **Hadoop (HDFS)** | ✅ HDFS cluster for distributed storage |
| **Apache Spark (RDD/DataFrame/Dataset)** | ✅ PySpark DataFrame API for ETL and processing |
| **Python** | ✅ Data cleaning, feature engineering, API |
| **Scala** | ✅ Scala preprocessing script |
| **Spark ML (MLlib)** | ✅ RandomForestClassifier for prediction |

## 📊 5 V's of Big Data

| Dimension | Implementation |
|-----------|----------------|
| **Volume** | 7+ GB of NYC Taxi data (46M+ trips from 2015-2016) |
| **Velocity** | 1,000+ vehicle events/second via Kafka streaming |
| **Variety** | GPS coordinates, timestamps, trip metrics, grid cells |
| **Veracity** | Data cleaning, outlier removal, coordinate validation |
| **Value** | Predict congestion 15 min ahead, optimize routes |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SMART CITY TRAFFIC PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  RAW DATA   │───▶│   HADOOP    │───▶│   SPARK     │───▶│  SPARK ML   │  │
│  │  CSV Files  │    │   HDFS      │    │   ETL       │    │   MLlib     │  │
│  │  (7+ GB)    │    │  (Storage)  │    │(Python+Scala│    │  Training   │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                    │        │
│                                                                    ▼        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   REACT     │◀───│   FLASK     │◀───│   KAFKA     │◀───│  PARQUET    │  │
│  │  Dashboard  │    │   REST API  │    │   Topics    │    │   Output    │  │
│  │  (Leaflet)  │    │  (5000)     │    │             │    │             │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
smart-city-traffic/
├── docker-compose.yml          # Hadoop + Kafka + Spark cluster
├── requirements.txt            # Python dependencies
│
├── data/
│   ├── raw/                    # Raw CSV files (or HDFS)
│   └── processed/              # Cleaned Parquet files
│
├── src/
│   ├── batch/
│   │   ├── data_cleaning_spark.py      # PySpark data cleaning
│   │   ├── feature_engineering_spark.py # PySpark feature engineering
│   │   ├── model_training_spark.py     # Spark MLlib training
│   │   └── hdfs_utils.py               # HDFS utilities
│   │
│   ├── scala/
│   │   ├── TrafficDataPreprocessor.scala  # Scala preprocessing
│   │   └── build.sbt                      # SBT build file
│   │
│   ├── streaming/
│   │   └── kafka_producer.py           # Kafka event producer
│   │
│   └── api/
│       ├── app.py                      # Original Flask API
│       └── app_spark.py                # Spark MLlib API
│
├── models/
│   ├── spark_congestion_model/         # Spark MLlib model
│   ├── model_info_spark.json           # Model metadata
│   └── feature_columns_spark.json      # Feature list
│
├── dashboard/                  # React frontend
│
└── docs/
    ├── architecture.md
    └── api_documentation.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker Desktop (for Hadoop, Kafka, Spark)
- Java 8+ (for Spark)
- 16GB+ RAM recommended

### 1. Start Infrastructure

```bash
cd smart-city-traffic

# Start Hadoop HDFS, Kafka, and Spark cluster
docker-compose up -d

# Verify services are running
docker-compose ps
```

**Service URLs:**
- HDFS NameNode UI: http://localhost:9870
- Spark Master UI: http://localhost:8081
- Kafka UI: http://localhost:8080

### 2. Setup Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Upload Data to HDFS

```bash
# Setup HDFS directories and upload data
python src/batch/hdfs_utils.py setup
python src/batch/hdfs_utils.py upload

# Verify data in HDFS
python src/batch/hdfs_utils.py list
```

### 4. Run Data Pipeline

```bash
# Step 1: Clean raw data with Spark
spark-submit src/batch/data_cleaning_spark.py

# Step 2: Create features with Spark
spark-submit src/batch/feature_engineering_spark.py

# Step 3: Train ML model with Spark MLlib
spark-submit src/batch/model_training_spark.py
```

### 5. Run Scala Preprocessing (Optional)

```bash
cd src/scala

# Build with SBT
sbt package

# Run with spark-submit
spark-submit --class TrafficDataPreprocessor target/scala-2.12/traffic-preprocessor_2.12-1.0.jar
```

### 6. Start API Server

```bash
# Start Flask API with Spark MLlib support
python src/api/app_spark.py
```

API will be available at: http://localhost:5000

### 7. Start Streaming (Optional)

```bash
# Start Kafka producer for real-time events
python src/streaming/kafka_producer.py
```

## 🤖 Machine Learning Model

### Spark MLlib RandomForestClassifier

**Features Used** (NO data leakage):
- `hour` - Hour of day (0-23)
- `day_of_week` - Day of week (0-6)
- `is_weekend` - Boolean flag
- `is_rush_hour` - Boolean flag (7-9 AM, 5-7 PM)
- `cell_lat`, `cell_lon` - Spatial grid indices
- `is_manhattan` - Boolean flag
- `prev_trip_count` - Previous hour's trip count
- `prev_avg_speed` - Previous hour's average speed
- `historical_avg_trips` - Historical average for cell+hour

**Target Variable:**
- `congestion_level` - Low (>20 mph), Medium (10-20 mph), High (<10 mph)

**Key Design Decisions:**
1. **No `avg_speed` in features** - Prevents data leakage
2. **Temporal train/test split** - Train on Jan-Feb, test on March
3. **Lagged features** - Use T-1 data to predict T

**Expected Metrics:**
```json
{
  "test_accuracy": "0.75-0.85",
  "test_precision": "0.70-0.85",
  "test_recall": "0.70-0.85",
  "test_f1": "0.70-0.85"
}
```

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| **namenode** | 9870, 9000 | HDFS NameNode |
| **datanode** | 9864 | HDFS DataNode |
| **spark-master** | 8081, 7077 | Spark Master |
| **spark-worker** | 8082 | Spark Worker |
| **kafka** | 9092 | Kafka Broker |
| **kafka-ui** | 8080 | Kafka Web UI |
| **zookeeper** | 2181 | Zookeeper |

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check + model status |
| `/api/current-traffic` | GET | Current traffic by cell |
| `/api/predictions` | GET | ML congestion predictions |
| `/api/hotspots` | GET | Top congested zones |
| `/api/stats` | GET | Overall statistics |
| `/api/model/info` | GET | Model details |

## 🧪 Running Tests

```bash
# Run pipeline end-to-end
python -m pytest tests/

# Test Spark jobs locally
spark-submit --master local[4] src/batch/data_cleaning_spark.py
```

## 📈 Monitoring

- **HDFS Health:** http://localhost:9870
- **Spark Jobs:** http://localhost:8081
- **Kafka Topics:** http://localhost:8080

## 🔧 Troubleshooting

**Spark Memory Issues:**
```bash
# Increase driver memory
spark-submit --driver-memory 8g src/batch/model_training_spark.py
```

**HDFS Connection Issues:**
```bash
# Check namenode status
docker logs namenode

# Verify HDFS is running
hdfs dfs -ls /
```

**Kafka Connection Issues:**
```bash
# Check Kafka logs
docker logs kafka

# Verify topics
kafka-topics.sh --list --bootstrap-server localhost:9092
```

## 📚 Technology Stack

| Category | Technologies |
|----------|-------------|
| **Storage** | Hadoop HDFS, Parquet |
| **Processing** | Apache Spark, PySpark, Scala |
| **ML** | Spark MLlib, Scikit-learn |
| **Streaming** | Apache Kafka |
| **API** | Flask, Flask-SocketIO |
| **Frontend** | React, Leaflet, Recharts |
| **Infrastructure** | Docker, Docker Compose |

## 📄 License

MIT License - See LICENSE file for details.

---

*Built for Big Data Course - December 2025*
