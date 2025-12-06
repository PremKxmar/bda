"""
Smart City Traffic - Model Training (Updated)
==============================================

Trains ML models for congestion prediction using the prepared features.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
import json

# Scikit-learn imports
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)
import warnings
warnings.filterwarnings('ignore')

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

RANDOM_STATE = 42
TEST_SIZE = 0.2

# Feature columns
FEATURE_COLUMNS = [
    'hour', 'avg_speed', 'speed_std', 'trip_count', 
    'avg_distance', 'weekend_ratio', 'rush_hour_ratio',
    'cell_lat', 'cell_lon', 'is_manhattan'
]


def load_training_data():
    """Load the prepared training dataset."""
    train_path = DATA_DIR / "training_features.parquet"
    
    if not train_path.exists():
        print("ERROR: Training data not found!")
        return None
    
    print(f"Loading training data from: {train_path}")
    df = pd.read_parquet(train_path)
    print(f"Loaded {len(df):,} samples")
    
    return df


def prepare_data(df):
    """Prepare features and target for training."""
    print("\nPreparing data for training...")
    
    # Use existing columns, handle missing
    feature_cols = [c for c in FEATURE_COLUMNS if c in df.columns]
    print(f"Using features: {feature_cols}")
    
    X = df[feature_cols].copy()
    y = df['congestion_level'].copy()  # Use congestion_level from our features
    
    # Check class distribution
    print("\nTarget distribution:")
    class_counts = y.value_counts().sort_index()
    class_names = {0: 'Low', 1: 'Medium', 2: 'High'}
    for label, count in class_counts.items():
        pct = 100 * count / len(y)
        print(f"  {class_names.get(label, label)}: {count:,} ({pct:.1f}%)")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    
    print(f"\nTraining set: {len(X_train):,} samples")
    print(f"Test set: {len(X_test):,} samples")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler, feature_cols


def train_random_forest(X_train, y_train):
    """Train Random Forest Classifier."""
    print("\n" + "=" * 50)
    print("🌲 Training Random Forest Classifier...")
    print("=" * 50)
    
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5,
        max_features='sqrt',
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight='balanced'
    )
    
    start_time = datetime.now()
    rf_model.fit(X_train, y_train)
    training_time = (datetime.now() - start_time).total_seconds()
    
    print(f"  Training time: {training_time:.2f} seconds")
    
    # Cross-validation
    cv_scores = cross_val_score(rf_model, X_train, y_train, cv=5)
    print(f"  Cross-validation accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
    
    return rf_model


def evaluate_model(model, X_test, y_test, model_name="Model"):
    """Evaluate model performance."""
    print(f"\n📊 {model_name} Evaluation:")
    print("-" * 40)
    
    y_pred = model.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    
    # Classification report
    print(f"\nClassification Report:")
    class_names = ['Low', 'Medium', 'High']
    print(classification_report(y_test, y_pred, target_names=class_names))
    
    # Confusion matrix
    print("Confusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  {'':>10} Pred_Low  Pred_Med  Pred_High")
    for i, row in enumerate(cm):
        print(f"  {class_names[i]:>10}    {row[0]:4d}     {row[1]:4d}      {row[2]:4d}")
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1
    }


def save_model(model, scaler, feature_columns, metrics):
    """Save trained model and artifacts."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save model
    model_path = MODELS_DIR / "congestion_model.joblib"
    joblib.dump(model, model_path)
    print(f"\n💾 Saved model to: {model_path}")
    
    # Save scaler
    scaler_path = MODELS_DIR / "scaler.joblib"
    joblib.dump(scaler, scaler_path)
    print(f"   Saved scaler to: {scaler_path}")
    
    # Save feature columns
    features_path = MODELS_DIR / "feature_columns.json"
    with open(features_path, 'w') as f:
        json.dump(feature_columns, f)
    print(f"   Saved features to: {features_path}")
    
    # Save model info
    model_info = {
        'model_type': 'RandomForestClassifier',
        'trained_at': datetime.now().isoformat(),
        'features': feature_columns,
        'metrics': metrics,
        'classes': ['Low', 'Medium', 'High'],
        'thresholds': {
            'low': '> 20 mph',
            'medium': '10-20 mph',
            'high': '< 10 mph'
        }
    }
    
    info_path = MODELS_DIR / "model_info.json"
    with open(info_path, 'w') as f:
        json.dump(model_info, f, indent=2)
    print(f"   Saved model info to: {info_path}")


def analyze_feature_importance(model, feature_columns):
    """Analyze and display feature importance."""
    print("\n📊 Feature Importance:")
    print("-" * 40)
    
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    for i, idx in enumerate(indices):
        bar = "█" * int(importances[idx] * 50)
        print(f"  {i+1}. {feature_columns[idx]:15s}: {importances[idx]:.4f} {bar}")


def main():
    """Main execution function."""
    print("=" * 60)
    print("🚀 SMART CITY TRAFFIC - MODEL TRAINING")
    print("=" * 60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load data
    df = load_training_data()
    if df is None:
        return
    
    # Prepare data
    X_train, X_test, y_train, y_test, scaler, feature_cols = prepare_data(df)
    
    # Train model
    rf_model = train_random_forest(X_train, y_train)
    
    # Evaluate
    metrics = evaluate_model(rf_model, X_test, y_test, "Random Forest")
    
    # Feature importance
    analyze_feature_importance(rf_model, feature_cols)
    
    # Save
    save_model(rf_model, scaler, feature_cols, metrics)
    
    print("\n" + "=" * 60)
    print("✅ MODEL TRAINING COMPLETE!")
    print("=" * 60)
    print(f"\nModel ready for predictions!")
    print(f"  - Accuracy: {metrics['accuracy']*100:.1f}%")
    print(f"  - F1 Score: {metrics['f1_score']:.4f}")
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
