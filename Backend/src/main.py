import serial
import json
import os
import sys
from mappls_client import MapplsGeospace
from risk_engine import calculate_risk_index
from weather_client import OpenWeatherClient

# Auto-detect config.json location
current_dir = os.path.dirname(os.path.abspath(__file__))
possible_configs = [
    os.path.join(current_dir, 'config.json'),
    os.path.join(current_dir, '..', 'config.json'),
    os.path.join(current_dir, '..', '..', 'config.json'),
    os.path.join(current_dir, 'Backend', 'config.json'),
]

config_path = None
for path in possible_configs:
    if os.path.exists(path):
        config_path = path
        print(f"✅ Found config at: {os.path.abspath(path)}")
        break

if config_path is None:
    print("❌ config.json not found! Searched:")
    for path in possible_configs:
        print(f"  - {os.path.abspath(path)}")
    sys.exit(1)

# Load config
with open(config_path) as f:
    config = json.load(f)

# Setup
mappls = MapplsGeospace()
weather_client = OpenWeatherClient(config['OPENWEATHER_API_KEY'])

# Try to open serial port
try:
    ser = serial.Serial('COM3', 115200, timeout=1)
    print("✅ Serial port COM3 opened successfully")
except serial.SerialException as e:
    print(f"❌ Could not open COM3: {e}")
    print("Make sure:")
    print("  1. ESP32 is connected via USB")
    print("  2. Correct COM port (check Device Manager)")
    print("  3. No other program is using the port")
    sys.exit(1)

print("\n" + "=" * 50)
print("--- UAV Pre-Flight Safety System Active ---")
print("=" * 50)

while True:
    if ser.in_waiting > 0:
        try:
            raw_data = ser.readline().decode('utf-8').strip()
            data = json.loads(raw_data)
            
            # Get GPS coordinates (handle different data structures)
            lat = data.get('gps', {}).get('latitude') or data.get('lat', 0)
            lng = data.get('gps', {}).get('longitude') or data.get('lng', 0)
            
            # Get weather at drone's location
            weather = weather_client.get_weather(lat, lng)
            
            # Geofence Check
            zone = mappls.check_airspace(lat, lng)
            
            # Risk Fusion (returns 3 values now)
            risk_val, msg, level = calculate_risk_index(data, zone, weather)
            
            # Feedback to ESP32
            if risk_val >= 80:
                ser.write(b"ALERT_RED\n")
            elif risk_val >= 40:
                ser.write(b"ALERT_YELLOW\n")
            else:
                ser.write(b"SAFE\n")

            print(f"[GPS: {lat:.5f}, {lng:.5f}] Zone: {zone} | Risk: {risk_val}% | {level}: {msg}")

        except json.JSONDecodeError as e:
            print(f"JSON Error: {e} | Raw: {raw_data[:50]}")
        except KeyError as e:
            print(f"Missing data key: {e}")
        except Exception as e:
            print(f"Sync Error: {e}")