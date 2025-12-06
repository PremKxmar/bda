import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Activity, Cpu, Globe, Database, Layers } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background text-white overflow-hidden relative">
      
      {/* Background Ambience */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-accent-purple/20 rounded-full blur-[120px] animate-blob"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-accent-cyan/20 rounded-full blur-[120px] animate-blob animation-delay-2000"></div>
        <div className="absolute top-[40%] left-[40%] w-[30%] h-[30%] bg-accent-orange/10 rounded-full blur-[100px] animate-blob animation-delay-4000"></div>
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
      </div>

      {/* Navigation */}
      <nav className="relative z-50 flex justify-between items-center px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-cyan to-accent-purple flex items-center justify-center">
                <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight">TrafficAI</span>
        </div>
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-300">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#tech" className="hover:text-white transition-colors">Technology</a>
            <a href="#about" className="hover:text-white transition-colors">About</a>
        </div>
        <button 
            onClick={() => navigate('/dashboard')}
            className="px-5 py-2 rounded-full bg-white/10 hover:bg-white/20 border border-white/10 transition-all text-sm font-semibold backdrop-blur-md"
        >
            Launch Demo
        </button>
      </nav>

      {/* Hero Section */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-32 text-center">
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-purple/10 border border-accent-purple/20 text-accent-purple text-xs font-semibold mb-8"
        >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-purple opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-purple"></span>
            </span>
            Big Data Final Year Project 2025
        </motion.div>

        <motion.h1 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="text-6xl md:text-8xl font-extrabold tracking-tighter mb-8 leading-tight"
        >
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-white via-gray-200 to-gray-500">SMART CITY</span>
            <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-accent-cyan via-accent-purple to-accent-orange">
                TRAFFIC INTELLIGENCE
            </span>
        </motion.h1>

        <motion.p 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto mb-12 leading-relaxed"
        >
            Real-time traffic prediction powered by 46M+ taxi trips, machine learning, and streaming analytics. Visualizing the heartbeat of NYC.
        </motion.p>

        <motion.div 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
            <button 
                onClick={() => navigate('/dashboard')}
                className="group relative px-8 py-4 rounded-full bg-white text-black font-bold text-lg hover:shadow-[0_0_40px_-10px_rgba(255,255,255,0.3)] transition-all flex items-center gap-2"
            >
                Enter Dashboard
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <button className="px-8 py-4 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 text-white font-semibold text-lg transition-all backdrop-blur-md">
                View Architecture
            </button>
        </motion.div>

        {/* Floating Stats */}
        <motion.div 
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.5 }}
            className="mt-24 grid grid-cols-2 md:grid-cols-4 gap-4"
        >
            <StatCard label="Data Processed" value="7+ GB" />
            <StatCard label="Taxi Trips" value="46M+" />
            <StatCard label="Events/Sec" value="500+" />
            <StatCard label="ML Accuracy" value="78.6%" />
        </motion.div>
      </div>

      {/* Feature Grid */}
      <div className="relative z-10 bg-surface/50 border-t border-white/5 backdrop-blur-3xl py-24">
        <div className="max-w-7xl mx-auto px-6">
            <div className="text-center mb-16">
                <h2 className="text-3xl font-bold mb-4">Powerful Features</h2>
                <p className="text-gray-400">Everything you need for traffic intelligence</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <FeatureCard 
                    icon={<Database className="w-8 h-8 text-accent-cyan" />}
                    title="Real-Time Streaming"
                    description="Processing 500+ GPS events per second using Kafka streams for instant visibility."
                />
                <FeatureCard 
                    icon={<Cpu className="w-8 h-8 text-accent-purple" />}
                    title="ML Predictions"
                    description="Advanced Random Forest models predicting congestion levels 15 minutes into the future."
                />
                <FeatureCard 
                    icon={<Globe className="w-8 h-8 text-accent-orange" />}
                    title="Interactive 3D Maps"
                    description="Live visualization of vehicle movements and congestion hotspots using Leaflet."
                />
            </div>
        </div>
      </div>
      
      <footer className="relative z-10 py-8 border-t border-white/5 text-center text-gray-500 text-sm">
        <p>© 2025 Smart City Traffic Intelligence System • Final Year Project</p>
      </footer>
    </div>
  );
};

const StatCard: React.FC<{ label: string; value: string }> = ({ label, value }) => (
    <div className="glass-card p-6 rounded-2xl text-center hover:-translate-y-1 transition-transform duration-300">
        <div className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-white to-gray-400 mb-1">{value}</div>
        <div className="text-xs text-gray-500 uppercase tracking-widest font-semibold">{label}</div>
    </div>
);

const FeatureCard: React.FC<{ icon: React.ReactNode; title: string; description: string }> = ({ icon, title, description }) => (
    <div className="p-8 rounded-3xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
        <div className="mb-6 p-4 rounded-2xl bg-black/40 w-fit">{icon}</div>
        <h3 className="text-xl font-bold mb-3">{title}</h3>
        <p className="text-gray-400 leading-relaxed">{description}</p>
    </div>
);

export default LandingPage;
