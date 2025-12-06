# 🎨 Frontend Prompt for Google AI Studio

## Use this prompt to generate your dashboard UI

Copy the entire prompt below into Google AI Studio to generate your frontend.

---

# PROMPT START

## Project Context

I need a **stunning, modern web dashboard** for a Smart City Real-Time Traffic Simulation project. This is a Big Data + ML project that visualizes NYC taxi traffic in real-time using Kepler.gl for 3D maps.

## Design Requirements

### Overall Style
- **Theme**: Dark mode with vibrant accent colors (cyan, orange, purple gradients)
- **Feel**: Futuristic, sci-fi, like a NASA mission control dashboard
- **Typography**: Modern sans-serif (Inter, Poppins, or system fonts)
- **Animations**: Smooth transitions, subtle glows, pulsing indicators for real-time data

### Color Palette
```
Primary Background: #0a0a1a (dark navy)
Secondary Background: #1a1a2e (card background)
Accent Cyan: #00d4ff
Accent Orange: #ff6b35
Accent Purple: #8b5cf6
Success Green: #10b981
Warning Yellow: #f59e0b
Danger Red: #ef4444
Text Primary: #ffffff
Text Secondary: #94a3b8
```

## Pages Required

### Page 1: Landing Page (index.html)

Create an impressive landing page with:

1. **Hero Section**
   - Large title: "SMART CITY TRAFFIC INTELLIGENCE"
   - Subtitle: "Real-time traffic prediction powered by Big Data & AI"
   - Animated background (gradient mesh or particle effect)
   - Glowing "Launch Dashboard" button

2. **Stats Counter Section** (animate numbers on scroll)
   - "7+ GB" - Data Processed
   - "46M+" - Taxi Trips Analyzed  
   - "1000+" - Events/Second
   - "82%" - ML Accuracy

3. **Features Section** (3 cards)
   - Card 1: "Real-Time Streaming" - Kafka icon, description
   - Card 2: "ML Predictions" - Brain icon, predict jams 15 min ahead
   - Card 3: "3D Visualization" - Map icon, Kepler.gl powered

4. **Tech Stack Section**
   - Logos/icons: Apache Spark, Kafka, Python, Kepler.gl
   - Brief description of each

5. **Architecture Diagram Section**
   - Visual flow: Data → Spark → Kafka → ML → Dashboard

6. **Footer**
   - "Final Year Big Data Project"
   - GitHub link placeholder

### Page 2: Dashboard (dashboard.html)

Create the main analytics dashboard with:

1. **Top Navigation Bar**
   - Logo: "🏙️ NYC Traffic"
   - Status indicator (green dot + "LIVE")
   - Current time (updating)
   - Settings icon

2. **KPI Cards Row** (4 cards, update in real-time)
   - Card 1: 🚕 Active Vehicles - "12,847" - "+2.3% from last hour"
   - Card 2: 🚦 Avg Congestion - "67.3%" - indicator bar
   - Card 3: ⚡ Avg Speed - "18.5 mph" - trend arrow
   - Card 4: 🎯 ML Accuracy - "82.4%"

3. **Main Content Area** (2 columns on desktop)
   
   **Left Column (70%)**
   - **Map Container**: Large div for Kepler.gl embed
     - ID: "kepler-map-container"
     - Height: 500px
     - Border: subtle glow
   
   - **Time Control Bar** below map:
     - Play/Pause button
     - Speed selector: 1x, 10x, 100x
     - Time slider (0:00 to 23:59)
     - Current simulation time display

   **Right Column (30%)**
   
   - **Predictions Panel**
     - Title: "🔮 ML Predictions (15 min)"
     - List of predicted congestion zones
     - Confidence percentage for each
   
   - **Hotspots Panel**
     - Title: "🔥 Top Congested Zones"
     - Ranked list (1-5)
     - Each item: Zone name, congestion %, trend arrow
   
   - **Real-Time Chart**
     - Title: "📊 Congestion Over Time"
     - Line chart showing last 2 hours
     - Use Chart.js or simple CSS animation

4. **Bottom Status Bar**
   - "Connected to API ✓"
   - "Kafka: 1,250 events/s"
   - "Last update: 2 seconds ago"

## API Integration

The dashboard should fetch data from these endpoints:

