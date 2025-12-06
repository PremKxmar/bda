/**
 * Smart City Traffic - Scala Data Preprocessing Module
 * =====================================================
 * 
 * This Scala script performs data preprocessing using Apache Spark:
 * - Loads raw NYC Taxi CSV data
 * - Applies data validation and filtering
 * - Calculates derived metrics (speed, duration)
 * - Creates spatial grid cell assignments
 * - Outputs cleaned Parquet files
 * 
 * Usage:
 *   spark-submit --class TrafficDataPreprocessor target/scala-2.12/traffic-preprocessor.jar
 *   OR
 *   Run from Spark shell: :load src/scala/TrafficDataPreprocessor.scala
 */

import org.apache.spark.sql.{SparkSession, DataFrame, Row}
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.sql.expressions.Window

/**
 * Main object for traffic data preprocessing
 */
object TrafficDataPreprocessor {

  // NYC Geographic bounds
  val NYC_LAT_MIN = 40.4774
  val NYC_LAT_MAX = 40.9176
  val NYC_LON_MIN = -74.2591
  val NYC_LON_MAX = -73.7004
  
  // Grid cell size (approximately 1km x 1km)
  val CELL_SIZE = 0.01

  /**
   * Create Spark session with appropriate configuration
   */
  def createSparkSession(): SparkSession = {
    SparkSession.builder()
      .appName("SmartCityTraffic-ScalaPreprocessor")
      .config("spark.driver.memory", "8g")
      .config("spark.executor.memory", "8g")
      .config("spark.sql.parquet.compression.codec", "snappy")
      .config("spark.sql.shuffle.partitions", "200")
      .getOrCreate()
  }

  /**
   * Define schema for NYC Taxi data (2015-2016 format)
   */
  def getTaxiSchema(): StructType = {
    StructType(Array(
      StructField("VendorID", IntegerType, true),
      StructField("tpep_pickup_datetime", StringType, true),
      StructField("tpep_dropoff_datetime", StringType, true),
      StructField("passenger_count", IntegerType, true),
      StructField("trip_distance", DoubleType, true),
      StructField("pickup_longitude", DoubleType, true),
      StructField("pickup_latitude", DoubleType, true),
      StructField("RatecodeID", IntegerType, true),
      StructField("store_and_fwd_flag", StringType, true),
      StructField("dropoff_longitude", DoubleType, true),
      StructField("dropoff_latitude", DoubleType, true),
      StructField("payment_type", IntegerType, true),
      StructField("fare_amount", DoubleType, true),
      StructField("extra", DoubleType, true),
      StructField("mta_tax", DoubleType, true),
      StructField("tip_amount", DoubleType, true),
      StructField("tolls_amount", DoubleType, true),
      StructField("improvement_surcharge", DoubleType, true),
      StructField("total_amount", DoubleType, true)
    ))
  }

  /**
   * Load raw CSV data into DataFrame
   */
  def loadRawData(spark: SparkSession, inputPath: String): DataFrame = {
    println(s"\n[SCALA] Loading data from: $inputPath")
    
    val df = spark.read
      .option("header", "true")
      .option("mode", "DROPMALFORMED")
      .schema(getTaxiSchema())
      .csv(inputPath)
    
    val count = df.count()
    println(s"[SCALA] Loaded $count rows")
    
    df
  }

  /**
   * Rename columns to standard names
   */
  def standardizeColumns(df: DataFrame): DataFrame = {
    println("[SCALA] Standardizing column names...")
    
    df.withColumnRenamed("tpep_pickup_datetime", "pickup_datetime")
      .withColumnRenamed("tpep_dropoff_datetime", "dropoff_datetime")
      .withColumnRenamed("pickup_longitude", "pickup_lon")
      .withColumnRenamed("pickup_latitude", "pickup_lat")
      .withColumnRenamed("dropoff_longitude", "dropoff_lon")
      .withColumnRenamed("dropoff_latitude", "dropoff_lat")
  }

  /**
   * Convert datetime strings to timestamps
   */
  def convertDatetimes(df: DataFrame): DataFrame = {
    println("[SCALA] Converting datetime columns...")
    
    df.withColumn("pickup_datetime", to_timestamp(col("pickup_datetime"), "yyyy-MM-dd HH:mm:ss"))
      .withColumn("dropoff_datetime", to_timestamp(col("dropoff_datetime"), "yyyy-MM-dd HH:mm:ss"))
  }

  /**
   * Filter records with valid NYC coordinates
   */
  def filterValidCoordinates(df: DataFrame): DataFrame = {
    println("[SCALA] Filtering valid NYC coordinates...")
    
    val filtered = df.filter(
      col("pickup_lat").between(NYC_LAT_MIN, NYC_LAT_MAX) &&
      col("pickup_lon").between(NYC_LON_MIN, NYC_LON_MAX) &&
      col("dropoff_lat").between(NYC_LAT_MIN, NYC_LAT_MAX) &&
      col("dropoff_lon").between(NYC_LON_MIN, NYC_LON_MAX)
    )
    
    val count = filtered.count()
    println(s"[SCALA] After coordinate filter: $count rows")
    
    filtered
  }

