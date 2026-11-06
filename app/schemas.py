from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# Ghat Schemas
class GhatBase(BaseModel):
    name: str
    latitude: float
    longitude: float

class GhatCreate(GhatBase):
    pass

class GhatResponse(GhatBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Vendor Schemas
class VendorBase(BaseModel):
    name: str
    contact_person: str
    on_time_pct: float
    quality_rating: float
    staff_deployed: int

class VendorCreate(VendorBase):
    pass

class VendorResponse(VendorBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# Work Update Schemas
class WorkUpdateBase(BaseModel):
    work_id: int
    progress_pct: int
    note: str
    photo_url: Optional[str] = None
    updated_by: str

class WorkUpdateCreate(BaseModel):
    progress_pct: int
    note: str
    photo_url: Optional[str] = None
    updated_by: str

class WorkUpdateResponse(WorkUpdateBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Work Schemas
class WorkBase(BaseModel):
    title: str
    category: str
    ghat_id: int
    vendor_id: int
    planned_start: datetime
    planned_end: datetime
    progress_pct: int
    status: str
    budget: float
    latitude: float
    longitude: float

class WorkCreate(WorkBase):
    pass

class WorkResponse(WorkBase):
    id: int
    last_updated: datetime
    ghat: Optional[GhatResponse] = None
    vendor: Optional[VendorResponse] = None
    model_config = ConfigDict(from_attributes=True)

# Asset Schemas
class AssetBase(BaseModel):
    name: str
    type: str
    ghat_id: int
    status: str
    last_service_date: Optional[datetime] = None
    next_service_date: Optional[datetime] = None

class AssetCreate(AssetBase):
    pass

class AssetResponse(AssetBase):
    id: int
    ghat: Optional[GhatResponse] = None
    model_config = ConfigDict(from_attributes=True)

# Alert Schemas
class AlertBase(BaseModel):
    type: str
    severity: str
    message: str
    related_work_id: Optional[int] = None
    related_asset_id: Optional[int] = None
    status: str

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

