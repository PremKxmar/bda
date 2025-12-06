export interface TrafficStats {
  totalVehicles: number;
  avgCongestion: number;
  avgSpeed: number;
  mlAccuracy: number;
  totalCells?: number;
  congestionBreakdown?: {
    low: number;
    medium: number;
    high: number;
  };
}

export interface Prediction {
  time: string;
  congestionLevel: number; // 0-100
  zone: string;
}

export interface Hotspot {
  id: string;
  name: string;
  congestion: number;
  coordinates: [number, number];
  trend: 'up' | 'down' | 'stable';
}

export interface TrafficEvent {
  id: string;
  lat: number;
  lng: number;
  speed: number;
  type: 'taxi' | 'bus' | 'private';
  // Extended properties for real data
  congestionLevel?: 'low' | 'medium' | 'high';
  congestionIndex?: number;
  vehicleCount?: number;
}

// API Connection Status
export interface ConnectionStatus {
  connected: boolean;
  lastUpdate: string | null;
  error: string | null;
}