  /**
   * Calculate trip duration and speed
   */
  def calculateDerivedMetrics(df: DataFrame): DataFrame = {
    println("[SCALA] Calculating derived metrics (duration, speed)...")
    
    df.withColumn("duration_seconds",
        unix_timestamp(col("dropoff_datetime")) - unix_timestamp(col("pickup_datetime")))
      .withColumn("duration_hours", col("duration_seconds") / 3600.0)
      .withColumn("speed_mph", 
        round(col("trip_distance") / col("duration_hours"), 2))
  }

  /**
   * Filter out invalid durations and speeds
   */
  def filterValidTrips(df: DataFrame): DataFrame = {
    println("[SCALA] Filtering valid trips (duration, distance, speed)...")
    
    val filtered = df.filter(
      // Duration between 1 minute and 3 hours
      col("duration_seconds").between(60, 10800) &&
      // Distance between 0.1 and 100 miles
      col("trip_distance").between(0.1, 100) &&
      // Speed between 1 and 60 mph
      col("speed_mph").between(1, 60)
    )
    
    val count = filtered.count()
    println(s"[SCALA] After trip validation filter: $count rows")
    
    filtered
  }

  /**
   * Create spatial grid cell indices
   */
  def createGridCells(df: DataFrame): DataFrame = {
    println("[SCALA] Creating spatial grid cells...")
    
    df.withColumn("cell_lat",
        ((col("pickup_lat") - lit(NYC_LAT_MIN)) / lit(CELL_SIZE)).cast(IntegerType))
      .withColumn("cell_lon",
        ((col("pickup_lon") - lit(NYC_LON_MIN)) / lit(CELL_SIZE)).cast(IntegerType))
      .withColumn("cell_id",
        concat_ws("_", lit("cell"), col("cell_lat"), col("cell_lon")))
  }

  /**
   * Extract temporal features
   */
  def extractTemporalFeatures(df: DataFrame): DataFrame = {
    println("[SCALA] Extracting temporal features...")
    
    df.withColumn("hour", hour(col("pickup_datetime")))
      .withColumn("day_of_week", dayofweek(col("pickup_datetime")))
      .withColumn("month", month(col("pickup_datetime")))
      .withColumn("year", year(col("pickup_datetime")))
  }

  /**
   * Create Manhattan flag based on coordinates
   */
  def createManhattanFlag(df: DataFrame): DataFrame = {
    println("[SCALA] Creating Manhattan flag...")
    
    df.withColumn("is_manhattan",
      when(
        col("pickup_lat").between(40.70, 40.88) &&
        col("pickup_lon").between(-74.02, -73.93),
        true
      ).otherwise(false))
  }

  /**
   * Select final columns for output
   */
  def selectFinalColumns(df: DataFrame): DataFrame = {
    println("[SCALA] Selecting final columns...")
    
    val finalColumns = Seq(
      "pickup_datetime", "dropoff_datetime",
      "pickup_lat", "pickup_lon",
      "dropoff_lat", "dropoff_lon",
      "trip_distance", "duration_hours", "speed_mph",
      "passenger_count", "fare_amount", "total_amount",
      "cell_id", "cell_lat", "cell_lon",
      "hour", "day_of_week", "month", "year",
      "is_manhattan"
    )
    
    df.select(finalColumns.map(col): _*)
  }

  /**
   * Print statistics about the DataFrame
   */
  def printStatistics(df: DataFrame, label: String): Unit = {
    println(s"\n[SCALA] $label Statistics:")
    println(s"  Total records: ${df.count()}")
    println(s"  Unique cells: ${df.select("cell_id").distinct().count()}")
    
    // Speed statistics
    val speedStats = df.agg(
      min("speed_mph").as("min_speed"),
      max("speed_mph").as("max_speed"),
      avg("speed_mph").as("avg_speed")
    ).first()
    
    println(f"  Speed (mph): min=${speedStats.getDouble(0)}%.1f, " +
            f"max=${speedStats.getDouble(1)}%.1f, avg=${speedStats.getDouble(2)}%.1f")
    
    // Sample output
    println("\n  Sample data:")
    df.select("pickup_datetime", "cell_id", "speed_mph", "is_manhattan")
      .show(5, truncate = false)
  }

  /**
   * Save DataFrame to Parquet format
   */
  def saveToParquet(df: DataFrame, outputPath: String): Unit = {
    println(s"\n[SCALA] Saving to: $outputPath")
    
    // Repartition for optimal file size
    val numPartitions = math.max(1, (df.count() / 500000).toInt)
    val repartitionedDf = df.repartition(numPartitions)
    
    repartitionedDf.write
      .mode("overwrite")
      .parquet(outputPath)
    
    println("[SCALA] Saved successfully!")
  }

