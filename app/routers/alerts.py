from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Alert
from app.schemas import AlertResponse, AlertCreate
from app.services import generate_alerts

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)
    if type:
        query = query.filter(Alert.type == type)
    return query.order_by(Alert.id.desc()).all()

@router.post("", response_model=AlertResponse)
def create_alert(payload: AlertCreate, db: Session = Depends(get_db)):
    alert = Alert(**payload.model_dump())
    alert.created_at = datetime.utcnow()
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert

def _resolve_alert_obj(alert_id: int, db: Session):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "resolved"
    db.commit()
    db.refresh(alert)
    return alert

@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def post_resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """POST /api/alerts/{id}/resolve: marks alert as resolved."""
    return _resolve_alert_obj(alert_id, db)

@router.put("/{alert_id}/resolve", response_model=AlertResponse)
def put_resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """PUT alias for resolving alert."""
    return _resolve_alert_obj(alert_id, db)

@router.post("/refresh")
def refresh_alerts(db: Session = Depends(get_db)):
    """POST /api/alerts/refresh runs the alert generation for everything."""
    new_alerts = generate_alerts(db)
    total_open = db.query(Alert).filter(Alert.status == "open").count()
    return {
        "status": "success",
        "newly_generated_alerts_count": len(new_alerts),
        "total_open_alerts": total_open
    }
