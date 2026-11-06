from datetime import datetime, date, timedelta
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Ghat, Vendor, Work, Asset, Alert, WorkUpdate
from app.services import (
    calculate_work_status,
    calculate_expected_progress,
    recalculate_work_status,
    generate_alerts,
    calculate_vendor_scores_and_ranking,
    get_system_summary,
    PUSHKARALU_START_DATE
)

# In-memory test database fixture
@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

# ----------------------------------------------------------------------
# 1. STATUS RULE TESTS
# ----------------------------------------------------------------------

def test_status_rule_completed():
    """progress = 100 means 'completed', regardless of dates."""
    today = date(2026, 6, 1)
    # Even if past planned end
    status, expected = calculate_work_status(
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 5, 1),
        progress_pct=100,
        current_date=today
    )
    assert status == "completed"

    # Even if before planned start
    status2, _ = calculate_work_status(
        planned_start=datetime(2026, 7, 1),
        planned_end=datetime(2026, 9, 1),
        progress_pct=100,
        current_date=today
    )
    assert status2 == "completed"

def test_status_rule_past_planned_end_delayed():
    """If today is after planned_end and progress is below 100, then 'delayed'."""
    today = date(2026, 6, 1)
    status, expected = calculate_work_status(
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 5, 1), # ended a month ago
        progress_pct=95,
        current_date=today
    )
    assert status == "delayed"
    assert expected == 100.0

def test_status_rule_before_planned_start_not_started():
    """If today is before planned_start and progress < 100, then 'not started'."""
    today = date(2026, 6, 1)
    status, expected = calculate_work_status(
        planned_start=datetime(2026, 6, 15),
        planned_end=datetime(2026, 8, 15),
        progress_pct=0,
        current_date=today
    )
    assert status == "not started"
    assert expected == 0.0

def test_status_rule_expected_progress_behind_by_15_points_delayed():
    """
    Expected progress = elapsed days / total days x 100.
    If actual progress is 15+ points behind expected, mark 'delayed'.
    """
    # Total days = 100 days (1 Jan to 11 April ~100 days)
    # Suppose today is day 50 -> expected progress = 50.0%
    start = datetime(2026, 1, 1)
    end = datetime(2026, 4, 11)
    total_days = (end.date() - start.date()).days # 100 days
    today = start.date() + timedelta(days=50) # day 50 -> expected 50%

    expected = calculate_expected_progress(start, end, current_date=today)
    assert expected == 50.0

    # Case A: actual progress is 35% -> behind by exactly 15 points (50 - 35 = 15) -> delayed
    status_delayed_15, _ = calculate_work_status(start, end, progress_pct=35, current_date=today)
    assert status_delayed_15 == "delayed"

    # Case B: actual progress is 30% -> behind by 20 points (50 - 30 = 20) -> delayed
    status_delayed_20, _ = calculate_work_status(start, end, progress_pct=30, current_date=today)
    assert status_delayed_20 == "delayed"

def test_status_rule_on_track():
    """If progress is within 15 points of expected progress, mark 'on track'."""
    start = datetime(2026, 1, 1)
    end = datetime(2026, 4, 11) # 100 days
    today = start.date() + timedelta(days=50) # expected 50%

    # Progress is 40% (behind by 10 points < 15) -> on track
    status_40, _ = calculate_work_status(start, end, progress_pct=40, current_date=today)
    assert status_40 == "on track"

    # Progress is 50% (on schedule) -> on track
    status_50, _ = calculate_work_status(start, end, progress_pct=50, current_date=today)
    assert status_50 == "on track"

    # Progress is 65% (ahead of schedule) -> on track
    status_65, _ = calculate_work_status(start, end, progress_pct=65, current_date=today)
    assert status_65 == "on track"

# ----------------------------------------------------------------------
# 2. ALERT CREATION & SEVERITY TESTS
# ----------------------------------------------------------------------

