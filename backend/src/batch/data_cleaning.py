"""
Smart City Traffic - Data Cleaning Module
==========================================

This script cleans the raw NYC Taxi data:
- Removes invalid coordinates
- Filters outliers in speed/distance
- Handles missing values
- Saves cleaned data as Parquet

Usage:
    python src/batch/data_cleaning.py
"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration
RAW_DATA_DIR = Path(r"c:\sem6-real\bigdata\vscode")
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHUNK_SIZE = 500000  # Process 500K rows at a time for memory efficiency

# NYC Geographic bounds
NYC_BOUNDS = {
    'lat_min': 40.4774,
    'lat_max': 40.9176,
    'lon_min': -74.2591,
    'lon_max': -73.7004
}

# Column mapping (2015-2016 data format)
COLUMN_MAPPING = {
    # Original -> Standardized
    'tpep_pickup_datetime': 'pickup_datetime',
    'tpep_dropoff_datetime': 'dropoff_datetime',
    'pickup_longitude': 'pickup_lon',
    'pickup_latitude': 'pickup_lat',
    'dropoff_longitude': 'dropoff_lon',
    'dropoff_latitude': 'dropoff_lat',
    'trip_distance': 'trip_distance',
    'passenger_count': 'passenger_count',
    'fare_amount': 'fare_amount',
    'total_amount': 'total_amount'
}

# Required columns for our analysis
REQUIRED_COLUMNS = [
    'pickup_datetime', 'dropoff_datetime',
    'pickup_lat', 'pickup_lon',
    'dropoff_lat', 'dropoff_lon',
    'trip_distance'
]


def get_taxi_files():
    """Find all taxi CSV files in the raw data directory."""
    files = list(RAW_DATA_DIR.glob('yellow_tripdata_*.csv'))
    print(f"Found {len(files)} taxi data files:")
    for f in files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  - {f.name}: {size_mb:.2f} MB")
    return files


def standardize_columns(df):
    """Rename columns to standardized names."""
    # Create mapping for columns that exist in this dataframe
    rename_map = {}
    for old_name, new_name in COLUMN_MAPPING.items():
        if old_name in df.columns:
            rename_map[old_name] = new_name
        elif old_name.lower() in [c.lower() for c in df.columns]:
            # Case-insensitive match
            actual_col = [c for c in df.columns if c.lower() == old_name.lower()][0]
            rename_map[actual_col] = new_name
    
    df = df.rename(columns=rename_map)
    return df


def clean_coordinates(df):
    """Filter records with valid NYC coordinates."""
    initial_count = len(df)
    
    # Check which coordinate columns exist
    has_pickup = 'pickup_lat' in df.columns and 'pickup_lon' in df.columns
    has_dropoff = 'dropoff_lat' in df.columns and 'dropoff_lon' in df.columns
    
    if has_pickup:
        # Filter pickup coordinates within NYC bounds
        df = df[
            (df['pickup_lat'].between(NYC_BOUNDS['lat_min'], NYC_BOUNDS['lat_max'])) &
            (df['pickup_lon'].between(NYC_BOUNDS['lon_min'], NYC_BOUNDS['lon_max']))
        ]
    
    if has_dropoff:
        # Filter dropoff coordinates within NYC bounds
        df = df[
            (df['dropoff_lat'].between(NYC_BOUNDS['lat_min'], NYC_BOUNDS['lat_max'])) &
            (df['dropoff_lon'].between(NYC_BOUNDS['lon_min'], NYC_BOUNDS['lon_max']))
        ]
    
    removed = initial_count - len(df)
    print(f"    Coordinates filter: removed {removed:,} records ({100*removed/max(initial_count,1):.1f}%)")
    return df


def clean_trip_distance(df):
    """Filter records with valid trip distance."""
    if 'trip_distance' not in df.columns:
        return df
    
    initial_count = len(df)
    
    # Remove trips with invalid distance (0, negative, or very long)
    df = df[
        (df['trip_distance'] > 0.1) &  # At least 0.1 miles
        (df['trip_distance'] < 100)     # Less than 100 miles
    ]
    
    removed = initial_count - len(df)
    print(f"    Distance filter: removed {removed:,} records ({100*removed/max(initial_count,1):.1f}%)")
    return df


def calculate_speed(df):
    """Calculate trip speed in mph."""
    if 'pickup_datetime' not in df.columns or 'dropoff_datetime' not in df.columns:
        return df
    
    # Convert to datetime if needed
    if df['pickup_datetime'].dtype == 'object':
        df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'], errors='coerce')
    if df['dropoff_datetime'].dtype == 'object':
        df['dropoff_datetime'] = pd.to_datetime(df['dropoff_datetime'], errors='coerce')
    
    # Calculate duration in hours
    df['duration_hours'] = (
        df['dropoff_datetime'] - df['pickup_datetime']
    ).dt.total_seconds() / 3600
    
    # Calculate speed (mph)
    if 'trip_distance' in df.columns:
        df['speed_mph'] = df['trip_distance'] / df['duration_hours'].replace(0, np.nan)
        
        # Filter unreasonable speeds
        initial_count = len(df)
        df = df[
            (df['speed_mph'] > 0) &
            (df['speed_mph'] < 80)  # Max 80 mph
        ]
        removed = initial_count - len(df)
        print(f"    Speed filter: removed {removed:,} records ({100*removed/max(initial_count,1):.1f}%)")
    
    return df


def add_time_features(df):
    """Add time-based features for ML."""
    if 'pickup_datetime' not in df.columns:
        return df
    
    df['hour'] = df['pickup_datetime'].dt.hour
    df['day_of_week'] = df['pickup_datetime'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['month'] = df['pickup_datetime'].dt.month
    df['day'] = df['pickup_datetime'].dt.day
    
    return df


def add_grid_cell(df, cell_size=0.005):
    """
    Assign each pickup location to a grid cell.
    
    cell_size=0.005 degrees ≈ 500m x 400m at NYC latitude
    """
    if 'pickup_lat' not in df.columns or 'pickup_lon' not in df.columns:
        return df
    
    # Calculate cell indices
    df['cell_lat_idx'] = (df['pickup_lat'] / cell_size).astype(int)
    df['cell_lon_idx'] = (df['pickup_lon'] / cell_size).astype(int)
    
    # Create cell ID
    df['cell_id'] = 'cell_' + df['cell_lat_idx'].astype(str) + '_' + df['cell_lon_idx'].astype(str)
    
    # Calculate cell center coordinates (for visualization)
    df['cell_center_lat'] = (df['cell_lat_idx'] + 0.5) * cell_size
    df['cell_center_lon'] = (df['cell_lon_idx'] + 0.5) * cell_size
    
    return df


def process_file(file_path, output_dir):
    """Process a single CSV file and save as Parquet."""
    print(f"\nProcessing: {file_path.name}")
    
    total_rows = 0
    cleaned_rows = 0
    chunks_processed = 0
    
    # Output file path
    output_file = output_dir / f"{file_path.stem}_cleaned.parquet"
    
    # Process in chunks
    all_chunks = []
    
    for chunk in pd.read_csv(file_path, chunksize=CHUNK_SIZE, low_memory=False):
        chunks_processed += 1
        initial_chunk_size = len(chunk)
        total_rows += initial_chunk_size
        
        print(f"  Chunk {chunks_processed}: {initial_chunk_size:,} rows")
        
        # Standardize column names
        chunk = standardize_columns(chunk)
        
        # Clean coordinates
        chunk = clean_coordinates(chunk)
        
        # Clean trip distance
        chunk = clean_trip_distance(chunk)
        
        # Calculate speed
        chunk = calculate_speed(chunk)
        
        # Add time features
        chunk = add_time_features(chunk)
        
        # Add grid cell assignment
        chunk = add_grid_cell(chunk)
        
        # Drop rows with missing required values
        chunk = chunk.dropna(subset=['pickup_lat', 'pickup_lon', 'pickup_datetime'])
        
        cleaned_rows += len(chunk)
        all_chunks.append(chunk)
        
        print(f"    After cleaning: {len(chunk):,} rows")
        
        # Save incrementally every 5 chunks to avoid memory issues
        if len(all_chunks) >= 5:
            chunk_df = pd.concat(all_chunks, ignore_index=True)
            # Append to parquet or create new
            if output_file.exists():
                existing = pd.read_parquet(output_file)
                chunk_df = pd.concat([existing, chunk_df], ignore_index=True)
            chunk_df.to_parquet(output_file, index=False, compression='snappy')
            all_chunks = []  # Clear memory
            print(f"    💾 Saved intermediate checkpoint...")
    
    # Save any remaining chunks
    if all_chunks:
        chunk_df = pd.concat(all_chunks, ignore_index=True)
        if output_file.exists():
            existing = pd.read_parquet(output_file)
            chunk_df = pd.concat([existing, chunk_df], ignore_index=True)
        chunk_df.to_parquet(output_file, index=False, compression='snappy')
    
    if output_file.exists():
        print(f"\n  Summary for {file_path.name}:")
        print(f"    Total rows: {total_rows:,}")
        print(f"    Cleaned rows: {cleaned_rows:,}")
        print(f"    Retention rate: {100*cleaned_rows/total_rows:.1f}%")
        print(f"    Output: {output_file}")
        print(f"    Output size: {output_file.stat().st_size / (1024*1024):.1f} MB")
        
        return pd.read_parquet(output_file)
    
    return None


def main():
    """Main execution function."""
    print("="*60)
    print("SMART CITY TRAFFIC - DATA CLEANING")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create output directory
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {PROCESSED_DIR}")
    
    # Get input files
    taxi_files = get_taxi_files()
    
    if not taxi_files:
        print("ERROR: No taxi data files found!")
        print(f"Expected location: {RAW_DATA_DIR}")
        return
    
    # Process each file
    all_results = []
    for file_path in taxi_files:
        result = process_file(file_path, PROCESSED_DIR)
        if result is not None:
            all_results.append(result)
    
    # Summary statistics
    print("\n" + "="*60)
    print("OVERALL SUMMARY")
    print("="*60)
    
    if all_results:
        total_clean = sum(len(df) for df in all_results)
        print(f"Total cleaned records: {total_clean:,}")
        print(f"Files processed: {len(all_results)}")
        
        # Sample of unique cells
        sample_df = all_results[0]
        unique_cells = sample_df['cell_id'].nunique() if 'cell_id' in sample_df.columns else 0
        print(f"Unique grid cells (sample): {unique_cells}")
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)


if __name__ == "__main__":
    main()
