# 🏙️ Smart City Real-Time Traffic Simulation & Predictive Analytics

> A Distributed Streaming Pipeline with GeoSpatial Analysis and Deep Learning

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Spark](https://img.shields.io/badge/Apache%20Spark-3.5-orange.svg)
![Kafka](https://img.shields.io/badge/Apache%20Kafka-3.6-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 📋 Project Overview

This project simulates and predicts city traffic in near-real-time using a 3D interactive dashboard. It processes **7+ GB of NYC Taxi trip data** (45+ million trips) through a complete big-data pipeline featuring:

- **Real-time streaming** of vehicle positions via Kafka
- **Distributed processing** with Apache Spark
- **ML-powered predictions** for traffic congestion
- **3D visualization** with Kepler.gl

## 🎯 Problem Statement & 5 V's

| Dimension | Implementation |
|-----------|----------------|
| **Volume** | 7+ GB of NYC Taxi data (45M+ trips from 2015-2016) |
| **Velocity** | 1,000+ vehicle events/second via Kafka streaming |
| **Variety** | GPS coordinates, timestamps, trip metrics, road cells |
| **Veracity** | Data cleaning, outlier removal, missing value handling |
| **Value** | Predict congestion 15 min ahead, optimize routes |

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  NYC Taxi CSV   │────▶│   Apache Spark  │────▶│   HDFS/Parquet  │
│  (7+ GB Raw)    │     │   (Batch ETL)   │     │   (Processed)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Kafka Producer │────▶│ Spark Streaming │────▶│   ML Scoring    │
│  (Trip Replay)  │     │  (Real-time)    │     │  (Predictions)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Kepler.gl     │◀────│   Flask API     │◀────│  Kafka Output   │
│  (3D Dashboard) │     │   (Backend)     │     │  (Events)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 📁 Project Structure

```
smart-city-traffic/
├── README.md
├── requirements.txt
├── docker-compose.yml
├── .gitignore
│
├── data/
│   ├── raw/                    # Symlink to CSV files
│   └── processed/              # Cleaned parquet files
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   └── 03_model_training.ipynb
│
├── src/
│   ├── batch/
│   │   ├── data_cleaning.py
│   │   ├── feature_engineering.py
│   │   └── model_training.py
│   │
│   ├── streaming/
│   │   ├── kafka_producer.py
│   │   └── spark_streaming.py
│   │
│   └── api/
│       └── app.py
│
├── models/                     # Saved ML models
│
├── dashboard/                  # Frontend (Kepler.gl)
│
└── docs/
    ├── architecture.md
    ├── api_documentation.md
    └── frontend_prompt.md
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Docker Desktop
- 16GB+ RAM recommended

### 1. Setup Environment
```bash
cd smart-city-traffic
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Start Infrastructure
```bash
docker-compose up -d
```

### 3. Run Data Pipeline
```bash
# Batch processing
python src/batch/data_cleaning.py
python src/batch/feature_engineering.py
python src/batch/model_training.py
```

### 4. Start Streaming
```bash
# Terminal 1: Kafka producer
python src/streaming/kafka_producer.py

# Terminal 2: Spark streaming
python src/streaming/spark_streaming.py
```

### 5. Launch Dashboard
```bash
python src/api/app.py
# Open http://localhost:5000
```

## 📊 Dataset

**Source**: NYC Taxi & Limousine Commission (TLC) Trip Record Data

| File | Size | Records |
|------|------|---------|
| yellow_tripdata_2015-01.csv | 1.89 GB | ~12M trips |
| yellow_tripdata_2016-01.csv | 1.63 GB | ~11M trips |
| yellow_tripdata_2016-02.csv | 1.70 GB | ~11M trips |
| yellow_tripdata_2016-03.csv | 1.83 GB | ~12M trips |
| **Total** | **~7 GB** | **~46M trips** |

## 🤖 Machine Learning

- **Algorithm**: Random Forest Classifier (Spark MLlib)
- **Features**: hour, day_of_week, cell_id, avg_speed, vehicle_count
- **Target**: Congestion level (low/medium/high)
- **Accuracy**: ~82% (3-class classification)

## 🎨 Visualization Features

- 🚕 Moving taxi dots (colored by speed)
- 🔥 3D hexagon heatmap (congestion density)
- 🔮 Predicted jam zones (15 min ahead)
- ⏱️ Time slider (replay entire day)
- 📊 Real-time KPI dashboard

## 👨‍💻 Author

Final Year Big Data Analytics Project

## 📄 License

MIT License
