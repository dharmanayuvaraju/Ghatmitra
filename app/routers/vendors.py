from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Vendor, Work
from app.schemas import VendorResponse
from app.services import calculate_vendor_scores_and_ranking

router = APIRouter(prefix="/api/vendors", tags=["vendors"])

@router.get("/ranking")
def get_vendor_ranking(db: Session = Depends(get_db)):
    """GET /api/vendors/ranking returns vendors with score and rank."""
    return calculate_vendor_scores_and_ranking(db)

@router.get("", response_model=List[VendorResponse])
def get_vendors(db: Session = Depends(get_db)):
    return db.query(Vendor).order_by(Vendor.quality_rating.desc()).all()

@router.get("/{vendor_id}")
def get_vendor_details(vendor_id: int, db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    works = db.query(Work).filter(Work.vendor_id == vendor_id).all()
    delayed_count = sum(1 for w in works if w.status == "delayed")
    completed_count = sum(1 for w in works if w.status == "completed")

    # Get ranking score for this vendor
    ranking = calculate_vendor_scores_and_ranking(db)
    v_rank_info = next((r for r in ranking if r["id"] == vendor_id), None)

    return {
        "id": vendor.id,
        "name": vendor.name,
        "contact_person": vendor.contact_person,
        "on_time_pct": vendor.on_time_pct,
        "quality_rating": vendor.quality_rating,
        "staff_deployed": vendor.staff_deployed,
        "total_works": len(works),
        "delayed_works": delayed_count,
        "completed_works": completed_count,
        "score": v_rank_info["score"] if v_rank_info else None,
        "rank": v_rank_info["rank"] if v_rank_info else None,
        "works": [
            {
                "id": w.id,
                "title": w.title,
                "category": w.category,
                "status": w.status,
                "progress_pct": w.progress_pct,
                "budget": w.budget
            }
            for w in works
        ]
    }
