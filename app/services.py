from datetime import datetime, date
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Work, Asset, Vendor, Ghat, Alert, WorkUpdate

PUSHKARALU_START_DATE = date(2027, 6, 26)

def calculate_expected_progress(planned_start: datetime, planned_end: datetime, current_date: Optional[date] = None) -> float:
    """Calculate expected progress percentage: elapsed days / total days * 100 (clamped 0 to 100)."""
    today = current_date or datetime.now().date()
    p_start = planned_start.date() if isinstance(planned_start, datetime) else planned_start
    p_end = planned_end.date() if isinstance(planned_end, datetime) else planned_end

    total_days = (p_end - p_start).days
    if total_days <= 0:
        return 100.0 if today >= p_end else 0.0

    elapsed_days = (today - p_start).days
    if elapsed_days <= 0:
        return 0.0
    if elapsed_days >= total_days:
        return 100.0

    expected = (elapsed_days / total_days) * 100.0
    return round(expected, 1)

def calculate_work_status(
    planned_start: datetime,
    planned_end: datetime,
    progress_pct: int,
    current_date: Optional[date] = None
) -> Tuple[str, float]:
    """
    Status rule:
    - progress = 100 means 'completed'
    - If today is after planned_end and progress is below 100, then 'delayed'
    - If today is before planned_start, then 'not started'
    - Expected progress = elapsed days / total days x 100
    - If actual progress is 15+ points behind expected, mark 'delayed'
    - Otherwise 'on track'
    """
    today = current_date or datetime.now().date()
    p_start = planned_start.date() if isinstance(planned_start, datetime) else planned_start
    p_end = planned_end.date() if isinstance(planned_end, datetime) else planned_end

    # Rule 1: progress = 100 means 'completed'
    if progress_pct >= 100:
        return "completed", 100.0

    # Rule 2: If today is after planned_end and progress is below 100, then 'delayed'
    if today > p_end:
        return "delayed", 100.0

    # Rule 3: If today is before planned_start, then 'not started'
    if today < p_start:
        return "not started", 0.0

    # Between start and end: calculate expected progress
    expected_pct = calculate_expected_progress(planned_start, planned_end, current_date=today)

    # Rule 4: If actual progress is 15+ points behind expected, mark 'delayed'
    if (expected_pct - progress_pct) >= 15.0:
        return "delayed", expected_pct

    # Rule 5: Otherwise 'on track'
    return "on track", expected_pct

def recalculate_work_status(work: Work, current_date: Optional[date] = None) -> Tuple[str, float]:
    """Recalculate and update a work item's status using the business rules."""
    new_status, expected = calculate_work_status(
        work.planned_start,
        work.planned_end,
        work.progress_pct,
        current_date=current_date
    )
    work.status = new_status
    work.last_updated = datetime.utcnow()
    return new_status, expected

