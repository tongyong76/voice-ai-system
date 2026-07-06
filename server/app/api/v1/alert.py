from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from ...core.database import get_db
from ...core.security import get_current_user
from ...models.result import AlertRule, AlertLog

router = APIRouter()


class AlertRuleCreate(BaseModel):
    name: str
    condition_type: str  # keyword/speaker/emotion/custom
    condition_expr: dict
    action_type: str  # websocket/sms/email/webhook
    action_target: str
    enabled: bool = True


class AlertRuleResponse(BaseModel):
    id: int
    name: str
    condition_type: str
    condition_expr: dict
    action_type: str
    action_target: str
    enabled: bool

    class Config:
        from_attributes = True


@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    rule: AlertRuleCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    db_rule = AlertRule(**rule.model_dump())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.get("/rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(AlertRule)
    if enabled is not None:
        query = query.filter(AlertRule.enabled == enabled)
    return query.all()


@router.put("/rules/{rule_id}")
async def update_alert_rule(
    rule_id: int,
    rule: AlertRuleCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    db_rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for key, value in rule.model_dump().items():
        setattr(db_rule, key, value)
    db.commit()
    return {"status": "updated"}


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    db_rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(db_rule)
    db.commit()
    return {"status": "deleted"}


@router.get("/logs")
async def list_alert_logs(
    acknowledged: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = db.query(AlertLog)
    if acknowledged is not None:
        query = query.filter(AlertLog.acknowledged == acknowledged)
    return query.order_by(AlertLog.triggered_at.desc()).offset(skip).limit(limit).all()


@router.put("/logs/{log_id}/acknowledge")
async def acknowledge_alert(
    log_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    log = db.query(AlertLog).filter(AlertLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Alert log not found")
    log.acknowledged = True
    log.acknowledged_by = user.get("sub")
    db.commit()
    return {"status": "acknowledged"}
