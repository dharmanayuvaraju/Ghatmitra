import os
import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Ghat, Vendor, Work, Asset, WorkUpdate, Alert
from app.seed import seed_db
from app.services import get_system_summary, calculate_vendor_scores_and_ranking, generate_alerts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(include_in_schema=False)

@router.get("/", response_class=HTMLResponse)
def view_dashboard(request: Request, db: Session = Depends(get_db)):
    summary = get_system_summary(db)

    # Needs attention now: top 3 alerts (high severity first)
    high_alerts_all = db.query(Alert).filter(Alert.status == "open", Alert.severity == "high").order_by(Alert.id.desc()).limit(3).all()
    if len(high_alerts_all) < 3:
        extra = db.query(Alert).filter(Alert.status == "open", Alert.severity != "high").order_by(Alert.id.desc()).limit(3 - len(high_alerts_all)).all()
        top_alerts = high_alerts_all + extra
    else:
        top_alerts = high_alerts_all

    # 1. Guard reports (isolated module)
    guard_reports_all = db.query(Alert).filter(Alert.type.like("Guard Report%")).order_by(Alert.created_at.desc()).all()

    # 2. Engineer updates (isolated module)
    engineer_updates_all = db.query(WorkUpdate).order_by(WorkUpdate.created_at.desc()).all()

    # 3. Works & Assets & Vendors & Alerts
    works_all = db.query(Work).order_by(Work.id.asc()).all()
    assets_all = db.query(Asset).order_by(Asset.id.asc()).all()
    ghats_all = db.query(Ghat).order_by(Ghat.id.asc()).all()
    vendors_ranked = calculate_vendor_scores_and_ranking(db)
    alerts_all = db.query(Alert).order_by(Alert.created_at.desc()).all()

    categories = ["ghat steps", "toilet", "lighting", "barricade", "parking", "shelter", "water point"]
    asset_types = ["mobile toilet", "bin", "light", "CCTV", "generator"]

    # Today counts
    from datetime import datetime
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    guard_today = [a for a in guard_reports_all if a.created_at >= today_start]
    guard_today_count = len(guard_today) if len(guard_today) > 0 else len(guard_reports_all)

    eng_today = [u for u in engineer_updates_all if u.created_at >= today_start]
    eng_today_count = len(eng_today) if len(eng_today) > 0 else len(engineer_updates_all)

    delayed_works_top = [w for w in works_all if w.status == "delayed"][:5]
    faulty_assets_list = [a for a in assets_all if a.status == "faulty"]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "active_page": "dashboard",
        "summary": summary,
        "top_alerts": top_alerts,
        "guard_reports": guard_reports_all,
        "guard_today_count": guard_today_count,
        "engineer_updates": engineer_updates_all,
        "eng_today_count": eng_today_count,
        "works": works_all,
        "assets": assets_all,
        "ghats": ghats_all,
        "vendors": vendors_ranked,
        "alerts": alerts_all,
        "categories": categories,
        "asset_types": asset_types,
        "delayed_works": delayed_works_top,
        "faulty_assets": faulty_assets_list,
        "top_5_vendors": vendors_ranked[:5]
    })

