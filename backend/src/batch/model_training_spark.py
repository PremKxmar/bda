"""
Smart City Traffic - Spark MLlib Model Training Module
=======================================================

This script trains ML models for congestion prediction using Apache Spark MLlib:
- Reads training features from HDFS or local filesystem
- Random Forest Classifier (primary model)
- Proper train/test split (temporal - no data leakage)
- Feature scaling and pipeline
- Model evaluation and metrics
- Saves trained model to HDFS or local

Key Changes from Original:
- Uses Spark MLlib instead of Scikit-learn
- Supports HDFS for distributed storage
- Temporal train/test split (Jan-Feb train, March test)
- No avg_speed in features (prevents data leakage)

Usage:
    python src/batch/model_training_spark.py             # Local mode
    python src/batch/model_training_spark.py --hdfs      # HDFS mode
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json
import argparse

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, count

from pyspark.ml import Pipeline
from pyspark.ml.feature import (
    VectorAssembler, 
    StandardScaler, 
    StringIndexer,
    IndexToString
)
from pyspark.ml.classification import RandomForestClassifier, GBTClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# CONFIGURATION
# =============================================================================

# HDFS Configuration
HDFS_NAMENODE = "hdfs://localhost:9000"
HDFS_FEATURES_DIR = "/smart-city-traffic/data/features"
HDFS_MODELS_DIR = "/smart-city-traffic/data/models"

# Local Configuration
LOCAL_FEATURES_DIR = PROJECT_ROOT / "data" / "processed"
LOCAL_MODELS_DIR = PROJECT_ROOT / "models"

# Model parameters
RANDOM_SEED = 42


# Spark cluster configuration
SPARK_MASTER_LOCAL = "local[*]"
SPARK_MASTER_CLUSTER = "spark://localhost:7077"


def create_spark_session(use_hdfs=False, use_cluster=False):
    """
    Create and configure Spark session for ML training.
    
    Args:
        use_hdfs: If True, configure HDFS as default filesystem
        use_cluster: If True, connect to Spark cluster; else local mode
    """
    import os
    
    # Windows workaround: Set Hadoop home for winutils.exe
    if os.name == 'nt':  # Windows
        hadoop_home = r"C:\hadoop"
        os.environ['HADOOP_HOME'] = hadoop_home
        os.environ['hadoop.home.dir'] = hadoop_home
        if hadoop_home not in os.environ.get('PATH', ''):
            os.environ['PATH'] = os.environ.get('PATH', '') + f";{hadoop_home}\\bin"
    
    # Determine master URL
    if use_cluster:
        master = SPARK_MASTER_CLUSTER
        shuffle_partitions = 200
        mode_str = f"Cluster ({master})"
    else:
        master = SPARK_MASTER_LOCAL
        shuffle_partitions = 50
        mode_str = "Local"
    
    builder = SparkSession.builder \
        .appName("SmartCityTraffic-MLlibTraining") \
        .master(master) \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions)) \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
    
    # Add HDFS configuration if using HDFS
    if use_hdfs:
        builder = builder \
            .config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE) \
            .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
    
    # Add cluster-specific configs
    if use_cluster:
        builder = builder \
            .config("spark.submit.deployMode", "client") \
            .config("spark.dynamicAllocation.enabled", "false")
    
    spark = builder.getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    print("=" * 60)
    print("Spark Session Created for MLlib Training")
    print(f"  App Name: {spark.sparkContext.appName}")
    print(f"  Spark Version: {spark.version}")
    print(f"  Mode: {mode_str}")
    print(f"  HDFS Mode: {use_hdfs}")
    if use_hdfs:
        print(f"  HDFS Namenode: {HDFS_NAMENODE}")
    print("=" * 60)
    
    return spark


def load_training_data(spark, use_hdfs=False):
    """Load the prepared training dataset from HDFS or local."""
    if use_hdfs:
        features_path = f"{HDFS_NAMENODE}{HDFS_FEATURES_DIR}/training_features_spark.parquet"
    else:
        features_path = str(LOCAL_FEATURES_DIR / "training_features_spark.parquet")
        if not (LOCAL_FEATURES_DIR / "training_features_spark.parquet").exists():
            print(f"ERROR: Training data not found at {features_path}")
            print("Run feature_engineering_spark.py first!")
            return None, None
    
    print(f"\nLoading training data from: {features_path}")
    
    try:
        df = spark.read.parquet(features_path)
        print(f"  ✓ Loaded {df.count():,} samples")
    except Exception as e:
        print(f"ERROR loading data: {e}")
        if use_hdfs:
            print("  Make sure feature data is in HDFS!")
            print("  Run: python src/batch/feature_engineering_spark.py --hdfs")
        return None, None
    
    # Load feature columns (always from local - saved by feature engineering)
    features_json_path = LOCAL_FEATURES_DIR / "feature_columns_spark.json"
    with open(features_json_path, 'r') as f:
        feature_columns = json.load(f)
    
    print(f"  Features: {len(feature_columns)} columns")
    
    return df, feature_columns


def analyze_data(df):
    """Analyze the training data."""
    print("\n" + "=" * 60)
    print("DATA ANALYSIS")
    print("=" * 60)
    
    # Class distribution
    print("\nTarget Distribution:")
    df.groupBy("congestion_label", "congestion_level") \
        .count() \
        .orderBy("congestion_label") \
        .show()
    
    # Train/Test split
    print("\nTemporal Split Distribution:")
    df.groupBy("dataset_split").count().show()
    
    # Sample data
    print("\nSample Features:")
    df.select("hour", "day_of_week", "prev_trip_count", "prev_avg_speed", 
              "congestion_label").show(5)


def create_train_test_split(df):
    """
    Create temporal train/test split.
    Train: January + February data
    Test: March data
    
    This is CRITICAL to prevent temporal data leakage!
    """
    print("\n" + "=" * 60)
    print("CREATING TEMPORAL TRAIN/TEST SPLIT")
    print("=" * 60)
    
    train_df = df.filter(col("dataset_split") == "train")
    test_df = df.filter(col("dataset_split") == "test")
    
    train_count = train_df.count()
    test_count = test_df.count()
    
    print(f"\n  Training set: {train_count:,} samples")
    print(f"  Test set: {test_count:,} samples")
    print(f"  Test ratio: {100 * test_count / (train_count + test_count):.1f}%")
    
    print("\n  Train data months:")
    train_df.groupBy("month").count().orderBy("month").show()
    
    print("  Test data months:")
    test_df.groupBy("month").count().orderBy("month").show()
    
    return train_df, test_df


def create_ml_pipeline(feature_columns):
    """
    Create Spark MLlib pipeline with:
    - VectorAssembler: Combine features into vector
    - StandardScaler: Normalize features
    - RandomForestClassifier: Main model
    """
    print("\n" + "=" * 60)
    print("CREATING ML PIPELINE")
    print("=" * 60)
    
    # Step 1: Assemble features into vector
    assembler = VectorAssembler(
        inputCols=feature_columns,
        outputCol="features_raw",
        handleInvalid="skip"
    )
    print("  1. VectorAssembler - combining features")
    
    # Step 2: Scale features
    scaler = StandardScaler(
        inputCol="features_raw",
        outputCol="features",
        withStd=True,
        withMean=True
    )
    print("  2. StandardScaler - normalizing features")
    
    # Step 3: Random Forest Classifier
    rf = RandomForestClassifier(
        featuresCol="features",
        labelCol="congestion_label",
        predictionCol="prediction",
        probabilityCol="probability",
        rawPredictionCol="rawPrediction",
        numTrees=100,
        maxDepth=10,
        minInstancesPerNode=10,
        featureSubsetStrategy="sqrt",
        seed=RANDOM_SEED
    )
    print("  3. RandomForestClassifier - 100 trees, maxDepth=10")
    
    # Create pipeline
    pipeline = Pipeline(stages=[assembler, scaler, rf])
    print("\n  Pipeline created successfully!")
    
    return pipeline


def train_model(pipeline, train_df):
    """Train the model on training data."""
    print("\n" + "=" * 60)
    print("TRAINING MODEL")
    print("=" * 60)
    
    start_time = datetime.now()
    
    print("\n  Training Random Forest model...")
    print("  This may take a few minutes...")
    
    # Fit the pipeline
    model = pipeline.fit(train_df)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n  Training completed in {duration:.1f} seconds")
    
    # Get the trained RF model
    rf_model = model.stages[-1]
    print(f"\n  Model details:")
    print(f"    - Number of trees: {rf_model.getNumTrees}")
    print(f"    - Total nodes: {rf_model.totalNumNodes}")
    
    return model


def evaluate_model(model, test_df, train_df):
    """Evaluate the trained model on test data."""
    print("\n" + "=" * 60)
    print("EVALUATING MODEL")
    print("=" * 60)
    
    # Make predictions on test set
    print("\n  Making predictions on test set...")
    test_predictions = model.transform(test_df)
    
    # Make predictions on train set (for comparison)
    train_predictions = model.transform(train_df)
    
    # Create evaluators
    accuracy_evaluator = MulticlassClassificationEvaluator(
        labelCol="congestion_label",
        predictionCol="prediction",
        metricName="accuracy"
    )
    
    precision_evaluator = MulticlassClassificationEvaluator(
        labelCol="congestion_label",
        predictionCol="prediction",
        metricName="weightedPrecision"
    )
    
    recall_evaluator = MulticlassClassificationEvaluator(
        labelCol="congestion_label",
        predictionCol="prediction",
        metricName="weightedRecall"
    )
    
    f1_evaluator = MulticlassClassificationEvaluator(
        labelCol="congestion_label",
        predictionCol="prediction",
        metricName="f1"
    )
    
    # Calculate metrics
    metrics = {
        "train_accuracy": accuracy_evaluator.evaluate(train_predictions),
        "test_accuracy": accuracy_evaluator.evaluate(test_predictions),
        "test_precision": precision_evaluator.evaluate(test_predictions),
        "test_recall": recall_evaluator.evaluate(test_predictions),
        "test_f1": f1_evaluator.evaluate(test_predictions)
    }
    
    print("\n  TRAINING SET METRICS:")
    print(f"    Accuracy: {metrics['train_accuracy']:.4f}")
    
    print("\n  TEST SET METRICS (on unseen March data):")
    print(f"    Accuracy:  {metrics['test_accuracy']:.4f}")
    print(f"    Precision: {metrics['test_precision']:.4f}")
    print(f"    Recall:    {metrics['test_recall']:.4f}")
    print(f"    F1-Score:  {metrics['test_f1']:.4f}")
    
    # Confusion matrix
    print("\n  CONFUSION MATRIX (Test Set):")
    test_predictions.groupBy("congestion_label", "prediction") \
        .count() \
        .orderBy("congestion_label", "prediction") \
        .show()
    
    # Per-class accuracy
    print("\n  PER-CLASS PERFORMANCE:")
    for label in [0, 1, 2]:
        class_df = test_predictions.filter(col("congestion_label") == label)
        correct = class_df.filter(col("prediction") == label).count()
        total = class_df.count()
        if total > 0:
            class_acc = correct / total
            class_name = ["Low", "Medium", "High"][label]
            print(f"    {class_name} (label={label}): {correct}/{total} = {class_acc:.4f}")
    
    return metrics, test_predictions


def get_feature_importance(model, feature_columns):
    """Extract feature importance from Random Forest model."""
    print("\n" + "=" * 60)
    print("FEATURE IMPORTANCE")
    print("=" * 60)
    
    rf_model = model.stages[-1]
    importances = rf_model.featureImportances.toArray()
    
    # Combine with feature names
    feature_importance = list(zip(feature_columns, importances))
    feature_importance.sort(key=lambda x: x[1], reverse=True)
    
    print("\n  Top 10 Most Important Features:")
    for i, (feature, importance) in enumerate(feature_importance[:10], 1):
        print(f"    {i:2d}. {feature}: {importance:.4f}")
    
    return dict(feature_importance)


def save_model(model, feature_columns, metrics, feature_importance, use_hdfs=False):
    """Save the trained model and metadata."""
    print("\n" + "=" * 60)
    print("SAVING MODEL")
    print("=" * 60)
    
    # Ensure local models directory exists (always save metadata locally)
    LOCAL_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save Spark MLlib model
    if use_hdfs:
        model_path = f"{HDFS_NAMENODE}{HDFS_MODELS_DIR}/spark_congestion_model"
    else:
        model_path = str(LOCAL_MODELS_DIR / "spark_congestion_model")
    
    print(f"\n  Saving Spark MLlib model to: {model_path}")
    model.write().overwrite().save(model_path)
    print("  ✓ Model saved successfully!")
    
    # Save model metadata (always locally for API use)
    model_info = {
        "model_type": "Spark MLlib RandomForestClassifier",
        "trained_at": datetime.now().isoformat(),
        "spark_model_path": model_path,
        "features": feature_columns,
        "metrics": {
            "train_accuracy": round(metrics["train_accuracy"], 4),
            "test_accuracy": round(metrics["test_accuracy"], 4),
            "test_precision": round(metrics["test_precision"], 4),
            "test_recall": round(metrics["test_recall"], 4),
            "test_f1": round(metrics["test_f1"], 4)
        },
        "classes": ["Low", "Medium", "High"],
        "thresholds": {
            "low": "> 20 mph",
            "medium": "10-20 mph",
            "high": "< 10 mph"
        },
        "feature_importance": {k: round(v, 4) for k, v in feature_importance.items()},
        "hdfs_mode": use_hdfs,
        "notes": [
            "Model uses Spark MLlib RandomForestClassifier",
            "avg_speed NOT included in features (prevents data leakage)",
            "Temporal train/test split (Jan-Feb train, March test)",
            "Uses lagged features for true prediction"
        ]
    }
    
    info_path = LOCAL_MODELS_DIR / "model_info_spark.json"
    with open(info_path, 'w') as f:
        json.dump(model_info, f, indent=2)
    print(f"  ✓ Saved model info to: {info_path}")
    
    # Save feature columns for API
    features_path = LOCAL_MODELS_DIR / "feature_columns_spark.json"
    with open(features_path, 'w') as f:
        json.dump(feature_columns, f, indent=2)
    print(f"  ✓ Saved feature columns to: {features_path}")
    
    return model_path


def main():
    """Main execution function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Spark MLlib Model Training for Smart City Traffic")
    parser.add_argument("--hdfs", action="store_true", help="Use HDFS for input/output")
    parser.add_argument("--cluster", action="store_true",
                        help="Submit to Spark cluster (spark://localhost:7077) instead of local mode")
    args = parser.parse_args()
    
    use_hdfs = args.hdfs
    use_cluster = args.cluster
    
    print("\n" + "=" * 60)
    print("SMART CITY TRAFFIC - SPARK MLlib MODEL TRAINING")
    print("=" * 60)
    print(f"Storage Mode: {'HDFS' if use_hdfs else 'Local'}")
    print(f"Spark Mode: {'Cluster' if use_cluster else 'Local'}")
    print("\n  NOTE: This model uses Spark MLlib and proper ML practices:")
    print("    - avg_speed is NOT in features (no data leakage)")
    print("    - Temporal train/test split (Jan-Feb train, March test)")
    print("    - Expected accuracy: 70-85% (realistic, not 100%!)")
    
    start_time = datetime.now()
    
    # Create Spark session
    spark = create_spark_session(use_hdfs=use_hdfs, use_cluster=use_cluster)
    
    # Load data
    df, feature_columns = load_training_data(spark, use_hdfs=use_hdfs)
    if df is None:
        spark.stop()
        return
    
    # Analyze data
    analyze_data(df)
    
    # Create train/test split
    train_df, test_df = create_train_test_split(df)
    
    # Check if we have enough data
    if train_df.count() < 100 or test_df.count() < 100:
        print("\nWARNING: Not enough data for training!")
        print("Make sure you have data from multiple months.")
        
        # Fall back to random split if temporal split doesn't work
        print("\nFalling back to random 80/20 split...")
        train_df, test_df = df.randomSplit([0.8, 0.2], seed=RANDOM_SEED)
        print(f"  Training set: {train_df.count():,} samples")
        print(f"  Test set: {test_df.count():,} samples")
    
    # Create pipeline
    pipeline = create_ml_pipeline(feature_columns)
    
    # Train model
    model = train_model(pipeline, train_df)
    
    # Evaluate model
    metrics, predictions = evaluate_model(model, test_df, train_df)
    
    # Get feature importance
    feature_importance = get_feature_importance(model, feature_columns)
    
    # Save model
    model_path = save_model(model, feature_columns, metrics, feature_importance, use_hdfs=use_hdfs)
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"\n  Mode: {'HDFS' if use_hdfs else 'Local'}")
    print(f"  Duration: {duration:.1f} seconds")
    print(f"  Model saved to: {model_path}")
    print(f"\n  TEST ACCURACY: {metrics['test_accuracy']:.4f}")
    print(f"\n  This accuracy is REALISTIC because:")
    print("    - avg_speed is not in features")
    print("    - Model predicts future congestion from past data")
    print("    - Test data is from a different time period")
    print("=" * 60)
    
    spark.stop()


if __name__ == "__main__":
    main()
