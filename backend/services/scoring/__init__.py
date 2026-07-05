def calculate_criticality_score(heart_rate: int, resp_rate: int, spo2: int) -> float:
    """
    Rule-based deterministic clinical Early Warning Score (EWS) calculator.
    Returns a priority score between 0.0 (stable) and 10.0 (critical distress).
    """
    points = 0
    
    # 1. Oxygen Saturation (SpO2) Points (Max 4)
    if spo2 >= 95:
        points += 0
    elif 92 <= spo2 < 95:
        points += 1
    elif 88 <= spo2 < 92:
        points += 3
    else:  # spo2 < 88%
        points += 4
        
    # 2. Respiratory Rate (RR) Points (Max 3)
    if 12 <= resp_rate <= 20:
        points += 0
    elif 9 <= resp_rate <= 11 or 21 <= resp_rate <= 24:
        points += 1
    elif resp_rate <= 8 or 25 <= resp_rate <= 30:
        points += 2
    else:  # resp_rate > 30
        points += 3
        
    # 3. Heart Rate (HR) Points (Max 3)
    if 51 <= heart_rate <= 90:
        points += 0
    elif 41 <= heart_rate <= 50 or 91 <= heart_rate <= 110:
        points += 1
    elif heart_rate <= 40 or 111 <= heart_rate <= 130:
        points += 2
    else:  # heart_rate > 130
        points += 3
        
    # Standardize result as a float (0.0 to 10.0)
    score = float(points)
    return min(10.0, max(0.0, score))