```javascript
// Base URL
const API_BASE = 'http://localhost:5000/api';

// Endpoints
GET /api/current-traffic    // Returns cell congestion data
GET /api/predictions        // Returns ML predictions
GET /api/hotspots           // Returns top congested zones
GET /api/stats              // Returns overall statistics
GET /api/geojson/cells      // Returns GeoJSON for Kepler.gl
GET /api/geojson/vehicles   // Returns vehicle positions
```

### Sample API Response (current-traffic):
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
            "avg_speed": 8.5
        }
    ]
}
```

## Kepler.gl Integration

Include this script for Kepler.gl:
```html
<script src="https://unpkg.com/kepler.gl@2.5.5/umd/keplergl.min.js"></script>
<link href="https://unpkg.com/kepler.gl@2.5.5/umd/keplergl.min.css" rel="stylesheet">
```

Map configuration:
- Center: NYC (40.7128, -74.0060)
- Zoom: 11
- 3D mode enabled
- Dark map style (Mapbox dark-v10)

Layers needed:
1. **Hexagon Layer**: Show congestion by cell (color + height)
2. **Point Layer**: Show moving vehicles (animated dots)
3. **Polygon Layer**: Show prediction zones (orange overlay)

## Technical Requirements

- **HTML5** semantic structure
- **CSS3** with CSS Grid/Flexbox
- **Vanilla JavaScript** (no React needed)
- **Responsive**: Works on 1920px and 1366px screens
- **Performance**: Smooth 60fps animations
- **Accessibility**: Proper ARIA labels

## File Structure
```
dashboard/
├── index.html          # Landing page
├── dashboard.html      # Main dashboard
├── css/
│   ├── style.css       # Main styles
│   └── dashboard.css   # Dashboard-specific styles
├── js/
│   ├── main.js         # Landing page scripts
│   ├── dashboard.js    # Dashboard logic
│   ├── api.js          # API calls
│   └── kepler-config.js # Kepler.gl setup
└── assets/
    └── (any icons/images)
```

## Example Component: KPI Card

```html
<div class="kpi-card">
    <div class="kpi-icon">🚕</div>
    <div class="kpi-content">
        <span class="kpi-label">Active Vehicles</span>
        <span class="kpi-value" id="vehicle-count">12,847</span>
        <span class="kpi-trend positive">▲ +2.3%</span>
    </div>
</div>
```

```css
.kpi-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 16px;
    padding: 24px;
    border: 1px solid rgba(0, 212, 255, 0.2);
    box-shadow: 0 0 20px rgba(0, 212, 255, 0.1);
    transition: transform 0.3s, box-shadow 0.3s;
}

.kpi-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 0 30px rgba(0, 212, 255, 0.2);
}

.kpi-value {
    font-size: 2.5rem;
    font-weight: 700;
    background: linear-gradient(90deg, #00d4ff, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
```

## Animations

1. **Number Counter**: Animate from 0 to target on page load
2. **Pulse Effect**: Subtle pulse on "LIVE" indicator
3. **Card Hover**: Lift and glow on hover
4. **Data Update**: Brief flash when values update
5. **Loading State**: Skeleton screens while fetching

## Must-Have Elements

✅ Glassmorphism effects on cards
✅ Gradient text on important numbers
✅ Animated gradient background on landing page
✅ Pulsing "LIVE" indicator
✅ Smooth number transitions
✅ Responsive grid layout
✅ Dark scrollbar styling
✅ Hover states on all interactive elements

---

# PROMPT END

---

## How to Use This Prompt

1. Open Google AI Studio (ai.studio.google.com)
2. Start a new chat with Gemini
3. Paste the entire prompt above
4. Ask: "Generate the complete HTML, CSS, and JavaScript files for this dashboard"
5. You may need to ask for files one at a time:
   - "Generate index.html"
   - "Generate dashboard.html"
   - "Generate style.css"
   - "Generate dashboard.js"

## After Generation

1. Save the generated files in `smart-city-traffic/dashboard/`
2. Test by opening `index.html` in browser
3. Make sure API endpoints match (adjust if needed)
4. Connect to your Flask backend

## Tips for Better Results

- If the output is too long, ask for one file at a time
- Ask for "complete, production-ready code"
- Specify "include all CSS in the file" if you want single-file output
- Ask to "make it more futuristic" if design is too plain
- Request "add more animations" for extra polish
