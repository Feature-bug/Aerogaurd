# risk_engine.py (updated)
def calculate_risk_index(sensor_data, zone, weather=None):
    score = 0
    reasons = []

    # 1. Geospace Penalty (Hard Rule)
    if zone == "RED":
        return 100, "CRITICAL: Restricted Airspace"
    elif zone == "YELLOW":
        score += 30
        reasons.append("Caution: Near Airport")

    # 2. Hardware Penalty
    if sensor_data.get('vib', 0) > 3.0:
        score += 40
        reasons.append("High Vibration")
    if sensor_data.get('hall', 1000) < 400:
        score += 30
        reasons.append("Motor Efficiency Low")

    # 3. WEATHER PENALTIES (NEW!)
    if weather:
        # High wind (>10 m/s ≈ 36 km/h)
        if weather.get('wind_speed', 0) > 10:
            score += 25
            reasons.append("High Wind")
        
        # Low visibility (<5000m = poor conditions)
        if weather.get('visibility', 10000) < 5000:
            score += 20
            reasons.append("Low Visibility")
        
        # Bad weather conditions
        bad_weather = ['Rain', 'Thunderstorm', 'Snow', 'Fog', 'Mist']
        if weather.get('weather_main') in bad_weather:
            score += 30
            reasons.append(f"{weather['weather_main']} Detected")
        
        # Extreme temperature (<0°C or >45°C)
        temp = weather.get('temp')
        if temp is not None and (temp < -20 or temp > 45):
            score += 15
            reasons.append("Extreme Temperature")
    else:
        reasons.append("Weather Data Unavailable")


    score = min(score, 100)
    if score < 40:
        level = "SAFE"
    elif score < 75:
        level = "CAUTION"
    else:
        level = "ABORT"

    reasons_str = ", ".join(reasons) if reasons else "All systems nominal"
    message = f"{level}: {reasons_str}"
    
    return score, level, message