def generate_alerts(db: Session, current_date: Optional[date] = None) -> List[Alert]:
    """
    Auto-generate alerts with NO DUPLICATE open alerts for the same item:
    - delayed work (high if more than 14 days late or more than 30 points behind, else medium)
    - asset faulty (high)
    - asset maintenance overdue (medium)
    - vendor on_time_pct below 70 (medium)
    """
    today = current_date or datetime.now().date()
    created_alerts = []

    # 1. Check Delayed Works
    works = db.query(Work).all()
    for work in works:
        status, expected = calculate_work_status(work.planned_start, work.planned_end, work.progress_pct, current_date=today)
        work.status = status

        if status == "delayed":
            p_end = work.planned_end.date() if isinstance(work.planned_end, datetime) else work.planned_end
            days_late = (today - p_end).days if today > p_end else 0
            points_behind = max(0.0, expected - work.progress_pct)

            # High if more than 14 days late or more than 30 points behind, else medium
            severity = "high" if (days_late > 14 or points_behind > 30.0) else "medium"

            # Check if duplicate open alert already exists
            existing_open = db.query(Alert).filter(
                Alert.related_work_id == work.id,
                Alert.type == "Work Delay",
                Alert.status == "open"
            ).first()

            if not existing_open:
                msg = f"Work #{work.id} '{work.title}' is delayed. Progress: {work.progress_pct}% (Expected: {round(expected, 1)}%)."
                if days_late > 0:
                    msg += f" Overdue by {days_late} days."
                elif points_behind > 0:
                    msg += f" Lagging {round(points_behind, 1)} points behind schedule."

                alert = Alert(
                    type="Work Delay",
                    severity=severity,
                    message=msg,
                    related_work_id=work.id,
                    related_asset_id=None,
                    status="open",
                    created_at=datetime.utcnow()
                )
                db.add(alert)
                created_alerts.append(alert)
            else:
                # Update severity if worsened
                if severity == "high" and existing_open.severity != "high":
                    existing_open.severity = "high"

    # 2. Check Assets (Faulty & Maintenance Overdue)
    assets = db.query(Asset).all()
    for asset in assets:
        # Asset Faulty (High)
        if asset.status == "faulty":
            existing_faulty = db.query(Alert).filter(
                Alert.related_asset_id == asset.id,
                Alert.type == "Asset Faulty",
                Alert.status == "open"
            ).first()

            if not existing_faulty:
                alert = Alert(
                    type="Asset Faulty",
                    severity="high",
                    message=f"Asset #{asset.id} '{asset.name}' ({asset.type}) at {asset.ghat.name if asset.ghat else 'Ghat'} is faulty and requires repair.",
                    related_work_id=None,
                    related_asset_id=asset.id,
                    status="open",
                    created_at=datetime.utcnow()
                )
                db.add(alert)
                created_alerts.append(alert)

        # Asset Maintenance Overdue (Medium)
        if asset.next_service_date:
            next_srv = asset.next_service_date.date() if isinstance(asset.next_service_date, datetime) else asset.next_service_date
            if next_srv < today and asset.status != "faulty":
                existing_maint = db.query(Alert).filter(
                    Alert.related_asset_id == asset.id,
                    Alert.type == "Asset Maintenance Overdue",
                    Alert.status == "open"
                ).first()

                if not existing_maint:
                    alert = Alert(
                        type="Asset Maintenance Overdue",
                        severity="medium",
                        message=f"Asset #{asset.id} '{asset.name}' ({asset.type}) maintenance is overdue since {next_srv.strftime('%d %b %Y')}.",
                        related_work_id=None,
                        related_asset_id=asset.id,
                        status="open",
                        created_at=datetime.utcnow()
                    )
                    db.add(alert)
                    created_alerts.append(alert)

    # 3. Check Vendors (on_time_pct below 70 -> medium)
    vendors = db.query(Vendor).all()
    for vendor in vendors:
        if vendor.on_time_pct < 70.0:
            vendor_msg_tag = f"Vendor #{vendor.id} '{vendor.name}'"
            existing_vendor_alert = db.query(Alert).filter(
                Alert.type == "Vendor Performance",
                Alert.status == "open",
                Alert.message.like(f"%{vendor_msg_tag}%")
            ).first()

            if not existing_vendor_alert:
                alert = Alert(
                    type="Vendor Performance",
                    severity="medium",
                    message=f"{vendor_msg_tag} on-time milestone delivery rate has dropped to {vendor.on_time_pct}% (below 70% threshold).",
                    related_work_id=None,
                    related_asset_id=None,
                    status="open",
                    created_at=datetime.utcnow()
                )
                db.add(alert)
                created_alerts.append(alert)

    db.commit()
    return created_alerts

