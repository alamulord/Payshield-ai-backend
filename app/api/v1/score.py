# app/api/v1/score.py — Synchronous risk scoring endpoint
"""
Score Router: Synchronous risk scoring for individual transactions.
O(r) where r = number of rules in the scoring pipeline
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from app.services.scoring_service import score_transaction, get_risk_explanation

router = APIRouter(prefix="/score", tags=["Scoring"])


class ScoreRequest(BaseModel):
    amount: float = Field(..., gt=0)
    country: str = Field(..., max_length=5)
    merchant_category: Optional[str] = None
    payment_method: Optional[str] = None
    ip_address: Optional[str] = None
    device: Optional[str] = None


class ScoreResponse(BaseModel):
    risk_score: float
    risk_level: str
    risk_factors: List[str]
    explanation: dict
    recommendation: str


@router.post("", response_model=ScoreResponse)
async def score(request: ScoreRequest):
    """
    Synchronous risk scoring.
    O(r) where r = number of rules evaluated
    """
    risk_score, risk_level, risk_factors = score_transaction(
        amount=request.amount,
        country=request.country,
        merchant_category=request.merchant_category or "",
        payment_method=request.payment_method or "",
        ip_address=request.ip_address or "",
        device=request.device or "",
    )

    explanation = get_risk_explanation(risk_factors, risk_score)

    # Generate recommendation
    if risk_level == "high":
        recommendation = "BLOCK: Transaction exhibits multiple high-risk indicators. Recommend blocking and creating an investigation."
    elif risk_level == "medium":
        recommendation = "REVIEW: Transaction has moderate risk indicators. Recommend manual review before approval."
    else:
        recommendation = "APPROVE: Transaction within normal parameters. Low risk profile."

    return ScoreResponse(
        risk_score=risk_score,
        risk_level=risk_level,
        risk_factors=risk_factors,
        explanation=explanation,
        recommendation=recommendation,
    )
