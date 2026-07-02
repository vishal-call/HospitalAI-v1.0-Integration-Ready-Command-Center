from typing import Dict, Any, Tuple, List, Optional
from models import PatientVitals, ScoringPolicy, RiskBand, ConsciousnessLevel, PatientBaseline

def calculate_news2(vitals: PatientVitals, policy: ScoringPolicy, baseline: Optional[PatientBaseline] = None) -> Tuple[int, RiskBand, Dict[str, Any], List[str]]:
    """
    Calculates the NEWS2 score based on the provided vitals and policy.
    Returns: (total_score, risk_band, parameter_breakdown, red_flags)
    """
    breakdown = {}
    red_flags = []
    
    # 1. Respiration Rate
    rr = vitals.resp_rate
    if rr <= 8 or rr >= 25:
        breakdown["resp_rate"] = 3
    elif 9 <= rr <= 11:
        breakdown["resp_rate"] = 1
    elif 12 <= rr <= 20:
        breakdown["resp_rate"] = 0
    elif 21 <= rr <= 24:
        breakdown["resp_rate"] = 2
        
    # 2. SpO2 (using Scale 1 for normal, Scale 2 for hypercapnic)
    spo2 = vitals.spo2
    use_scale_2 = vitals.spo2_scale == 2
    
    if baseline:
        notes = baseline.notes or ""
        if (baseline.baseline_spo2 is not None and baseline.baseline_spo2 <= 92) or "COPD" in notes or "Hypercapnic" in notes:
            use_scale_2 = True
            breakdown["baseline_applied"] = True

    if not use_scale_2:
        if spo2 <= 91:
            breakdown["spo2"] = 3
        elif 92 <= spo2 <= 93:
            breakdown["spo2"] = 2
        elif 94 <= spo2 <= 95:
            breakdown["spo2"] = 1
        elif spo2 >= 96:
            breakdown["spo2"] = 0
    else:
        # Scale 2 logic (example based on NEWS2)
        if spo2 <= 83 or (spo2 >= 97 and vitals.oxygen_supplement):
            breakdown["spo2"] = 3
        elif 84 <= spo2 <= 85 or (95 <= spo2 <= 96 and vitals.oxygen_supplement):
            breakdown["spo2"] = 2
        elif 86 <= spo2 <= 87 or (93 <= spo2 <= 94 and vitals.oxygen_supplement):
            breakdown["spo2"] = 1
        else:
            breakdown["spo2"] = 0
            
    # 3. Air or Oxygen?
    if vitals.oxygen_supplement:
        breakdown["oxygen_supplement"] = 2
    else:
        breakdown["oxygen_supplement"] = 0
        
    # 4. Systolic BP
    sbp = vitals.systolic_bp
    if sbp is not None:
        if sbp <= 90 or sbp >= 220:
            breakdown["systolic_bp"] = 3
        elif 91 <= sbp <= 100:
            breakdown["systolic_bp"] = 2
        elif 101 <= sbp <= 110:
            breakdown["systolic_bp"] = 1
        elif 111 <= sbp <= 219:
            breakdown["systolic_bp"] = 0
    else:
        breakdown["systolic_bp"] = 0 # Assume 0 if not provided for safety in transition, ideally should be mandatory
        
    # 5. Heart Rate
    hr = vitals.heart_rate
    if hr <= 40 or hr >= 131:
        breakdown["heart_rate"] = 3
    elif 41 <= hr <= 50 or 111 <= hr <= 130:
        breakdown["heart_rate"] = 2
    elif 51 <= hr <= 90:
        breakdown["heart_rate"] = 0
    elif 91 <= hr <= 110:
        breakdown["heart_rate"] = 1
        
    # 6. Level of Consciousness
    loc = vitals.consciousness_level
    if loc == ConsciousnessLevel.ALERT:
        breakdown["consciousness_level"] = 0
    else:
        breakdown["consciousness_level"] = 3
        
    # 7. Temperature
    temp = vitals.temperature
    if temp is not None:
        if temp <= 35.0:
            breakdown["temperature"] = 3
        elif 35.1 <= temp <= 36.0 or 38.1 <= temp <= 39.0:
            breakdown["temperature"] = 1
        elif 36.1 <= temp <= 38.0:
            breakdown["temperature"] = 0
        elif temp >= 39.1:
            breakdown["temperature"] = 2
    else:
        breakdown["temperature"] = 0

    # Calculate Totals and Red Flags
    total_score = 0
    for param, score in breakdown.items():
        if param == "baseline_applied":
            continue
        total_score += score
        if score == 3:
            red_flags.append(param)
            
    # Determine Risk Band
    if len(red_flags) > 0:
        if total_score >= 7:
            risk_band = RiskBand.HIGH
        else:
            risk_band = RiskBand.MEDIUM
    else:
        if total_score <= 4:
            risk_band = RiskBand.LOW
        elif 5 <= total_score <= 6:
            risk_band = RiskBand.MEDIUM
        else:
            risk_band = RiskBand.HIGH

    return total_score, risk_band, breakdown, red_flags
