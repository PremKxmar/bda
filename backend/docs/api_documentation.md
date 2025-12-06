# 📡 Smart City Traffic - API Documentation

## Base URL
```
http://localhost:5000/api
```

## Authentication
No authentication required for local development.

---

## Endpoints

### 1. Health Check

**GET** `/api/health`

Check if the API server is running.

#### Response
```json
{
    "status": "healthy",
    "timestamp": "2025-12-06T10:30:00Z",
    "version": "1.0.0"
}
```

---

### 2. Current Traffic State

**GET** `/api/current-traffic`

Get the current congestion state for all grid cells.

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 100 | Max number of cells to return |
| `min_congestion` | float | 0.0 | Filter by minimum congestion index |

#### Response
```json
{
    "timestamp": "2025-12-06T10:30:00Z",
    "total_cells": 245,
    "data": [
        {
            "cell_id": "cell_40_-74",
            "latitude": 40.7580,
            "longitude": -73.9855,
            "congestion_index": 0.85,
            "congestion_level": "high",
            "vehicle_count": 127,
            "avg_speed": 8.5,
            "speed_variance": 3.2
        },
        {
            "cell_id": "cell_40_-73",
            "latitude": 40.7484,
            "longitude": -73.9857,
            "congestion_index": 0.45,
            "congestion_level": "medium",
            "vehicle_count": 65,
            "avg_speed": 18.3,
            "speed_variance": 5.1
        }
    ]
}
```

---

### 3. Predictions

**GET** `/api/predictions`

Get ML-powered congestion predictions for the next 15 minutes.

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `horizon_minutes` | int | 15 | Prediction horizon |
| `min_confidence` | float | 0.7 | Minimum prediction confidence |

#### Response
```json
{
    "timestamp": "2025-12-06T10:30:00Z",
    "prediction_horizon": "15 minutes",
    "model_accuracy": 0.824,
    "predictions": [
        {
            "cell_id": "cell_40_-74",
            "current_level": "medium",
            "predicted_level": "high",
            "confidence": 0.89,
            "predicted_congestion_index": 0.92,
            "change": "+47%"
        },
        {
            "cell_id": "cell_41_-74",
            "current_level": "low",
            "predicted_level": "medium",
            "confidence": 0.76,
            "predicted_congestion_index": 0.55,
            "change": "+120%"
        }
    ]
}
```

---

### 4. Historical Data

**GET** `/api/historical`