def test_alert_creation_delayed_work(db_session):
    """
    Delayed work creates alert:
    - high if more than 14 days late OR more than 30 points behind
    - else medium
    """
    today = date(2026, 6, 1)
    ghat = Ghat(name="Test Ghat", latitude=17.0, longitude=81.7)
    vendor = Vendor(name="Vendor A", contact_person="Rao", on_time_pct=85.0, quality_rating=4.5, staff_deployed=10)
    db_session.add_all([ghat, vendor])
    db_session.commit()

    # Work 1: >14 days late (planned_end 1 May, today 1 June -> 31 days late) -> High
    w1 = Work(
        title="Delayed 31 Days",
        category="ghat steps",
        ghat_id=ghat.id,
        vendor_id=vendor.id,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 5, 1),
        progress_pct=60,
        status="delayed",
        budget=100000.0,
        latitude=17.0,
        longitude=81.7
    )

    # Work 2: 50 days elapsed out of 100 (expected 50%), progress is 15% (behind by 35 points > 30) -> High
    w2 = Work(
        title="35 Points Behind Schedule",
        category="toilet",
        ghat_id=ghat.id,
        vendor_id=vendor.id,
        planned_start=datetime(2026, 4, 12),
        planned_end=datetime(2026, 7, 21),
        progress_pct=15,
        status="delayed",
        budget=200000.0,
        latitude=17.0,
        longitude=81.7
    )

    # Work 3: Expected ~50%, progress 32% (behind by 18 points, between 15 and 30, not past planned_end) -> Medium
    w3 = Work(
        title="18 Points Behind Schedule",
        category="lighting",
        ghat_id=ghat.id,
        vendor_id=vendor.id,
        planned_start=datetime(2026, 4, 12),
        planned_end=datetime(2026, 7, 21),
        progress_pct=32,
        status="delayed",
        budget=150000.0,
        latitude=17.0,
        longitude=81.7
    )

    db_session.add_all([w1, w2, w3])
    db_session.commit()

    alerts = generate_alerts(db_session, current_date=today)

    alert_w1 = db_session.query(Alert).filter(Alert.related_work_id == w1.id).first()
    alert_w2 = db_session.query(Alert).filter(Alert.related_work_id == w2.id).first()
    alert_w3 = db_session.query(Alert).filter(Alert.related_work_id == w3.id).first()

    assert alert_w1 is not None and alert_w1.severity == "high"
    assert alert_w2 is not None and alert_w2.severity == "high"
    assert alert_w3 is not None and alert_w3.severity == "medium"

def test_alert_creation_faulty_and_overdue_assets(db_session):
    """
    - asset faulty -> high severity
    - asset maintenance overdue -> medium severity
    """
    today = date(2026, 6, 1)
    ghat = Ghat(name="Test Ghat", latitude=17.0, longitude=81.7)
    db_session.add(ghat)
    db_session.commit()

    # Asset 1: faulty
    a1 = Asset(
        name="Faulty Generator",
        type="generator",
        ghat_id=ghat.id,
        status="faulty",
        last_service_date=datetime(2026, 1, 1),
        next_service_date=datetime(2026, 5, 20)
    )

    # Asset 2: working but maintenance overdue
    a2 = Asset(
        name="Overdue CCTV",
        type="CCTV",
        ghat_id=ghat.id,
        status="working",
        last_service_date=datetime(2026, 1, 1),
        next_service_date=datetime(2026, 5, 15) # overdue
    )

    # Asset 3: working and next service in future -> NO alert
    a3 = Asset(
        name="Healthy Toilet",
        type="mobile toilet",
        ghat_id=ghat.id,
        status="working",
        last_service_date=datetime(2026, 5, 1),
        next_service_date=datetime(2026, 7, 1) # future
    )

    db_session.add_all([a1, a2, a3])
    db_session.commit()

    generate_alerts(db_session, current_date=today)

    alert_a1 = db_session.query(Alert).filter(Alert.related_asset_id == a1.id).first()
    alert_a2 = db_session.query(Alert).filter(Alert.related_asset_id == a2.id).first()
    alert_a3 = db_session.query(Alert).filter(Alert.related_asset_id == a3.id).first()

    assert alert_a1 is not None
    assert alert_a1.type == "Asset Faulty"
    assert alert_a1.severity == "high"

    assert alert_a2 is not None
    assert alert_a2.type == "Asset Maintenance Overdue"
    assert alert_a2.severity == "medium"

    assert alert_a3 is None