@router.get("/works", response_class=HTMLResponse)
def view_works(
    request: Request,
    status: Optional[str] = None,
    category: Optional[str] = None,
    ghat_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
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
        
    works = query.order_by(Work.id.asc()).all()
    ghats = db.query(Ghat).all()
    vendors = db.query(Vendor).all()
    categories = ["ghat steps", "toilet", "lighting", "barricade", "parking", "shelter", "water point"]

    return templates.TemplateResponse("works.html", {
        "request": request,
        "active_page": "works",
        "works": works,
        "ghats": ghats,
        "vendors": vendors,
        "categories": categories,
        "selected_status": status,
        "selected_category": category,
        "selected_ghat": ghat_id,
        "selected_vendor": vendor_id
    })

@router.get("/works/{work_id}", response_class=HTMLResponse)
def view_work_detail(request: Request, work_id: int, db: Session = Depends(get_db)):
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        return RedirectResponse("/works", status_code=303)
        
    updates = db.query(WorkUpdate).filter(WorkUpdate.work_id == work_id).order_by(WorkUpdate.created_at.desc()).all()
    alerts = db.query(Alert).filter(Alert.related_work_id == work_id).all()

    return templates.TemplateResponse("work_detail.html", {
        "request": request,
        "active_page": "works",
        "work": work,
        "updates": updates,
        "alerts": alerts
    })

@router.get("/assets", response_class=HTMLResponse)
def view_assets(
    request: Request,
    type: Optional[str] = None,
    status: Optional[str] = None,
    ghat_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Asset)
    if type:
        query = query.filter(Asset.type == type)
    if status:
        query = query.filter(Asset.status == status)
    if ghat_id:
        query = query.filter(Asset.ghat_id == ghat_id)
        
    assets = query.order_by(Asset.id.asc()).all()
    ghats = db.query(Ghat).all()
    types = ["mobile toilet", "bin", "light", "CCTV", "generator"]

    return templates.TemplateResponse("assets.html", {
        "request": request,
        "active_page": "assets",
        "assets": assets,
        "ghats": ghats,
        "types": types,
        "selected_type": type,
        "selected_status": status,
        "selected_ghat": ghat_id
    })

@router.get("/vendors", response_class=HTMLResponse)
def view_vendors(request: Request, db: Session = Depends(get_db)):
    ranked_vendors = calculate_vendor_scores_and_ranking(db)
    return templates.TemplateResponse("vendors.html", {
        "request": request,
        "active_page": "vendors",
        "vendors": ranked_vendors
    })

@router.get("/alerts", response_class=HTMLResponse)
def view_alerts(
    request: Request,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)
        
    alerts = query.order_by(Alert.id.desc()).all()
    return templates.TemplateResponse("alerts.html", {
        "request": request,
        "active_page": "alerts",
        "alerts": alerts,
        "selected_severity": severity,
        "selected_status": status
    })

# --- STEP 4: FIELD OFFICER MOBILE ROUTE ---
@router.get("/field", response_class=HTMLResponse)
def view_field_app(request: Request, db: Session = Depends(get_db)):
    works = db.query(Work).order_by(Work.id.asc()).all()
    assets = db.query(Asset).order_by(Asset.id.asc()).all()
    return templates.TemplateResponse("field.html", {
        "request": request,
        "active_page": "field",
        "works": works,
        "assets": assets
    })

# --- STEP 6: PRINTABLE READINESS REPORT & EXPORTS ---
@router.get("/report", response_class=HTMLResponse)
def view_report(request: Request, db: Session = Depends(get_db)):
    summary = get_system_summary(db)
    delayed_works = db.query(Work).filter(Work.status == "delayed").order_by(Work.budget.desc()).limit(5).all()
    faulty_assets = db.query(Asset).filter(Asset.status == "faulty").all()
    ranked_vendors = calculate_vendor_scores_and_ranking(db)
    top_5_vendors = ranked_vendors[:5]

    return templates.TemplateResponse("report.html", {
        "request": request,
        "active_page": "report",
        "summary": summary,
        "delayed_works": delayed_works,
        "faulty_assets": faulty_assets,
        "top_5_vendors": top_5_vendors
    })

# --- CSV EXPORT ENDPOINTS ---
@router.get("/api/export/works.csv")
def export_works_csv(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Category", "Ghat", "Vendor", "Progress_Pct", "Status", "Budget_INR", "Planned_Start", "Planned_End", "Latitude", "Longitude"])
    for w in db.query(Work).all():
        writer.writerow([w.id, w.title, w.category, w.ghat.name, w.vendor.name, w.progress_pct, w.status, w.budget, w.planned_start.strftime('%Y-%m-%d'), w.planned_end.strftime('%Y-%m-%d'), w.latitude, w.longitude])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=pushkar_works.csv"})

@router.get("/api/export/assets.csv")
def export_assets_csv(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Type", "Ghat", "Status", "Last_Service_Date", "Next_Service_Date"])
    for a in db.query(Asset).all():
        writer.writerow([a.id, a.name, a.type, a.ghat.name, a.status, a.last_service_date.strftime('%Y-%m-%d') if a.last_service_date else "", a.next_service_date.strftime('%Y-%m-%d') if a.next_service_date else ""])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=pushkar_assets.csv"})

@router.get("/api/export/vendors.csv")
def export_vendors_csv(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Rank", "ID", "Name", "Contact_Person", "Composite_Score", "On_Time_Pct", "Quality_Rating", "Staff_Deployed", "Open_Alerts"])
    for v in calculate_vendor_scores_and_ranking(db):
        writer.writerow([v["rank"], v["id"], v["name"], v["contact_person"], v["score"], v["on_time_pct"], v["quality_rating"], v["staff_deployed"], v["open_alerts_count"]])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=pushkar_vendors.csv"})

@router.get("/api/export/alerts.csv")
def export_alerts_csv(db: Session = Depends(get_db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Type", "Severity", "Status", "Message", "Related_Work_ID", "Related_Asset_ID", "Created_At"])
    for a in db.query(Alert).all():
        writer.writerow([a.id, a.type, a.severity, a.status, a.message, a.related_work_id or "", a.related_asset_id or "", a.created_at.strftime('%Y-%m-%d %H:%M:%S')])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=pushkar_alerts.csv"})

@router.post("/seed")
def trigger_seed():
    seed_db()
    return RedirectResponse(url="/?seeded=true", status_code=303)
