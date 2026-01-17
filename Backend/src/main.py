# main.py (updated)
import serial
import json
from mappls_client import MapplsGeospace
from risk_engine import calculate_risk_index
from weather_client import OpenWeatherClient

# Load config
with open('config.json') as f:
    config = json.load(f)

# Setup
mappls = MapplsGeospace()
weather_client = OpenWeatherClient(config['OPENWEATHER_API_KEY'])
ser = serial.Serial('COM10', 115200, timeout=1)

print("--- UAV Pre-Flight Safety System Active ---")

while True:
    if ser.in_waiting > 0:
        try:
            raw_data = ser.readline().decode('utf-8').strip()
            data = json.loads(raw_data)
            
            # Get weather at drone's location
            weather = weather_client.get_weather(data['lat'], data['lng'])
            
            # Simulated Geofence Check
            zone = mappls.check_airspace(data['lat'], data['lng'])
            
            # Risk Fusion (now includes weather!)
            risk_val, msg = calculate_risk_index(data, zone, weather)
            
            # Feedback to ESP8266
            if risk_val >= 80:
                ser.write(b"ALERT_RED\n")
            elif risk_val >= 40:
                ser.write(b"ALERT_YELLOW\n")
            else:
                ser.write(b"SAFE\n")

            print(f"[GPS: {data['lat']}, {data['lng']}] Zone: {zone} | Risk: {risk_val}% | Status: {msg}")

        except Exception as e:
            print(f"Sync Error: {e}")