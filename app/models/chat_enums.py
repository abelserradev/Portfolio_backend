from enum import StrEnum


class ChatFlowState(StrEnum):
    GREETING = "greeting"
    DISCOVERY = "discovery"
    SCOPE = "scope"
    ESTIMATE = "estimate"
    CONTACT = "contact"
    SUBMITTED = "submitted"


class PreferredChannel(StrEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"


class QuoteLeadStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    NOTIFIED = "notified"
