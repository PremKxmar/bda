# Smart City Real-Time Traffic Simulation & Predictive Analytics

## Project Summary

This project is a **Big Data analytics system** for NYC taxi traffic prediction and congestion analysis. It processes ~46 million trip records using Apache Spark and provides real-time traffic predictions via a Flask API and React dashboard.

---

## 📁 Project Structure

```
vscode2/
├── smart-city-traffic/          # Main backend project
│   ├── src/
│   │   ├── api/
│   │   │   ├── app.py           # Flask REST API (port 5000)
│   │   │   └── app_spark.py     # Spark-enabled API (alternative)
│   │   ├── batch/
│   │   │   ├── data_cleaning_spark.py      # ✅ Spark data cleaning
│   │   │   ├── feature_engineering_spark.py # ✅ Spark feature engineering
│   │   │   ├── model_training_spark.py     # ✅ Spark MLlib training
│   │   │   ├── data_cleaning.py            # Original Pandas version
│   │   │   ├── feature_engineering.py      # Original Pandas version
│   │   │   └── model_training.py           # Original sklearn version
│   │   ├── scala/
│   │   │   ├── TrafficDataPreprocessor.scala  # Scala preprocessing
│   │   │   └── build.sbt                      # Scala build config
│   │   └── streaming/
│   │       └── kafka_producer.py           # Kafka streaming producer
│   ├── data/
│   │   ├── processed/
│   │   │   ├── yellow_tripdata_*_clean.parquet  # Cleaned data
│   │   │   ├── training_features_spark.parquet  # ML features
│   │   │   └── feature_columns_spark.json
│   │   └── raw/                            # Raw CSV location
│   ├── models/
│   │   ├── spark_congestion_model/         # Spark MLlib model
│   │   ├── congestion_model.joblib         # sklearn model
│   │   ├── scaler.joblib
│   │   └── model_info_spark.json
│   ├── dashboard/                          # Static HTML dashboard
│   ├── docker-compose.yml                  # Infrastructure
│   └── requirements.txt
│
├── bigdata/                     # React Vite Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx    # Main dashboard
│   │   │   ├── Map.tsx          # Traffic map
│   │   │   └── LandingPage.tsx
│   │   ├── services/
│   │   │   ├── api.ts           # API client
│   │   │   └── mockData.ts
│   │   └── types.ts
│   ├── package.json
│   └── vite.config.ts
│
├── vscode/                      # Documentation
│   ├── PROJECT_DOCUMENTATION.md
│   └── SPARK_MLLIB_MIGRATION_GUIDE.md
│
└── yellow_tripdata_*.csv        # Raw data files (~7GB total)
```

---

## 🔧 Technical Stack

### Requirements Met:
| Requirement | Implementation | Status |
|-------------|----------------|--------|
| **Hadoop (HDFS)** | Docker: namenode, datanode | ✅ Configured |
| **Apache Spark** | PySpark 4.0.1, DataFrame API | ✅ Working |
| **Spark MLlib** | RandomForestClassifier Pipeline | ✅ Trained |
| **Python** | Data processing, API, ML | ✅ Working |
| **Scala** | TrafficDataPreprocessor.scala | ✅ Created |
| **Kafka** | Docker: Kafka + Zookeeper | ✅ Configured |

### Technologies:
- **Backend**: Python 3.11, Flask, Flask-SocketIO, PySpark 4.0.1
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Recharts
- **ML**: Spark MLlib (RandomForestClassifier), scikit-learn (fallback)
- **Data**: Parquet files, ~46 million records
- **Infrastructure**: Docker Compose (HDFS, Kafka, Spark cluster)

---

## 📊 Data Pipeline

### 1. Data Cleaning (`data_cleaning_spark.py`)
```bash
cd C:\sem6-real\vscode2\smart-city-traffic
python src/batch/data_cleaning_spark.py
```
- **Input**: 4 CSV files (~7GB): `yellow_tripdata_2015-01.csv`, `2016-01.csv`, `2016-02.csv`, `2016-03.csv`
- **Output**: Cleaned Parquet files in `data/processed/`
- **Records**: 45,963,556 cleaned trips
- **Features Added**: grid cell IDs, hour, day_of_week, speed_mph, is_manhattan

### 2. Feature Engineering (`feature_engineering_spark.py`)
```bash
python src/batch/feature_engineering_spark.py
```
- **Input**: Cleaned Parquet files
- **Output**: `training_features_spark.parquet`
- **Records**: 499,817 aggregated samples
- **Key Features** (16 total):
  - Temporal: hour, day_of_week, month, is_weekend, is_rush_hour, is_night
  - Spatial: cell_lat, cell_lon, is_manhattan_int
  - **Lagged** (prevents data leakage): prev_trip_count, prev_avg_speed, prev_congestion_label, prev_2h_trip_count, prev_2h_avg_speed
  - Historical: historical_avg_trips, historical_avg_speed
- **Target**: congestion_label (0=Low, 1=Medium, 2=High)
- **⚠️ IMPORTANT**: `avg_speed` is NOT in features (prevents data leakage!)

### 3. Model Training (`model_training_spark.py`)
```bash
python src/batch/model_training_spark.py
```
- **Algorithm**: Spark MLlib RandomForestClassifier (100 trees, maxDepth=10)
- **Train/Test Split**: Temporal (Jan-Feb 2016 = train, March 2016 = test)
- **Results**:
  - **Test Accuracy: 78.60%** (realistic, not 100%!)
  - Precision: 78.71%
  - Recall: 78.60%
  - F1-Score: 76.82%
- **Model saved to**: `models/spark_congestion_model/`

