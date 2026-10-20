"""
UI package for jz CLI: Textual application, Header, Dashboard, and Prompt widgets.
"""

from jz_cli.ui.app import JZApp
from jz_cli.ui.dashboard import (
    CanvasDueDatesWidget,
    ConfigWizardWidget,
    ExpandedCanvasWidget,
    HelpWidget,
    SplitDashboardWidget,
    StudyPlannerWidget,
    TodayAgendaWidget,
    WeekCalendarWidget,
)
from jz_cli.ui.header import HeaderView, JZLogo, NoticeBanner, SessionMetadata
from jz_cli.ui.prompt_input import FooterStatusBar, PromptBox

__all__ = [
    "JZApp",
    "HeaderView",
    "JZLogo",
    "NoticeBanner",
    "SessionMetadata",
    "TodayAgendaWidget",
    "CanvasDueDatesWidget",
    "SplitDashboardWidget",
    "ExpandedCanvasWidget",
    "WeekCalendarWidget",
    "StudyPlannerWidget",
    "ConfigWizardWidget",
    "HelpWidget",
    "PromptBox",
    "FooterStatusBar",
]
