import React, { useState, useEffect, useCallback } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Car, Zap, BarChart3, Clock, Menu, Settings, Bell, ChevronUp, ChevronDown, MapPin, Wifi, WifiOff } from 'lucide-react';
import { motion } from 'framer-motion';
import Map from './Map';
import { TrafficStats, Prediction, Hotspot, TrafficEvent, ConnectionStatus } from '../types';
import { api, convertStatsToFrontend, convertHotspotsToFrontend, convertTrafficToEvents, APICellData } from '../services/api';
import { INITIAL_STATS, generatePredictions } from '../services/mockData';

// Constants
const UPDATE_INTERVAL = 5000; // 5 seconds

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<TrafficStats>(INITIAL_STATS);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [hotspots, setHotspots] = useState<Hotspot[]>([]);
  const [events, setEvents] = useState<TrafficEvent[]>([]);
  const [currentTime, setCurrentTime] = useState<string>('');
  const [connection, setConnection] = useState<ConnectionStatus>({
    connected: false,
    lastUpdate: null,
    error: null
  });
  const [congestionHistory, setCongestionHistory] = useState<Prediction[]>([]);

  // Fetch all data from API
  const fetchAllData = useCallback(async () => {
    try {
      // Fetch all data in parallel
      const [statsRes, trafficRes, hotspotsRes, predictionsRes] = await Promise.all([
        api.getStats(),
        api.getTraffic(5000),
        api.getHotspots(10),
        api.getPredictions(0.5)
      ]);

      console.log('API Responses:', { statsRes, trafficRes, hotspotsRes, predictionsRes });

      // Update stats
      const frontendStats = convertStatsToFrontend(statsRes);
      setStats(frontendStats);

      // Update traffic events (cells)
      const trafficEvents = convertTrafficToEvents(trafficRes.data);
      setEvents(trafficEvents);

      // Update hotspots
      const frontendHotspots = convertHotspotsToFrontend(hotspotsRes.hotspots);
      setHotspots(frontendHotspots);

      // Update congestion history for chart
      const now = new Date();
      const timeLabel = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setCongestionHistory(prev => {
        const newHistory = [...prev, {
          time: timeLabel,
          congestionLevel: frontendStats.avgCongestion,
          zone: 'Manhattan'
        }];
        // Keep last 12 points (1 minute of data at 5s intervals)
        return newHistory.slice(-12);
      });

      // Update predictions for chart (combine history with future predictions)
      const futurePredictions = predictionsRes.predictions.slice(0, 6).map((p, i) => {
        const futureTime = new Date(now.getTime() + (i + 1) * 15 * 60000);
        return {
          time: futureTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          congestionLevel: p.predicted_index * 100,
          zone: 'Manhattan'
        };
      });
      setPredictions(futurePredictions);

      // Update connection status
      setConnection({
        connected: true,
        lastUpdate: new Date().toISOString(),
        error: null
      });

    } catch (error) {
      console.error('Failed to fetch data:', error);
      setConnection(prev => ({
        ...prev,
        connected: false,
        error: error instanceof Error ? error.message : 'Connection failed'
      }));

      // Fall back to generated predictions if API fails
      if (predictions.length === 0) {
        setPredictions(generatePredictions());
      }
    }
  }, [predictions.length]);

  // Initialize and set up polling
  useEffect(() => {
    // Initial fetch
    fetchAllData();

    // Update time every second
    const timeInterval = setInterval(() => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString());
    }, 1000);

    // Fetch data every UPDATE_INTERVAL
    const dataInterval = setInterval(fetchAllData, UPDATE_INTERVAL);

    return () => {
      clearInterval(timeInterval);
      clearInterval(dataInterval);
    };
  }, [fetchAllData]);

  return (
    <div className="min-h-screen bg-background text-white flex flex-col">
      {/* Navbar */}
      <nav className="h-16 border-b border-white/5 bg-surface/80 backdrop-blur-md sticky top-0 z-50 flex items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="bg-accent-cyan/10 p-2 rounded-lg">
            <Activity className="w-5 h-5 text-accent-cyan" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight">TrafficAI <span className="text-xs px-2 py-0.5 rounded-full bg-accent-purple/20 text-accent-purple ml-2 border border-accent-purple/20">NYC</span></h1>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            {connection.connected ? (
              <>
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
                <span className="text-xs font-medium text-emerald-400 tracking-wider">LIVE</span>
              </>
            ) : (
              <>
                <span className="relative flex h-3 w-3">
                  <span className="animate-pulse absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-yellow-500"></span>
                </span>
                <span className="text-xs font-medium text-yellow-400 tracking-wider">CONNECTING</span>
              </>
            )}
          </div>
          <div className="h-6 w-px bg-white/10"></div>
          <div className="flex items-center gap-2 text-sm font-mono text-gray-400">
            <Clock className="w-4 h-4" />
            {currentTime || '--:--:--'}
          </div>
          <div className="flex items-center gap-3">
            <button className="p-2 hover:bg-white/5 rounded-lg transition-colors"><Bell className="w-5 h-5 text-gray-400" /></button>
            <button className="p-2 hover:bg-white/5 rounded-lg transition-colors"><Settings className="w-5 h-5 text-gray-400" /></button>
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-accent-cyan to-accent-purple"></div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 p-6 grid grid-cols-12 gap-6 overflow-hidden">

        {/* KPI Row (Spans full width initially) */}
        <div className="col-span-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-2">
          <KPICard
            title="Active Vehicles"
            value={stats.totalVehicles.toLocaleString()}
            icon={<Car className="w-5 h-5 text-accent-cyan" />}
            trend="+12%"
            trendUp={true}
            color="cyan"
          />
          <KPICard
            title="Avg Congestion"
            value={`${stats.avgCongestion.toFixed(1)}%`}
            icon={<Activity className="w-5 h-5 text-accent-orange" />}
            trend="+2.4%"
            trendUp={true} // Bad thing increasing
            color="orange"
          />
          <KPICard
            title="Network Speed"
            value={`${stats.avgSpeed.toFixed(1)} mph`}
            icon={<Zap className="w-5 h-5 text-accent-purple" />}
            trend="-0.8%"
            trendUp={false}
            color="purple"
          />
          <KPICard
            title="ML Accuracy"
            value={`${stats.mlAccuracy}%`}
            icon={<BarChart3 className="w-5 h-5 text-emerald-500" />}
            trend="Stable"
            trendUp={true}
            color="emerald"
          />
        </div>

        {/* Middle Section: Map (Left) & Sidebar (Right) */}
        <div className="col-span-12 lg:col-span-8 h-[600px] flex flex-col gap-4">
          <div className="flex-1 rounded-2xl overflow-hidden relative border border-white/5 bg-surface">
            <Map events={events} hotspots={hotspots} />

            <div className="absolute top-4 left-4 glass-panel px-4 py-2 rounded-lg z-[400]">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">Active Region</h3>
              <div className="text-sm font-bold flex items-center gap-1">
                Manhattan, NYC
                <span className={`w-2 h-2 rounded-full ml-2 ${connection.connected ? 'bg-emerald-500' : 'bg-red-500 animate-pulse'}`}></span>
              </div>
            </div>

            {/* Connection Status Badge */}
            <div className={`absolute top-4 right-4 glass-panel px-3 py-1.5 rounded-lg z-[400] flex items-center gap-2 ${connection.connected ? 'border-emerald-500/30' : 'border-red-500/30'} border`}>
              {connection.connected ? (
                <>
                  <Wifi className="w-3 h-3 text-emerald-500" />
                  <span className="text-xs text-emerald-400">API Connected</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3 h-3 text-red-500" />
                  <span className="text-xs text-red-400">Connecting...</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right Sidebar: Predictions & Hotspots */}
        <div className="col-span-12 lg:col-span-4 flex flex-col gap-6 h-[600px]">

          {/* Predictions Chart */}
          <div className="glass-panel p-5 rounded-2xl flex-1 flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-semibold text-lg">Traffic Forecast</h3>
              <span className="text-xs bg-white/5 px-2 py-1 rounded text-gray-400">Next hour</span>
            </div>
            <div className="flex-1 w-full min-h-[150px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={predictions}>
                  <defs>
                    <linearGradient id="colorCongestion" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                  <XAxis dataKey="time" stroke="#ffffff40" fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke="#ffffff40" fontSize={10} tickLine={false} axisLine={false} unit="%" />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0a0a0f', borderColor: '#ffffff20', borderRadius: '8px' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Area type="monotone" dataKey="congestionLevel" stroke="#8b5cf6" strokeWidth={3} fillOpacity={1} fill="url(#colorCongestion)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Hotspots List */}
          <div className="glass-panel p-5 rounded-2xl flex-1 overflow-hidden flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-semibold text-lg">Congestion Hotspots</h3>
              <span className={`text-xs px-2 py-0.5 rounded-full ${connection.connected ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                {connection.connected ? 'LIVE' : 'OFFLINE'}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto pr-2 space-y-3 custom-scrollbar">
              {hotspots.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <div className="animate-spin w-6 h-6 border-2 border-accent-cyan border-t-transparent rounded-full mx-auto mb-2"></div>
                  Loading hotspots...
                </div>
              ) : (
                hotspots.map((hotspot, idx) => (
                  <div key={hotspot.id} className="group flex items-center justify-between p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors border border-transparent hover:border-white/10 cursor-pointer">
                    <div className="flex items-center gap-3">
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${idx < 2 ? 'bg-gradient-to-br from-red-500 to-orange-600 text-white' : 'bg-surfaceHighlight text-gray-400'}`}>
                        {idx + 1}
                      </div>
                      <div>
                        <div className="font-medium text-sm">{hotspot.name}</div>
                        <div className="text-xs text-gray-500 flex items-center gap-1">
                          <MapPin className="w-3 h-3" /> {hotspot.coordinates[0].toFixed(4)}, {hotspot.coordinates[1].toFixed(4)}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`font-bold text-sm ${hotspot.congestion > 85 ? 'text-accent-orange' : 'text-accent-cyan'}`}>
                        {hotspot.congestion}%
                      </div>
                      <div className="flex items-center justify-end">
                        {hotspot.trend === 'up' ? (
                          <ChevronUp className="w-3 h-3 text-red-500" />
                        ) : hotspot.trend === 'down' ? (
                          <ChevronDown className="w-3 h-3 text-emerald-500" />
                        ) : (
                          <span className="text-xs text-gray-500">-</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Status Bar */}
      <footer className="h-10 border-t border-white/5 bg-surface/80 backdrop-blur-md flex items-center justify-between px-6 text-xs text-gray-400">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-2">
            {connection.connected ? (
              <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
            ) : (
              <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
            )}
            API: {connection.connected ? 'Connected' : 'Disconnected'}
          </span>
          <span className="text-white/20">|</span>
          <span>Cells: {stats.totalCells || events.length}</span>
          <span className="text-white/20">|</span>
          <span>Update: {UPDATE_INTERVAL / 1000}s</span>
        </div>
        <div>
          {connection.lastUpdate && `Last update: ${new Date(connection.lastUpdate).toLocaleTimeString()}`}
        </div>
      </footer>
    </div>
  );
};

// Subcomponent: KPI Card
interface KPICardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  trend: string;
  trendUp: boolean;
  color: string;
}

const KPICard: React.FC<KPICardProps> = ({ title, value, icon, trend, trendUp, color }) => {
  return (
    <motion.div
      whileHover={{ y: -5 }}
      className="glass-card p-5 rounded-2xl relative overflow-hidden group"
    >
      <div className={`absolute top-0 right-0 p-24 bg-accent-${color}/5 rounded-full blur-3xl -mr-10 -mt-10 transition-opacity group-hover:opacity-100 opacity-50`}></div>

      <div className="flex justify-between items-start mb-4 relative z-10">
        <div className="p-2 bg-white/5 rounded-lg border border-white/5">
          {icon}
        </div>
        <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${trendUp ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
          {trend}
          {trendUp ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </div>
      </div>

      <div className="relative z-10">
        <div className="text-3xl font-bold tracking-tight mb-1 text-white">{value}</div>
        <div className="text-sm text-gray-400 font-medium">{title}</div>
      </div>
    </motion.div>
  )
}

export default Dashboard;
