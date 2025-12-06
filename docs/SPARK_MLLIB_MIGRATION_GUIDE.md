# 🔄 Spark MLlib Migration Guide

## Objective

Migrate the current ML pipeline from **Scikit-learn** to **Apache Spark MLlib** and fix the **overfitting problem** (100% accuracy due to data leakage).

---

## Current Problems to Fix

### Problem 1: Using Scikit-learn instead of Spark MLlib
- Current implementation uses Scikit-learn's RandomForestClassifier
- For a Big Data project, we should use Spark MLlib for consistency
- Demonstrates full Spark ecosystem usage (Spark SQL + Spark MLlib)

### Problem 2: Overfitting / Data Leakage (100% Accuracy)
- **Root Cause**: The target variable `congestion_level` is directly derived from `avg_speed`:
  ```python
  if avg_speed > 20: "Low"
  elif avg_speed >= 10: "Medium"
  else: "High"
  ```
- The model sees `avg_speed` as a feature and learns the exact threshold rules
- This is NOT a real prediction - it's just memorizing the derivation formula

### Solution: True Predictive Model
- Remove `avg_speed` from features (it leaks the target)
- Predict congestion at time T+15 using features from time T (temporal prediction)
- Use proper train/test split (train on earlier months, test on later months)

---

## Migration Steps

### Step 1: Update Feature Engineering

**File**: `src/batch/feature_engineering_spark.py` (new file)

**Task**: Rewrite feature engineering using PySpark instead of Pandas

```python
# Use PySpark DataFrame operations
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, stddev, hour, dayofweek, when, lag
from pyspark.sql.window import Window

# Create Spark session
spark = SparkSession.builder \
    .appName("TrafficFeatureEngineering") \
    .config("spark.driver.memory", "8g") \
    .getOrCreate()

# Read parquet files
df = spark.read.parquet("data/processed/*_clean.parquet")
```

**Features to Create** (WITHOUT avg_speed for prediction):
1. `hour` - Hour of day (0-23)
2. `day_of_week` - Day of week (0-6)
3. `is_weekend` - Boolean (Saturday/Sunday)
4. `is_rush_hour` - Boolean (7-9 AM, 5-7 PM)
5. `cell_lat` - Cell latitude index
6. `cell_lon` - Cell longitude index
7. `is_manhattan` - Boolean
8. `prev_hour_trip_count` - Trip count from previous hour (lagged feature)
9. `prev_hour_congestion` - Congestion from previous hour (lagged feature)
10. `historical_avg_congestion` - Average congestion for this cell+hour combination

**Target Variable**:
- `congestion_level` - Derived from avg_speed but NOT included in features
- Classes: "Low" (>20 mph), "Medium" (10-20 mph), "High" (<10 mph)

---

### Step 2: Create Spark MLlib Training Script

**File**: `src/batch/model_training_spark.py` (new file)

**Task**: Train a Random Forest model using Spark MLlib

```python
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StringIndexer, StandardScaler
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

# 1. Prepare features
feature_columns = [
    "hour", "day_of_week", "is_weekend", "is_rush_hour",
    "cell_lat", "cell_lon", "is_manhattan",
    "prev_hour_trip_count", "historical_avg_congestion"
]
# NOTE: avg_speed is NOT included to prevent data leakage

# 2. Create pipeline
assembler = VectorAssembler(inputCols=feature_columns, outputCol="features")
scaler = StandardScaler(inputCol="features", outputCol="scaled_features")
label_indexer = StringIndexer(inputCol="congestion_level", outputCol="label")

rf = RandomForestClassifier(
    featuresCol="scaled_features",
    labelCol="label",
    numTrees=100,
    maxDepth=10,
    seed=42
)

pipeline = Pipeline(stages=[assembler, scaler, label_indexer, rf])

# 3. Train/Test Split - Use temporal split
# Train on January-February, Test on March
train_df = df.filter(col("month").isin([1, 2]))
test_df = df.filter(col("month") == 3)

# 4. Train model
model = pipeline.fit(train_df)

# 5. Evaluate
predictions = model.transform(test_df)
evaluator = MulticlassClassificationEvaluator(
    labelCol="label", 
    predictionCol="prediction", 
    metricName="accuracy"
)
accuracy = evaluator.evaluate(predictions)
print(f"Test Accuracy: {accuracy:.4f}")

# 6. Save model
model.write().overwrite().save("models/spark_congestion_model")
```

---

### Step 3: Create Lagged Features for True Prediction

**Task**: Create time-shifted features so model predicts FUTURE congestion

```python
from pyspark.sql.window import Window
from pyspark.sql.functions import lag, lead

# Define window partitioned by cell, ordered by time
window_spec = Window.partitionBy("cell_lat", "cell_lon").orderBy("timestamp")

# Create lagged features (data from PREVIOUS time period)
df = df.withColumn("prev_trip_count", lag("trip_count", 1).over(window_spec))
df = df.withColumn("prev_avg_speed", lag("avg_speed", 1).over(window_spec))
df = df.withColumn("prev_congestion", lag("congestion_level", 1).over(window_spec))

# Target: CURRENT congestion (we predict this from PREVIOUS features)
# This ensures no data leakage - we use past data to predict present/future
```

---

### Step 4: Update API to Load Spark Model

**File**: `src/api/app.py`

**Task**: Update model loading to use Spark MLlib model

