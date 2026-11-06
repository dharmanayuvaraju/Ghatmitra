from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Ghat, Work, Asset
from app.schemas import GhatResponse

router = APIRouter(prefix="/api/ghats", tags=["ghats"])

@router.get("", response_model=List[GhatResponse])
def get_ghats(db: Session = Depends(get_db)):
    return db.query(Ghat).order_by(Ghat.id.asc()).all()

@router.get("/{ghat_id}")
def get_ghat_summary(ghat_id: int, db: Session = Depends(get_db)):
    ghat = db.query(Ghat).filter(Ghat.id == ghat_id).first()
    if not ghat:
        raise HTTPException(status_code=404, detail="Ghat not found")

    works = db.query(Work).filter(Work.ghat_id == ghat_id).all()
    assets = db.query(Asset).filter(Asset.ghat_id == ghat_id).all()
    
    return {
        "id": ghat.id,
        "name": ghat.name,
        "latitude": ghat.latitude,
        "longitude": ghat.longitude,
        "total_works": len(works),
        "delayed_works": sum(1 for w in works if w.status == "delayed"),
        "completed_works": sum(1 for w in works if w.status == "completed"),
        "total_assets": len(assets),
        "faulty_assets": sum(1 for a in assets if a.status == "faulty"),
    }

