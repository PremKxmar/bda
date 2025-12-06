"""
Smart City Traffic - Model Training Module
==========================================

This script trains ML models for congestion prediction:
- Random Forest Classifier (primary)
- Gradient Boosting (comparison)
- Evaluates model performance
- Saves trained model for streaming inference

Usage:
    python src/batch/model_training.py
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
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix
)
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

# Model parameters
RANDOM_STATE = 42
TEST_SIZE = 0.2


def load_training_data():
    """Load the prepared training dataset."""
    train_path = DATA_DIR / "training_features.parquet"
    
    if not train_path.exists():
        print("ERROR: Training data not found!")
        print("Run feature_engineering.py first.")
        return None, None
    
    print(f"Loading training data from: {train_path}")
    df = pd.read_parquet(train_path)
    print(f"Loaded {len(df):,} samples")
    
    # Load feature columns
    features_path = DATA_DIR / "feature_columns.txt"
    with open(features_path, 'r') as f:
        feature_columns = [line.strip() for line in f.readlines()]
    
    print(f"Features: {feature_columns}")
    
    return df, feature_columns


def prepare_data(df, feature_columns):
    """Prepare features and target for training."""
    print("\nPreparing data for training...")
    
    X = df[feature_columns].copy()
    y = df['congestion_label'].copy()
    
    # Check class distribution
    print("\nTarget distribution:")
    class_counts = y.value_counts().sort_index()
    class_names = {0: 'low', 1: 'medium', 2: 'high'}
    for label, count in class_counts.items():
        print(f"  {class_names[label]}: {count:,} ({100*count/len(y):.1f}%)")
    
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
    
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler


def train_random_forest(X_train, y_train):
    """Train Random Forest Classifier."""
    print("\n" + "="*50)
    print("Training Random Forest Classifier...")
    print("="*50)
    
    # Define model with good defaults
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5,
        max_features='sqrt',
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight='balanced'  # Handle imbalanced classes
    )
    
    # Train
    start_time = datetime.now()
    rf_model.fit(X_train, y_train)
    training_time = (datetime.now() - start_time).total_seconds()
    
    print(f"Training time: {training_time:.2f} seconds")
    
    # Cross-validation score
    cv_scores = cross_val_score(rf_model, X_train, y_train, cv=5, scoring='accuracy')
    print(f"Cross-validation accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
    
    return rf_model


def train_gradient_boosting(X_train, y_train):
    """Train Gradient Boosting Classifier for comparison."""
    print("\n" + "="*50)
    print("Training Gradient Boosting Classifier...")
    print("="*50)
    
    gb_model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=7,
        learning_rate=0.1,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=RANDOM_STATE
    )
    
    start_time = datetime.now()
    gb_model.fit(X_train, y_train)
    training_time = (datetime.now() - start_time).total_seconds()
    
    print(f"Training time: {training_time:.2f} seconds")
    
    cv_scores = cross_val_score(gb_model, X_train, y_train, cv=5, scoring='accuracy')
    print(f"Cross-validation accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
    
    return gb_model


def evaluate_model(model, X_test, y_test, model_name):
    """Evaluate model performance."""
    print(f"\n{'='*50}")
    print(f"Evaluation: {model_name}")
    print("="*50)
    
    # Predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test) if hasattr(model, 'predict_proba') else None
    
    # Metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    print(f"\nMetrics:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    
    # Classification report
    class_names = ['low', 'medium', 'high']
    print(f"\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=class_names))
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print("Confusion Matrix:")
    print(f"              Predicted")
    print(f"              low  med  high")
    for i, row in enumerate(cm):
        print(f"  Actual {class_names[i]:>4}: {row}")
    
    metrics = {
        'model_name': model_name,
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1_score': float(f1)
    }
    
    return metrics


def get_feature_importance(model, feature_columns):
    """Get feature importance from the model."""
    if hasattr(model, 'feature_importances_'):
        importance = pd.DataFrame({
            'feature': feature_columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\nFeature Importance:")
        for _, row in importance.iterrows():
            bar = '█' * int(row['importance'] * 50)
            print(f"  {row['feature']:20s}: {row['importance']:.4f} {bar}")
        
        return importance
    return None


def save_model(model, scaler, feature_columns, metrics, model_name):
    """Save trained model and associated files."""
    print(f"\nSaving {model_name}...")
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save model
    model_path = MODELS_DIR / f"{model_name.lower().replace(' ', '_')}.joblib"
    joblib.dump(model, model_path)
    print(f"  Model saved: {model_path}")
    
    # Save scaler
    scaler_path = MODELS_DIR / "feature_scaler.joblib"
    joblib.dump(scaler, scaler_path)
    print(f"  Scaler saved: {scaler_path}")
    
    # Save feature columns
    features_path = MODELS_DIR / "feature_columns.json"
    with open(features_path, 'w') as f:
        json.dump(feature_columns, f, indent=2)
    print(f"  Features saved: {features_path}")
    
    # Save metrics
    metrics_path = MODELS_DIR / f"{model_name.lower().replace(' ', '_')}_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"  Metrics saved: {metrics_path}")
    
    # Save model info
    model_info = {
        'model_name': model_name,
        'model_file': model_path.name,
        'scaler_file': scaler_path.name,
        'features_file': features_path.name,
        'n_features': len(feature_columns),
        'n_classes': 3,
        'class_names': ['low', 'medium', 'high'],
        'metrics': metrics,
        'trained_at': datetime.now().isoformat()
    }
    
    info_path = MODELS_DIR / "model_info.json"
    with open(info_path, 'w') as f:
        json.dump(model_info, f, indent=2)
    print(f"  Info saved: {info_path}")


def main():
    """Main execution function."""
    print("="*60)
    print("SMART CITY TRAFFIC - MODEL TRAINING")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load data
    df, feature_columns = load_training_data()
    if df is None:
        return
    
    # Prepare data
    X_train, X_test, y_train, y_test, scaler = prepare_data(df, feature_columns)
    
    # Train Random Forest
    rf_model = train_random_forest(X_train, y_train)
    rf_metrics = evaluate_model(rf_model, X_test, y_test, "Random Forest")
    rf_importance = get_feature_importance(rf_model, feature_columns)
    
    # Train Gradient Boosting (for comparison)
    gb_model = train_gradient_boosting(X_train, y_train)
    gb_metrics = evaluate_model(gb_model, X_test, y_test, "Gradient Boosting")
    
    # Choose best model
    print("\n" + "="*60)
    print("MODEL COMPARISON")
    print("="*60)
    print(f"Random Forest F1:       {rf_metrics['f1_score']:.4f}")
    print(f"Gradient Boosting F1:   {gb_metrics['f1_score']:.4f}")
    
    if rf_metrics['f1_score'] >= gb_metrics['f1_score']:
        best_model = rf_model
        best_metrics = rf_metrics
        best_name = "Random Forest"
    else:
        best_model = gb_model
        best_metrics = gb_metrics
        best_name = "Gradient Boosting"
    
    print(f"\nBest Model: {best_name}")
    
    # Save best model
    save_model(best_model, scaler, feature_columns, best_metrics, best_name)
    
    # Also save RF as primary model (for consistent naming)
    save_model(rf_model, scaler, feature_columns, rf_metrics, "congestion_predictor")
    
    # Summary
    print("\n" + "="*60)
    print("MODEL TRAINING COMPLETE")
    print("="*60)
    print(f"Best Model: {best_name}")
    print(f"Accuracy: {best_metrics['accuracy']:.4f}")
    print(f"F1 Score: {best_metrics['f1_score']:.4f}")
    print(f"\nModels saved to: {MODELS_DIR}")
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


if __name__ == "__main__":
    main()