def calculate_vendor_scores_and_ranking(db: Session) -> List[Dict[str, Any]]:
    """
    Vendor score out of 100:
    - 50% on_time_pct
    - 30% quality_rating (scaled to 100, i.e. quality_rating * 20)
    - 20% (100 minus 10 per open alert linked to the vendor, minimum 0)
    Adds a rank (1, 2, 3... sorted by score descending).
    """
    vendors = db.query(Vendor).all()
    vendor_scores = []

    for v in vendors:
        # Find open alerts linked to this vendor's works
        vendor_work_ids = [w.id for w in v.works]
        if vendor_work_ids:
            open_alerts_count = db.query(Alert).filter(
                Alert.related_work_id.in_(vendor_work_ids),
                Alert.status == "open"
            ).count()
        else:
            open_alerts_count = 0

        # Component 1: 50% on_time_pct
        c1 = 0.50 * float(v.on_time_pct)

        # Component 2: 30% quality_rating scaled to 100 (rating out of 5 -> rating * 20)
        c2 = 0.30 * (float(v.quality_rating) * 20.0)

        # Component 3: 20% (100 minus 10 per open alert, min 0)
        alert_penalty_score = max(0.0, 100.0 - (10.0 * open_alerts_count))
        c3 = 0.20 * alert_penalty_score

        total_score = round(c1 + c2 + c3, 1)

        vendor_scores.append({
            "id": v.id,
            "name": v.name,
            "contact_person": v.contact_person,
            "on_time_pct": v.on_time_pct,
            "quality_rating": v.quality_rating,
            "staff_deployed": v.staff_deployed,
            "open_alerts_count": open_alerts_count,
            "works_count": len(v.works),
            "score": total_score,
            "score_breakdown": {
                "on_time_component": round(c1, 1),
                "quality_component": round(c2, 1),
                "alert_component": round(c3, 1)
            }
        })

    # Sort descending by score, tiebreak by on_time_pct
    vendor_scores.sort(key=lambda x: (x["score"], x["on_time_pct"]), reverse=True)

    # Assign ranks
    for rank, item in enumerate(vendor_scores, start=1):
        item["rank"] = rank

    return vendor_scores

def get_system_summary(db: Session, current_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Summary function:
    - counts by status
    - average progress per ghat
    - days left to Pushkaralu (26 Jun 2027)
    - total budget vs budget of delayed works
    """
    today = current_date or datetime.now().date()
    days_left = max(0, (PUSHKARALU_START_DATE - today).days)

    works = db.query(Work).all()
    total_works = len(works)

    counts_by_status = {
        "not started": 0,
        "on track": 0,
        "delayed": 0,
        "completed": 0
    }
    total_budget = 0.0
    delayed_budget = 0.0

    for w in works:
        status = w.status
        counts_by_status[status] = counts_by_status.get(status, 0) + 1
        total_budget += float(w.budget)
        if status == "delayed":
            delayed_budget += float(w.budget)

    delayed_budget_pct = round((delayed_budget / total_budget * 100), 1) if total_budget > 0 else 0.0

    # Average progress per ghat
    ghats = db.query(Ghat).all()
    ghat_summaries = []
    for g in ghats:
        g_works = [w for w in works if w.ghat_id == g.id]
        if g_works:
            avg_prog = round(sum(w.progress_pct for w in g_works) / len(g_works), 1)
        else:
            avg_prog = 0.0
        ghat_summaries.append({
            "ghat_id": g.id,
            "ghat_name": g.name,
            "average_progress": avg_prog,
            "works_count": len(g_works),
            "latitude": g.latitude,
            "longitude": g.longitude
        })

    # Total assets & alerts counts
    total_assets = db.query(Asset).count()
    faulty_assets = db.query(Asset).filter(Asset.status == "faulty").count()
    open_alerts = db.query(Alert).filter(Alert.status == "open").count()
    avg_prog_overall = round(sum(w.progress_pct for w in works) / total_works, 1) if total_works > 0 else 0.0

    return {
        "event": "Godavari Pushkaralu 2027",
        "target_date": PUSHKARALU_START_DATE.isoformat(),
        "days_left": days_left,
        "total_works": total_works,
        "avg_progress": avg_prog_overall,
        "counts_by_status": counts_by_status,
        "budget": {
            "total_budget": total_budget,
            "delayed_budget": delayed_budget,
            "delayed_budget_pct": delayed_budget_pct
        },
        "average_progress_per_ghat": ghat_summaries,
        "ghat_progress": {g["ghat_name"]: g["average_progress"] for g in ghat_summaries},
        "assets": {
            "total": total_assets,
            "faulty": faulty_assets,
            "working": max(0, total_assets - faulty_assets)
        },
        "open_alerts": open_alerts
    }

