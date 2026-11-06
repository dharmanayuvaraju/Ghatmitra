import os
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import Base, engine, get_db
from app.models import Ghat, Vendor, Work, Asset, Alert, WorkUpdate
from app.seed import seed_db
from app.services import get_system_summary, generate_alerts, calculate_vendor_scores_and_ranking
from app.routers import works, assets, alerts, vendors, ghats, views, guard

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)

    # Ensure SQLite has latest Alert columns if using sqlite
    if engine.dialect.name == "sqlite":
        try:
            with engine.connect() as conn:
                res = conn.execute(text("PRAGMA table_info(alerts)")).fetchall()
                cols = [r[1] for r in res]
                cols_to_add = [
                    ("photo_url", "VARCHAR(255)"),
                    ("guard_name", "VARCHAR(100)"),
                    ("issue_type", "VARCHAR(60)"),
                    ("ghat_name", "VARCHAR(120)"),
                    ("note", "TEXT"),
                    ("assigned_to", "VARCHAR(100)"),
                    ("assigned_at", "DATETIME"),
                    ("in_progress_at", "DATETIME"),
                    ("resolution_photo_url", "VARCHAR(255)"),
                    ("resolution_note", "TEXT"),
                    ("resolved_by", "VARCHAR(100)"),
                    ("resolved_at", "DATETIME")
                ]
                for col_name, col_type in cols_to_add:
                    if col_name not in cols:
                        conn.execute(text(f"ALTER TABLE alerts ADD COLUMN {col_name} {col_type}"))
                conn.commit()
        except Exception as e:
            print("Schema update notice:", e)

    # Check if empty, auto-seed on first run
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(Ghat).count() == 0:
            print("Database empty. Auto-seeding initial GhatMitra data...")
            seed_db()
        else:
            # Refresh alerts on startup
            generate_alerts(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title="GhatMitra",
    description="Every ghat, every asset, every pilgrim looked after • Godavari Pushkaralu 2027 (Rajamahendravaram)",
    version="2.0.0",
    lifespan=lifespan
)

# Resolve static directory reliably whether run from root or package
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
if not os.path.exists(STATIC_DIR):
    STATIC_DIR = os.path.abspath("static")

os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include Routers
app.include_router(views.router)
app.include_router(guard.router)
app.include_router(works.router)
app.include_router(assets.router)
app.include_router(alerts.router)
app.include_router(vendors.router)
app.include_router(ghats.router)

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        if "text/html" in request.headers.get("accept", ""):
            return views.templates.TemplateResponse("404.html", {"request": request, "active_page": ""}, status_code=404)
        return JSONResponse(status_code=404, content={"detail": exc.detail or "Not Found"})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.get("/api/summary")
def api_summary(db: Session = Depends(get_db)):
    """GET /api/summary: returns summary counts, days left, ghat progress, and budget at risk."""
    return get_system_summary(db)

@app.get("/api/hub/counts")
def api_hub_counts(db: Session = Depends(get_db)):
    """GET /api/hub/counts: lightweight live polling for SPA Home Hub badges & tiles."""
    summary = get_system_summary(db)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Guard reports count
    guard_query = db.query(Alert).filter(Alert.type.like("Guard Report%"))
    guard_reports_today = guard_query.filter(Alert.created_at >= today_start).count()
    if guard_reports_today == 0:
        guard_reports_today = guard_query.count()

    # 2. Engineer updates count
    updates_query = db.query(WorkUpdate)
    engineer_updates_today = updates_query.filter(WorkUpdate.created_at >= today_start).count()
    if engineer_updates_today == 0:
        engineer_updates_today = updates_query.count()

    # 3. Lowest vendor score
    vendors = calculate_vendor_scores_and_ranking(db)
    lowest_score = min([v["score"] for v in vendors]) if vendors else 100

    delayed_count = summary["counts_by_status"].get("delayed", 0)
    faulty_count = summary["assets"]["faulty"]
    open_alerts_count = summary["open_alerts"]

    return {
        "guard_reports_today": guard_reports_today,
        "engineer_updates_today": engineer_updates_today,
        "works_total": summary["total_works"],
        "works_delayed": delayed_count,
        "delayed_works": delayed_count,
        "assets_total": summary["assets"]["total"],
        "assets_faulty": faulty_count,
        "faulty_assets": faulty_count,
        "vendors_lowest_score": lowest_score,
        "lowest_vendor_score": lowest_score,
        "alerts_open": open_alerts_count,
        "open_alerts": open_alerts_count,
        "days_left": summary["days_left"],
        "budget_at_risk": summary["budget"]["delayed_budget"],
        "budget_at_risk_pct": summary["budget"]["delayed_budget_pct"]
    }

