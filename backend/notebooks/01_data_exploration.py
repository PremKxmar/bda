"""
NYC Taxi Data Exploration Script
Smart City Real-Time Traffic Simulation & Prediction

This script explores the NYC Yellow Taxi trip dataset to understand:
- Data structure and schema
- Data quality issues
- Geographic distribution
- Temporal patterns
- Statistics for ML feature engineering
"""

# Core libraries
import pandas as pd
import numpy as np
import os
from pathlib import Path

# Visualization
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

# Settings
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 100)
plt.style.use('seaborn-v0_8-whitegrid')

# Data directory - where your CSV files are located
DATA_DIR = Path(r"c:\sem6-real\bigdata\vscode")

print("=" * 60)
print("🏙️ NYC TAXI DATA EXPLORATION")
print("=" * 60)
print(f"\n✅ Libraries imported successfully!")
print(f"📁 Data directory: {DATA_DIR}")

# ============================================================
# 1. DISCOVER DATASET FILES
# ============================================================
print("\n" + "=" * 60)
print("📂 1. DISCOVER DATASET FILES")
print("=" * 60)

taxi_files = list(DATA_DIR.glob('yellow_tripdata_*.csv'))

print(f"\n📊 Found {len(taxi_files)} taxi data files:\n")

total_size = 0
for f in taxi_files:
    size_mb = f.stat().st_size / (1024 * 1024)
    size_gb = size_mb / 1024
    total_size += size_mb
    print(f"  📄 {f.name}: {size_mb:.2f} MB ({size_gb:.2f} GB)")

print(f"\n{'='*50}")
print(f"📦 TOTAL SIZE: {total_size:.2f} MB ({total_size/1024:.2f} GB)")
print(f"{'='*50}")

# ============================================================
# 2. LOAD SAMPLE DATA
# ============================================================
print("\n" + "=" * 60)
print("📂 2. LOAD SAMPLE DATA")
print("=" * 60)

sample_file = taxi_files[0]
print(f"\n📂 Loading sample from: {sample_file.name}")

# Read first 100,000 rows
df_sample = pd.read_csv(sample_file, nrows=100000)

print(f"\n✅ Loaded {len(df_sample):,} rows")
print(f"📊 Columns: {len(df_sample.columns)}")
print(f"\n🏷️ Column names:")
for i, col in enumerate(df_sample.columns, 1):
    print(f"   {i:2d}. {col}")

# Display first 5 rows
print("\n🔍 First 5 rows of the dataset:")
print(df_sample.head().to_string())

# Data types and memory usage
print("\n📋 Data Types:")
print(df_sample.dtypes.to_string())

# Statistical summary
print("\n📈 Statistical Summary:")
print(df_sample.describe().to_string())

# ============================================================
# 3. DATA QUALITY ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("📂 3. DATA QUALITY ANALYSIS")
print("=" * 60)

missing = df_sample.isnull().sum()
missing_pct = (missing / len(df_sample)) * 100

missing_df = pd.DataFrame({
    'Missing Count': missing,
    'Missing %': missing_pct
}).sort_values('Missing %', ascending=False)

print("\n❌ Missing Values Analysis:")
missing_with_values = missing_df[missing_df['Missing Count'] > 0]
if len(missing_with_values) > 0:
    print(missing_with_values.to_string())
else:
    print("✅ No missing values found!")

# ============================================================
# 4. GEOGRAPHIC ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("📂 4. GEOGRAPHIC ANALYSIS")
print("=" * 60)

NYC_BOUNDS = {
    'lat_min': 40.4774,
    'lat_max': 40.9176,
    'lon_min': -74.2591,
    'lon_max': -73.7004
}

coord_info = []
for col in df_sample.columns:
    col_lower = col.lower()
    if 'lat' in col_lower or 'lon' in col_lower:
        coord_info.append({
            'column': col,
            'min': df_sample[col].min(),
            'max': df_sample[col].max(),
            'mean': df_sample[col].mean()
        })

print("\n🗺️ Coordinate Columns Found:\n")
for info in coord_info:
    print(f"  📍 {info['column']}:")
    print(f"      Min: {info['min']:.6f}")
    print(f"      Max: {info['max']:.6f}")
    print(f"      Mean: {info['mean']:.6f}")
    print()

print(f"🏙️ NYC Valid Bounds:")
print(f"   Latitude:  {NYC_BOUNDS['lat_min']:.4f} to {NYC_BOUNDS['lat_max']:.4f}")
print(f"   Longitude: {NYC_BOUNDS['lon_min']:.4f} to {NYC_BOUNDS['lon_max']:.4f}")

