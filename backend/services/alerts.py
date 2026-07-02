from typing import List, Optional
import models

def evaluate_vitals_for_alerts(
    patient_id: int,
    patient_name: str,
    old_score: float,
    new_score: float,
    spo2: int
) -> List[models.Alert]:
    """
    Evaluates patient vitals and score differentials to determine if clinical deterioration
    alerts should be generated. Returns a list of unsaved Alert models.
    """
    alerts = []
    
    # 1. Hypoxia Check
    if spo2 < 92:
        severity = models.AlertSeverity.CRITICAL
        message = f"Patient {patient_name} displays severe hypoxaemia (SpO2: {spo2}%). Immediate clinical assessment required."
        alerts.append(
            models.Alert(
                patient_id=patient_id,
                alert_type=models.AlertType.LOW_OXYGEN,
                severity=severity,
                message=message,
                is_acknowledged=False
            )
        )
        
    # 2. Criticality Score Spike Check (Deterioration of 2.0 or more)
    score_diff = new_score - old_score
    if score_diff >= 2.0:
        severity = models.AlertSeverity.HIGH
        message = f"Patient {patient_name} EWS score spiked by {score_diff:.1f} points (previous: {old_score:.1f} -> current: {new_score:.1f}). Monitor closely."
        alerts.append(
            models.Alert(
                patient_id=patient_id,
                alert_type=models.AlertType.SCORE_SPIKE,
                severity=severity,
                message=message,
                is_acknowledged=False
            )
        )
        
    return alerts