def test_alert_creation_vendor_low_on_time(db_session):
    """Vendor on_time_pct below 70 -> medium severity alert."""
    today = date(2026, 6, 1)
    v_low = Vendor(name="Slow Contracting Co", contact_person="Sharma", on_time_pct=65.0, quality_rating=4.0, staff_deployed=15)
    v_good = Vendor(name="Good Contracting Co", contact_person="Verma", on_time_pct=88.0, quality_rating=4.5, staff_deployed=20)
    db_session.add_all([v_low, v_good])
    db_session.commit()

    generate_alerts(db_session, current_date=today)

    alert_v_low = db_session.query(Alert).filter(Alert.type == "Vendor Performance", Alert.message.like("%Slow Contracting Co%")).first()
    alert_v_good = db_session.query(Alert).filter(Alert.type == "Vendor Performance", Alert.message.like("%Good Contracting Co%")).first()

    assert alert_v_low is not None
    assert alert_v_low.severity == "medium"
    assert alert_v_good is None

# ----------------------------------------------------------------------
# 3. NO DUPLICATE ALERTS TEST
# ----------------------------------------------------------------------

def test_no_duplicate_open_alerts(db_session):
    """Running generate_alerts multiple times does not create duplicate open alerts for the same item."""
    today = date(2026, 6, 1)
    ghat = Ghat(name="Test Ghat", latitude=17.0, longitude=81.7)
    vendor = Vendor(name="Test Vendor", contact_person="Reddy", on_time_pct=62.0, quality_rating=3.5, staff_deployed=12)
    db_session.add_all([ghat, vendor])
    db_session.commit()

    work = Work(
        title="Delayed Stairs",
        category="ghat steps",
        ghat_id=ghat.id,
        vendor_id=vendor.id,
        planned_start=datetime(2026, 1, 1),
        planned_end=datetime(2026, 4, 1),
        progress_pct=50,
        status="delayed",
        budget=100000.0,
        latitude=17.0,
        longitude=81.7
    )
    asset = Asset(
        name="Broken Light",
        type="light",
        ghat_id=ghat.id,
        status="faulty",
        last_service_date=datetime(2026, 1, 1),
        next_service_date=datetime(2026, 3, 1)
    )
    db_session.add_all([work, asset])
    db_session.commit()

    # Pass 1
    new_alerts_1 = generate_alerts(db_session, current_date=today)
    initial_count = db_session.query(Alert).filter(Alert.status == "open").count()
    assert initial_count > 0

    # Pass 2: should create 0 new alerts
    new_alerts_2 = generate_alerts(db_session, current_date=today)
    assert len(new_alerts_2) == 0
    count_pass_2 = db_session.query(Alert).filter(Alert.status == "open").count()
    assert count_pass_2 == initial_count

    # Pass 3: should still create 0 new alerts
    new_alerts_3 = generate_alerts(db_session, current_date=today)
    assert len(new_alerts_3) == 0
    count_pass_3 = db_session.query(Alert).filter(Alert.status == "open").count()
    assert count_pass_3 == initial_count

# ----------------------------------------------------------------------
# 4. VENDOR SCORE AND RANKING TESTS
# ----------------------------------------------------------------------

