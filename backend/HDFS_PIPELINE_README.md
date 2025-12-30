# HDFS Pipeline - Smart City Traffic

This document explains how to run the complete data pipeline using HDFS for distributed storage.

## Prerequisites

1. **Docker Desktop** must be running
2. **Raw CSV files** should be in `c:\sem6-real\vscode2\` directory:
   - `yellow_tripdata_2015-01.csv`
   - `yellow_tripdata_2016-01.csv`
   - `yellow_tripdata_2016-02.csv`
   - `yellow_tripdata_2016-03.csv`

---

## Step 1: Start HDFS Containers

```powershell
cd c:\sem6-real\vscode2\SmartCityTrafficSystem\backend
docker-compose up -d namenode datanode
```

Wait ~30 seconds for HDFS to initialize. Verify it's running:

```powershell
# Check containers
docker ps

# Check HDFS health
python src/batch/hdfs_utils.py health
```

**HDFS Web UI**: http://localhost:9870

---

## Step 2: Setup HDFS Directories

```powershell
python src/batch/hdfs_utils.py setup
```

This creates:
- `/smart-city-traffic/data/raw`
- `/smart-city-traffic/data/processed`
- `/smart-city-traffic/data/features`
- `/smart-city-traffic/data/models`

---

## Step 3: Upload Raw Data to HDFS

```powershell
python src/batch/hdfs_utils.py upload
```

This uploads CSV files from local to HDFS `/smart-city-traffic/data/raw/`

Verify upload:
```powershell
python src/batch/hdfs_utils.py list
```

---

## Step 4: Run Data Cleaning (HDFS Mode)

```powershell
python src/batch/data_cleaning_spark.py --hdfs
```

This:
- Reads raw CSV from HDFS
- Cleans and transforms data
- Writes cleaned Parquet to HDFS `/smart-city-traffic/data/processed/`

---

## Step 5: Run Feature Engineering (HDFS Mode)

```powershell
python src/batch/feature_engineering_spark.py --hdfs
```

This:
- Reads cleaned data from HDFS
- Creates ML features with lagged values
- Writes features to HDFS `/smart-city-traffic/data/features/`

---

## Step 6: Train ML Model (HDFS Mode)

```powershell
python src/batch/model_training_spark.py --hdfs
```

This:
- Reads training features from HDFS
- Trains Spark MLlib RandomForest model
- Saves model to HDFS `/smart-city-traffic/data/models/`
- Also saves model metadata locally for API use

---

## Step 7: Start the Application

```powershell
# Backend API
cd c:\sem6-real\vscode2\SmartCityTrafficSystem\backend
python src/api/app.py

# Frontend (in new terminal)
cd c:\sem6-real\vscode2\SmartCityTrafficSystem\frontend
npm run dev
```

Access the dashboard at: http://localhost:3000

---

## Quick Reference - Command Summary

```powershell
# Start HDFS
docker-compose up -d namenode datanode

# Setup and upload
python src/batch/hdfs_utils.py setup
python src/batch/hdfs_utils.py upload

# Run pipeline with HDFS
python src/batch/data_cleaning_spark.py --hdfs
python src/batch/feature_engineering_spark.py --hdfs
python src/batch/model_training_spark.py --hdfs

# Check HDFS contents
python src/batch/hdfs_utils.py list

# Start app
python src/api/app.py
```

---

## Local Mode (Without HDFS)

All scripts also work in local mode (without `--hdfs` flag):

```powershell
python src/batch/data_cleaning_spark.py
python src/batch/feature_engineering_spark.py
python src/batch/model_training_spark.py
```

---

## HDFS Directory Structure

```
hdfs://localhost:9000/smart-city-traffic/
├── data/
│   ├── raw/                           # Raw CSV files
│   │   ├── yellow_tripdata_2015-01/
│   │   ├── yellow_tripdata_2016-01/
│   │   ├── yellow_tripdata_2016-02/
│   │   └── yellow_tripdata_2016-03/
│   ├── processed/                     # Cleaned Parquet files
│   │   ├── yellow_tripdata_2015-01_clean.parquet/
│   │   ├── yellow_tripdata_2016-01_clean.parquet/
│   │   └── ...
│   ├── features/                      # ML training features
│   │   └── training_features_spark.parquet/
│   └── models/                        # Trained Spark MLlib model
│       └── spark_congestion_model/
```

---

## Troubleshooting

### Docker Desktop not running
```
Error: The system cannot find the file specified
```
Solution: Start Docker Desktop application

### HDFS not accessible
```
Error: Connection refused
```
Solution: Wait for containers to fully start, check with `docker logs namenode`

### No data in HDFS
```
Error: Path does not exist
```
Solution: Run `python src/batch/hdfs_utils.py upload` first