@app.get("/api/engineer/updates")
def list_engineer_updates(limit: int = 20, db: Session = Depends(get_db)):
    """GET /api/engineer/updates: returns newest engineer work updates and fault logs."""
    updates = db.query(WorkUpdate).order_by(WorkUpdate.created_at.desc()).limit(limit).all()
    results = []
    for u in updates:
        results.append({
            "id": u.id,
            "work_id": u.work_id,
            "work_title": u.work.title if u.work else f"Work #{u.work_id}",
            "ghat_name": u.work.ghat.name if u.work and u.work.ghat else "Pushkar Ghat",
            "progress_pct": u.progress_pct,
            "status": u.work.status if u.work else "updated",
            "note": u.note,
            "photo_url": u.photo_url,
            "updated_by": u.updated_by,
            "created_at": u.created_at.strftime("%d %b, %H:%M"),
            "created_at_iso": u.created_at.isoformat()
        })
    return results

@app.get("/api/alerts/{alert_id}")
def get_alert_detail(alert_id: int, db: Session = Depends(get_db)):
    """GET /api/alerts/{id}: returns full detail for the detail drawer with safe non-null fields."""
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    ghat_name = a.clean_ghat or "Pushkar Ghat"
    lat, lng = 17.0015, 81.7770
    linked_entity_title = "General Incident"

    if a.related_work:
        ghat_name = a.related_work.ghat.name if (a.related_work.ghat and a.related_work.ghat.name) else ghat_name
        lat = a.related_work.latitude or lat
        lng = a.related_work.longitude or lng
        linked_entity_title = f"Work #{a.related_work.id}: {a.related_work.title}"
    elif a.related_asset:
        ghat_name = a.related_asset.ghat.name if (a.related_asset.ghat and a.related_asset.ghat.name) else ghat_name
        lat = a.related_asset.ghat.latitude if a.related_asset.ghat else lat
        lng = a.related_asset.ghat.longitude if a.related_asset.ghat else lng
        linked_entity_title = f"Asset #{a.related_asset.id}: {a.related_asset.name} ({a.related_asset.type})"

    return {
        "id": a.id,
        "ref_no": f"GRD-{a.id:04d}" if (a.type and "Guard" in a.type) else f"ALT-{a.id:04d}",
        "type": a.type or "Alert",
        "clean_title": a.clean_title,
        "severity": a.severity or "medium",
        "message": a.clean_message or "",
        "clean_message": a.clean_message or "",
        "note": a.note or "",
        "guard_name": a.clean_guard or "Patrol Guard",
        "ghat_name": ghat_name,
        "photo_url": a.photo_url or "",
        "status": a.status or "open",
        "latitude": lat,
        "longitude": lng,
        "linked_entity": linked_entity_title,
        "related_work_id": a.related_work_id,
        "related_asset_id": a.related_asset_id,
        "assigned_to": a.assigned_to or "",
        "assigned_at": a.assigned_at.strftime("%d %b %Y, %H:%M") if a.assigned_at else "",
        "in_progress_at": a.in_progress_at.strftime("%d %b %Y, %H:%M") if a.in_progress_at else "",
        "resolution_photo_url": a.resolution_photo_url or "",
        "resolution_note": a.resolution_note or "",
        "resolved_by": a.resolved_by or "",
        "resolved_at": a.resolved_at.strftime("%d %b %Y, %H:%M") if a.resolved_at else "",
        "resolution_minutes": a.resolution_minutes,
        "created_at": a.created_at.strftime("%d %b %Y, %H:%M") if a.created_at else ""
    }

