# app/services/scoring_service.py — Rule-based + simulated ML scoring pipeline
"""
Scoring Service: Evaluates transaction risk using a rule-based engine
with simulated ML scoring. In production, this would call actual LightGBM/PyTorch models.

Big-O: O(r) where r = number of rules evaluated per transaction
"""
import random
import json
from typing import Dict, List, Tuple


# Risk factor weights (simulating ML feature importance)
RISK_WEIGHTS = {
    "high_amount": 25,          # Large transaction amount
    "velocity_spike": 20,       # Multiple txns in short time
    "new_device": 15,           # First time device
    "geo_mismatch": 20,         # Country doesn't match profile
    "unusual_time": 10,         # Transaction at unusual hour
    "high_risk_merchant": 15,   # Merchant category risk
    "card_testing": 25,         # Rapid small transactions
    "ip_mismatch": 18,          # IP location mismatch
}

HIGH_RISK_COUNTRIES = {"NG", "RU", "CN", "BR", "IN", "UA", "VN", "PH"}
HIGH_RISK_CATEGORIES = {"gambling", "crypto", "electronics", "luxury", "jewelry"}


def score_transaction(
    amount: float,
    country: str,
    merchant_category: str = "",
    payment_method: str = "",
    ip_address: str = "",
    device: str = "",
) -> Tuple[float, str, List[str]]:
    """
    Score a transaction for fraud risk.
    Returns: (risk_score, risk_level, risk_factors)
    O(r) where r = number of rules
    """
    score = 0.0
    factors = []

    # Rule 1: High amount — O(1)
    if amount > 5000:
        score += RISK_WEIGHTS["high_amount"]
        factors.append("Large Amount")
    elif amount > 2000:
        score += RISK_WEIGHTS["high_amount"] * 0.5
        factors.append("Elevated Amount")

    # Rule 2: High-risk country — O(1) set lookup
    if country.upper() in HIGH_RISK_COUNTRIES:
        score += RISK_WEIGHTS["geo_mismatch"]
        factors.append("High Risk Country")

    # Rule 3: High-risk merchant category — O(1) set lookup
    if merchant_category and merchant_category.lower() in HIGH_RISK_CATEGORIES:
        score += RISK_WEIGHTS["high_risk_merchant"]
        factors.append("High Risk Merchant Category")

    # Rule 4: Simulated velocity check — O(1) (in production: Redis rolling window)
    velocity_risk = random.random()
    if velocity_risk > 0.85:
        score += RISK_WEIGHTS["velocity_spike"]
        factors.append("Velocity Spike")

    # Rule 5: Simulated new device — O(1) (in production: device fingerprint DB lookup)
    if random.random() > 0.8:
        score += RISK_WEIGHTS["new_device"]
        factors.append("New Device")

    # Rule 6: Simulated unusual time — O(1)
    if random.random() > 0.9:
        score += RISK_WEIGHTS["unusual_time"]
        factors.append("Unusual Time")

    # Add some ML noise to simulate ensemble model
    ml_adjustment = random.gauss(0, 5)
    score = max(0, min(100, score + ml_adjustment))

    # Determine risk level
    if score >= 75:
        risk_level = "high"
    elif score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    return round(score, 1), risk_level, factors


def get_risk_explanation(risk_factors: List[str], risk_score: float) -> Dict:
    """
    Generate SHAP-like explainability for risk score.
    O(m) where m = number of risk factors
    """
    explanations = {
        "Large Amount": "Transaction amount significantly exceeds user's average spending pattern",
        "Elevated Amount": "Transaction amount is above typical range for this merchant category",
        "High Risk Country": "Transaction originates from a country with elevated fraud rates",
        "High Risk Merchant Category": "Merchant category has historically higher fraud incidence",
        "Velocity Spike": "Multiple transactions detected in rapid succession",
        "New Device": "Transaction from a device not previously associated with this account",
        "Unusual Time": "Transaction occurred outside the user's normal activity window",
        "IP Mismatch": "IP address location doesn't match the user's known locations",
    }

    factor_contributions = {}
    remaining = risk_score
    for i, factor in enumerate(risk_factors):
        if i == len(risk_factors) - 1:
            contribution = remaining
        else:
            contribution = round(risk_score / len(risk_factors) + random.uniform(-3, 3), 1)
            remaining -= contribution
        factor_contributions[factor] = {
            "contribution": max(0, contribution),
            "explanation": explanations.get(factor, "Factor identified by ML model"),
        }

    return {
        "risk_score": risk_score,
        "factors": factor_contributions,
        "model_version": "v2.4.1",
        "confidence": round(0.7 + random.random() * 0.25, 2),
    }
