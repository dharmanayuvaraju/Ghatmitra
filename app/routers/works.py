from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Work, WorkUpdate, Ghat, Vendor, Alert
from app.schemas import WorkResponse, WorkCreate, WorkUpdateCreate, WorkUpdateResponse
from app.services import recalculate_work_status, generate_alerts

router = APIRouter(prefix="/api/works", tags=["works"])

class WorkUpdatePayload(BaseModel):
    progress_pct: int
    note: str
    updated_by: str
    photo: Optional[str] = None
    photo_url: Optional[str] = None

@router.get("", response_model=List[WorkResponse])
def get_works(
    status: Optional[str] = None,
    category: Optional[str] = None,
    ghat_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    sort_by: Optional[str] = Query(None, description="budget, progress_pct, planned_end, last_updated"),
    order: Optional[str] = Query("asc", description="asc or desc"),
    db: Session = Depends(get_db)
):
    query = db.query(Work)
    if status:
        query = query.filter(Work.status == status)
    if category:
        query = query.filter(Work.category == category)
    if ghat_id:
        query = query.filter(Work.ghat_id == ghat_id)
    if vendor_id:
        query = query.filter(Work.vendor_id == vendor_id)

    # Sorting
    sort_column_map = {
        "budget": Work.budget,
        "progress_pct": Work.progress_pct,
        "planned_end": Work.planned_end,
        "last_updated": Work.last_updated,
        "id": Work.id,
        "title": Work.title
    }
    col = sort_column_map.get(sort_by, Work.id)
    if order.lower() == "desc":
        query = query.order_by(col.desc())
    else:
        query = query.order_by(col.asc())

    return query.all()

@router.get("/{work_id}", response_model=WorkResponse)
def get_work(work_id: int, db: Session = Depends(get_db)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return work

@router.post("", response_model=WorkResponse)
def create_work(payload: WorkCreate, db: Session = Depends(get_db)):
    if not db.query(Ghat).filter(Ghat.id == payload.ghat_id).first():
        raise HTTPException(status_code=400, detail="Invalid ghat_id")
    if not db.query(Vendor).filter(Vendor.id == payload.vendor_id).first():
        raise HTTPException(status_code=400, detail="Invalid vendor_id")

    work = Work(**payload.model_dump())
    work.last_updated = datetime.utcnow()
    recalculate_work_status(work)
    db.add(work)
    db.commit()
    db.refresh(work)
    generate_alerts(db)
    return work

def _process_work_update(work_id: int, payload: WorkUpdatePayload, db: Session):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")

    # Update work progress and recalculate status via business logic
    prev_progress = work.progress_pct
    prev_status = work.status
    work.progress_pct = max(0, min(100, payload.progress_pct))
    recalculate_work_status(work)

    import base64
    import time
    photo_path = payload.photo or payload.photo_url
    if photo_path and "base64," in photo_path:
        try:
            format_part, base64_data = photo_path.split(";base64,")
            ext = "jpg"
            if "png" in format_part:
                ext = "png"
            filename = f"field_{int(time.time())}_{work_id}.{ext}"
            upload_dir = os.path.join("static", "uploads", "field")
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.join(upload_dir, filename)
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(base64_data))
            photo_path = f"/static/uploads/field/{filename}"
        except Exception as e:
            print("Field photo decode warning:", e)

    update = WorkUpdate(
        work_id=work_id,
        progress_pct=work.progress_pct,
        note=payload.note,
        photo_url=photo_path,
        updated_by=payload.updated_by,
        created_at=datetime.utcnow()
    )
    db.add(update)
    db.commit()
    db.refresh(update)
    db.refresh(work)

    # Log engineer field alert for immediate tracking
    severity = "high" if work.status == "delayed" else "medium"
    alert_type = f"Engineer Update: {work.category.title()}"
    alert_msg = f"[{payload.updated_by}] updated Work #{work.id} ({work.title}) from {prev_progress}% to {work.progress_pct}% ({work.status}). Note: {payload.note}"
    eng_alert = Alert(
        type=alert_type,
        severity=severity,
        message=alert_msg,
        photo_url=photo_path,
        related_work_id=work.id,
        status="open",
        created_at=datetime.utcnow()
    )
    db.add(eng_alert)
    db.commit()

    # Regenerate alerts for everything
    generate_alerts(db)

    return update

@router.post("/{work_id}/update", response_model=WorkUpdateResponse)
def post_work_update(work_id: int, payload: WorkUpdatePayload, db: Session = Depends(get_db)):
    """POST /api/works/{id}/update: saves update, recalculates status, and regenerates alerts."""
    return _process_work_update(work_id, payload, db)

@router.post("/{work_id}/updates", response_model=WorkUpdateResponse)
def post_work_updates_alias(work_id: int, payload: WorkUpdatePayload, db: Session = Depends(get_db)):
    """Alias for POST /api/works/{id}/updates"""
    return _process_work_update(work_id, payload, db)

@router.put("/{work_id}/status", response_model=WorkResponse)
def update_work_status(work_id: int, status: str = Query(...), db: Session = Depends(get_db)):
    valid_statuses = ["not started", "on track", "delayed", "completed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")

    work.status = status
    if status == "completed":
        work.progress_pct = 100
    work.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(work)
    generate_alerts(db)
    return work
