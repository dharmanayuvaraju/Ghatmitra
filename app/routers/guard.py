import os
import re
import base64
import time
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Ghat, Alert, Asset, Work
from app.routers.views import templates

router = APIRouter(tags=["guard"])

# Base directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads", "guard")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SW_FILE = os.path.join(BASE_DIR, "static", "js", "guard-sw.js")

ISSUE_MAP = {
    "toilet": {
        "te": "మరుగుదొడ్డి పనిచేయట్లేదు",
        "en": "Toilet not working",
        "icon": "🚽",
        "severity": "high",
        "match_type": "asset",
        "match_key": "toilet"
    },
    "water": {
        "te": "తాగునీరు లేదు",
        "en": "No drinking water",
        "icon": "🚰",
        "severity": "high",
        "match_type": "work",
        "match_key": "water"
    },
    "barrier": {
        "te": "మెట్లు/రక్షణ కంచె విరిగింది",
        "en": "Barrier or steps broken",
        "icon": "⚠️",
        "severity": "high",
        "match_type": "work",
        "match_key": ["barricade", "ghat steps"]
    },
    "light": {
        "te": "లైటు వెలగట్లేదు",
        "en": "Light not working",
        "icon": "💡",
        "severity": "medium",
        "match_type": "asset",
        "match_key": "light"
    },
    "bin": {
        "te": "చెత్త కుండీ నిండింది",
        "en": "Dustbin full",
        "icon": "🗑️",
        "severity": "medium",
        "match_type": "asset",
        "match_key": "bin"
    },
    "work_delayed": {
        "te": "పని ఆగింది/ఆలస్యం",
        "en": "Work stopped or delayed",
        "icon": "⏳",
        "severity": "medium",
        "match_type": "work",
        "match_key": None
    },
    "other": {
        "te": "వేరే సమస్య",
        "en": "Something else",
        "icon": "❓",
        "severity": "medium",
        "match_type": None,
        "match_key": None
    }
}

GHAT_TELUGU_MAP = {
    1: {"te": "పుష్కర్ ఘాట్", "en": "Pushkar Ghat"},
    2: {"te": "కోటిలింగాల ఘాట్", "en": "Kotilingala Ghat"},
    3: {"te": "సరస్వతి ఘాట్", "en": "Saraswati Ghat"},
    4: {"te": "మార్కండేయ ఘాట్", "en": "Markandeya Ghat"},
    5: {"te": "వి.ఐ.పి గౌతమి ఘాట్", "en": "VIP Gautami Ghat"}
}

class GuardReportPayload(BaseModel):
    ghat_id: int
    issue_type: str
    note: Optional[str] = ""
    photo: Optional[str] = None  # base64 data url
    guard_name: Optional[str] = "రాము / Ramu"

@router.get("/guard", response_class=HTMLResponse)
def view_guard_app(request: Request, db: Session = Depends(get_db)):
    ghats = db.query(Ghat).order_by(Ghat.id.asc()).all()
    ghats_data = []
    for g in ghats:
        t_info = GHAT_TELUGU_MAP.get(g.id, {"te": g.name, "en": g.name})
        ghats_data.append({
            "id": g.id,
            "name": g.name,
            "name_te": t_info["te"],
            "name_en": t_info["en"]
        })
    return templates.TemplateResponse("guard.html", {
        "request": request,
        "ghats": ghats_data
    })

@router.get("/guard-sw.js")
def service_worker_file():
    if not os.path.exists(SW_FILE):
        return Response("/* SW missing */", media_type="application/javascript")
    return FileResponse(
        SW_FILE,
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"}
    )

