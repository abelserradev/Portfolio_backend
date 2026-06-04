"""Estados públicos del catálogo de proyectos del portfolio."""

from enum import StrEnum


class ProjectStatus(StrEnum):
    LIVE = "live"
    MVP_ACTIVE = "mvp_active"
    IN_DEVELOPMENT = "in_development"
    COMING_SOON = "coming_soon"
