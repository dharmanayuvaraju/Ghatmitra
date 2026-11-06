from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Ghat(Base):
    __tablename__ = "ghats"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    works = relationship("Work", back_populates="ghat", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="ghat", cascade="all, delete-orphan")

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    contact_person = Column(String(120), nullable=False)
    on_time_pct = Column(Float, default=90.0)
    quality_rating = Column(Float, default=4.5)
    staff_deployed = Column(Integer, default=10)

    works = relationship("Work", back_populates="vendor")

class Work(Base):
    __tablename__ = "works"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(60), nullable=False)  # ghat steps/toilet/lighting/barricade/parking/shelter/water point
    ghat_id = Column(Integer, ForeignKey("ghats.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    planned_start = Column(DateTime, nullable=False)
    planned_end = Column(DateTime, nullable=False)
    progress_pct = Column(Integer, default=0)
    status = Column(String(30), default="not started")  # not started/on track/delayed/completed
    budget = Column(Float, default=0.0)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ghat = relationship("Ghat", back_populates="works")
    vendor = relationship("Vendor", back_populates="works")
    updates = relationship("WorkUpdate", back_populates="work", cascade="all, delete-orphan", order_by="desc(WorkUpdate.created_at)")
    alerts = relationship("Alert", back_populates="related_work")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    type = Column(String(60), nullable=False)  # mobile toilet/bin/light/CCTV/generator
    ghat_id = Column(Integer, ForeignKey("ghats.id"), nullable=False)
    status = Column(String(30), default="working")  # working/faulty/under maintenance
    last_service_date = Column(DateTime, nullable=True)
    next_service_date = Column(DateTime, nullable=True)

    ghat = relationship("Ghat", back_populates="assets")
    alerts = relationship("Alert", back_populates="related_asset")

class WorkUpdate(Base):
    __tablename__ = "work_updates"

    id = Column(Integer, primary_key=True, index=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=False)
    progress_pct = Column(Integer, nullable=False)
    note = Column(Text, nullable=False)
    photo_url = Column(String(255), nullable=True)
    updated_by = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    work = relationship("Work", back_populates="updates")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(60), nullable=False)
    severity = Column(String(20), nullable=False)  # high/medium/low
    message = Column(Text, nullable=False)
    photo_url = Column(String(255), nullable=True)
    related_work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    related_asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    status = Column(String(20), default="open")  # open/in_progress/resolved
    created_at = Column(DateTime, default=datetime.utcnow)

    # Clean structured fields
    guard_name = Column(String(100), nullable=True)
    issue_type = Column(String(60), nullable=True)
    ghat_name = Column(String(120), nullable=True)
    note = Column(Text, nullable=True)

    # Workflow & Resolution Tracking
    assigned_to = Column(String(100), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    in_progress_at = Column(DateTime, nullable=True)
    resolution_photo_url = Column(String(255), nullable=True)
    resolution_note = Column(Text, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    related_work = relationship("Work", back_populates="alerts")
    related_asset = relationship("Asset", back_populates="alerts")

    @property
    def clean_title(self):
        """Returns clean title like '🚽 Toilet not working' or work/asset alert title."""
        ISSUE_TITLE_MAP = {
            "toilet": "🚽 Toilet not working",
            "water": "🚰 No drinking water",
            "barrier": "⚠️ Barrier or steps broken",
            "light": "💡 Light not working",
            "bin": "🗑️ Dustbin full",
            "work_delayed": "⏳ Work stopped or delayed",
            "other": "❓ Field Issue Reported"
        }
        if self.issue_type and self.issue_type in ISSUE_TITLE_MAP:
            return ISSUE_TITLE_MAP[self.issue_type]
        
        if self.type:
            clean_t = self.type.replace("Guard Report:", "").strip()
            low = clean_t.lower()
            if "toilet" in low: return f"🚽 {clean_t}"
            if "water" in low: return f"🚰 {clean_t}"
            if "light" in low: return f"💡 {clean_t}"
            if "bin" in low or "dustbin" in low: return f"🗑️ {clean_t}"
            if "step" in low or "barrier" in low or "barricade" in low: return f"⚠️ {clean_t}"
            if "work" in low or "delay" in low: return f"🔨 {clean_t}"
            return clean_t
        return "General Incident"

    @property
    def clean_message(self):
        import re
        if not self.message:
            return ""
        txt = self.message
        # Strip [Photo: ...]
        txt = re.sub(r'\[Photo:\s*[^\]]+\]', '', txt)
        # Strip guard prefix e.g. [రాము / Ramu]: or [Guard Name]:
        txt = re.sub(r'^\s*\[[^\]]+\]\s*:\s*', '', txt)
        return txt.strip().rstrip('|').strip()

    @property
    def clean_guard(self):
        if self.guard_name:
            if '/' in self.guard_name:
                return self.guard_name.split('/')[1].strip()
            return self.guard_name
        import re
        m = re.search(r'\[([^\]]+)\]', self.message or "")
        if m:
            raw = m.group(1)
            if '/' in raw:
                return raw.split('/')[1].strip()
            return raw
        return "Patrol Guard"

    @property
    def clean_ghat(self):
        if self.ghat_name:
            return self.ghat_name
        if self.related_work and self.related_work.ghat:
            return self.related_work.ghat.name
        if self.related_asset and self.related_asset.ghat:
            return self.related_asset.ghat.name
        if self.message and " at " in self.message:
            parts = self.message.split(" at ")
            if len(parts) > 1:
                return parts[1].split(" | ")[0].strip()
        return "Pushkar Ghat"

    @property
    def resolution_minutes(self):
        if self.created_at and self.resolved_at:
            delta = self.resolved_at - self.created_at
            mins = max(1, int(delta.total_seconds() / 60))
            return mins
        return None

