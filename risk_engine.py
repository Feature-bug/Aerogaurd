
def calculate_risk_index(sensor_data, zone, weather=None):
    """
    Inputs:
    sensor_data: Dict with 'mpu', 'motor', and 'gps' structures
    zone: "RED", "YELLOW", or "GREEN"
    weather: Dict from weather_client
    """
    score = 0
    reasons = []

    # 1. Geospace Penalty (Critical)
    if zone == "RED":
        return 100, "ABORT: No-Fly Zone (Restricted Airspace)", "DANGER"
    elif zone == "YELLOW":
        score += 35
        reasons.append("Near Airport")

    # 2. Hardware Penalty
    vib = sensor_data.get('mpu', {}).get('vibration_rms', 0)
    if vib > 0.4: 
        score += 45
        reasons.append("High Vibration")
    
    rpm = sensor_data.get('motor', {}).get('rpm', 1000)
    if rpm < 400 and rpm > 0:
        score += 30
        reasons.append("Low Motor RPM")

    # 3. GNSS Quality
    raw_hdop = sensor_data.get('gps', {}).get('hdop', 1.0)
    hdop = raw_hdop / 100.0 if raw_hdop > 50 else raw_hdop
    if hdop > 3.0:
        score += 25
        reasons.append("Poor GPS Precision")
    
    if sensor_data.get('gps', {}).get('satellites', 0) < 6:
        score += 30
        reasons.append("Low Sat Count")

    # 4. Weather Penalty (Advanced Fusion)
    if weather:
        # High Wind (> 8 m/s is typically risky for small UAVs)
        wind = weather.get('wind_speed', 0)
        if wind > 12:
            score += 60
            reasons.append(f"Gale Force Wind ({wind}m/s)")
        elif wind > 7:
            score += 25
            reasons.append("Moderate Wind")

        # Visibility (< 2000m is dangerous for VLOS)
        vis = weather.get('visibility', 10000)
        if vis < 1500:
            score += 40
            reasons.append("Low Visibility")

        # Bad Weather Conditions
        precip_conditions = ['Rain', 'Thunderstorm', 'Snow', 'Squall']
        if weather.get('weather_main') in precip_conditions:
            score += 50
            reasons.append(f"{weather['weather_main']} Detected")
            
        # Extreme Temp
        temp = weather.get('temp')
        if temp is not None and (temp < 0 or temp > 45):
            score += 20
            reasons.append("Extreme Temp")
    else:
        score += 10
        reasons.append("Weather Check Failed")

    # Final logic
    score = min(score, 100)
    recommendation = "SAFE" if score < 30 else "CAUTION" if score < 70 else "ABORT"
    
    reason_str = ", ".join(reasons) if reasons else "Systems Nominal"
    return score, f"{recommendation}: {reason_str}", recommendation
