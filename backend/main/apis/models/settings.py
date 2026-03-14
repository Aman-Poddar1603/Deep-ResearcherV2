from enum import Enum

from pydantic import BaseModel, Field


class Theme(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class ColorScheme(str, Enum):
    DEFAULT = "default"
    COFFEE = "coffee"
    FRESH = "fresh"
    NERD = "nerd"
    SMOOTH = "smooth"


class ReportFormat(str, Enum):
    MD = "md"
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"


class ResearchTemplates(str, Enum):
    COMPREHENSIVE = "comprehensive"
    QUICKSUMMARY = "quick_summary"
    ACADEMIC = "academic"
    MARKET_ANALYSIS = "market_analysis"
    TECHNICAL_INSIGHT = "technical_insights"
    COMPARATIVE_STUDY = "comparative_study"
    VACATION_PLANNER = "vacation_planner"


class SettingsRecord(BaseModel):
    """Represents `settings` table row shape from migrations.py."""

    user_name: str | None = None
    user_email: str | None = None
    user_bio: str | None = None
    theme: Theme | str | None = Theme.SYSTEM
    color_mode: ColorScheme | str | None = ColorScheme.DEFAULT
    max_depth_search: int | None = None
    default_report_fmt: ReportFormat | str | None = ReportFormat.MD
    default_research_template: ResearchTemplates | str | None = (
        ResearchTemplates.QUICKSUMMARY
    )
    default_bucket: str | None = None
    notification_on_complete_research: bool = True
    show_error_on_alerts: bool = True
    sound_effect: bool = True
    default_model: str | None = None
    ai_name: str | None = None
    ai_personality: str | None = None
    ai_custom_prompt: str | None = None
    stream_response: bool = True
    show_citations: bool = True
    thinking_in_chats: bool = True
    keep_backup: bool = True
    temperory_data_retention: int = Field(default=30, ge=0)


class SettingsPatch(BaseModel):
    user_name: str | None = None
    user_email: str | None = None
    user_bio: str | None = None
    theme: Theme | str | None = None
    color_mode: ColorScheme | str | None = None
    max_depth_search: int | None = None
    default_report_fmt: ReportFormat | str | None = None
    default_research_template: ResearchTemplates | str | None = None
    default_bucket: str | None = None
    notification_on_complete_research: bool | None = None
    show_error_on_alerts: bool | None = None
    sound_effect: bool | None = None
    default_model: str | None = None
    ai_name: str | None = None
    ai_personality: str | None = None
    ai_custom_prompt: str | None = None
    stream_response: bool | None = None
    show_citations: bool | None = None
    thinking_in_chats: bool | None = None
    keep_backup: bool | None = None
    temperory_data_retention: int | None = Field(default=None, ge=0)


# Backward-compatible name kept for existing imports.
class Settings(SettingsRecord):
    pass
