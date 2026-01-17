from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
import json

from mappls_client import MapplsGeospace
from risk_engine import calculate_risk_index
from weather_client import OpenWeatherClient

# Get the project root directory (go up from src -> Backend -> ROBO-HACK)
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)  # Backend/
project_root = os.path.dirname(backend_dir)  # ROBO-HACK/

app = Flask(__name__, static_folder=project_root)
CORS(app)

# Load Config
config_path = os.path.join(backend_dir, 'config.json')
try:
    with open(config_path) as f:
        config = json.load(f)
    print(f"[Config] Loaded from: {config_path}")
except FileNotFoundError:
    print(f"[Config] Not found, using defaults")
    config = {"OPENWEATHER_API_KEY": ""}

# Initialize Logic Engines
mappls = MapplsGeospace(config_path)
weather_api = OpenWeatherClient(config.get('OPENWEATHER_API_KEY', ''))

# Initial sensor state
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
        "blocked_reason": "All Systems Normal",
        "scan_triggered": False,
        "timestamp": datetime.now().isoformat()
    }
}

@app.route('/data', methods=['POST'])
def receive_data():
    global sensor_data
    try:
        incoming = request.json
        if not incoming: 
            return jsonify({"status": "error", "message": "No data"}), 400

        print(f"\n[INCOMING] {incoming}")

        # Update core state
        for cat in ["mpu", "environment", "motor", "gps", "system"]:
            if cat in incoming:
                sensor_data[cat].update(incoming[cat])

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

        print(f"[RISK] Zone:{zone} | Score:{score} | Level:{level} | Reason:{reason}\n")

        return jsonify({"status": "success", "risk": score}), 200
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/current')
def get_current():
    return jsonify(sensor_data)

@app.route('/weather/set/<condition>', methods=['POST'])
def set_weather(condition):
    """Manually set weather condition for testing."""
    try:
        weather_api.set_weather_condition(condition)
        
        # Update weather data immediately
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
        
        # Recalculate risk with new weather
        zone = sensor_data['gps']['geo_zone']
        score, reason, level = calculate_risk_index(sensor_data, zone, weather_data)
        
        sensor_data['system']['risk_score'] = score
        sensor_data['system']['blocked_reason'] = reason
        sensor_data['system']['risk_level'] = level
        
        print(f"[WEATHER] Set to {condition} | New Score: {score}")
        
        return jsonify({
            "status": "success", 
            "condition": condition,
            "weather": sensor_data['weather'],
            "risk": score
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def index():
    return send_from_directory(project_root, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(project_root, filename)

if __name__ == '__main__':
    print("="*70)
    print("🚁 AeroGuard - Smart UAV Pre-Flight Risk Assessment System")
    print("="*70)
    print(f"📂 Project Root: {project_root}")
    print(f"📂 Backend Dir: {backend_dir}")
    print(f"⚙️  Config: {config_path}")
    print(f"🌐 Local: http://localhost:5000")
    print(f"🌐 Network: http://0.0.0.0:5000")
    print("="*70)
    app.run(host="0.0.0.0", port=5000, debug=True)