def test_vendor_score_formula_and_ranking(db_session):
    """
    Vendor score out of 100:
    50% on_time_pct + 30% quality_rating (scaled to 100, i.e. quality_rating * 20) + 20% (100 - 10 per open alert, min 0)
    """
    ghat = Ghat(name="Test Ghat", latitude=17.0, longitude=81.7)
    db_session.add(ghat)
    db_session.commit()

    # Vendor 1: on_time = 100%, rating = 5.0, 0 open alerts
    # Score: 0.50 * 100 + 0.30 * 100 + 0.20 * 100 = 50 + 30 + 20 = 100.0
    v1 = Vendor(name="Perfect Vendor", contact_person="Leader", on_time_pct=100.0, quality_rating=5.0, staff_deployed=50)

    # Vendor 2: on_time = 80%, rating = 4.0, 2 open alerts linked to works
    # Quality scaled: 4.0 * 20 = 80
    # Alerts component: 100 - 20 = 80
    # Score: 0.50 * 80 + 0.30 * 80 + 0.20 * 80 = 40 + 24 + 16 = 80.0
    v2 = Vendor(name="Good Vendor", contact_person="Manager", on_time_pct=80.0, quality_rating=4.0, staff_deployed=30)

    # Vendor 3: on_time = 60%, rating = 3.0, 12 open alerts (penalty clamped to 0)
    # Quality scaled: 3.0 * 20 = 60
    # Alerts component: max(0, 100 - 120) = 0
    # Score: 0.50 * 60 + 0.30 * 60 + 0.20 * 0 = 30 + 18 + 0 = 48.0
    v3 = Vendor(name="Struggling Vendor", contact_person="Foreman", on_time_pct=60.0, quality_rating=3.0, staff_deployed=20)

    db_session.add_all([v1, v2, v3])
    db_session.commit()

    # Create 2 works and open alerts for Vendor 2
    w_v2_a = Work(title="W1", category="lighting", ghat_id=ghat.id, vendor_id=v2.id, planned_start=datetime.now(), planned_end=datetime.now(), progress_pct=10, status="delayed", budget=50000, latitude=17.0, longitude=81.7)
    w_v2_b = Work(title="W2", category="lighting", ghat_id=ghat.id, vendor_id=v2.id, planned_start=datetime.now(), planned_end=datetime.now(), progress_pct=10, status="delayed", budget=50000, latitude=17.0, longitude=81.7)
    w_v3 = Work(title="W3", category="toilet", ghat_id=ghat.id, vendor_id=v3.id, planned_start=datetime.now(), planned_end=datetime.now(), progress_pct=10, status="delayed", budget=50000, latitude=17.0, longitude=81.7)
    db_session.add_all([w_v2_a, w_v2_b, w_v3])
    db_session.commit()

    alert_1 = Alert(type="Work Delay", severity="high", message="delay", related_work_id=w_v2_a.id, status="open", created_at=datetime.now())
    alert_2 = Alert(type="Work Delay", severity="medium", message="delay", related_work_id=w_v2_b.id, status="open", created_at=datetime.now())
    db_session.add_all([alert_1, alert_2])

    # Add 12 alerts for Vendor 3
    for k in range(12):
        db_session.add(Alert(type="Work Delay", severity="high", message=f"delay {k}", related_work_id=w_v3.id, status="open", created_at=datetime.now()))
    db_session.commit()

    ranking = calculate_vendor_scores_and_ranking(db_session)

    # Check order
    assert len(ranking) == 3
    assert ranking[0]["name"] == "Perfect Vendor"
    assert ranking[0]["rank"] == 1
    assert ranking[0]["score"] == 100.0

    assert ranking[1]["name"] == "Good Vendor"
    assert ranking[1]["rank"] == 2
    assert ranking[1]["score"] == 80.0

    assert ranking[2]["name"] == "Struggling Vendor"
    assert ranking[2]["rank"] == 3
    assert ranking[2]["score"] == 48.0

# ----------------------------------------------------------------------
# 5. SUMMARY FUNCTION TESTS
# ----------------------------------------------------------------------

def test_system_summary(db_session):
    """Verify days left to 26 Jun 2027, counts by status, and budget at risk."""
    fixed_today = date(2026, 11, 6)
    expected_days = (date(2027, 6, 26) - fixed_today).days
    assert expected_days == 232

    ghat = Ghat(name="VIP Ghat", latitude=17.0, longitude=81.7)
    vendor = Vendor(name="V1", contact_person="C1", on_time_pct=90.0, quality_rating=4.5, staff_deployed=10)
    db_session.add_all([ghat, vendor])
    db_session.commit()

    w_completed = Work(title="W1", category="shelter", ghat_id=ghat.id, vendor_id=vendor.id, planned_start=datetime.now(), planned_end=datetime.now(), progress_pct=100, status="completed", budget=100000, latitude=17.0, longitude=81.7)
    w_delayed = Work(title="W2", category="shelter", ghat_id=ghat.id, vendor_id=vendor.id, planned_start=datetime.now(), planned_end=datetime.now(), progress_pct=30, status="delayed", budget=400000, latitude=17.0, longitude=81.7)
    db_session.add_all([w_completed, w_delayed])
    db_session.commit()

    summary = get_system_summary(db_session, current_date=fixed_today)
    assert summary["days_left"] == 232
    assert summary["counts_by_status"]["completed"] == 1
    assert summary["counts_by_status"]["delayed"] == 1
    assert summary["budget"]["total_budget"] == 500000.0
    assert summary["budget"]["delayed_budget"] == 400000.0
    assert summary["budget"]["delayed_budget_pct"] == 80.0

