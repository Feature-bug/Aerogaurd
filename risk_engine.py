def calculate_risk_index(sensor_data, zone):
    # Base weights
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

    # Final logic
    score = min(score, 100) # Cap at 100
    recommendation = "SAFE" if score < 40 else "CAUTION" if score < 75 else "ABORT"
    
    return score, f"{recommendation}: {', '.join(reasons)}"