"""
NYC Taxi Data Cleaning Pipeline - Memory Optimized Version
Processes large CSV files in chunks and saves directly to parquet
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import os
import gc

# Configuration
DATA_DIR = Path(r"c:\sem6-real\bigdata\vscode")
PROJECT_DIR = Path(__file__).parent.parent.parent
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
CHUNK_SIZE = 200_000  # Smaller chunks for memory efficiency

# NYC geographic bounds
NYC_BOUNDS = {
    'lat_min': 40.4774,
    'lat_max': 40.9176,
    'lon_min': -74.2591,
    'lon_max': -73.7004
}

# Grid configuration (0.01 degree cells ~ 1km)
GRID_SIZE = 0.01


def standardize_columns(df):
    """Standardize column names across different dataset versions."""
    column_mapping = {
        # 2015 format
        'pickup_longitude': 'pickup_lon',
        'pickup_latitude': 'pickup_lat',
        'dropoff_longitude': 'dropoff_lon',
        'dropoff_latitude': 'dropoff_lat',
        'tpep_pickup_datetime': 'pickup_datetime',
        'tpep_dropoff_datetime': 'dropoff_datetime',
        # Already standard
        'pickup_lon': 'pickup_lon',
        'pickup_lat': 'pickup_lat',
    }
    
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    return df


def filter_nyc_coordinates(df):
    """Filter records to NYC bounds."""
    initial_count = len(df)
    
    df = df[
        (df['pickup_lat'].between(NYC_BOUNDS['lat_min'], NYC_BOUNDS['lat_max'])) &
        (df['pickup_lon'].between(NYC_BOUNDS['lon_min'], NYC_BOUNDS['lon_max'])) &
        (df['dropoff_lat'].between(NYC_BOUNDS['lat_min'], NYC_BOUNDS['lat_max'])) &
        (df['dropoff_lon'].between(NYC_BOUNDS['lon_min'], NYC_BOUNDS['lon_max']))
    ]
    
    removed = initial_count - len(df)
    return df, removed


def clean_trip_distance(df):
    """Remove trips with invalid distances."""
    initial_count = len(df)
    df = df[(df['trip_distance'] > 0) & (df['trip_distance'] < 100)]
    removed = initial_count - len(df)
    return df, removed


def calculate_speed(df):
    """Calculate trip speed in mph."""
    df['pickup_datetime'] = pd.to_datetime(df['pickup_datetime'], errors='coerce')
    df['dropoff_datetime'] = pd.to_datetime(df['dropoff_datetime'], errors='coerce')
    
    duration_hours = (df['dropoff_datetime'] - df['pickup_datetime']).dt.total_seconds() / 3600
    
    # Avoid division by zero
    duration_hours = duration_hours.replace(0, np.nan)
    df['speed_mph'] = df['trip_distance'] / duration_hours
    
    # Filter unrealistic speeds
    initial_count = len(df)
    df = df[(df['speed_mph'] > 0) & (df['speed_mph'] < 60)]
    removed = initial_count - len(df)
    
    return df, removed


def add_time_features(df):
    """Extract time features."""
    df['hour'] = df['pickup_datetime'].dt.hour
    df['day_of_week'] = df['pickup_datetime'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['is_rush_hour'] = df['hour'].isin([7, 8, 9, 17, 18, 19]).astype(int)
    return df


def add_grid_cell(df):
    """Assign each pickup to a grid cell."""
    df['cell_lat'] = ((df['pickup_lat'] - NYC_BOUNDS['lat_min']) / GRID_SIZE).astype(int)
    df['cell_lon'] = ((df['pickup_lon'] - NYC_BOUNDS['lon_min']) / GRID_SIZE).astype(int)
    df['cell_id'] = df['cell_lat'].astype(str) + '_' + df['cell_lon'].astype(str)
    return df


def process_chunk(chunk, chunk_num):
    """Process a single chunk of data."""
    # Standardize columns
    chunk = standardize_columns(chunk)
    
    # Check required columns
    required = ['pickup_lat', 'pickup_lon', 'dropoff_lat', 'dropoff_lon', 
                'pickup_datetime', 'dropoff_datetime', 'trip_distance']
    
    missing = [col for col in required if col not in chunk.columns]
    if missing:
        print(f"    ⚠️ Missing columns: {missing}")
        return None, {}
    
    stats = {'initial': len(chunk)}
    
    # Filter coordinates
    chunk, coord_removed = filter_nyc_coordinates(chunk)
    stats['coord_removed'] = coord_removed
    
    # Clean distance
    chunk, dist_removed = clean_trip_distance(chunk)
    stats['dist_removed'] = dist_removed
    
    # Calculate speed
    chunk, speed_removed = calculate_speed(chunk)
    stats['speed_removed'] = speed_removed
    
    # Add features
    chunk = add_time_features(chunk)
    chunk = add_grid_cell(chunk)
    
    # Drop missing values
    chunk = chunk.dropna(subset=['pickup_lat', 'pickup_lon', 'pickup_datetime', 'speed_mph'])
    
    # Select only needed columns
    output_cols = [
        'pickup_datetime', 'pickup_lat', 'pickup_lon',
        'dropoff_lat', 'dropoff_lon', 'trip_distance',
        'speed_mph', 'hour', 'day_of_week', 'is_weekend',
        'is_rush_hour', 'cell_id', 'cell_lat', 'cell_lon'
    ]
    
    chunk = chunk[[c for c in output_cols if c in chunk.columns]]
    stats['final'] = len(chunk)
    
    return chunk, stats


def process_file(file_path, output_dir):
    """Process a single file in chunks, saving each chunk to parquet."""
    print(f"\nProcessing: {file_path.name}")
    
    # Create temp directory for chunks
    temp_dir = output_dir / "temp_chunks"
    temp_dir.mkdir(exist_ok=True)
    
    chunk_files = []
    total_rows = 0
    cleaned_rows = 0
    chunk_num = 0
    
    # Process in chunks
    for chunk in pd.read_csv(file_path, chunksize=CHUNK_SIZE, low_memory=False):
        chunk_num += 1
        print(f"  Chunk {chunk_num}: {len(chunk):,} rows", end="")
        
        processed, stats = process_chunk(chunk, chunk_num)
        
        if processed is not None and len(processed) > 0:
            # Save chunk to temp parquet file
            chunk_file = temp_dir / f"{file_path.stem}_chunk_{chunk_num:04d}.parquet"
            processed.to_parquet(chunk_file, index=False, compression='snappy')
            chunk_files.append(chunk_file)
            
            total_rows += stats['initial']
            cleaned_rows += stats['final']
            
            print(f" → {stats['final']:,} clean ({stats['coord_removed']} coord, {stats['dist_removed']} dist, {stats['speed_removed']} speed removed)")
        
        # Force garbage collection
        del chunk, processed
        gc.collect()
    
    # Combine all chunk files into one
    if chunk_files:
        print(f"\n  Combining {len(chunk_files)} chunks...")
        
        output_file = output_dir / f"{file_path.stem}_clean.parquet"
        
        # Read and combine in batches to save memory
        dfs = []
        for i, cf in enumerate(chunk_files):
            dfs.append(pd.read_parquet(cf))
            
            # Combine every 10 files
            if len(dfs) >= 10:
                combined = pd.concat(dfs, ignore_index=True)
                dfs = [combined]
                gc.collect()
        
        # Final combine
        final_df = pd.concat(dfs, ignore_index=True)
        final_df.to_parquet(output_file, index=False, compression='snappy')
        
        # Clean up temp files
        for cf in chunk_files:
            cf.unlink()
        temp_dir.rmdir()
        
        print(f"\n  ✅ Summary for {file_path.name}:")
        print(f"     Total rows: {total_rows:,}")
        print(f"     Cleaned rows: {cleaned_rows:,}")
        print(f"     Retention rate: {100*cleaned_rows/total_rows:.1f}%")
        print(f"     Output: {output_file}")
        print(f"     Output size: {output_file.stat().st_size / (1024*1024):.1f} MB")
        
        return output_file
    
    return None


def main():
    """Main execution function."""
    print("=" * 60)
    print("SMART CITY TRAFFIC - DATA CLEANING (Memory Optimized)")
    print("=" * 60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create output directory
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {PROCESSED_DIR}")
    
    # Find taxi files
    taxi_files = sorted(DATA_DIR.glob('yellow_tripdata_*.csv'))
    
    if not taxi_files:
        print(f"❌ No taxi data files found in {DATA_DIR}")
        return
    
    print(f"\nFound {len(taxi_files)} taxi data files:")
    for f in taxi_files:
        print(f"  - {f.name}: {f.stat().st_size / (1024*1024):.2f} MB")
    
    # Process each file
    output_files = []
    for file_path in taxi_files:
        result = process_file(file_path, PROCESSED_DIR)
        if result:
            output_files.append(result)
        gc.collect()
    
    # Summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"\nOutput files created:")
    total_output_size = 0
    for f in output_files:
        size = f.stat().st_size / (1024*1024)
        total_output_size += size
        print(f"  📁 {f.name}: {size:.1f} MB")
    
    print(f"\nTotal output size: {total_output_size:.1f} MB")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
