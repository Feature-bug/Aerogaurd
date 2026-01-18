from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os
import json
import sys
import time

# ============================================
# PATH SETUP
# ============================================

# Get the directory where server.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Determine project structure
if os.path.basename(current_dir) == 'src':
    # Running from Backend/src/
    backend_dir = os.path.dirname(current_dir)  # Backend/
    project_root = os.path.dirname(backend_dir)  # ROBO-HACK/
    config_path = os.path.join(backend_dir, 'config.json')
else:
    # Running from project root
    project_root = current_dir
    backend_dir = os.path.join(current_dir, 'Backend')
    config_path = os.path.join(backend_dir, 'config.json')

# Add Backend/src to Python path for imports
sys.path.insert(0, os.path.join(backend_dir, 'src'))

print(f"📂 Project Root: {project_root}")
print(f"📂 Backend Dir: {backend_dir}")
print(f"📂 Config Path: {config_path}")

# Import modules
from mappls_client import MapplsGeospace
from risk_engine import calculate_risk_index
from weather_client import OpenWeatherClient

# ============================================
# FLASK APP SETUP
# ============================================

app = Flask(__name__, static_folder=project_root)
CORS(app)

# CRITICAL: Disable all caching for real-time data
@app.after_request
def add_no_cache_headers(response):
    """Prevent caching to ensure real-time updates"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# ============================================
# LOAD CONFIGURATION
# ============================================

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
            "airport_red_zone": {"lat": 9.9401, "lng": 76.2701, "radius_km": 2.0},
            "caution_yellow_zone": {"lat": 9.9401, "lng": 76.2701, "radius_km": 5.0}
        },
        "risk_thresholds": {
            "gps": {
                "min_satellites": {"safe": 8, "critical": 4},
                "hdop": {"good": 5.0, "poor": 10.0}
            }
        }
    }
    
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✅ Created default config at: {config_path}")

# ============================================
# INITIALIZE MODULES
# ============================================

mappls = MapplsGeospace()
weather_api = OpenWeatherClient(config.get('OPENWEATHER_API_KEY', ''))

# ============================================
# GLOBAL STATE (Initial Values)
# ============================================

sensor_data = {
    "mpu": {
        "ax": 0.0, 
        "ay": 0.0, 
        "az": 1.0, 
        "vibration_rms": 0.0, 
        "tilt_angle": 0.0
    },
    "environment": {
        "temperature": None,  # None = sensor not connected
        "humidity": None, 
        "light_percent": None
    },
    "motor": {
        "rpm": 0, 
        "hall_detected": False
    },
    "gps": {
        "latitude": None,  # None = no GPS fix
        "longitude": None,
        "speed": 0.0, 
        "satellites": 0, 
        "geo_zone": "UNKNOWN", 
        "hdop": 99.9,
        "raw_signal": 0,
        "gps_quality": "UNKNOWN"
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
        "source": "NONE",
        "timestamp": datetime.now().isoformat(),
        "gps_valid": False,
        "sensors_valid": False
    }
}

scan_reset_time = 0

# ============================================
# CORE UPDATE FUNCTION
# ============================================

def update_global_state(incoming, source="UNKNOWN"):
    """
    Update global sensor state with incoming data.
    Returns: (success: bool, message: str)
    """
    global sensor_data, scan_reset_time
    
    print("\n" + "="*70)
    print(f"📡 INCOMING DATA FROM {source} @ {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    print("="*70)
    
    has_valid_gps = False
    has_valid_sensors = False
    
    # ============================================
    # UPDATE SENSOR DATA
    # ============================================
    
    for cat in ["mpu", "environment", "motor", "gps", "system"]:
        if cat in incoming:
            # Update only non-None values
            for key, value in incoming[cat].items():
                if value is not None:
                    sensor_data[cat][key] = value
            
            # Log received data
            if cat == "environment":
                temp = incoming[cat].get('temperature')
                humid = incoming[cat].get('humidity')
                light = incoming[cat].get('light_percent')
                
                print(f"🌡️  Environment:")
                if temp is not None:
                    print(f"   Temp: {temp:.1f}°C")
                    has_valid_sensors = True
                else:
                    print(f"   Temp: N/A")
                    
                if humid is not None:
                    print(f"   Humidity: {humid:.0f}%")
                    has_valid_sensors = True
                else:
                    print(f"   Humidity: N/A")
                    
                if light is not None:
                    print(f"   💡 Light: {light}%")
                    has_valid_sensors = True
                else:
                    print(f"   💡 Light: N/A")
            
            elif cat == "mpu":
                vib = incoming[cat].get('vibration_rms', 0)
                tilt = incoming[cat].get('tilt_angle', 0)
                print(f"📊 MPU6050:")
                print(f"   Vibration: {vib:.3f}G")
                print(f"   Tilt: {tilt:.1f}°")
                has_valid_sensors = True
            
            elif cat == "motor":
                rpm = incoming[cat].get('rpm', 0)
                hall = incoming[cat].get('hall_detected', False)
                print(f"⚙️  Motor:")
                print(f"   RPM: {rpm:.0f}")
                print(f"   Hall: {'✅ OK' if hall else '❌ FAULT'}")
                has_valid_sensors = True
            
            elif cat == "gps":
                lat = incoming[cat].get('latitude')
                lng = incoming[cat].get('longitude')
                sats = incoming[cat].get('satellites', 0)
                hdop_raw = incoming[cat].get('hdop', 9999)
                
                # Convert HDOP if needed (ESP32 sends raw * 100)
                hdop = hdop_raw / 100.0 if hdop_raw > 50 else hdop_raw
                sensor_data['gps']['hdop'] = hdop
                
                print(f"🛰️  GPS:")
                if lat is not None and lng is not None and lat != 0 and lng != 0:
                    print(f"   Location: {lat:.6f}, {lng:.6f}")
                    print(f"   Satellites: {sats}")
                    print(f"   HDOP: {hdop:.2f}")
                    has_valid_gps = True
                    
                    # Update GPS quality label
                    if hdop < 1.0:
                        sensor_data['gps']['gps_quality'] = "IDEAL"
                    elif hdop < 2.0:
                        sensor_data['gps']['gps_quality'] = "EXCELLENT"
                    elif hdop < 5.0:
                        sensor_data['gps']['gps_quality'] = "GOOD"
                    elif hdop < 10.0:
                        sensor_data['gps']['gps_quality'] = "MODERATE"
                    elif hdop < 20.0:
                        sensor_data['gps']['gps_quality'] = "FAIR"
                    else:
                        sensor_data['gps']['gps_quality'] = "POOR"
                else:
                    print(f"   ⚠️  NO FIX (Sats: {sats}, HDOP: {hdop:.2f})")
                    sensor_data['gps']['gps_quality'] = "NO_FIX"
    
    # ============================================
    # UPDATE SYSTEM FLAGS
    # ============================================
    
    sensor_data['system']['source'] = source
    sensor_data['system']['gps_valid'] = has_valid_gps
    sensor_data['system']['sensors_valid'] = has_valid_sensors
    
    # ============================================
    # HANDLE DIAGNOSTIC SCAN
    # ============================================
    
    if incoming.get('system', {}).get('scan_triggered'):
        sensor_data['system']['scan_triggered'] = True
        scan_reset_time = time.time() + 5
        print(f"🔍 DIAGNOSTIC SCAN TRIGGERED (5s duration)")
    
    # Auto-reset scan after timeout
    if sensor_data['system']['scan_triggered'] and time.time() > scan_reset_time:
        sensor_data['system']['scan_triggered'] = False
        print(f"✅ Diagnostic scan completed")
    
    # ============================================
    # FETCH WEATHER DATA
    # ============================================
    
    weather_data = None
    
    if has_valid_gps:
        try:
            weather_data = weather_api.get_weather(
                sensor_data['gps']['latitude'], 
                sensor_data['gps']['longitude']
            )
            
            if weather_data:
                sensor_data['weather'] = {
                    "wind_speed": weather_data.get('wind_speed', 0),
                    "visibility": weather_data.get('visibility', 10000),
                    "condition": weather_data.get('weather_main', 'Clear')
                }
                print(f"🌤️  Weather:")
                print(f"   Condition: {weather_data.get('weather_main', 'Unknown')}")
                print(f"   Wind: {weather_data.get('wind_speed', 0):.1f} m/s")
                print(f"   Visibility: {weather_data.get('visibility', 10000)/1000:.1f} km")
        except Exception as e:
            print(f"⚠️  Weather fetch failed: {e}")
            sensor_data['weather'] = {
                "wind_speed": None,
                "visibility": None,
                "condition": "Unavailable"
            }
    else:
        sensor_data['weather'] = {
            "wind_speed": None,
            "visibility": None,
            "condition": "No GPS Fix"
        }
    
    # ============================================
    # GEOFENCE & RISK ASSESSMENT
    # ============================================
    
    if has_valid_gps:
        # Check airspace zone
        zone = mappls.check_airspace(
            sensor_data['gps']['latitude'], 
            sensor_data['gps']['longitude']
        )
        sensor_data['gps']['geo_zone'] = zone
        
        # Calculate risk
        score, reason, level = calculate_risk_index(
            sensor_data, 
            zone, 
            weather_data
        )
        
        sensor_data['system']['risk_score'] = score
        sensor_data['system']['blocked_reason'] = reason
        sensor_data['system']['risk_level'] = level
        
        print(f"\n⚠️  Risk Assessment:")
        print(f"   Zone: {zone}")
        print(f"   Level: {level}")
        print(f"   Score: {score}%")
        print(f"   Reason: {reason}")
    else:
        # No GPS = No geofence, no risk calculation
        sensor_data['gps']['geo_zone'] = "UNKNOWN"
        sensor_data['system']['risk_score'] = 0
        sensor_data['system']['blocked_reason'] = "Waiting for GPS Fix..."
        sensor_data['system']['risk_level'] = "STANDBY"
        
        print(f"\n⚠️  Risk Assessment:")
        print(f"   Status: STANDBY (No GPS Fix)")
    
    # Update timestamp
    sensor_data["system"]["timestamp"] = datetime.now().isoformat()
    
    print("="*70 + "\n")
    
    return True, "Data updated successfully"

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/data', methods=['POST'])
def receive_data():
    """
    Receive sensor data from ESP32 or web simulator.
    POST /data
    Body: JSON with sensor readings
    """
    try:
        incoming = request.json
        if not incoming: 
            return jsonify({
                "status": "error", 
                "message": "No data received"
            }), 400
        
        # Determine source
        if 'system' in incoming and incoming.get('system', {}).get('source'):
            source = incoming['system']['source']
        else:
            source = "ESP32"
        
        # Update global state
        success, message = update_global_state(incoming, source=source)
        
        if success:
            return jsonify({
                "status": "success", 
                "risk": sensor_data['system']['risk_score'],
                "risk_level": sensor_data['system']['risk_level'],
                "gps_valid": sensor_data['system']['gps_valid'],
                "message": message
            }), 200
        else:
            return jsonify({
                "status": "error", 
                "message": message
            }), 400
            
    except Exception as e:
        print(f"❌ Error in /data endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/current', methods=['GET'])
def get_current():
    """
    Get current sensor state.
    GET /api/current
    Returns: JSON with all sensor data
    """
    global sensor_data
    
    # Auto-reset scan trigger after timeout
    if sensor_data['system']['scan_triggered'] and time.time() > scan_reset_time:
        sensor_data['system']['scan_triggered'] = False
    
    # Always return fresh timestamp
    sensor_data['system']['timestamp'] = datetime.now().isoformat()
    
    return jsonify(sensor_data)

@app.route('/weather/set/<condition>', methods=['POST'])
def set_weather(condition):
    """
    Manually set weather condition for testing.
    POST /weather/set/<condition>
    Example: POST /weather/set/Thunderstorm
    """
    try:
        weather_api.set_weather_condition(condition)
        
        # Update weather immediately if GPS is valid
        if sensor_data['system']['gps_valid']:
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
            
            # Recalculate risk
            zone = sensor_data['gps']['geo_zone']
            score, reason, level = calculate_risk_index(
                sensor_data, 
                zone, 
                weather_data
            )
            
            sensor_data['system']['risk_score'] = score
            sensor_data['system']['blocked_reason'] = reason
            sensor_data['system']['risk_level'] = level
            
            print(f"🌤️  Weather set to: {condition} | New risk: {score}%")
        
        return jsonify({
            "status": "success", 
            "condition": condition,
            "weather": sensor_data['weather'],
            "risk": sensor_data['system']['risk_score']
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@app.route('/api/config/scenarios', methods=['GET'])
def get_scenarios():
    """Get demo scenarios from config."""
    if 'demo_scenarios' in config:
        return jsonify(config['demo_scenarios'])
    return jsonify({}), 404

@app.route('/api/config/thresholds', methods=['GET'])
def get_thresholds():
    """Get risk thresholds from config."""
    if 'risk_thresholds' in config:
        return jsonify(config['risk_thresholds'])
    return jsonify({}), 404

# ============================================
# STATIC FILE SERVING
# ============================================

@app.route('/')
def index():
    """Serve main HTML page."""
    return send_from_directory(project_root, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS, images)."""
    return send_from_directory(project_root, filename)

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 AeroGuard Mission Control - Server Starting")
    print("="*70)
    print(f"📁 Project Root: {project_root}")
    print(f"📁 Backend Dir: {backend_dir}")
    print(f"📄 Config: {config_path}")
    print(f"🌐 Frontend: http://localhost:5000")
    print(f"🌐 Network: http://0.0.0.0:5000")
    print(f"📡 POST Endpoint: /data")
    print(f"📊 GET Endpoint: /api/current")
    print(f"🌤️  Weather Control: POST /weather/set/<condition>")
    print("="*70)
    print("✅ Real-time logging enabled")
    print("✅ Cache disabled for live updates")
    print("✅ CORS enabled for cross-origin requests")
    print("⚠️  Using NULL defaults - Real sensor data only")
    print("="*70 + "\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)