@app.post("/api/alerts/{alert_id}/status")
def update_alert_status(alert_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """POST /api/alerts/{id}/status: sets status to open, in_progress, or resolved, supporting photos & assignments."""
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    new_status = payload.get("status", "resolved")
    a.status = new_status
    now = datetime.utcnow()

    if new_status == "in_progress":
        a.in_progress_at = now
        if payload.get("assigned_to"):
            a.assigned_to = payload.get("assigned_to")
            a.assigned_at = now
    elif new_status == "resolved":
        a.resolved_at = now
        if payload.get("resolved_by"):
            a.resolved_by = payload.get("resolved_by")
        if payload.get("resolution_note"):
            a.resolution_note = payload.get("resolution_note")
        
        # Save fix photo if provided (compressed base64)
        res_photo = payload.get("resolution_photo")
        if res_photo and "base64," in res_photo:
            try:
                import base64, time
                res_dir = os.path.join("static", "uploads", "resolutions")
                os.makedirs(res_dir, exist_ok=True)
                format_part, base64_data = res_photo.split(";base64,")
                ext = "jpg"
                if "png" in format_part: ext = "png"
                fname = f"res_{int(time.time())}_{alert_id}.{ext}"
                fpath = os.path.join(res_dir, fname)
                with open(fpath, "wb") as f:
                    f.write(base64.b64decode(base64_data))
                a.resolution_photo_url = f"/static/uploads/resolutions/{fname}"
            except Exception as ex:
                print("Resolution photo decode warning:", ex)
    elif new_status == "open":
        # Re-opened
        a.resolved_at = None
        a.resolution_photo_url = None
        a.resolution_note = None
        a.resolved_by = None

    if payload.get("assigned_to") and not a.assigned_to:
        a.assigned_to = payload.get("assigned_to")
        a.assigned_at = now

    db.commit()
    db.refresh(a)
    return {
        "status": "success",
        "alert_id": a.id,
        "new_status": a.status,
        "assigned_to": a.assigned_to,
        "resolved_at": a.resolved_at.strftime("%d %b %Y, %H:%M") if a.resolved_at else None,
        "resolution_minutes": a.resolution_minutes
    }

@app.post("/api/admin/reset")
def api_admin_reset():
    """POST /api/admin/reset: reset and reseed database cleanly."""
    result = seed_db()
    return {
        "status": "success",
        "message": "Database reset and re-seeded successfully",
        "data": result
    }

@app.get("/health")
def health_check(quick: bool = False, db: Session = Depends(get_db)):
    """GET /health: fast endpoint for uptime monitors and deployment checks."""
    if quick:
        return {"status": "healthy", "project": "GhatMitra", "version": "2.0.0"}
    
    ghats_c = db.query(Ghat).count()
    vendors_c = db.query(Vendor).count()
    works_c = db.query(Work).count()
    delayed_c = db.query(Work).filter(Work.status == "delayed").count()
    assets_c = db.query(Asset).count()
    faulty_c = db.query(Asset).filter(Asset.status == "faulty").count()
    alerts_c = db.query(Alert).count()
    updates_c = db.query(WorkUpdate).count()

    return {
        "status": "healthy",
        "project": "GhatMitra",
        "tagline": "Every ghat, every asset, every pilgrim looked after",
        "version": "2.0.0",
        "event": "Godavari Pushkaralu 2027",
        "database": engine.dialect.name,
        "counts": {
            "ghats": ghats_c,
            "vendors": vendors_c,
            "works": works_c,
            "delayed_works": delayed_c,
            "delayed_pct": round((delayed_c / works_c * 100), 1) if works_c else 0,
            "assets": assets_c,
            "faulty_assets": faulty_c,
            "faulty_pct": round((faulty_c / assets_c * 100), 1) if assets_c else 0,
            "alerts": alerts_c,
            "work_updates": updates_c
        }
    }

@app.post("/api/seed")
def api_seed():
    result = seed_db()
    return {
        "status": "success",
        "message": "Database reseeded successfully",
        "data": result
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