### Feature Importance (Top 5):
1. historical_avg_speed: 37.06%
2. prev_avg_speed: 16.34%
3. prev_congestion_label: 13.65%
4. prev_2h_avg_speed: 6.34%
5. cell_lon: 4.61%

---

## 🚀 How to Run

### Prerequisites:
1. **Python 3.11** with packages:
   ```bash
   pip install pyspark pandas numpy scikit-learn flask flask-cors flask-socketio pyarrow requests eventlet
   ```

2. **Windows Hadoop Setup** (required for PySpark on Windows):
   - Download `winutils.exe` and `hadoop.dll` for Hadoop 3.3.x
   - Place in `C:\hadoop\bin\`
   - The Spark scripts automatically set `HADOOP_HOME`

3. **Docker Desktop** (for infrastructure)

### Start Everything:

#### 1. Start Docker Infrastructure:
```bash
cd C:\sem6-real\vscode2\smart-city-traffic
docker-compose up -d
```
Services:
- HDFS NameNode: http://localhost:9870
- HDFS DataNode: http://localhost:9864
- Kafka: localhost:9092
- Kafka UI: http://localhost:8080
- Spark Master: http://localhost:8081
- Spark Worker: http://localhost:8082

#### 2. Start Flask API:
```bash
cd C:\sem6-real\vscode2\smart-city-traffic
python src/api/app.py
```
API runs on: http://localhost:5000

#### 3. Start React Frontend:
```bash
cd C:\sem6-real\vscode2\bigdata
npm install
npm run dev
```
Frontend runs on: http://localhost:3000

---

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/stats` | GET | Overall statistics |
| `/api/current-traffic` | GET | Current traffic data |
| `/api/predictions` | GET | ML predictions |
| `/api/hotspots?limit=5` | GET | Top congested zones |
| `/api/cell/<cell_id>` | GET | Cell details |
| `/api/geojson/cells` | GET | GeoJSON for map |

### Example API Response (`/api/hotspots`):
```json
{
  "timestamp": "2025-12-06T16:30:00Z",
  "hotspots": [
    {
      "rank": 1,
      "cell_id": "cell_25_47",
      "latitude": 40.7258,
      "longitude": -73.9901,
      "congestion_index": 0.92,
      "congestion_level": "high",
      "vehicle_count": 145,
      "avg_speed": 8.5,
      "trend": "increasing"
    }
  ]
}
```

---

## 🐛 Known Issues & Solutions

### 1. Windows Hadoop Error
**Error**: `NativeIO$Windows.access0 UnsatisfiedLinkError`
**Solution**: 
- Download `winutils.exe` and `hadoop.dll` to `C:\hadoop\bin\`
- Scripts already include this workaround:
```python
if os.name == 'nt':
    os.environ['HADOOP_HOME'] = r"C:\hadoop"
```

### 2. Port 5000 Already in Use
```bash
taskkill /F /IM python.exe
# or
netstat -ano | findstr :5000
taskkill /F /PID <PID>
```

### 3. API Crashing with Debug Mode
- Changed `debug=True` to `debug=False` in `app.py` line 549

### 4. Docker Spark Images Not Found
- Changed from `bitnami/spark:3.5` to `apache/spark:3.5.0`

---

## 📈 Model Performance

### Before Migration (Data Leakage):
- Accuracy: ~100% ❌ (unrealistic - avg_speed was in features)

### After Migration (Fixed):
- Accuracy: 78.60% ✅ (realistic prediction from historical data)

### Per-Class Performance:
| Class | Accuracy |
|-------|----------|
| Low (0) | 54.03% |
| Medium (1) | 93.66% |
| High (2) | 40.88% |

---

## 📂 Important Files

### Backend Scripts:
- `src/batch/data_cleaning_spark.py` - Run first
- `src/batch/feature_engineering_spark.py` - Run second
- `src/batch/model_training_spark.py` - Run third
- `src/api/app.py` - Flask API server

### Frontend:
- `bigdata/components/Dashboard.tsx` - Main UI
- `bigdata/services/api.ts` - API client

### Configuration:
- `docker-compose.yml` - Infrastructure setup
- `requirements.txt` - Python dependencies
- `bigdata/package.json` - Node dependencies

### Models:
- `models/spark_congestion_model/` - Spark MLlib model
- `models/congestion_model.joblib` - sklearn fallback

---

## 🔄 Quick Start Commands

```bash
# Terminal 1: Start Docker
cd C:\sem6-real\vscode2\smart-city-traffic
docker-compose up -d

# Terminal 2: Start API
cd C:\sem6-real\vscode2\smart-city-traffic
python src/api/app.py

# Terminal 3: Start Frontend
cd C:\sem6-real\vscode2\bigdata
npm run dev

# Open browser: http://localhost:3000
```

---

## 📝 Next Steps / TODO

1. **Fix API stability** - The API sometimes crashes; may need to investigate Flask-SocketIO issues
2. **Build Scala project** - Run `sbt package` in `src/scala/` directory
3. **Test HDFS integration** - Upload data to HDFS and process from there
4. **Kafka streaming** - Implement real-time data streaming with `kafka_producer.py`
5. **Improve model** - Try other algorithms (GBT, LogisticRegression) or tune hyperparameters

---

## 📚 References

- `vscode/PROJECT_DOCUMENTATION.md` - Detailed project documentation
- `vscode/SPARK_MLLIB_MIGRATION_GUIDE.md` - MLlib migration guide with data leakage fix
- `smart-city-traffic/docs/` - Architecture and API documentation

---

*Last Updated: December 6, 2025*
