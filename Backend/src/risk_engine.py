def calculate_risk_index(sensor_data, zone, weather=None):
    """
    Calculate risk index based on sensor data, geofence zone, and weather.
    Returns: (score, reason, level)
    """
    score = 0
    reasons = []

    # 1. Geospace Penalty (Hard Rule)
    if zone == "RED":
        return 100, "CRITICAL: Restricted Airspace", "ABORT"
    elif zone == "YELLOW":
        score += 30
        reasons.append("Caution: Near Airport")

    # 2. Hardware Penalties (use correct data structure)
    mpu = sensor_data.get('mpu', {})
    motor = sensor_data.get('motor', {})
    
    # High vibration (threshold: 0.5 G)
    vibration = mpu.get('vibration_rms', 0)
    if vibration > 0.5:
        score += 40
        reasons.append("High Vibration")
    
    # Low RPM (motor problem - threshold: 500 RPM)
    rpm = motor.get('rpm', 0)
    if rpm > 0 and rpm < 500:
        score += 30
        reasons.append("Motor Efficiency Low")

    # 3. WEATHER PENALTIES
    if weather:
        # High wind (>10 m/s ≈ 36 km/h)
        wind_speed = weather.get('wind_speed', 0)
        if wind_speed > 10:
            score += 25
            reasons.append("High Wind")
        
        # Low visibility (<5000m = poor conditions)
        visibility = weather.get('visibility', 10000)
        if visibility < 5000:
            score += 20
            reasons.append("Low Visibility")
        
        # Bad weather conditions
        bad_weather = ['Rain', 'Thunderstorm', 'Snow', 'Fog', 'Mist']
        weather_condition = weather.get('weather_main', 'Clear')
        if weather_condition in bad_weather:
            score += 30
            reasons.append(f"{weather_condition} Detected")
        
        # Extreme temperature (<-20°C or >45°C)
        temp = weather.get('temp')
        if temp is not None and (temp < -20 or temp > 45):
            score += 15
            reasons.append("Extreme Temperature")
    else:
        reasons.append("Weather Data Unavailable")

    # Cap at 100
    score = min(score, 100)
    
    # Determine level
    if score < 40:
        level = "SAFE"
    elif score < 75:
        level = "CAUTION"
    else:
        level = "ABORT"
    
    # Format reason text
    reason_text = ', '.join(reasons) if reasons else "Systems Nominal"
    
    return score, reason_text, level