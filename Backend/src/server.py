from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
import json
import sys

# Setup paths
root_dir = os.path.abspath(os.path.dirname(__file__))

# Add Backend/src to Python path
if os.path.exists(os.path.join(root_dir, 'Backend', 'src')):
    sys.path.insert(0, os.path.join(root_dir, 'Backend', 'src'))
    config_path = os.path.join(root_dir, 'Backend', 'config.json')
else:
    sys.path.insert(0, root_dir)
    config_path = os.path.join(root_dir, '..', 'config.json')

from mappls_client import MapplsGeospace
from risk_engine import calculate_risk_index
from weather_client import OpenWeatherClient

app = Flask(__name__, static_folder=root_dir)
CORS(app)

# CRITICAL: Disable all caching for real-time data
@app.after_request
def add_no_cache_headers(response):
    """Prevent caching to ensure real-time updates"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Load Config
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
    config_dir = os.path.dirname(config_path)
    os.makedirs(config_dir, exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✅ Created default config at: {config_path}")

# Initialize Logic Engines
mappls = MapplsGeospace()
weather_api = OpenWeatherClient(config.get('OPENWEATHER_API_KEY', ''))

# ✅ FIXED: Initialize with NULL values to detect missing data
sensor_data = {
    "mpu": {"ax": 0.0, "ay": 0.0, "az": 1.0, "vibration_rms": 0.0, "tilt_angle": 0.0},
    "environment": {"temperature": None, "humidity": None, "light_percent": None},
    "motor": {"rpm": 0, "hall_detected": False},
    "gps": {
        "latitude": None,  # None = no GPS fix yet
        "longitude": None,
        "speed": 0.0, 
        "satellites": 0, 
<<<<<<< HEAD
        "geo_zone": "UNKNOWN", 
        "hdop": 99.9,
        "raw_signal": 0
=======
        "geo_zone": "GREEN", 
        "hdop": 100,
        "raw_signal": 1000,
        "gps_quality": "UNKNOWN"
>>>>>>> 8e6b949a02823f0b2a488b3329d5ef7802b1a226
    },
    "weather": {
        "wind_speed": None,
        "visibility": None,
        "condition": "No Data"
    },
    "system": {
        "risk_score": 0,
        "risk_level": "STANDBY",
        "blocked_reason": "Waiting for Hardware...",
        "scan_triggered": False,
<<<<<<< HEAD
        "source": "NONE",
        "timestamp": datetime.now().isoformat(),
        "gps_valid": False,
        "sensors_valid": False
=======
        "timestamp": datetime.now().isoformat(),
        "source": "SIM"
>>>>>>> 8e6b949a02823f0b2a488b3329d5ef7802b1a226
    }
}

scan_reset_time = 0

def update_global_state(incoming, source="WiFi"):
    global sensor_data, scan_reset_time
    import time
    
    print("\n" + "="*60)
    print(f"📡 INCOMING DATA FROM {source} at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    print("="*60)
    
    # ✅ FIXED: Track if we have valid sensor data
    has_valid_gps = False
    has_valid_sensors = False
    
    # Update core state - ONLY with real data
    for cat in ["mpu", "environment", "motor", "gps", "system"]:
        if cat in incoming:
            # Only update if incoming data is not None
            for key, value in incoming[cat].items():
                if value is not None:
                    sensor_data[cat][key] = value
            
            # Print received values
            if cat == "environment":
                print(f"🌡️  Environment Data:")
                temp = incoming[cat].get('temperature')
                humid = incoming[cat].get('humidity')
                light = incoming[cat].get('light_percent')
                
                if temp is not None:
                    print(f"   Temperature: {temp:.1f}°C")
                    has_valid_sensors = True
                else:
                    print(f"   Temperature: N/A (sensor error)")
                    
                if humid is not None:
                    print(f"   Humidity: {humid:.0f}%")
                else:
                    print(f"   Humidity: N/A (sensor error)")
                    
                if light is not None:
                    print(f"   💡 Light Intensity: {light}%")
                    has_valid_sensors = True
                else:
                    print(f"   💡 Light Intensity: N/A")
            
            elif cat == "mpu":
                print(f"📊 MPU6050 Data:")
                print(f"   Vibration RMS: {incoming[cat].get('vibration_rms', 0):.3f}")
                print(f"   Tilt Angle: {incoming[cat].get('tilt_angle', 0):.1f}°")
                has_valid_sensors = True
            
            elif cat == "motor":
                rpm = incoming[cat].get('rpm', 0)
                print(f"⚙️  Motor Data:")
                print(f"   RPM: {rpm:.0f}")
                print(f"   Hall Sensor: {'✅ OK' if incoming[cat].get('hall_detected') else '❌ FAULT'}")
                has_valid_sensors = True
            
            elif cat == "gps":
                lat = incoming[cat].get('latitude')
                lng = incoming[cat].get('longitude')
                sats = incoming[cat].get('satellites', 0)
                hdop = incoming[cat].get('hdop', 99.9)
                
                print(f"🛰️  GPS Data:")
                if lat is not None and lng is not None:
                    print(f"   Location: {lat:.6f}, {lng:.6f}")
                    print(f"   Satellites: {sats}")
                    print(f"   HDOP: {hdop:.2f}")
                    has_valid_gps = True
                else:
                    print(f"   ⚠️  NO GPS FIX - Satellites: {sats}")
                    print(f"   HDOP: {hdop:.2f}")
    
    sensor_data['system']['source'] = source
    sensor_data['system']['gps_valid'] = has_valid_gps
    sensor_data['system']['sensors_valid'] = has_valid_sensors

    # Handle scan trigger
    if incoming.get('system', {}).get('scan_triggered'):
        scan_reset_time = time.time() + 5
        print(f"🔍 DIAGNOSTIC SCAN TRIGGERED!")

<<<<<<< HEAD
    if sensor_data['system']['scan_triggered'] and time.time() > scan_reset_time:
        sensor_data['system']['scan_triggered'] = False

    # ✅ FIXED: Only fetch weather if GPS is valid
    if has_valid_gps and sensor_data['gps']['latitude'] is not None:
=======
        # Mark data source
        if 'system' in incoming:
            sensor_data['system']['source'] = "WEB_SIM"  # From web simulator
        else:
            sensor_data['system']['source'] = "ESP32"

        # Update core state
        for cat in ["mpu", "environment", "motor", "gps", "system"]:
            if cat in incoming:
                sensor_data[cat].update(incoming[cat])

        # Fetch Environmental Data (Weather)
>>>>>>> 8e6b949a02823f0b2a488b3329d5ef7802b1a226
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
            print(f"🌤️  Weather Data:")
            print(f"   Condition: {weather_data['weather_main']}")
            print(f"   Wind Speed: {weather_data['wind_speed']} m/s")
    else:
        print(f"⚠️  Skipping weather check - GPS not valid")
        sensor_data['weather'] = {
            "wind_speed": None,
            "visibility": None,
            "condition": "No GPS Fix"
        }

    # ✅ FIXED: Only run risk assessment if GPS is valid
    if has_valid_gps and sensor_data['gps']['latitude'] is not None:
        zone = mappls.check_airspace(
            sensor_data['gps']['latitude'], 
            sensor_data['gps']['longitude']
        )
        sensor_data['gps']['geo_zone'] = zone
        
        score, reason, level = calculate_risk_index(sensor_data, zone, weather_data if has_valid_gps else None)
        
        sensor_data['system']['risk_score'] = score
        sensor_data['system']['blocked_reason'] = reason
        sensor_data['system']['risk_level'] = level
    else:
        sensor_data['gps']['geo_zone'] = "NO_GPS"
        sensor_data['system']['risk_score'] = 0
        sensor_data['system']['blocked_reason'] = "Waiting for GPS Fix..."
        sensor_data['system']['risk_level'] = "STANDBY"
    
    sensor_data["system"]["timestamp"] = datetime.now().isoformat()
    
    # Print risk assessment
    print(f"\n⚠️  Risk Assessment:")
    print(f"   Geo Zone: {sensor_data['gps']['geo_zone']}")
    print(f"   Risk Level: {sensor_data['system']['risk_level']}")
    print(f"   Risk Score: {sensor_data['system']['risk_score']}%")
    print(f"   Reason: {sensor_data['system']['blocked_reason']}")
    print("="*60 + "\n")

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        incoming = request.json
        if not incoming: 
            return jsonify({"status": "error", "message": "No data"}), 400
        
        update_global_state(incoming, source="ESP32")
        return jsonify({
            "status": "success", 
            "risk": sensor_data['system']['risk_score'],
            "gps_valid": sensor_data['system']['gps_valid']
        }), 200
    except Exception as e:
        print(f"❌ Server Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/current')
def get_current():
    import time
    global sensor_data
    if sensor_data['system']['scan_triggered'] and time.time() > scan_reset_time:
        sensor_data['system']['scan_triggered'] = False
    
    # Return fresh data with current timestamp
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
    print(f"🌐 Network: http://10.183.218.203:5000")
    print(f"📡 API endpoint: POST /data")
    print(f"📊 Data endpoint: GET /api/current")
    print("=" * 60)
    print("📝 Real-time logging enabled - Cache disabled")
    print("⚠️  Using REAL sensor data only - No simulation fallbacks")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)