# ----------------------------------------------------------------------
# 6. GUARD REPORT & LOW-LITERACY APP LOGIC TESTS
# ----------------------------------------------------------------------

def test_guard_report_creation(db_session):
    """Test guard reporting maps severity, matches assets/works, and logs alerts."""
    from app.routers.guard import create_guard_report, GuardReportPayload

    ghat = Ghat(name="Pushkar Ghat", latitude=17.0, longitude=81.78)
    vendor = Vendor(name="V1", contact_person="C1", on_time_pct=90.0, quality_rating=4.5, staff_deployed=10)
    db_session.add_all([ghat, vendor])
    db_session.commit()

    asset_toilet = Asset(name="Pushkar Bio-Toilet Block A", type="mobile toilet", ghat_id=ghat.id, status="working")
    work_water = Work(title="Ghat Drinking Water Point", category="water point", ghat_id=ghat.id, vendor_id=vendor.id, planned_start=datetime.now(), planned_end=datetime.now(), progress_pct=50, status="on track", budget=100000, latitude=17.0, longitude=81.78)
    db_session.add_all([asset_toilet, work_water])
    db_session.commit()

    # 1. Toilet report -> High severity, links to Asset
    payload1 = GuardReportPayload(ghat_id=ghat.id, issue_type="toilet", note="Water valve leaking", guard_name="Ramu Guard")
    res1 = create_guard_report(payload1, db_session)
    assert res1["status"] == "success"
    assert res1["severity"] == "high"
    assert res1["ref_no"].startswith("GRD-")

    alert1 = db_session.query(Alert).filter(Alert.id == res1["alert_id"]).first()
    assert alert1 is not None
    assert alert1.severity == "high"
    assert alert1.related_asset_id == asset_toilet.id
    assert "మరుగుదొడ్డి" in alert1.message

    # 2. Water report -> High severity, links to Work
    payload2 = GuardReportPayload(ghat_id=ghat.id, issue_type="water", note="No supply at taps")
    res2 = create_guard_report(payload2, db_session)
    assert res2["severity"] == "high"

    alert2 = db_session.query(Alert).filter(Alert.id == res2["alert_id"]).first()
    assert alert2.related_work_id == work_water.id
    assert "తాగునీరు" in alert2.message

    # 3. Light report -> Medium severity
    payload3 = GuardReportPayload(ghat_id=ghat.id, issue_type="light")
    res3 = create_guard_report(payload3, db_session)
    assert res3["severity"] == "medium"

# ----------------------------------------------------------------------
# 7. PHOTO URL, CLEAN MESSAGE & ENGINEER UPDATES TESTS
# ----------------------------------------------------------------------

def test_alert_photo_url_and_clean_message():
    """Verify photo_url is stored in Alert and clean_message strips [Photo: ...] properly."""
    alert_with_photo_text = Alert(
        type="Guard Report: Toilet",
        severity="high",
        message="మరుగుదొడ్డి పని చేయడం లేదు [Photo: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA] | Note: Door latch broken",
        photo_url="/static/uploads/guard/guard_12345.jpg",
        status="open",
        created_at=datetime.utcnow()
    )
    assert alert_with_photo_text.photo_url == "/static/uploads/guard/guard_12345.jpg"
    assert "[Photo:" not in alert_with_photo_text.clean_message
    assert "మరుగుదొడ్డి పని చేయడం లేదు" in alert_with_photo_text.clean_message
    assert "Door latch broken" in alert_with_photo_text.clean_message