  /**
   * Full preprocessing pipeline
   */
  def preprocessData(spark: SparkSession, inputPath: String, outputPath: String): DataFrame = {
    println("\n" + "=" * 60)
    println("[SCALA] STARTING DATA PREPROCESSING PIPELINE")
    println("=" * 60)
    
    // Load raw data
    var df = loadRawData(spark, inputPath)
    
    // Apply transformations
    df = standardizeColumns(df)
    df = convertDatetimes(df)
    df = filterValidCoordinates(df)
    df = calculateDerivedMetrics(df)
    df = filterValidTrips(df)
    df = createGridCells(df)
    df = extractTemporalFeatures(df)
    df = createManhattanFlag(df)
    df = selectFinalColumns(df)
    
    // Print statistics
    printStatistics(df, "Cleaned Data")
    
    // Save output
    saveToParquet(df, outputPath)
    
    println("\n" + "=" * 60)
    println("[SCALA] PREPROCESSING COMPLETE")
    println("=" * 60)
    
    df
  }

  /**
   * Aggregate data by cell and hour (for feature engineering)
   */
  def aggregateByCellHour(df: DataFrame): DataFrame = {
    println("\n[SCALA] Aggregating by cell and hour...")
    
    val hourBucketDf = df.withColumn("hour_bucket", 
      date_trunc("hour", col("pickup_datetime")))
    
    val aggDf = hourBucketDf.groupBy(
      "cell_id", "cell_lat", "cell_lon", "hour_bucket", "hour", "day_of_week", "month", "year"
    ).agg(
      count("*").as("trip_count"),
      avg("speed_mph").as("avg_speed"),
      stddev("speed_mph").as("speed_std"),
      min("speed_mph").as("min_speed"),
      max("speed_mph").as("max_speed"),
      avg("trip_distance").as("avg_distance"),
      avg("duration_hours").as("avg_duration"),
      first("is_manhattan").as("is_manhattan")
    )
    
    // Fill null std values
    val filledDf = aggDf.withColumn("speed_std",
      coalesce(col("speed_std"), lit(0.0)))
    
    println(s"[SCALA] Aggregated records: ${filledDf.count()}")
    
    filledDf
  }

  /**
   * Create congestion labels based on speed
   */
  def createCongestionLabels(df: DataFrame): DataFrame = {
    println("[SCALA] Creating congestion labels...")
    
    df.withColumn("congestion_label",
        when(col("avg_speed") > 20, 0)      // Low
        .when(col("avg_speed") >= 10, 1)    // Medium
        .otherwise(2))                       // High
      .withColumn("congestion_level",
        when(col("congestion_label") === 0, "Low")
        .when(col("congestion_label") === 1, "Medium")
        .otherwise("High"))
  }

  /**
   * Main entry point
   */
  def main(args: Array[String]): Unit = {
    println("\n" + "=" * 60)
    println("SMART CITY TRAFFIC - SCALA DATA PREPROCESSOR")
    println("=" * 60)
    
    val startTime = System.currentTimeMillis()
    
    // Create Spark session
    val spark = createSparkSession()
    spark.sparkContext.setLogLevel("WARN")
    
    // Default paths (can be overridden with args)
    val inputPath = if (args.length > 0) args(0) 
                    else "c:/sem6-real/vscode2/yellow_tripdata_*.csv"
    val outputPath = if (args.length > 1) args(1) 
                     else "c:/sem6-real/vscode2/smart-city-traffic/data/processed/scala_cleaned.parquet"
    
    // Run preprocessing
    val cleanedDf = preprocessData(spark, inputPath, outputPath)
    
    // Also create aggregated features
    val aggDf = aggregateByCellHour(cleanedDf)
    val labeledDf = createCongestionLabels(aggDf)
    
    // Save aggregated features
    val featuresPath = "c:/sem6-real/vscode2/smart-city-traffic/data/processed/scala_features.parquet"
    saveToParquet(labeledDf, featuresPath)
    
    // Print final summary
    val endTime = System.currentTimeMillis()
    val duration = (endTime - startTime) / 1000.0
    
    println("\n" + "=" * 60)
    println("[SCALA] ALL PROCESSING COMPLETE")
    println("=" * 60)
    println(f"  Duration: $duration%.1f seconds")
    println(s"  Cleaned output: $outputPath")
    println(s"  Features output: $featuresPath")
    println("=" * 60)
    
    // Stop Spark
    spark.stop()
  }
}

// For running in Spark shell
// :load src/scala/TrafficDataPreprocessor.scala
// TrafficDataPreprocessor.main(Array())
