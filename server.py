from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
import json
import sys

# Setup paths
root_dir = os.path.abspath(os.path.dirname(__file__))

# Add Backend/src to Python path if server.py is in root
# OR add parent directory if server.py is in Backend/src
if os.path.exists(os.path.join(root_dir, 'Backend', 'src')):
    # server.py is in project root
    sys.path.insert(0, os.path.join(root_dir, 'Backend', 'src'))
    config_path = os.path.join(root_dir, 'Backend', 'config.json')
else:
    # server.py is in Backend/src
    sys.path.insert(0, root_dir)
    config_path = os.path.join(root_dir, '..', 'config.json')

from mappls_client import MapplsGeospace
from risk_engine import calculate_risk_index
from weather_client import OpenWeatherClient

app = Flask(__name__, static_folder=root_dir)
CORS(app)

# Load Config with error handling
try:
    with open(config_path) as f:
        config = json.load(f)
    print(f"✅ Config loaded from: {config_path}")
except FileNotFoundError:
    print(f"❌ Config not found at: {config_path}")
    print("Creating default config.json...")
    config = {
        "OPENWEATHER_API_KEY": "your_api_key_here",
        "MAPPLS_API_KEY": "your_mappls_key_here",
        "simulation_settings": {
            "airport_red_zone": {"lat": 9.9300, "lng": 76.2670, "radius_km": 5.0},
            "caution_yellow_zone": {"lat": 9.9300, "lng": 76.2670, "radius_km": 10.0}
        }
    }
    # Create Backend directory if needed
    config_dir = os.path.dirname(config_path)
    os.makedirs(config_dir, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✅ Created default config at: {config_path}")

# Initialize Logic Engines
mappls = MapplsGeospace()
weather_api = OpenWeatherClient(config.get('OPENWEATHER_API_KEY', ''))

sensor_data = {
    "mpu": {"ax": 0.0, "ay": 0.0, "az": 1.0, "vibration_rms": 0.02, "tilt_angle": 0.0},
    "environment": {"temperature": 25.0, "humidity": 45.0, "light_percent": 0.0},
    "motor": {"rpm": 0, "hall_detected": True},
    "gps": {
        "latitude": 9.9312, 
        "longitude": 76.2673, 
        "speed": 0.0, 
        "satellites": 0, 
        "geo_zone": "GREEN", 
        "hdop": 100,
        "raw_signal": 1000 
    },
    "weather": {
        "wind_speed": 0.0,
        "visibility": 10000,
        "condition": "Clear"
    },
    "system": {
        "risk_score": 0,
        "risk_level": "SAFE",
        "blocked_reason": "STANDBY",
        "scan_triggered": False,
        "source": "IDLE",
        "timestamp": datetime.now().isoformat()
    }
}

scan_reset_time = 0

def update_global_state(incoming, source="WiFi"):
    global sensor_data, scan_reset_time
    import time
    
    # Update core state
    for cat in ["mpu", "environment", "motor", "gps", "system"]:
        if cat in incoming:
            sensor_data[cat].update(incoming[cat])
    
    sensor_data['system']['source'] = source

    # Handle scan trigger
    if incoming.get('system', {}).get('scan_triggered'):
        scan_reset_time = time.time() + 5

    if sensor_data['system']['scan_triggered'] and time.time() > scan_reset_time:
        sensor_data['system']['scan_triggered'] = False

    # Fetch Environmental Data (Weather)
    weather_data = weather_api.get_weather(
        sensor_data['gps']['latitude'], 
        sensor_data['gps']['longitude']
    )
    
    if weather_data:
        sensor_data['weather'] = {
            "wind_speed": weather_data['wind_speed'],
            "visibility": weather_data['visibility'],
            "condition": weather_data['weather_main']
        }

    # Run Risk Assessment Engine
    zone = mappls.check_airspace(
        sensor_data['gps']['latitude'], 
        sensor_data['gps']['longitude']
    )
    sensor_data['gps']['geo_zone'] = zone
    
    score, reason, level = calculate_risk_index(sensor_data, zone, weather_data)
    
    sensor_data['system']['risk_score'] = score
    sensor_data['system']['blocked_reason'] = reason
    sensor_data['system']['risk_level'] = level
    sensor_data["system"]["timestamp"] = datetime.now().isoformat()

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        incoming = request.json
        if not incoming: 
            return jsonify({"status": "error", "message": "No data"}), 400
        
        update_global_state(incoming, source="WiFi")
        return jsonify({"status": "success", "risk": sensor_data['system']['risk_score']}), 200
    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/current')
def get_current():
    import time
    global sensor_data
    if sensor_data['system']['scan_triggered'] and time.time() > scan_reset_time:
        sensor_data['system']['scan_triggered'] = False
    return jsonify(sensor_data)

@app.route('/')
def index():
    return send_from_directory(root_dir, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(root_dir, filename)

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 AeroGuard Mission Control - Server Starting")
    print("=" * 60)
    print(f"📁 Root directory: {root_dir}")
    print(f"📄 Config loaded: {config_path}")
    print(f"🌐 Frontend: http://localhost:5000")
    print(f"🌐 Network: http://YOUR_IP:5000")
    print(f"📡 API endpoint: POST /data")
    print(f"📊 Data endpoint: GET /api/current")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)