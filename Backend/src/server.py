
from flask import flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
import json

from mappls_client import MapplsGeospace
from risk_engine import calculate_risk_index
from weather_client import OpenWeatherClient

root_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, static_folder=root_dir)
CORS(app)

# Load Config
with open(os.path.join(root_dir, 'config.json')) as f:
    config = json.load(f)

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
        "timestamp": datetime.now().isoformat()
    }
}

@app.route('/data', methods=['POST'])
def receive_data():
    global sensor_data
    try:
        incoming = request.json
        if not incoming: return jsonify({"status": "error"}), 400

        # Update core state
        for cat in ["mpu", "environment", "motor", "gps", "system"]:
            if cat in incoming:
                sensor_data[cat].update(incoming[cat])

        # Fetch Environmental Data (Weather)
        weather_data = weather_api.get_weather(sensor_data['gps']['latitude'], sensor_data['gps']['longitude'])
        if weather_data:
            sensor_data['weather'] = {
                "wind_speed": weather_data['wind_speed'],
                "visibility": weather_data['visibility'],
                "condition": weather_data['weather_main']
            }

        # Run Risk Assessment Engine
        zone = mappls.check_airspace(sensor_data['gps']['latitude'], sensor_data['gps']['longitude'])
        sensor_data['gps']['geo_zone'] = zone
        
        score, reason, level = calculate_risk_index(sensor_data, zone, weather_data)
        
        sensor_data['system']['risk_score'] = score
        sensor_data['system']['blocked_reason'] = reason
        sensor_data['system']['risk_level'] = level
        sensor_data["system"]["timestamp"] = datetime.now().isoformat()

        return jsonify({"status": "success", "risk": score}), 200
    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/current')
def get_current():
    return jsonify(sensor_data)

@app.route('/')
def index():
    return send_from_directory(root_dir, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(root_dir, filename)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
