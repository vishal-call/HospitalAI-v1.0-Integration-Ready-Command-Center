def calculate_operational_priority(clinical_score: int) -> float:
    """
    Calculates the 0.0 to 10.0 operational priority float.
    Logic: min(news2_total / 10, 1.0) * 10.0
    """
    return min(clinical_score / 10.0, 1.0) * 10.0
