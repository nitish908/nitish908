from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_owner
from app.core.audit import record_audit
from app.core.csrf import verify_csrf
from app.core.db import get_db
from app.models.scoring import ScoreEvidence, ScoringRule
from app.models.user import User
from app.services.scoring_engine import seed_default_scoring_rules

router = APIRouter(prefix="/api/scoring", tags=["scoring"], dependencies=[Depends(verify_csrf)])


class ScoringRuleOut(BaseModel):
    id: UUID
    key: str
    label: str
    description: str
    max_points: int
    is_enabled: bool
    hot_threshold: int
    warm_threshold: int

    model_config = {"from_attributes": True}


class ScoringRuleUpdate(BaseModel):
    max_points: int | None = None
    is_enabled: bool | None = None
    hot_threshold: int | None = None
    warm_threshold: int | None = None


@router.get("/rules", response_model=list[ScoringRuleOut])
def list_rules(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rules = list(db.scalars(select(ScoringRule)))
    if not rules:
        seed_default_scoring_rules(db)
        db.commit()
        rules = list(db.scalars(select(ScoringRule)))
    return rules


@router.patch("/rules/{rule_id}", response_model=ScoringRuleOut)
def update_rule(rule_id: UUID, payload: ScoringRuleUpdate, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    rule = db.get(ScoringRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Scoring rule not found")
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(rule, field, value)
    record_audit(db, actor_id=user.id, action="scoring_rule_updated", object_type="scoring_rule", object_id=str(rule.id), detail=str(data))
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/leads/{lead_id}/evidence")
def get_lead_evidence(lead_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    evidence = db.scalars(select(ScoreEvidence).where(ScoreEvidence.lead_id == lead_id)).all()
    return [
        {
            "rule_key": e.rule_key, "points_awarded": e.points_awarded, "max_points": e.max_points,
            "explanation": e.explanation, "source_url": e.source_url,
        }
        for e in evidence
    ]
