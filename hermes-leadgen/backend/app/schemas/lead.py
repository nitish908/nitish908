from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class LeadCreate(BaseModel):
    company_name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    public_email: Optional[str] = None
    contact_page_url: Optional[str] = None
    estimated_company_size: Optional[str] = None
    source_name: str = "manual_entry"
    source_url: Optional[str] = None


class LeadUpdate(BaseModel):
    stage: Optional[str] = None
    owner_id: Optional[UUID] = None
    next_follow_up_at: Optional[date] = None
    is_suppressed: Optional[bool] = None
    is_unsubscribed: Optional[bool] = None
    outreach_angle: Optional[str] = None
    best_service_package: Optional[str] = None


class LeadOut(BaseModel):
    id: UUID
    company_name: str
    website: Optional[str]
    industry: Optional[str]
    country: Optional[str]
    city: Optional[str]
    description: Optional[str]
    public_email: Optional[str]
    contact_page_url: Optional[str]
    estimated_company_size: Optional[str]
    source_name: Optional[str]
    source_url: Optional[str]
    discovered_at: datetime
    score: int
    score_explanation: Optional[str]
    tier: Optional[str]
    outreach_angle: Optional[str]
    best_service_package: Optional[str]
    stage: str
    owner_id: Optional[UUID]
    last_contacted_at: Optional[datetime]
    next_follow_up_at: Optional[date]
    consent_status: str
    is_suppressed: bool
    is_unsubscribed: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadNoteCreate(BaseModel):
    body: str


class LeadTaskCreate(BaseModel):
    title: str
    due_date: Optional[date] = None
