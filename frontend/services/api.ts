/**
 * API Service for Smart City Traffic Dashboard
 * Connects to the Flask backend at localhost:5000
 */

import { TrafficStats, Prediction, Hotspot, TrafficEvent } from '../types';

// API Configuration
const API_CONFIG = {
  BASE_URL: 'http://localhost:5000/api',
  ENDPOINTS: {
    health: '/health',
    stats: '/stats',
    traffic: '/current-traffic',
    predictions: '/predictions',
    hotspots: '/hotspots',
    geojsonCells: '/geojson/cells',
    geojsonVehicles: '/geojson/vehicles'
  }
};

// Types for API responses
export interface APIStatsResponse {
  timestamp: string;
  overview: {
    total_cells: number;
    total_vehicles: number;
    avg_congestion: number;
    avg_speed: number;
    data_processed: string;
    total_trips: string;
  };
  congestion_breakdown: {
    low: number;
    medium: number;
    high: number;
  };
  ml_model: {
    name: string;
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
  };
}

export interface APITrafficResponse {
  timestamp: string;
  total_cells: number;
  returned_cells: number;
  data: APICellData[];
}

export interface APICellData {
  cell_id: string;
  latitude: number;
  longitude: number;
  congestion_index: number;
  congestion_level: 'low' | 'medium' | 'high';
  vehicle_count: number;
  avg_speed: number;
  last_update: string;
}

export interface APIPredictionsResponse {
  timestamp: string;
  prediction_horizon: string;
  model_accuracy: number;
  predictions: APIPrediction[];
}

export interface APIPrediction {
  cell_id: string;
  latitude: number;
  longitude: number;
  current_level: string;
  current_index: number;
  predicted_level: string;
  predicted_index: number;
  confidence: number;
  change_percent: number;
}

export interface APIHotspotsResponse {
  timestamp: string;
  hotspots: APIHotspot[];
}

export interface APIHotspot {
  rank: number;
  cell_id: string;
  latitude: number;
  longitude: number;
  congestion_index: number;
  congestion_level: string;
  vehicle_count: number;
  avg_speed: number;
  trend: 'increasing' | 'stable' | 'decreasing';
}

export interface APIHealthResponse {
  status: string;
  timestamp: string;
  version: string;
  model_loaded: boolean;
  cells_loaded: number;
}

// API Client Class
class TrafficAPI {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_CONFIG.BASE_URL;
  }

  private async fetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // Health check
  async checkHealth(): Promise<APIHealthResponse> {
    return this.fetch<APIHealthResponse>(API_CONFIG.ENDPOINTS.health);
  }

  // Get overall stats
  async getStats(): Promise<APIStatsResponse> {
    return this.fetch<APIStatsResponse>(API_CONFIG.ENDPOINTS.stats);
  }

  // Get current traffic data
  async getTraffic(limit: number = 500): Promise<APITrafficResponse> {
    return this.fetch<APITrafficResponse>(`${API_CONFIG.ENDPOINTS.traffic}?limit=${limit}`);
  }

  // Get predictions
  async getPredictions(minConfidence: number = 0.7): Promise<APIPredictionsResponse> {
    return this.fetch<APIPredictionsResponse>(`${API_CONFIG.ENDPOINTS.predictions}?min_confidence=${minConfidence}`);
  }

  // Get hotspots
  async getHotspots(limit: number = 5): Promise<APIHotspotsResponse> {
    return this.fetch<APIHotspotsResponse>(`${API_CONFIG.ENDPOINTS.hotspots}?limit=${limit}`);
  }
}

// Create singleton instance
export const api = new TrafficAPI();

// Helper functions to convert API responses to frontend types
export function convertStatsToFrontend(apiStats: APIStatsResponse): TrafficStats {
  return {
    totalVehicles: apiStats.overview.total_vehicles,
    avgCongestion: apiStats.overview.avg_congestion * 100, // Convert 0-1 to 0-100
    avgSpeed: apiStats.overview.avg_speed,
    mlAccuracy: apiStats.ml_model.accuracy * 100 // Convert 0-1 to 0-100
  };
}

export function convertHotspotsToFrontend(apiHotspots: APIHotspot[]): Hotspot[] {
  return apiHotspots.map(h => ({
    id: h.cell_id,
    name: getZoneName(h.latitude, h.longitude, h.rank),
    congestion: Math.round(h.congestion_index * 100),
    coordinates: [h.latitude, h.longitude] as [number, number],
    trend: h.trend === 'increasing' ? 'up' : h.trend === 'decreasing' ? 'down' : 'stable'
  }));
}

export function convertTrafficToEvents(apiTraffic: APICellData[]): TrafficEvent[] {
  return apiTraffic.map(cell => ({
    id: cell.cell_id,
    lat: cell.latitude,
    lng: cell.longitude,
    speed: cell.avg_speed,
    type: 'taxi' as const,
    congestionLevel: cell.congestion_level,
    congestionIndex: cell.congestion_index,
    vehicleCount: cell.vehicle_count
  }));
}

// Helper to generate zone names based on coordinates
function getZoneName(lat: number, lon: number, rank: number): string {
  const zones = [
    { name: 'Times Square Area', lat: 40.758, lon: -73.985, radius: 0.01 },
    { name: 'Penn Station', lat: 40.750, lon: -73.993, radius: 0.01 },
    { name: 'Grand Central', lat: 40.752, lon: -73.977, radius: 0.01 },
    { name: 'SoHo District', lat: 40.723, lon: -74.003, radius: 0.01 },
    { name: 'Lower Manhattan', lat: 40.71, lon: -74.01, radius: 0.02 },
    { name: 'Midtown East', lat: 40.755, lon: -73.970, radius: 0.01 },
    { name: 'Midtown West', lat: 40.755, lon: -73.995, radius: 0.01 },
    { name: 'Upper East Side', lat: 40.775, lon: -73.960, radius: 0.015 },
    { name: 'Upper West Side', lat: 40.785, lon: -73.975, radius: 0.015 },
    { name: 'Chelsea', lat: 40.745, lon: -74.000, radius: 0.01 },
  ];

  for (const zone of zones) {
    const distance = Math.sqrt(Math.pow(lat - zone.lat, 2) + Math.pow(lon - zone.lon, 2));
    if (distance < zone.radius) {
      return zone.name;
    }
  }
  
  // Generate a name based on position
  return `Zone ${rank}`;
}

export default api;