def test_engineer_field_update_creates_log_and_alert(db_session):
    """Verify that field updates to a civil work create both a WorkUpdate and an Alert."""
    from app.routers.works import _process_work_update, WorkUpdatePayload

    ghat = Ghat(name="Kotilingala Ghat", latitude=17.002, longitude=81.778)
    vendor = Vendor(name="Godavari Builders", contact_person="Rao", on_time_pct=85.0, quality_rating=4.2, staff_deployed=20)
    db_session.add_all([ghat, vendor])
    db_session.commit()

    work = Work(
        title="Ghat Steps Granite Cladding",
        category="ghat steps",
        ghat_id=ghat.id,
        vendor_id=vendor.id,
        planned_start=datetime.utcnow() - timedelta(days=20),
        planned_end=datetime.utcnow() + timedelta(days=20),
        progress_pct=40,
        status="on track",
        budget=800000.0,
        latitude=17.002,
        longitude=81.778
    )
    db_session.add(work)
    db_session.commit()

    payload = WorkUpdatePayload(
        progress_pct=55,
        note="Sub-base concrete cured. Commenced granite tile placement.",
        updated_by="Er. Rao (Field QC)",
        photo=None
    )

    _process_work_update(work.id, payload, db_session)

    # Verify WorkUpdate is saved
    update = db_session.query(WorkUpdate).filter(WorkUpdate.work_id == work.id).order_by(WorkUpdate.id.desc()).first()
    assert update is not None
    assert update.progress_pct == 55
    assert "granite tile" in update.note

    # Verify Alert is created for the engineer update
    alert = db_session.query(Alert).filter(Alert.related_work_id == work.id, Alert.type.like("Engineer Update%")).first()
    assert alert is not None
    assert "from 40% to 55%" in alert.message
    assert alert.status == "open"

def test_hub_counts_calculation(db_session):
    """Verify hub counts computation matches expected values."""
    ghat = Ghat(name="Saraswathi Ghat", latitude=17.003, longitude=81.779)
    vendor = Vendor(name="Delta Power", contact_person="Kiran", on_time_pct=72.0, quality_rating=3.8, staff_deployed=12)
    db_session.add_all([ghat, vendor])
    db_session.commit()

    # Add works
    w1 = Work(title="Light 1", category="lighting", ghat_id=ghat.id, vendor_id=vendor.id, planned_start=datetime.now(), planned_end=datetime.now(), progress_pct=100, status="completed", budget=50000, latitude=17.0, longitude=81.7)
    w2 = Work(title="Light 2", category="lighting", ghat_id=ghat.id, vendor_id=vendor.id, planned_start=datetime.now(), planned_end=datetime.now(), progress_pct=20, status="delayed", budget=100000, latitude=17.0, longitude=81.7)
    db_session.add_all([w1, w2])

    # Add assets
    a1 = Asset(name="Floodlight Pole A", type="light", ghat_id=ghat.id, status="working")
    a2 = Asset(name="Genset B", type="generator", ghat_id=ghat.id, status="faulty")
    db_session.add_all([a1, a2])

    # Add guard report
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    gr = Alert(type="Guard Report: Dustbin", severity="medium", message="Dustbin full", status="open", created_at=today_start + timedelta(minutes=10))
    db_session.add(gr)
    db_session.commit()

    # Assert counts logic
    guard_reports_today = db_session.query(Alert).filter(Alert.type.like("Guard Report%"), Alert.created_at >= today_start).count()
    assert guard_reports_today == 1

    delayed_count = db_session.query(Work).filter(Work.status == "delayed").count()
    assert delayed_count == 1

    faulty_count = db_session.query(Asset).filter(Asset.status == "faulty").count()
    assert faulty_count == 1

# ----------------------------------------------------------------------
# 8. DETAIL DRAWER, RESOLVE/REOPEN & HUB KEYS VERIFICATION TESTS
# ----------------------------------------------------------------------

def test_detail_drawer_data_with_null_fields(db_session):
    """Verify detail drawer handles null/undefined fields safely without .split() exceptions."""
    from app.main import get_alert_detail

    # Bare minimal alert with mostly nulls
    bare_alert = Alert(
        type="Incident",
        severity="low",
        message="Bare description without formatting",
        status="open",
        created_at=datetime.utcnow()
    )
    db_session.add(bare_alert)
    db_session.commit()

    detail = get_alert_detail(bare_alert.id, db_session)
    assert detail["id"] == bare_alert.id
    assert detail["clean_title"] is not None
    assert detail["clean_message"] == "Bare description without formatting"
    assert detail["photo_url"] == ""
    assert detail["note"] == ""
    assert detail["assigned_to"] == ""
    assert detail["ghat_name"] is not None
    assert detail["status"] == "open"

