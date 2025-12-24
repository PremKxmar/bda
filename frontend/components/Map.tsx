import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { TrafficEvent, Hotspot } from '../types';

interface MapProps {
  events: TrafficEvent[];
  hotspots: Hotspot[];
}

const Map: React.FC<MapProps> = ({ events, hotspots }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const cellLayersRef = useRef<L.Layer[]>([]);
  const hotspotLayersRef = useRef<L.Layer[]>([]);

  useEffect(() => {
    if (mapContainerRef.current && !mapInstanceRef.current) {
      // Initialize Map
      const map = L.map(mapContainerRef.current, {
        center: [40.7580, -73.9855],
        zoom: 13,
        zoomControl: false,
        attributionControl: false
      });

      // Dark Matter Tile Layer (CartoDB)
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        subdomains: 'abcd',
        maxZoom: 19
      }).addTo(map);

      // Add zoom control to bottom right
      L.control.zoom({ position: 'bottomright' }).addTo(map);

      mapInstanceRef.current = map;
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update traffic cell visualization with smooth heatmap-style circles
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    // Clear old cell layers
    cellLayersRef.current.forEach(l => l.remove());
    cellLayersRef.current = [];

    // Create smooth circular markers for each cell
    events.forEach(event => {
      // Determine color and intensity based on congestion level
      let color: string;
      let glowColor: string;
      let fillOpacity: number;
      let radius: number;
      
      const congestionValue = event.congestionIndex || 0.5;
      
      if (event.congestionLevel) {
        switch (event.congestionLevel) {
          case 'high':
            color = '#ef4444'; // Red
            glowColor = 'rgba(239, 68, 68, 0.4)';
            fillOpacity = 0.4;
            radius = 120 + congestionValue * 60;
            break;
          case 'medium':
            color = '#f59e0b'; // Amber
            glowColor = 'rgba(245, 158, 11, 0.3)';
            fillOpacity = 0.3;
            radius = 100 + congestionValue * 40;
            break;
          case 'low':
          default:
            color = '#10b981'; // Green
            glowColor = 'rgba(16, 185, 129, 0.25)';
            fillOpacity = 0.2;
            radius = 80 + congestionValue * 30;
        }
      } else {
        // Fallback to speed-based coloring
        if (event.speed < 15) {
          color = '#ef4444';
          glowColor = 'rgba(239, 68, 68, 0.4)';
          fillOpacity = 0.4;
          radius = 140;
        } else if (event.speed < 30) {
          color = '#f59e0b';
          glowColor = 'rgba(245, 158, 11, 0.3)';
          fillOpacity = 0.3;
          radius = 120;
        } else {
          color = '#10b981';
          glowColor = 'rgba(16, 185, 129, 0.25)';
          fillOpacity = 0.2;
          radius = 100;
        }
      }

      // Create outer glow circle (larger, more transparent)
      const outerGlow = L.circle([event.lat, event.lng], {
        color: 'transparent',
        fillColor: color,
        fillOpacity: fillOpacity * 0.2,
        radius: radius * 1.3,
        weight: 0
      });
      outerGlow.addTo(map);
      cellLayersRef.current.push(outerGlow);

      // Create main circle with gradient effect
      const mainCircle = L.circle([event.lat, event.lng], {
        color: color,
        fillColor: color,
        fillOpacity: fillOpacity,
        radius: radius,
        weight: 1,
        opacity: 0.6
      });

      // Add popup with cell info
      const popupContent = `
        <div style="font-family: 'Inter', sans-serif; padding: 12px; min-width: 180px;">
          <div style="font-weight: 700; font-size: 14px; margin-bottom: 10px; color: #1f2937; border-bottom: 2px solid ${color}; padding-bottom: 6px;">
            📍 ${event.id}
          </div>
          <div style="display: grid; gap: 6px; font-size: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="color: #6b7280;">Congestion:</span>
              <span style="font-weight: 700; color: ${color}; background: ${color}20; padding: 2px 8px; border-radius: 4px;">
                ${event.congestionIndex ? Math.round(event.congestionIndex * 100) + '%' : 'N/A'}
              </span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="color: #6b7280;">Avg Speed:</span>
              <span style="font-weight: 600; color: #1f2937;">${event.speed.toFixed(1)} mph</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="color: #6b7280;">Vehicles:</span>
              <span style="font-weight: 600; color: #1f2937;">${event.vehicleCount || 'N/A'}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="color: #6b7280;">Status:</span>
              <span style="font-weight: 600; color: ${color}; text-transform: uppercase; font-size: 10px;">
                ${event.congestionLevel || 'Unknown'}
              </span>
            </div>
          </div>
        </div>
      `;
      mainCircle.bindPopup(popupContent);

      mainCircle.addTo(map);
      cellLayersRef.current.push(mainCircle);
    });

  }, [events]);

  // Update hotspot indicators
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    hotspotLayersRef.current.forEach(l => l.remove());
    hotspotLayersRef.current = [];

    hotspots.forEach(hotspot => {
        const isTrendUp = hotspot.trend === 'up';
        
        let color = '#00d4ff'; // default cyan
        if (isTrendUp) color = '#ef4444'; // red (danger)
        if (hotspot.trend === 'down') color = '#10b981'; // emerald (success)

        // The geofence area (Base circle)
        const circle = L.circle(hotspot.coordinates, {
            color: color,
            fillColor: color,
            fillOpacity: isTrendUp ? 0.15 : 0.05,
            radius: 400, // Slightly larger coverage
            weight: isTrendUp ? 1 : 1,
            dashArray: isTrendUp ? undefined : '4, 4'
        }).addTo(map);
        hotspotLayersRef.current.push(circle);

        // Prominent Visual for UP Trends
        if (isTrendUp) {
            // Complex HTML icon for the "Alarm" effect
            const pulseIcon = L.divIcon({
                className: 'bg-transparent border-none',
                html: `
                    <div class="relative w-full h-full flex items-center justify-center">
                        <!-- Outer slow ripple -->
                        <span class="absolute inline-flex h-full w-full rounded-full bg-red-500 opacity-20 animate-[ping_2s_linear_infinite]"></span>
                        
                        <!-- Inner fast ripple -->
                        <span class="absolute inline-flex h-3/4 w-3/4 rounded-full bg-red-500 opacity-40 animate-[ping_1.5s_linear_infinite]"></span>
                        
                        <!-- Glowing Core -->
                        <div class="relative w-8 h-8 bg-gradient-to-br from-red-500 to-orange-600 rounded-full border-2 border-white shadow-[0_0_25px_rgba(239,68,68,0.6)] flex items-center justify-center z-10">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="12" y1="5" x2="12" y2="19"></line>
                                <line x1="5" y1="12" x2="19" y2="12"></line>
                            </svg>
                        </div>
                        
                        <!-- Label (Optional, floating above) -->
                        <div class="absolute -top-8 bg-black/80 backdrop-blur px-2 py-0.5 rounded text-[10px] font-bold text-red-400 whitespace-nowrap border border-red-500/30">
                            ${hotspot.congestion}% Congestion
                        </div>
                    </div>
                `,
                iconSize: [64, 64], // Larger container
                iconAnchor: [32, 32]
            });

            const marker = L.marker(hotspot.coordinates, {
                icon: pulseIcon,
                zIndexOffset: 1000 // Ensure it sits on top of vehicles
            }).addTo(map);
            hotspotLayersRef.current.push(marker);
        } else {
            // Simple marker for stable/down trends
             const simpleIcon = L.divIcon({
                className: 'bg-transparent border-none',
                html: `
                    <div class="flex items-center justify-center w-full h-full">
                         <div class="w-3 h-3 ${hotspot.trend === 'down' ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : 'bg-cyan-500 shadow-[0_0_10px_#00d4ff]'} rounded-full border border-white/50"></div>
                    </div>
                `,
                iconSize: [20, 20],
                iconAnchor: [10, 10]
             });
             const marker = L.marker(hotspot.coordinates, { icon: simpleIcon }).addTo(map);
             hotspotLayersRef.current.push(marker);
        }
    });
  }, [hotspots]);

  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden border border-white/10 shadow-2xl">
      <div ref={mapContainerRef} className="w-full h-full z-0" />
      
      {/* Map Overlay Gradient */}
      <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-background/80 via-transparent to-transparent z-[400]" />
      
      {/* Legend */}
      <div className="absolute bottom-4 right-4 z-[500] glass-card p-4 rounded-lg text-xs space-y-3 w-48 border-l-4 border-l-surfaceHighlight">
        <h4 className="font-bold text-gray-400 uppercase tracking-widest text-[10px] mb-2">Live Traffic Map</h4>
        
        <div className="space-y-2">
            <div className="flex items-center justify-between">
                <span className="text-gray-300">Fast Flow</span>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] text-emerald-500 font-mono">&gt;30mph</span>
                    <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
                </div>
            </div>
            <div className="flex items-center justify-between">
                <span className="text-gray-300">Moderate</span>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] text-amber-500 font-mono">15-30</span>
                    <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                </div>
            </div>
            <div className="flex items-center justify-between">
                <span className="text-gray-300">Heavy</span>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] text-red-500 font-mono">&lt;15mph</span>
                    <span className="w-2 h-2 rounded-full bg-red-500"></span>
                </div>
            </div>
        </div>

        <div className="my-2 border-t border-white/10"></div>

        <div className="flex items-center gap-3 bg-red-500/10 p-2 rounded border border-red-500/20">
            <div className="w-6 h-6 flex items-center justify-center relative flex-shrink-0">
                <span className="absolute w-full h-full bg-red-500/30 rounded-full animate-ping"></span>
                <div className="relative w-3 h-3 bg-gradient-to-br from-red-500 to-orange-500 rounded-full border border-white shadow-sm"></div>
            </div>
            <div>
                <div className="text-red-400 font-bold">Severe Hotspot</div>
                <div className="text-[10px] text-red-300/70 leading-tight">Congestion Trend Rising</div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default Map;