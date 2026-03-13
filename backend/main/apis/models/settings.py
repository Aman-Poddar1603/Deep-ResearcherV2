from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Theme(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class ColorScheme(str, Enum):
    DEFAULT = ("default",)
    COFFEE = ("coffee",)
    FRESH = ("fresh",)
    NERD = ("nerd",)
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


class userInfo(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )
    email: str = Field(
        ...,
        min_length=5,
        max_length=100,
    )
    bio: str = Field(
        ...,
        min_length=10,
        max_length=500,
    )
    avatar: str = Field(
        ...,
        min_length=10,
        max_length=500,
    )


class AppAppearance(BaseModel):
    theme: Theme = Field(
        Theme.SYSTEM,
        description="The theme to use for the app",
    )
    color_scheme: ColorScheme = Field(
        ColorScheme.DEFAULT,
        description="The color scheme to use for the app",
    )


class ResearchSettings(BaseModel):
    auto_save: bool = Field(
        True,
        description="Whether to automatica lly save research results",
    )
    max_search_depth: int = Field(
        3,
        description="The maximum search depth for research",
    )
    default_report_fmt: ReportFormat = Field(
        ReportFormat.MD,
        description="The default report format for research results",
    )


class AgentSettings(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )
    personality: str = Field(
        ...,
        min_length=10,
        max_length=500,
    )
    custom_template: str = Field(
        ...,
        min_length=10,
        max_length=500,
    )
    research_template: ResearchTemplates = Field(
        ResearchTemplates.QUICKSUMMARY,
        description="The research template to use for the agent",
    )
    stream_responses: bool = Field(
        False,
        description="Whether to stream responses in real-time from the agent",
    )
    show_src_citations: bool = Field(
        False,
        description="Whether to show source citations in the agent's responses",
    )


class Notifications(BaseModel):
    on_research_complete: bool = Field(
        False,
        description="Whether to send a notification when research is complete",
    )
    error_alerts: bool = Field(
        False,
        description="Whether to send a notification for errors",
    )
    sound_effects: bool = Field(
        False,
        description="Whether to play sound effects for notifications",
    )


class DataAndStorage(BaseModel):
    data_retention: int = Field(
        -1,  # -1: forever, int(1-1000): days
        description="The number of days to retain data",
    )


class Settings(
    userInfo,
    AppAppearance,
    ResearchSettings,
    AgentSettings,
    Notifications,
    DataAndStorage,
):
    delete_all_data: bool = Field(
        False,
        description="Whether to delete all data when the user logs out",
    )

    delete_all_buckets: bool = Field(
        False,
        description="Whether to delete all buckets when the user logs out",
    )

    reset_application: bool = Field(
        False,
        description="Whether to reset the application to its default state when the user logs out",
    )

    last_update: datetime = Field(
        ...,
        description="The last time the user updated their settings",
    )