# Find pickup coordinate columns
pickup_lat_col = None
pickup_lon_col = None

for col in df_sample.columns:
    col_lower = col.lower()
    if 'pickup' in col_lower and 'lat' in col_lower:
        pickup_lat_col = col
    elif 'pickup' in col_lower and 'lon' in col_lower:
        pickup_lon_col = col

if pickup_lat_col and pickup_lon_col:
    print(f"\n✅ Found pickup coordinates: {pickup_lat_col}, {pickup_lon_col}\n")
    
    valid_coords = df_sample[
        (df_sample[pickup_lat_col].between(NYC_BOUNDS['lat_min'], NYC_BOUNDS['lat_max'])) &
        (df_sample[pickup_lon_col].between(NYC_BOUNDS['lon_min'], NYC_BOUNDS['lon_max']))
    ]
    
    total = len(df_sample)
    valid = len(valid_coords)
    invalid = total - valid
    
    print(f"📊 Coordinate Validity:")
    print(f"   Total records:    {total:,}")
    print(f"   Valid (in NYC):   {valid:,} ({100*valid/total:.1f}%)")
    print(f"   Invalid:          {invalid:,} ({100*invalid/total:.1f}%)")
else:
    print("⚠️ Could not find pickup coordinate columns")

# ============================================================
# 5. TEMPORAL ANALYSIS
# ============================================================
print("\n" + "=" * 60)
print("📂 5. TEMPORAL ANALYSIS")
print("=" * 60)

datetime_cols = [col for col in df_sample.columns if 'time' in col.lower() or 'date' in col.lower()]
print(f"\n🕐 Datetime columns found: {datetime_cols}")

pickup_time_col = None
for col in datetime_cols:
    if 'pickup' in col.lower():
        pickup_time_col = col
        break

if pickup_time_col:
    df_sample[pickup_time_col] = pd.to_datetime(df_sample[pickup_time_col], errors='coerce')
    
    df_sample['hour'] = df_sample[pickup_time_col].dt.hour
    df_sample['day_of_week'] = df_sample[pickup_time_col].dt.dayofweek
    df_sample['day_name'] = df_sample[pickup_time_col].dt.day_name()
    
    print(f"\n📅 Date range: {df_sample[pickup_time_col].min()} to {df_sample[pickup_time_col].max()}")
    print(f"✅ Created time features: hour, day_of_week, day_name")
    
    # Generate insights
    hourly_counts = df_sample['hour'].value_counts().sort_index()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_counts = df_sample['day_name'].value_counts().reindex(day_order)
    
    peak_hour = hourly_counts.idxmax()
    peak_day = daily_counts.idxmax()
    
    print(f"\n📊 Temporal Insights:")
    print(f"   Peak hour: {peak_hour}:00 ({hourly_counts.max():,} trips)")
    print(f"   Peak day: {peak_day} ({daily_counts.max():,} trips)")
    
    print(f"\n🕐 Trips by Hour:")
    for hour in range(24):
        count = hourly_counts.get(hour, 0)
        bar = "█" * int(count / hourly_counts.max() * 30)
        print(f"   {hour:02d}:00  {bar} {count:,}")
else:
    print("⚠️ Could not find pickup time column")

# ============================================================
# 6. TRIP STATISTICS
# ============================================================
print("\n" + "=" * 60)
print("📂 6. TRIP STATISTICS")
print("=" * 60)

distance_col = None
for col in df_sample.columns:
    if 'distance' in col.lower():
        distance_col = col
        break

if distance_col:
    print(f"\n📏 Distance column: {distance_col}")
    
    valid_dist = df_sample[(df_sample[distance_col] > 0) & (df_sample[distance_col] < 50)][distance_col]
    
    print(f"\n📊 Distance Statistics (valid trips):")
    print(f"   Count:  {len(valid_dist):,}")
    print(f"   Mean:   {valid_dist.mean():.2f} miles")
    print(f"   Median: {valid_dist.median():.2f} miles")
    print(f"   Std:    {valid_dist.std():.2f} miles")
    print(f"   Min:    {valid_dist.min():.2f} miles")
    print(f"   Max:    {valid_dist.max():.2f} miles")
else:
    print("⚠️ Could not find distance column")

# Calculate trip duration and speed
dropoff_time_col = None
for col in df_sample.columns:
    if 'dropoff' in col.lower() and 'time' in col.lower():
        dropoff_time_col = col
        break

