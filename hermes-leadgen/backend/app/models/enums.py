import enum


class UserRole(str, enum.Enum):
    OWNER = "owner"
    VIEWER = "viewer"


class LeadStage(str, enum.Enum):
    DISCOVERED = "discovered"
    RESEARCHING = "researching"
    QUALIFIED = "qualified"
    DRAFT_READY = "draft_ready"
    APPROVED = "approved"
    CONTACTED = "contacted"
    REPLIED = "replied"
    DEMO_BOOKED = "demo_booked"
    PROPOSAL_SENT = "proposal_sent"
    WON = "won"
    LOST = "lost"
    DO_NOT_CONTACT = "do_not_contact"


class LeadTier(str, enum.Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class SourceType(str, enum.Enum):
    CSV_UPLOAD = "csv_upload"
    MANUAL_ENTRY = "manual_entry"
    COMPANY_WEBSITE = "company_website"
    GOOGLE_PLACES = "google_places"
    PRODUCT_HUNT = "product_hunt"
    GITHUB_ORG = "github_org"
    BUSINESS_DIRECTORY = "business_directory"


class MessageType(str, enum.Enum):
    INITIAL_EMAIL = "initial_email"
    CONTACT_FORM = "contact_form"
    LINKEDIN_DRAFT = "linkedin_draft"
    FOLLOW_UP_1 = "follow_up_1"
    FOLLOW_UP_2 = "follow_up_2"
    FINAL_FOLLOW_UP = "final_follow_up"


class MessageChannel(str, enum.Enum):
    EMAIL = "email"
    CONTACT_FORM = "contact_form"
    LINKEDIN_MANUAL = "linkedin_manual"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELED = "canceled"


class ResearchConfidence(str, enum.Enum):
    VERIFIED = "verified"
    ASSUMPTION = "assumption"


class TaskStatus(str, enum.Enum):
    OPEN = "open"
    DONE = "done"
