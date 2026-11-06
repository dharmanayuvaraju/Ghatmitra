from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Asset, Ghat
from app.schemas import AssetResponse, AssetCreate
from app.services import generate_alerts

router = APIRouter(prefix="/api/assets", tags=["assets"])

class AssetStatusPayload(BaseModel):
    status: str
    note: Optional[str] = ""
    severity: Optional[str] = "high"
    reported_by: Optional[str] = "Site Engineer"
    photo: Optional[str] = None

@router.get("", response_model=List[AssetResponse])
def get_assets(
    type: Optional[str] = None,
    ghat_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Asset)
    if type:
        query = query.filter(Asset.type == type)
    if ghat_id:
        query = query.filter(Asset.ghat_id == ghat_id)
    if status:
        query = query.filter(Asset.status == status)
    return query.order_by(Asset.id.asc()).all()

@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.post("", response_model=AssetResponse)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    if not db.query(Ghat).filter(Ghat.id == payload.ghat_id).first():
        raise HTTPException(status_code=400, detail="Invalid ghat_id")

    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    generate_alerts(db)
    return asset

def _set_asset_status(asset_id: int, new_status: str, db: Session, payload: Optional[AssetStatusPayload] = None):
    valid_statuses = ["working", "faulty", "under maintenance"]
    clean_status = new_status.strip().lower()
    if clean_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status '{new_status}'. Must be one of: {valid_statuses}")

    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.status = clean_status
    db.commit()
    db.refresh(asset)

    # Handle photo upload if present
    photo_path = None
    if payload and payload.photo and "base64," in payload.photo:
        try:
            import os, base64, time
            format_part, base64_data = payload.photo.split(";base64,")
            ext = "jpg"
            if "png" in format_part:
                ext = "png"
            filename = f"asset_{int(time.time())}_{asset_id}.{ext}"
            upload_dir = os.path.join("static", "uploads", "field")
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(base64_data))
            photo_path = f"/static/uploads/field/{filename}"
        except Exception as e:
            print("Asset photo decode warning:", e)

    # If faulty or maintenance reported, log an Alert so it shows in Engineer Updates & Alerts
    if clean_status != "working":
        from app.models import Alert
        from datetime import datetime
        rep_by = payload.reported_by if payload and payload.reported_by else "Site Engineer"
        note_text = payload.note if payload and payload.note else "Field equipment outage"
        sev = payload.severity if payload and payload.severity else ("high" if clean_status == "faulty" else "medium")
        alert = Alert(
            type=f"Asset Fault: {asset.type.title()}",
            severity=sev,
            message=f"[{rep_by}] reported {asset.name} at {asset.ghat.name} is {clean_status}. Note: {note_text}",
            photo_url=photo_path,
            related_asset_id=asset.id,
            status="open",
            created_at=datetime.utcnow()
        )
        db.add(alert)
        db.commit()

    # Regenerate alerts
    generate_alerts(db)
    return asset

@router.post("/{asset_id}/status", response_model=AssetResponse)
def post_asset_status(
    asset_id: int, 
    payload: Optional[AssetStatusPayload] = None,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """POST /api/assets/{id}/status takes working, faulty or under maintenance, then regenerates alerts."""
    target_status = payload.status if payload else status
    if not target_status:
        raise HTTPException(status_code=400, detail="Missing status parameter")
    return _set_asset_status(asset_id, target_status, db, payload)

@router.put("/{asset_id}/status", response_model=AssetResponse)
def put_asset_status(asset_id: int, status: str = Query(...), db: Session = Depends(get_db)):
    """PUT alias for updating asset status."""
    return _set_asset_status(asset_id, status, db, None)
