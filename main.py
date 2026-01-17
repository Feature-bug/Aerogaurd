import serial
import json
from mappls_client import MapplsGeospace
from risk_engine import calculate_risk_index

# Setup
mappls = MapplsGeospace()
#ser = serial.Serial('COM3', 115200, timeout=1) # Ensure COM port matches

print("--- UAV Pre-Flight Safety System Active ---")

while True:
    if ser.in_waiting > 0:
        try:
            raw_data = ser.readline().decode('utf-8').strip()
            data = json.loads(raw_data)
            
            # Simulated Geofence Check
            zone = mappls.check_airspace(data['lat'], data['lng'])
            
            # Risk Fusion
            risk_val, msg = calculate_risk_index(data, zone)
            
            # Feedback to ESP8266
            if risk_val >= 80:
                ser.write(b"ALERT_RED\n") # Trigger Solid Buzzer
            elif risk_val >= 40:
                ser.write(b"ALERT_YELLOW\n") # Trigger Beeping
            else:
                ser.write(b"SAFE\n")

            print(f"[GPS: {data['lat']}, {data['lng']}] Zone: {zone} | Risk: {risk_val}% | Status: {msg}")

        except Exception as e:
            print(f"Sync Error: {e}")