def test_alert_resolve_with_photo_and_minutes(db_session):
    """Verify resolving an alert saves resolution note, photo, resolved_at, and computes minutes."""
    from app.main import update_alert_status

    created_time = datetime.utcnow() - timedelta(minutes=24)
    alert = Alert(
        type="Guard Report: Water Leak",
        severity="high",
        message="Water pipe valve ruptured",
        status="open",
        created_at=created_time
    )
    db_session.add(alert)
    db_session.commit()

    resolve_payload = {
        "status": "resolved",
        "resolution_note": "Replaced valve gasket and pressure-tested line.",
        "resolved_by": "Er. Rao (QC Engineer)",
        "resolution_photo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    }

    res = update_alert_status(alert.id, resolve_payload, db_session)
    assert res["status"] == "success"
    assert res["new_status"] == "resolved"
    assert res["resolution_minutes"] >= 23

    db_session.refresh(alert)
    assert alert.status == "resolved"
    assert alert.resolved_at is not None
    assert "valve gasket" in alert.resolution_note
    assert alert.resolution_photo_url.startswith("/static/uploads/resolutions/")

def test_alert_reopen_workflow(db_session):
    """Verify re-opening a resolved alert clears resolution metadata."""
    from app.main import update_alert_status

    alert = Alert(
        type="Guard Report: Broken Light",
        severity="medium",
        message="Floodlight casing broken",
        status="resolved",
        resolved_at=datetime.utcnow(),
        resolution_note="Replaced cover",
        resolution_photo_url="/static/uploads/resolutions/res_test.jpg"
    )
    db_session.add(alert)
    db_session.commit()

    reopen_payload = {"status": "open"}
    res = update_alert_status(alert.id, reopen_payload, db_session)
    assert res["new_status"] == "open"

    db_session.refresh(alert)
    assert alert.status == "open"
    assert alert.resolved_at is None
    assert alert.resolution_photo_url is None
    assert alert.resolution_note is None

def test_hub_counts_all_required_keys_exist(db_session):
    """Verify /api/hub/counts returns all required keys and none are None."""
    from app.main import api_hub_counts

    ghat = Ghat(name="Pushkar Ghat", latitude=17.0, longitude=81.78)
    vendor = Vendor(name="V1", contact_person="C1", on_time_pct=85.0, quality_rating=4.0, staff_deployed=8)
    db_session.add_all([ghat, vendor])
    db_session.commit()

    work = Work(
        title="W1", category="lighting", ghat_id=ghat.id, vendor_id=vendor.id,
        planned_start=datetime.now(), planned_end=datetime.now(),
        progress_pct=30, status="delayed", budget=100000, latitude=17.0, longitude=81.78
    )
    asset = Asset(name="A1", type="light", ghat_id=ghat.id, status="faulty")
    db_session.add_all([work, asset])
    db_session.commit()

    counts = api_hub_counts(db_session)

    required_keys = [
        "guard_reports_today",
        "engineer_updates_today",
        "works_total",
        "works_delayed",
        "delayed_works",
        "assets_total",
        "assets_faulty",
        "faulty_assets",
        "vendors_lowest_score",
        "lowest_vendor_score",
        "alerts_open",
        "open_alerts",
        "days_left",
        "budget_at_risk",
        "budget_at_risk_pct"
    ]

    for key in required_keys:
        assert key in counts, f"Missing key in hub counts: {key}"
        assert counts[key] is not None, f"Value for key {key} is None"

def test_real_time_guard_report_api_flow(db_session):
    """Verify that posting a guard report updates the DB and immediately registers in hub counts."""
    from app.routers.guard import create_guard_report, GuardReportPayload
    from app.main import api_hub_counts

    ghat = Ghat(name="Kotilingala Ghat", latitude=17.002, longitude=81.778)
    db_session.add(ghat)
    db_session.commit()

    initial_counts = api_hub_counts(db_session)
    init_guards = initial_counts["guard_reports_today"]

    payload = GuardReportPayload(
        ghat_id=ghat.id,
        issue_type="toilet",
        note="Water leak in cabin 3",
        guard_name="రాము / Ramu"
    )
    res = create_guard_report(payload, db_session)
    assert res["status"] == "success"

    new_counts = api_hub_counts(db_session)
    assert new_counts["guard_reports_today"] >= init_guards



