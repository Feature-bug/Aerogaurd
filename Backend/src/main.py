import serial
import json
import os
import sys
from mappls_client import MapplsGeospace
from risk_engine import calculate_risk_index
from weather_client import OpenWeatherClient
import requests


# Load config
config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
try:
    with open(config_path) as f:
        config = json.load(f)
    print(f"✅ Config loaded from: {config_path}")
except FileNotFoundError:
    print("❌ config.json not found")
    sys.exit(1)

# Initialize clients
mappls = MapplsGeospace(config_path)
weather_client = OpenWeatherClient(config.get('OPENWEATHER_API_KEY', ''))

# Try to connect to ESP32
serial_config = config.get('hardware_config', {}).get('serial', {})
port = serial_config.get('port', 'COM10')
baudrate = serial_config.get('baudrate', 115200)

try:
    ser = serial.Serial(port, baudrate, timeout=1)
    print(f"✅ Connected to ESP32 on {port}")
except serial.SerialException as e:
    print(f"❌ Could not open {port}: {e}")
    print("\nTroubleshooting:")
    print("  1. Check ESP32 is connected via USB")
    print("  2. Verify COM port in Device Manager (Windows)")
    print("  3. Close Arduino Serial Monitor if open")
    print("  4. Try alternative ports:", serial_config.get('alternative_ports', []))
    sys.exit(1)

print("\n" + "=" * 60)
print("🚁 AeroGuard - Real-Time ESP32 Data Stream Active")
print("=" * 60)
print("Waiting for GPS fix... (This may take 30-60 seconds outdoors)\n")

gps_fix_obtained = False

while True:
    if ser.in_waiting > 0:
        try:
            raw_line = ser.readline().decode('utf-8').strip()
            
            # Skip debug messages
            if not raw_line.startswith('{'):
                print(f"[ESP32] {raw_line}")
                continue
            
            # Parse JSON data
            data = json.loads(raw_line)
            
            # Extract GPS coordinates
            lat = data.get('gps', {}).get('latitude', 0)
            lng = data.get('gps', {}).get('longitude', 0)
            sats = data.get('gps', {}).get('satellites', 0)
            
            # Check for valid GPS fix
            if lat != 0 and lng != 0 and not gps_fix_obtained:
                print(f"\n🛰️  GPS FIX ACQUIRED! Position: {lat:.6f}, {lng:.6f}")
                print(f"📡 Satellites: {sats}\n")
                gps_fix_obtained = True
            
            # Get weather data
            weather = weather_client.get_weather(lat, lng)
            
            # Check airspace zone
            zone = mappls.check_airspace(lat, lng)
            data['gps']['geo_zone'] = zone
            
            # Calculate risk
            risk_score, reason, level = calculate_risk_index(data, zone, weather)

            # After calculating risk, send to web server
            try:
                response = requests.post('http://localhost:5000/data', json=data, timeout=1)
            except:
                pass  # Web server offline, continue with serial
            
            # Send feedback to ESP32
            if risk_score >= 75:
                ser.write(b"ABORT\n")
                status_led = "🔴"
            elif risk_score >= 40:
                ser.write(b"CAUTION\n")
                status_led = "🟡"
            else:
                ser.write(b"SAFE\n")
                status_led = "🟢"

            while True:
                if ser.in_waiting > 0:
                    try:
                        raw_line = ser.readline().decode('utf-8').strip()
                        
                        if not raw_line.startswith('{'):
                            print(f"[ESP32] {raw_line}")
                            continue
                        
                        data = json.loads(raw_line)
                        
                        # Get weather and calculate risk
                        lat = data.get('gps', {}).get('latitude', 0)
                        lng = data.get('gps', {}).get('longitude', 0)
                        sats = data.get('gps', {}).get('satellites', 0)
                        
                        weather = weather_client.get_weather(lat, lng)
                        zone = mappls.check_airspace(lat, lng)
                        data['gps']['geo_zone'] = zone
                        
                        risk_score, reason, level = calculate_risk_index(data, zone, weather)
                        
                        # Add system data
                        if 'system' not in data:
                            data['system'] = {}
                        
                        data['system']['risk_score'] = risk_score
                        data['system']['blocked_reason'] = reason
                        data['system']['risk_level'] = level
                        data['system']['source'] = 'ESP32'
                        
                        # ✅ SEND TO WEB SERVER
                        try:
                            response = requests.post('http://localhost:5000/data', json=data,timeout=1)
                            if response.ok:
                                print(f"✅ Data sent to web server")
                        except:
                            print("⚠️  Web server offline")
                        
                        # Send feedback to ESP32
                        if risk_score >= 75:
                            ser.write(b"ABORT\n")
                        elif risk_score >= 40:
                            ser.write(b"CAUTION\n")
                        else:
                            ser.write(b"SAFE\n")
                        
                        print(f"🟢 GPS:[{lat:.5f}, {lng:.5f}] Zone:{zone} | Risk:{risk_score}%")
                        
                    except Exception as e:
                        print(f"⚠️  Error: {e}")
            
            # Display telemetry
            print(f"{status_led} GPS:[{lat:.5f}, {lng:.5f}] Zone:{zone} | "
                  f"Sats:{sats} | Risk:{risk_score}% ({level}) | {reason}")
            
            # Also send to web server (if running)
            # This would POST to your Flask server's /data endpoint
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON Error: {e}")
            print(f"   Raw data: {raw_line[:100]}")
        except Exception as e:
            print(f"⚠️  Error: {e}")