@router.post("/api/guard/report")
def create_guard_report(payload: GuardReportPayload, db: Session = Depends(get_db)):
    ghat = db.query(Ghat).filter(Ghat.id == payload.ghat_id).first()
    if not ghat:
        raise HTTPException(status_code=400, detail="Invalid ghat_id")

    issue_info = ISSUE_MAP.get(payload.issue_type, ISSUE_MAP["other"])
    icon = issue_info["icon"]
    label_te = issue_info["te"]
    label_en = issue_info["en"]
    severity = issue_info["severity"]

    # Match nearest asset or work in this ghat
    matched_asset_id = None
    matched_work_id = None

    if issue_info["match_type"] == "asset" and issue_info["match_key"]:
        asset = db.query(Asset).filter(
            Asset.ghat_id == payload.ghat_id,
            Asset.type.ilike(f"%{issue_info['match_key']}%")
        ).first()
        if asset:
            matched_asset_id = asset.id
            # Also optionally flag asset as faulty for high-severity toilet
            if payload.issue_type == "toilet":
                asset.status = "faulty"

    elif issue_info["match_type"] == "work":
        if isinstance(issue_info["match_key"], list):
            work = db.query(Work).filter(
                Work.ghat_id == payload.ghat_id,
                Work.category.in_(issue_info["match_key"])
            ).first()
        elif issue_info["match_key"]:
            work = db.query(Work).filter(
                Work.ghat_id == payload.ghat_id,
                Work.category.ilike(f"%{issue_info['match_key']}%")
            ).first()
        else:
            work = db.query(Work).filter(Work.ghat_id == payload.ghat_id).first()

        if work:
            matched_work_id = work.id

    # Handle photo saving if provided
    photo_rel_url = None
    if payload.photo and "base64," in payload.photo:
        try:
            format_part, base64_data = payload.photo.split(";base64,")
            ext = "jpg"
            if "png" in format_part:
                ext = "png"
            filename = f"guard_{int(time.time())}_{payload.ghat_id}_{payload.issue_type}.{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(base64_data))
            photo_rel_url = f"/static/uploads/guard/{filename}"
        except Exception as e:
            print("Guard photo decode warning:", e)

    # Format bilingual message without [Photo: ...] text
    guard_disp = payload.guard_name or "రాము / Ramu"
    note_clean = (payload.note or "").strip()
    msg_parts = [f"[{guard_disp}]: {icon} {label_te} / {label_en} at {ghat.name}"]
    if note_clean:
        msg_parts.append(f"Note: {note_clean}")

    alert_message = " | ".join(msg_parts)

    alert = Alert(
        type=f"Guard Report: {label_en}",
        severity=severity,
        message=alert_message,
        photo_url=photo_rel_url,
        related_work_id=matched_work_id,
        related_asset_id=matched_asset_id,
        status="open",
        created_at=datetime.utcnow(),
        guard_name=guard_disp,
        issue_type=payload.issue_type,
        ghat_name=ghat.name,
        note=note_clean
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "status": "success",
        "alert_id": alert.id,
        "ref_no": f"GRD-{alert.id:04d}",
        "ghat_id": payload.ghat_id,
        "ghat_name": ghat.name,
        "issue_type": payload.issue_type,
        "issue_label_te": label_te,
        "issue_label_en": label_en,
        "photo_url": photo_rel_url,
        "severity": severity,
        "created_at": alert.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }

@router.get("/api/guard/reports")
def list_guard_reports(limit: int = 50, db: Session = Depends(get_db)):
    alerts = db.query(Alert).filter(
        Alert.type.like("Guard Report%")
    ).order_by(Alert.created_at.desc()).limit(limit).all()

    results = []
    for a in alerts:
        ghat_name = "Pushkar Ghat"
        if a.related_work and a.related_work.ghat:
            ghat_name = a.related_work.ghat.name
        elif a.related_asset and a.related_asset.ghat:
            ghat_name = a.related_asset.ghat.name

        # Extract guard name from message if available
        guard_name = "రాము / Ramu"
        if "[" in a.message and "]" in a.message:
            guard_name = a.message.split("[")[1].split("]")[0]

        results.append({
            "id": a.id,
            "ref_no": f"GRD-{a.id:04d}",
            "type": a.type,
            "severity": a.severity,
            "message": a.clean_message,
            "photo_url": a.photo_url,
            "ghat_name": ghat_name,
            "guard_name": guard_name,
            "status": a.status,
            "created_at": a.created_at.strftime("%d %b, %H:%M"),
            "created_at_iso": a.created_at.isoformat(),
            "related_work_id": a.related_work_id,
            "related_asset_id": a.related_asset_id
        })
    return results