Get time-series congestion data for charts.

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hours` | int | 24 | Hours of history to return |
| `interval` | string | "1h" | Aggregation interval (5m, 15m, 1h) |
| `cell_id` | string | null | Filter by specific cell |

#### Response
```json
{
    "start_time": "2025-12-05T10:30:00Z",
    "end_time": "2025-12-06T10:30:00Z",
    "interval": "1h",
    "data": [
        {
            "timestamp": "2025-12-05T10:00:00Z",
            "avg_congestion": 0.42,
            "total_vehicles": 8547,
            "avg_speed": 22.3
        },
        {
            "timestamp": "2025-12-05T11:00:00Z",
            "avg_congestion": 0.58,
            "total_vehicles": 12340,
            "avg_speed": 16.8
        }
    ]
}
```

---

### 5. Hotspots

**GET** `/api/hotspots`

Get the top congested zones.

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Number of hotspots to return |

#### Response
```json
{
    "timestamp": "2025-12-06T10:30:00Z",
    "hotspots": [
        {
            "rank": 1,
            "cell_id": "cell_40_-74",
            "name": "Times Square",
            "congestion_index": 0.94,
            "vehicle_count": 185,
            "avg_speed": 5.2,
            "trend": "increasing",
            "change_1h": "+12%"
        },
        {
            "rank": 2,
            "cell_id": "cell_40_-73",
            "name": "Penn Station",
            "congestion_index": 0.87,
            "vehicle_count": 142,
            "avg_speed": 8.1,
            "trend": "stable",
            "change_1h": "+2%"
        }
    ]
}
```

---

### 6. Cell Details

**GET** `/api/cell/{cell_id}`

Get detailed information for a specific grid cell.

#### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| `cell_id` | string | Grid cell identifier (e.g., "cell_40_-74") |

#### Response
```json
{
    "cell_id": "cell_40_-74",
    "location": {
        "latitude": 40.7580,
        "longitude": -73.9855,
        "name": "Times Square",
        "borough": "Manhattan"
    },
    "current": {
        "congestion_index": 0.94,
        "congestion_level": "high",
        "vehicle_count": 185,
        "avg_speed": 5.2,
        "speed_variance": 2.1
    },
    "prediction": {
        "predicted_level": "high",
        "predicted_index": 0.91,
        "confidence": 0.88,
        "horizon": "15 minutes"
    },
    "history_24h": {
        "avg_congestion": 0.72,
        "peak_congestion": 0.96,
        "peak_time": "08:30",
        "low_congestion": 0.25,
        "low_time": "03:00"
    },
    "vehicles": [
        {"vehicle_id": "taxi_12345", "speed": 4.2},
        {"vehicle_id": "taxi_67890", "speed": 6.1}
    ]
}
```

---

### 7. Statistics

**GET** `/api/stats`

Get overall system statistics.

#### Response
```json
{
    "timestamp": "2025-12-06T10:30:00Z",
    "overview": {
        "total_vehicles": 12847,
        "active_cells": 245,
        "avg_congestion": 0.52,
        "avg_speed": 18.5
    },
    "congestion_breakdown": {
        "low": 98,
        "medium": 89,
        "high": 58
    },
    "ml_model": {
        "name": "Random Forest Classifier",
        "accuracy": 0.824,
        "precision": 0.81,
        "recall": 0.79,
        "f1_score": 0.80
    },
    "streaming": {
        "events_per_second": 1250,
        "latency_ms": 1850,
        "uptime_hours": 24.5
    }
}
```

---

## WebSocket

### Real-time Stream

**WS** `/ws/stream`

Subscribe to real-time traffic updates.

#### Connection
```javascript
const ws = new WebSocket('ws://localhost:5000/ws/stream');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

#### Message Format
```json
{
    "type": "traffic_update",
    "timestamp": "2025-12-06T10:30:02Z",
    "cells": [
        {
            "cell_id": "cell_40_-74",
            "congestion_index": 0.85,
            "vehicle_count": 127,
            "avg_speed": 8.5,
            "prediction": "high"
        }
    ]
}
```

#### Message Types
| Type | Description |
|------|-------------|
| `traffic_update` | Regular congestion updates (every 2s) |
| `prediction_alert` | New prediction for a cell |
| `hotspot_change` | Hotspot ranking changed |

---

## Error Responses

### 400 Bad Request
```json
{
    "error": "Bad Request",
    "message": "Invalid cell_id format",
    "code": 400
}
```

### 404 Not Found
```json
{
    "error": "Not Found",
    "message": "Cell cell_99_99 not found",
    "code": 404
}
```

### 500 Internal Server Error
```json
{
    "error": "Internal Server Error",
    "message": "Database connection failed",
    "code": 500
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| REST APIs | 100 requests/minute |
| WebSocket | 1 connection per client |

---

## GeoJSON Format (for Kepler.gl)

### Point Data (Vehicles)
```json
{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [-73.9855, 40.7580]
            },
            "properties": {
                "vehicle_id": "taxi_12345",
                "speed": 15.5,
                "timestamp": "2025-12-06T10:30:00Z"
            }
        }
    ]
}
```

### Hexagon Data (Congestion)
```json
{
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-73.990, 40.755],
                    [-73.985, 40.758],
                    [-73.980, 40.755],
                    [-73.980, 40.750],
                    [-73.985, 40.747],
                    [-73.990, 40.750],
                    [-73.990, 40.755]
                ]]
            },
            "properties": {
                "cell_id": "cell_40_-74",
                "congestion_index": 0.85,
                "congestion_level": "high",
                "vehicle_count": 127,
                "height": 850
            }
        }
    ]
}
```
