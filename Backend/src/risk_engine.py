import json
import os

def load_config():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(os.path.dirname(current_dir), 'config.json')
    
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print("[Risk Engine] Warning: config.json not found, using defaults")
        return None

CONFIG = load_config()

def calculate_risk_index(sensor_data, zone, weather=None):
    """
    Calculate risk index with HDOP-based GPS quality assessment.
    Returns: (score, reason, level)
    """
    score = 0
    reasons = []
    
    # Load thresholds
    if CONFIG and 'risk_thresholds' in CONFIG:
        thresholds = CONFIG['risk_thresholds']
    else:
        thresholds = {}
    
    # 1. GEOSPACE PENALTY (Hard Rule)
    if zone == "RED":
        return 100, "CRITICAL: Restricted Airspace", "ABORT"
    elif zone == "YELLOW":
        score += 30
        reasons.append("Caution: Near Airport")
    
    # 2. GPS QUALITY ASSESSMENT (HDOP-based)
    gps = sensor_data.get('gps', {})
    hdop_raw = gps.get('hdop', 9999)
    satellites = gps.get('satellites', 0)
    
    # Convert HDOP (TinyGPS++ gives value * 100)
    hdop = hdop_raw / 100.0 if hdop_raw < 9999 else 99.99
    
    # HDOP Penalties
    gps_thresholds = thresholds.get('gps', {}).get('hdop', {})
    
    if hdop > 20.0:
        score += 50
        reasons.append(f"Critical GPS Accuracy (HDOP: {hdop:.1f})")
    elif hdop > 10.0:
        score += 35
        reasons.append(f"Poor GPS Accuracy (HDOP: {hdop:.1f})")
    elif hdop > 5.0:
        score += 20
        reasons.append(f"Moderate GPS Accuracy (HDOP: {hdop:.1f})")
    elif hdop > 2.0:
        score += 10
        reasons.append(f"Fair GPS Accuracy (HDOP: {hdop:.1f})")
    
    # Satellite Count Penalties
    min_sats_config = thresholds.get('gps', {}).get('min_satellites', {})
    min_sats = min_sats_config.get('safe', 8)
    critical_sats = min_sats_config.get('critical', 4)
    
    if satellites < critical_sats:
        score += 40
        reasons.append(f"Critical Satellite Count ({satellites})")
    elif satellites < min_sats:
        sat_deficit = min_sats - satellites
        penalty = sat_deficit * min_sats_config.get('penalty_per_missing', 5)
        score += penalty
        reasons.append(f"Low Satellite Count ({satellites})")
    
    # Combined GPS Health Check
    # If both HDOP is bad AND satellite count is low → Extra penalty
    if hdop > 10.0 and satellites < 6:
        score += 15
        reasons.append("GPS System Degraded")
    
    # ============================================
    # 3. HARDWARE PENALTIES
    # ============================================
    mpu = sensor_data.get('mpu', {})
    motor = sensor_data.get('motor', {})
    
    # Vibration
    vibration = mpu.get('vibration_rms', 0)
    vib_thresholds = thresholds.get('vibration', {})
    
    if vibration > vib_thresholds.get('critical', 0.8):
        score += vib_thresholds.get('penalty_points', {}).get('critical', 40)
        reasons.append("Critical Vibration")
    elif vibration > vib_thresholds.get('warning', 0.5):
        score += vib_thresholds.get('penalty_points', {}).get('warning', 20)
        reasons.append("High Vibration")
    
    # Motor RPM
    rpm = motor.get('rpm', 0)
    min_rpm = thresholds.get('motor_rpm', {}).get('minimum_safe', 500)
    
    if rpm > 0 and rpm < min_rpm:
        score += thresholds.get('motor_rpm', {}).get('penalty_points', {}).get('low', 30)
        reasons.append("Motor Efficiency Low")
    
    # Hall sensor
    if not motor.get('hall_detected', True):
        score += 15
        reasons.append("Hall Sensor Fault")
    
    # Tilt angle
    tilt = mpu.get('tilt_angle', 0)
    if tilt > 30:
        score += 25
        reasons.append(f"Excessive Tilt ({tilt:.1f}°)")
    elif tilt > 15:
        score += 10
        reasons.append(f"High Tilt Angle ({tilt:.1f}°)")
    
    # ============================================
    # 4. WEATHER PENALTIES
    # ============================================
    if weather:
        weather_thresholds = thresholds.get('weather', {})
        
        # Wind speed
        wind_speed = weather.get('wind_speed', 0)
        wind_limits = weather_thresholds.get('wind_speed', {})
        
        if wind_speed > wind_limits.get('critical', 15.0):
            score += wind_limits.get('penalty_points', {}).get('critical', 25)
            reasons.append(f"Critical Wind ({wind_speed:.1f}m/s)")
        elif wind_speed > wind_limits.get('caution', 10.0):
            score += wind_limits.get('penalty_points', {}).get('caution', 15)
            reasons.append(f"High Wind ({wind_speed:.1f}m/s)")
        
        # Visibility
        visibility = weather.get('visibility', 10000)
        vis_limits = weather_thresholds.get('visibility', {})
        
        if visibility < vis_limits.get('critical', 1000):
            score += vis_limits.get('penalty_points', {}).get('critical', 20)
            reasons.append("Critical Visibility")
        elif visibility < vis_limits.get('caution', 5000):
            score += vis_limits.get('penalty_points', {}).get('caution', 15)
            reasons.append("Low Visibility")
        
        # Weather conditions
        weather_condition = weather.get('weather_main', 'Clear')
        dangerous_conditions = weather_thresholds.get('dangerous_conditions', {})
        
        if weather_condition in dangerous_conditions:
            penalty = dangerous_conditions[weather_condition]
            score += penalty
            reasons.append(f"{weather_condition} Detected")
        
        # Temperature
        temp = weather.get('temp')
        temp_limits = weather_thresholds.get('temperature', {})
        
        if temp is not None:
            if temp < temp_limits.get('critical_low', -20) or temp > temp_limits.get('critical_high', 45):
                score += temp_limits.get('penalty_points', 15)
                reasons.append(f"Extreme Temperature ({temp:.1f}°C)")
    
    # ============================================
    # 5. FINAL RISK CALCULATION
    # ============================================
    score = min(score, 100)
    
    # Determine level
    if CONFIG and 'alerts' in CONFIG:
        alert_levels = CONFIG['alerts']['risk_levels']
        if score <= alert_levels['safe']['max_score']:
            level = "SAFE"
        elif score <= alert_levels['caution']['max_score']:
            level = "CAUTION"
        else:
            level = "ABORT"
    else:
        if score < 40:
            level = "SAFE"
        elif score < 75:
            level = "CAUTION"
        else:
            level = "ABORT"
    
    # Format reason text
    reason_text = ', '.join(reasons) if reasons else "All Systems Normal"
    
    return score, reason_text, level