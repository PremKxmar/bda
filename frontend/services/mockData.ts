import { TrafficStats, Prediction, Hotspot, TrafficEvent } from '../types';

export const INITIAL_STATS: TrafficStats = {
  totalVehicles: 0,
  avgCongestion: 0,
  avgSpeed: 0,
  mlAccuracy: 78.6, // Based on Spark MLlib model - 78.60% accuracy (realistic, no data leakage)
  totalCells: 0
};

// Fallback hotspots (used when API is not available)
export const HOTSPOTS: Hotspot[] = [
  { id: '1', name: 'Times Square', congestion: 92, coordinates: [40.7580, -73.9855], trend: 'up' },
  { id: '2', name: 'Penn Station', congestion: 87, coordinates: [40.7505, -73.9934], trend: 'up' },
  { id: '3', name: 'Grand Central', congestion: 84, coordinates: [40.7527, -73.9772], trend: 'down' },
  { id: '4', name: 'SoHo District', congestion: 76, coordinates: [40.7233, -74.0030], trend: 'stable' },
  { id: '5', name: 'Williamsburg Bridge', congestion: 71, coordinates: [40.7126, -73.9576], trend: 'down' },
];

export const generatePredictions = (): Prediction[] => {
  const predictions: Prediction[] = [];
  const now = new Date();
  for (let i = 0; i < 6; i++) {
    const time = new Date(now.getTime() + i * 15 * 60000);
    predictions.push({
      time: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      congestionLevel: 60 + Math.random() * 30,
      zone: 'Manhattan Core'
    });
  }
  return predictions;
};

// Generate some random traffic around NYC
export const generateTrafficEvents = (count: number): TrafficEvent[] => {
  const events: TrafficEvent[] = [];
  for (let i = 0; i < count; i++) {
    events.push({
      id: `v-${Math.random().toString(36).substr(2, 9)}`,
      lat: 40.7128 + (Math.random() - 0.5) * 0.1,
      lng: -74.0060 + (Math.random() - 0.5) * 0.1,
      speed: 10 + Math.random() * 30,
      type: Math.random() > 0.8 ? 'bus' : 'taxi'
    });
  }
  return events;
};