if pickup_time_col and dropoff_time_col and distance_col:
    df_sample[dropoff_time_col] = pd.to_datetime(df_sample[dropoff_time_col], errors='coerce')
    
    df_sample['duration_minutes'] = (df_sample[dropoff_time_col] - df_sample[pickup_time_col]).dt.total_seconds() / 60
    df_sample['speed_mph'] = df_sample[distance_col] / (df_sample['duration_minutes'] / 60)
    
    valid_speed = df_sample[(df_sample['speed_mph'] > 0) & (df_sample['speed_mph'] < 60)]['speed_mph']
    
    print(f"\n🚗 Speed Statistics (valid trips):")
    print(f"   Count:  {len(valid_speed):,}")
    print(f"   Mean:   {valid_speed.mean():.2f} mph")
    print(f"   Median: {valid_speed.median():.2f} mph")
    print(f"   Std:    {valid_speed.std():.2f} mph")
    
    print(f"\n🚦 Congestion Analysis (based on speed):")
    high_congestion = (valid_speed < 10).sum()
    medium_congestion = ((valid_speed >= 10) & (valid_speed < 20)).sum()
    low_congestion = (valid_speed >= 20).sum()
    total_valid = len(valid_speed)
    
    print(f"   🔴 High congestion (<10 mph):     {high_congestion:,} ({100*high_congestion/total_valid:.1f}%)")
    print(f"   🟡 Medium congestion (10-20 mph): {medium_congestion:,} ({100*medium_congestion/total_valid:.1f}%)")
    print(f"   🟢 Low congestion (>20 mph):      {low_congestion:,} ({100*low_congestion/total_valid:.1f}%)")
else:
    print("⚠️ Could not calculate speed - missing columns")

# ============================================================
# 7. FULL DATASET ROW COUNT
# ============================================================
print("\n" + "=" * 60)
print("📂 7. FULL DATASET ROW COUNT")
print("=" * 60)

print("\n⏳ Counting rows in all files (this may take a minute)...\n")

total_records = 0
file_stats = []

for f in taxi_files:
    print(f"  Counting: {f.name}...", end=" ", flush=True)
    
    with open(f, 'r', encoding='utf-8', errors='ignore') as file:
        row_count = sum(1 for _ in file) - 1
    
    size_mb = f.stat().st_size / (1024 * 1024)
    file_stats.append({
        'file': f.name,
        'size_mb': size_mb,
        'records': row_count
    })
    total_records += row_count
    print(f"{row_count:,} rows")

print(f"\n{'='*60}")
print(f"📊 TOTAL RECORDS: {total_records:,}")
print(f"📦 TOTAL SIZE: {sum(f['size_mb'] for f in file_stats):.2f} MB")
print(f"{'='*60}")

# ============================================================
# 8. SUMMARY
# ============================================================
print("\n" + "=" * 60)
print("📊 NYC TAXI DATA EXPLORATION SUMMARY")
print("=" * 60)

print(f"\n📁 Dataset Overview:")
print(f"   Files: {len(taxi_files)}")
print(f"   Total Size: ~{total_size/1024:.1f} GB")
print(f"   Total Records: {total_records:,}")
print(f"   Columns: {len(df_sample.columns)}")

print(f"\n📍 Geographic Coverage:")
print(f"   Area: New York City")
if pickup_lat_col and pickup_lon_col:
    print(f"   Valid coordinates: {100*valid/total:.1f}% of trips")

print(f"\n⏰ Temporal Coverage:")
print(f"   Months: 2015-01, 2016-01, 2016-02, 2016-03")

print(f"\n🔑 Key Columns for ML:")
print(f"   • Pickup datetime (for time features)")
print(f"   • Pickup latitude/longitude (for cell mapping)")
print(f"   • Trip distance (for speed calculation)")
print(f"   • Derived: speed_mph, hour, day_of_week")

print(f"\n⚠️ Data Quality Issues to Handle:")
print(f"   • Coordinates outside NYC bounds")
print(f"   • Zero or negative distances")
print(f"   • Unrealistic speeds (>60 mph or <0)")
print(f"   • Missing timestamp values")

print(f"\n✅ Next Steps:")
print(f"   1. Run data_cleaning.py to clean the data")
print(f"   2. Run feature_engineering.py to create ML features")
print(f"   3. Run model_training.py to train the model")
print(f"   4. Start the API server with app.py")

print("\n" + "=" * 60)
print("🎉 Data exploration complete! Ready for processing.")
print("=" * 60)
