"""
Smart City Traffic - Feature Engineering (Memory Optimized)
============================================================

Creates features for ML model training by processing files one at a time.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import gc

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

# Congestion thresholds (based on speed)
CONGESTION_THRESHOLDS = {
    'low': 20,      # > 20 mph = low congestion
    'medium': 10,   # 10-20 mph = medium congestion
    'high': 0       # < 10 mph = high congestion
}


def assign_congestion_label(avg_speed):
    """Assign congestion label based on average speed."""
    if avg_speed >= CONGESTION_THRESHOLDS['low']:
        return 0  # Low congestion
    elif avg_speed >= CONGESTION_THRESHOLDS['medium']:
        return 1  # Medium congestion
    else:
        return 2  # High congestion


def create_features_from_file(file_path):
    """Create aggregated features from a single parquet file."""
    print(f"\n  Processing: {file_path.name}")
    
    # Load file
    df = pd.read_parquet(file_path)
    print(f"    Loaded {len(df):,} rows")
    
    # Ensure datetime
    df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'])
    
    # Group by cell and hour
    print(f"    Aggregating by cell and hour...")
    
    agg_df = df.groupby(['cell_id', 'hour']).agg({
        'speed_mph': ['mean', 'std', 'count'],
        'trip_distance': 'mean',
        'is_weekend': 'mean',
        'is_rush_hour': 'mean',
        'cell_lat': 'first',
        'cell_lon': 'first'
    }).reset_index()
    
    # Flatten column names
    agg_df.columns = [
        'cell_id', 'hour', 'avg_speed', 'speed_std', 'trip_count',
        'avg_distance', 'weekend_ratio', 'rush_hour_ratio',
        'cell_lat', 'cell_lon'
    ]
    
    # Fill NaN std values (single trip cells)
    agg_df['speed_std'] = agg_df['speed_std'].fillna(0)
    
    # Add congestion label
    agg_df['congestion_level'] = agg_df['avg_speed'].apply(assign_congestion_label)
    
    # Filter cells with at least 10 trips (for statistical significance)
    agg_df = agg_df[agg_df['trip_count'] >= 10]
    
    print(f"    Created {len(agg_df):,} cell-hour aggregations")
    
    # Free memory
    del df
    gc.collect()
    
    return agg_df


def main():
    """Main execution function."""
    print("=" * 60)
    print("SMART CITY TRAFFIC - FEATURE ENGINEERING")
    print("=" * 60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find cleaned files
    parquet_files = sorted(PROCESSED_DIR.glob('*_clean.parquet'))
    
    if not parquet_files:
        print("ERROR: No cleaned Parquet files found!")
        return
    
    print(f"\nFound {len(parquet_files)} cleaned data files")
    
    # Process each file
    all_features = []
    
    for file_path in parquet_files:
        features = create_features_from_file(file_path)
        all_features.append(features)
        gc.collect()
    
    # Combine all features
    print(f"\n📊 Combining features from all files...")
    combined = pd.concat(all_features, ignore_index=True)
    
    # Further aggregate across all months (same cell-hour combinations)
    print(f"  Final aggregation across all months...")
    
    final_df = combined.groupby(['cell_id', 'hour']).agg({
        'avg_speed': 'mean',
        'speed_std': 'mean',
        'trip_count': 'sum',
        'avg_distance': 'mean',
        'weekend_ratio': 'mean',
        'rush_hour_ratio': 'mean',
        'cell_lat': 'first',
        'cell_lon': 'first'
    }).reset_index()
    
    # Recalculate congestion label based on final average
    final_df['congestion_level'] = final_df['avg_speed'].apply(assign_congestion_label)
    
    # Add derived features
    final_df['is_manhattan'] = (
        (final_df['cell_lat'] >= 13) & (final_df['cell_lat'] <= 35) &
        (final_df['cell_lon'] >= 35) & (final_df['cell_lon'] <= 50)
    ).astype(int)
    
    print(f"\n  Final dataset: {len(final_df):,} cell-hour combinations")
    
    # Congestion distribution
    print(f"\n📊 Congestion Distribution:")
    congestion_counts = final_df['congestion_level'].value_counts().sort_index()
    labels = ['Low (>20mph)', 'Medium (10-20mph)', 'High (<10mph)']
    for level, count in congestion_counts.items():
        pct = 100 * count / len(final_df)
        print(f"    {labels[level]}: {count:,} ({pct:.1f}%)")
    
    # Save features
    output_file = OUTPUT_DIR / "training_features.parquet"
    final_df.to_parquet(output_file, index=False)
    print(f"\n✅ Saved training features to: {output_file}")
    print(f"   Size: {output_file.stat().st_size / (1024*1024):.2f} MB")
    
    # Also save a sample CSV for inspection
    sample_file = OUTPUT_DIR / "training_features_sample.csv"
    final_df.head(1000).to_csv(sample_file, index=False)
    print(f"   Sample CSV: {sample_file}")
    
    # Summary statistics
    print(f"\n📈 Feature Summary Statistics:")
    print(final_df[['avg_speed', 'trip_count', 'avg_distance']].describe().to_string())
    
    print(f"\n✅ Feature engineering complete!")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