```python
from pyspark.ml import PipelineModel

# Load Spark MLlib model
spark = SparkSession.builder.appName("TrafficAPI").getOrCreate()
model = PipelineModel.load("models/spark_congestion_model")

# For real-time predictions, convert input to Spark DataFrame
def predict_congestion(features_dict):
    # Create single-row DataFrame
    input_df = spark.createDataFrame([features_dict])
    prediction = model.transform(input_df)
    return prediction.select("prediction").collect()[0][0]
```

---

### Step 5: Proper Train/Test Split Strategy

**Task**: Implement temporal train/test split to avoid data leakage

```
Training Data:
├── yellow_tripdata_2015-01 (January 2015)
├── yellow_tripdata_2016-01 (January 2016)
└── yellow_tripdata_2016-02 (February 2016)

Testing Data:
└── yellow_tripdata_2016-03 (March 2016)
```

This ensures:
- Model learns patterns from Jan-Feb
- Model is tested on completely unseen March data
- No temporal leakage (future data doesn't leak into training)

---

### Step 6: Expected Results After Fix

**Before (Overfitting)**:
```json
{
  "accuracy": 1.0,
  "precision": 1.0,
  "recall": 1.0,
  "f1_score": 1.0
}
```

**After (Realistic)**:
```json
{
  "accuracy": 0.75-0.85,
  "precision": 0.70-0.85,
  "recall": 0.70-0.85,
  "f1_score": 0.70-0.85
}
```

A realistic accuracy of 75-85% is actually GOOD for traffic prediction!

---

## File Changes Summary

### New Files to Create:
1. `src/batch/feature_engineering_spark.py` - Spark-based feature engineering
2. `src/batch/model_training_spark.py` - Spark MLlib model training

### Files to Modify:
1. `src/api/app.py` - Update to load Spark model
2. `models/model_info.json` - Update with new metrics

### Files to Keep:
1. `src/batch/data_cleaning.py` - Data cleaning can stay (or convert to Spark)
2. All frontend files - No changes needed

---

## Detailed Implementation Tasks

### Task 1: Feature Engineering with Spark

Create `src/batch/feature_engineering_spark.py`:

1. Initialize SparkSession with sufficient memory
2. Read all cleaned parquet files using `spark.read.parquet()`
3. Create temporal features:
   - Extract hour, day_of_week, month from timestamp
   - Create is_weekend, is_rush_hour boolean flags
4. Create spatial features:
   - cell_lat, cell_lon indices
   - is_manhattan boolean
5. Create lagged features using Window functions:
   - Previous hour's trip count
   - Previous hour's average speed (for context, not as direct feature)
   - Historical average for this cell+hour combination
6. Create target variable:
   - Calculate avg_speed per cell per hour
   - Derive congestion_level from avg_speed
   - DROP avg_speed from final features to prevent leakage
7. Save processed features to parquet

### Task 2: Model Training with Spark MLlib

Create `src/batch/model_training_spark.py`:

1. Initialize SparkSession
2. Load processed features from parquet
3. Define feature columns (EXCLUDING avg_speed)
4. Create ML Pipeline:
   - VectorAssembler to combine features
   - StandardScaler to normalize
   - StringIndexer for labels
   - RandomForestClassifier
5. Split data temporally (not randomly):
   - Train: January + February data
   - Test: March data
6. Train pipeline on training data
7. Evaluate on test data:
   - Accuracy
   - Precision, Recall, F1 per class
   - Confusion matrix
8. Save model using `model.write().save()`
9. Save model metadata to JSON

### Task 3: Update API for Spark Model

Modify `src/api/app.py`:

1. Initialize SparkSession in API startup
2. Load PipelineModel from saved path
3. Update prediction function:
   - Accept feature dictionary
   - Convert to Spark DataFrame
   - Run through pipeline
   - Extract prediction
4. Update `/api/predictions` endpoint to use new model

---

## Validation Checklist

After implementation, verify:

- [ ] Spark MLlib model trains without errors
- [ ] Test accuracy is realistic (70-85%), not 100%
- [ ] `avg_speed` is NOT in feature columns
- [ ] Temporal train/test split is used (not random)
- [ ] Model can make predictions in API
- [ ] Dashboard still displays predictions correctly
- [ ] Model metadata JSON has realistic metrics

---

## Commands to Run

```bash
# 1. Run new feature engineering
cd smart-city-traffic
python src/batch/feature_engineering_spark.py

# 2. Train Spark MLlib model
python src/batch/model_training_spark.py

# 3. Verify model saved
ls models/spark_congestion_model/

# 4. Start API with new model
python src/api/app.py

# 5. Test prediction endpoint
curl http://localhost:5000/api/predictions
```

---

## Additional Notes

### Why This Matters for Big Data Project:

1. **Demonstrates Spark MLlib**: Shows understanding of distributed ML
2. **Proper ML Practices**: No data leakage, proper validation
3. **Realistic Results**: 75-85% accuracy is believable and defensible
4. **End-to-End Spark**: Spark for ETL + Spark for ML = consistent tech stack

### Common Pitfalls to Avoid:

1. Don't include `avg_speed` as a feature (causes leakage)
2. Don't use random train/test split (causes temporal leakage)
3. Don't train and test on same time period
4. Don't expect 100% accuracy (that's a red flag!)

---

*This guide provides all steps needed to migrate from Scikit-learn to Spark MLlib and fix the overfitting problem.*
