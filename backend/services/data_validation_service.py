from typing import Dict, Any, List, Tuple

def _safe_float(val: Any) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def _safe_int(val: Any) -> int | None:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None

def validate_patient_row(row: dict) -> dict:
    errors = []
    normalized_data = {}

    # Required fields
    patient_code = row.get("patient_code", "").strip()
    name = row.get("name", "").strip()
    ward_code = row.get("ward_code", "").strip()

    if not patient_code:
        errors.append("Missing required field: 'patient_code'")
    else:
        normalized_data["patient_code"] = patient_code

    if not name:
        errors.append("Missing required field: 'name'")
    else:
        normalized_data["name"] = name

    if not ward_code:
        errors.append("Missing required field: 'ward_code'")
    else:
        normalized_data["ward_code"] = ward_code

    # Age validation (0-120)
    age_str = row.get("age")
    if age_str is not None and str(age_str).strip() != "":
        age = _safe_int(age_str)
        if age is None:
            errors.append(f"Invalid age format: '{age_str}'")
        elif not (0 <= age <= 120):
            errors.append(f"Age out of bounds (0-120): {age}")
        else:
            normalized_data["age"] = age
    else:
        normalized_data["age"] = None # Optional or default handling later

    # Other optional fields
    normalized_data["gender"] = str(row.get("gender", "")).strip()
    normalized_data["admission_reason"] = str(row.get("admission_reason", "")).strip()

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "normalized_data": normalized_data
    }


def validate_vitals_row(row: dict) -> dict:
    errors = []
    normalized_data = {}

    # Required fields
    patient_code = row.get("patient_code", "").strip()
    if not patient_code:
        errors.append("Missing required field: 'patient_code'")
    else:
        normalized_data["patient_code"] = patient_code

    # Vitals validation
    # spo2 (0-100)
    spo2_str = row.get("spo2")
    if spo2_str is not None and str(spo2_str).strip() != "":
        spo2 = _safe_float(spo2_str)
        if spo2 is None:
            errors.append(f"Invalid spo2 format: '{spo2_str}'")
        elif not (0 <= spo2 <= 100):
            errors.append(f"spo2 out of bounds (0-100): {spo2}")
        else:
            normalized_data["spo2"] = spo2
    else:
        errors.append("Missing required field: 'spo2'")

    # heart_rate (20-250)
    hr_str = row.get("heart_rate")
    if hr_str is not None and str(hr_str).strip() != "":
        hr = _safe_float(hr_str)
        if hr is None:
            errors.append(f"Invalid heart_rate format: '{hr_str}'")
        elif not (20 <= hr <= 250):
            errors.append(f"heart_rate out of bounds (20-250): {hr}")
        else:
            normalized_data["heart_rate"] = hr
    else:
        errors.append("Missing required field: 'heart_rate'")

    # respiratory_rate (5-80)
    rr_str = row.get("respiratory_rate")
    if rr_str is not None and str(rr_str).strip() != "":
        rr = _safe_float(rr_str)
        if rr is None:
            errors.append(f"Invalid respiratory_rate format: '{rr_str}'")
        elif not (5 <= rr <= 80):
            errors.append(f"respiratory_rate out of bounds (5-80): {rr}")
        else:
            normalized_data["respiratory_rate"] = rr
    else:
        errors.append("Missing required field: 'respiratory_rate'")
        
    # temperature (optional, let's say 30-45 C just to be safe if provided)
    temp_str = row.get("temperature")
    if temp_str is not None and str(temp_str).strip() != "":
        temp = _safe_float(temp_str)
        if temp is None:
            errors.append(f"Invalid temperature format: '{temp_str}'")
        elif not (30 <= temp <= 45):
            errors.append(f"temperature out of bounds (30-45 C): {temp}")
        else:
            normalized_data["temperature"] = temp
            
    # consciousness_level (optional, default to ALERT)
    cl_str = row.get("consciousness_level", "ALERT").strip().upper()
    if cl_str not in ["ALERT", "CVPU"]:
        errors.append(f"Invalid consciousness_level: '{cl_str}'. Must be ALERT or CVPU.")
    else:
        normalized_data["consciousness_level"] = cl_str

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "normalized_data": normalized_data
    }
