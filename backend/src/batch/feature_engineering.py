"""
Smart City Traffic - Feature Engineering Module
================================================

This script creates features for ML model training:
- Aggregates trip data by cell and time window
- Calculates congestion labels
- Creates feature vectors for training

Usage:
    python src/batch/feature_engineering.py
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

# Congestion thresholds (based on speed)
CONGESTION_THRESHOLDS = {
    'low': 20,      # > 20 mph = low congestion
    'medium': 10,   # 10-20 mph = medium congestion
    'high': 0       # < 10 mph = high congestion
}


def load_cleaned_data():
    """Load all cleaned Parquet files."""
    parquet_files = list(PROCESSED_DIR.glob('*_clean.parquet'))
    
    if not parquet_files:
        print("ERROR: No cleaned Parquet files found!")
        print(f"Run data_cleaning.py first.")
        return None
    
    print(f"Found {len(parquet_files)} cleaned data files:")
    
    dfs = []
    for f in parquet_files:
        print(f"  Loading: {f.name}")
        df = pd.read_parquet(f)
        dfs.append(df)
        print(f"    Rows: {len(df):,}")
    
    combined = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal records loaded: {len(combined):,}")
    return combined


def aggregate_by_cell_hour(df):
    """
    Aggregate trip data by cell and hour.
    This creates the training dataset for congestion prediction.
    """
    print("\nAggregating by cell and hour...")
    
    # Ensure datetime column
    if df['pickup_datetime'].dtype == 'object':
        df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
    
    # Create hour bucket
    df['hour_bucket'] = df['pickup_datetime'].dt.floor('H')
    
    # Aggregate by cell and hour
    agg_df = df.groupby(['cell_id', 'hour_bucket', 'hour', 'day_of_week']).agg({
        'pickup_lat': 'mean',           # Cell center latitude
        'pickup_lon': 'mean',           # Cell center longitude
        'speed_mph': ['mean', 'std', 'min', 'max', 'count'],
        'trip_distance': 'mean',
        'duration_hours': 'mean'
    }).reset_index()
    
    # Flatten column names
    agg_df.columns = [
        'cell_id', 'hour_bucket', 'hour', 'day_of_week',
        'cell_lat', 'cell_lon',
        'avg_speed', 'speed_std', 'min_speed', 'max_speed', 'vehicle_count',
        'avg_distance', 'avg_duration'
    ]
    
    # Fill NaN std values (when only 1 trip in cell-hour)
    agg_df['speed_std'] = agg_df['speed_std'].fillna(0)
    
    print(f"Aggregated records: {len(agg_df):,}")
    print(f"Unique cells: {agg_df['cell_id'].nunique():,}")
    print(f"Date range: {agg_df['hour_bucket'].min()} to {agg_df['hour_bucket'].max()}")
    
    return agg_df


def create_congestion_labels(df):
    """
    Create congestion level labels based on average speed.
    
    Labels:
        0 = low congestion (avg_speed > 20 mph)
        1 = medium congestion (10 < avg_speed <= 20 mph)
        2 = high congestion (avg_speed <= 10 mph)
    """
    print("\nCreating congestion labels...")
    
    conditions = [
        df['avg_speed'] > CONGESTION_THRESHOLDS['low'],
        df['avg_speed'] > CONGESTION_THRESHOLDS['medium'],
        df['avg_speed'] <= CONGESTION_THRESHOLDS['medium']
    ]
    choices = [0, 1, 2]  # low, medium, high
    
    df['congestion_label'] = np.select(conditions, choices, default=1)
    df['congestion_level'] = df['congestion_label'].map({
        0: 'low',
        1: 'medium',
        2: 'high'
    })
    
    # Calculate congestion index (0-1 scale)
    # Lower speed = higher congestion
    max_speed = 50  # Reference max speed
    df['congestion_index'] = 1 - (df['avg_speed'].clip(0, max_speed) / max_speed)
    
    # Print label distribution
    label_counts = df['congestion_level'].value_counts()
    print("Label distribution:")
    for level, count in label_counts.items():
        print(f"  {level}: {count:,} ({100*count/len(df):.1f}%)")
    
    return df


def create_additional_features(df):
    """Create additional features for ML model."""
    print("\nCreating additional features...")
    
    # Time-based features
    df['is_rush_hour'] = df['hour'].isin([7, 8, 9, 17, 18, 19]).astype(int)
    df['is_night'] = df['hour'].isin([22, 23, 0, 1, 2, 3, 4, 5]).astype(int)
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # Speed-based features
    df['speed_coefficient_var'] = df['speed_std'] / df['avg_speed'].replace(0, np.nan)
    df['speed_coefficient_var'] = df['speed_coefficient_var'].fillna(0)
    
    df['speed_range'] = df['max_speed'] - df['min_speed']
    
    # Density feature (proxy for congestion)
    df['density_score'] = df['vehicle_count'] / df['vehicle_count'].max()
    
    # Interaction features
    df['rush_hour_density'] = df['is_rush_hour'] * df['density_score']
    
    print(f"Total features: {len(df.columns)}")
    
    return df


def create_cell_statistics(df):
    """
    Create summary statistics for each cell.
    Useful for API responses and visualization.
    """
    print("\nCreating cell statistics...")
    
    cell_stats = df.groupby('cell_id').agg({
        'cell_lat': 'first',
        'cell_lon': 'first',
        'avg_speed': 'mean',
        'vehicle_count': 'mean',
        'congestion_index': 'mean',
        'congestion_label': lambda x: x.mode().iloc[0] if len(x) > 0 else 1
    }).reset_index()
    
    cell_stats.columns = [
        'cell_id', 'latitude', 'longitude',
        'typical_speed', 'typical_vehicle_count',
        'typical_congestion', 'dominant_congestion_level'
    ]
    
    # Map numeric label to string
    cell_stats['dominant_congestion'] = cell_stats['dominant_congestion_level'].map({
        0: 'low', 1: 'medium', 2: 'high'
    })
    
    print(f"Cell statistics created for {len(cell_stats)} cells")
    
    return cell_stats


def prepare_training_data(df):
    """
    Prepare final training dataset with selected features.
    """
    print("\nPreparing training dataset...")
    
    feature_columns = [
        'hour',
        'day_of_week',
        'is_rush_hour',
        'is_night',
        'is_weekend',
        'avg_speed',
        'speed_std',
        'speed_range',
        'vehicle_count',
        'density_score',
        'avg_distance',
        'avg_duration'
    ]
    
    target_column = 'congestion_label'
    
    # Check for missing columns
    missing_cols = [c for c in feature_columns if c not in df.columns]
    if missing_cols:
        print(f"WARNING: Missing columns: {missing_cols}")
        feature_columns = [c for c in feature_columns if c in df.columns]
    
    # Create training dataframe
    train_df = df[feature_columns + [target_column, 'cell_id', 'hour_bucket']].copy()
    
    # Remove any rows with NaN
    initial_count = len(train_df)
    train_df = train_df.dropna()
    print(f"Removed {initial_count - len(train_df)} rows with NaN values")
    
    print(f"Training dataset shape: {train_df.shape}")
    print(f"Features: {feature_columns}")
    
    return train_df, feature_columns


def save_datasets(agg_df, cell_stats, train_df, feature_columns):
    """Save all processed datasets."""
    print("\nSaving datasets...")
    
    # Aggregated data
    agg_path = OUTPUT_DIR / "aggregated_traffic.parquet"
    agg_df.to_parquet(agg_path, index=False)
    print(f"  Saved: {agg_path} ({agg_path.stat().st_size / (1024*1024):.1f} MB)")
    
    # Cell statistics
    cells_path = OUTPUT_DIR / "cell_statistics.parquet"
    cell_stats.to_parquet(cells_path, index=False)
    print(f"  Saved: {cells_path} ({cells_path.stat().st_size / 1024:.1f} KB)")
    
    # Training data
    train_path = OUTPUT_DIR / "training_data.parquet"
    train_df.to_parquet(train_path, index=False)
    print(f"  Saved: {train_path} ({train_path.stat().st_size / (1024*1024):.1f} MB)")
    
    # Feature list (for model loading)
    features_path = OUTPUT_DIR / "feature_columns.txt"
    with open(features_path, 'w') as f:
        f.write('\n'.join(feature_columns))
    print(f"  Saved: {features_path}")
    
    # Also save as CSV for easy inspection
    sample_path = OUTPUT_DIR / "training_sample.csv"
    train_df.sample(min(10000, len(train_df))).to_csv(sample_path, index=False)
    print(f"  Saved: {sample_path} (sample for inspection)")


def main():
    """Main execution function."""
    print("="*60)
    print("SMART CITY TRAFFIC - FEATURE ENGINEERING")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load cleaned data
    df = load_cleaned_data()
    if df is None:
        return
    
    # Aggregate by cell and hour
    agg_df = aggregate_by_cell_hour(df)
    
    # Create congestion labels
    agg_df = create_congestion_labels(agg_df)
    
    # Create additional features
    agg_df = create_additional_features(agg_df)
    
    # Create cell statistics
    cell_stats = create_cell_statistics(agg_df)
    
    # Prepare training data
    train_df, feature_columns = prepare_training_data(agg_df)
    
    # Save all datasets
    save_datasets(agg_df, cell_stats, train_df, feature_columns)
    
    # Summary
    print("\n" + "="*60)
    print("FEATURE ENGINEERING COMPLETE")
    print("="*60)
    print(f"Aggregated records: {len(agg_df):,}")
    print(f"Unique cells: {agg_df['cell_id'].nunique():,}")
    print(f"Training samples: {len(train_df):,}")
    print(f"Features: {len(feature_columns)}")
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


if __name__ == "__main__":
    main()
