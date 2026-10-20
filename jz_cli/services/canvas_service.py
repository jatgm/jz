"""
Canvas LMS REST API client supporting personal access tokens,
course enrollment queries, upcoming assignments, countdowns, and demo fallback.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dateutil import parser as date_parser

from jz_cli.config import AppConfig


@dataclass
class CanvasCourse:
    id: int
    name: str
    course_code: str
    enrollment_term_id: Optional[int] = None
    color: str = "cyan"


@dataclass
class CanvasAssignment:
    id: int
    course_id: int
    course_code: str
    name: str
    due_at: Optional[datetime.datetime]
    points_possible: float = 0.0
    submission_types: List[str] = field(default_factory=list)
    has_submitted: bool = False
    html_url: str = ""

    def get_due_countdown(self, now: Optional[datetime.datetime] = None) -> Tuple[str, str]:
        """
        Returns (countdown_text, style_class_or_color)
        e.g.:
          - 'Due tonight at 11:59 PM', 'bold red'
          - 'Due tomorrow at 5:00 PM', 'bold yellow'
          - 'Due in 3 days', 'cyan'
          - '[OVERDUE]', 'bold red reverse'
          - 'No due date', 'dim'
        """
        if not self.due_at:
            return ("No due date", "dim")

        if now is None:
            now = datetime.datetime.now(self.due_at.tzinfo or datetime.timezone.utc)

        # Standardize timezone awareness
        if self.due_at.tzinfo is not None and now.tzinfo is None:
            now = now.astimezone(self.due_at.tzinfo)
        elif self.due_at.tzinfo is None and now.tzinfo is not None:
            self.due_at = self.due_at.replace(tzinfo=now.tzinfo)

        if now > self.due_at:
            diff_overdue = now - self.due_at
            hours = int(diff_overdue.total_seconds() // 3600)
            if hours < 24:
                return (f"[OVERDUE ({hours}h ago)]", "bold red")
            days = int(hours // 24)
            return (f"[OVERDUE ({days}d ago)]", "bold red")

        diff = self.due_at - now
        total_seconds = diff.total_seconds()
        hours = total_seconds / 3600.0
        days = total_seconds / 86400.0

        due_time_str = self.due_at.strftime("%I:%M %p")
        if self.due_at.date() == now.date():
            if total_seconds < 7200:  # < 2 hours
                mins = int(total_seconds // 60)
                return (f"Due in {mins}m ({due_time_str})", "bold red blink")
            return (f"Due tonight at {due_time_str}", "bold yellow")
        elif self.due_at.date() == (now + datetime.timedelta(days=1)).date():
            return (f"Due tomorrow at {due_time_str}", "yellow")
        elif days < 7:
            day_name = self.due_at.strftime("%a")
            return (f"Due {day_name} ({int(days)}d left)", "cyan")
        else:
            return (f"Due in {int(days)} days ({self.due_at.strftime('%b %d')})", "blue")


class CanvasService:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config
        self._courses_cache: List[CanvasCourse] = []
        self._assignments_cache: List[CanvasAssignment] = []

    @property
    def is_configured(self) -> bool:
        return bool(
            self.config
            and self.config.canvas_url
            and self.config.canvas_token
            and not self.config.demo_mode
        )

    def _get_headers(self) -> Dict[str, str]:
        token = self.config.canvas_token if self.config else ""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    def _normalize_url(self, raw_url: str) -> str:
        url = raw_url.strip().rstrip("/")
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        return url

    def test_connection(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Test authentication token and API endpoint with Canvas LMS."""
        if not self.config or not self.config.canvas_url or not self.config.canvas_token:
            return False, "Canvas URL or API token missing", {}

        base_url = self._normalize_url(self.config.canvas_url)
        endpoint = f"{base_url}/api/v1/users/self/profile"

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(endpoint, headers=self._get_headers())
                if resp.status_code == 200:
                    profile = resp.json()
                    name = profile.get("name", "Student")
                    email = profile.get("primary_email", profile.get("login_id", ""))
                    return True, f"Connected to Canvas as {name} ({email})", profile
                elif resp.status_code == 401:
                    return False, "Authentication failed: Invalid personal access token.", {}
                else:
                    return False, f"Canvas API returned status {resp.status_code}: {resp.text[:100]}", {}
        except Exception as e:
            return False, f"Network connection error: {e}", {}

    def get_courses(self) -> List[CanvasCourse]:
        """Fetch list of active enrolled courses."""
        if not self.is_configured:
            return self._get_demo_courses()

        base_url = self._normalize_url(self.config.canvas_url)
        endpoint = f"{base_url}/api/v1/courses"
        params = {"enrollment_state": "active", "per_page": 50}

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(endpoint, headers=self._get_headers(), params=params)
                if resp.status_code == 200:
                    courses_raw = resp.json()
                    courses = []
                    for c in courses_raw:
                        # Skip courses without course_code or access restricted
                        code = c.get("course_code") or c.get("name", "Course")
                        name = c.get("name", code)
                        cid = c.get("id")
                        if cid and code:
                            courses.append(CanvasCourse(id=cid, name=name, course_code=code))
                    self._courses_cache = courses
                    return courses
        except Exception:
            pass

        return self._get_demo_courses()

    def get_upcoming_assignments(self) -> List[CanvasAssignment]:
        """Fetch upcoming assignments across enrolled courses, sorted by due date."""
        if not self.is_configured:
            return self._get_demo_assignments()

        courses = self.get_courses()
        base_url = self._normalize_url(self.config.canvas_url)
        all_assignments: List[CanvasAssignment] = []

        now = datetime.datetime.now().astimezone()

        try:
            with httpx.Client(timeout=15.0) as client:
                for course in courses:
                    endpoint = f"{base_url}/api/v1/courses/{course.id}/assignments"
                    params = {
                        "bucket": "upcoming",
                        "order_by": "due_at",
                        "per_page": 20,
                    }
                    resp = client.get(endpoint, headers=self._get_headers(), params=params)
                    if resp.status_code == 200:
                        assignments_raw = resp.json()
                        for item in assignments_raw:
                            due_raw = item.get("due_at")
                            due_dt = date_parser.parse(due_raw) if due_raw else None
                            has_sub = bool(item.get("has_submitted_submissions", False))
                            all_assignments.append(
                                CanvasAssignment(
                                    id=item.get("id", 0),
                                    course_id=course.id,
                                    course_code=course.course_code,
                                    name=item.get("name", "Assignment"),
                                    due_at=due_dt,
                                    points_possible=float(item.get("points_possible") or 0.0),
                                    submission_types=item.get("submission_types", []),
                                    has_submitted=has_sub,
                                    html_url=item.get("html_url", ""),
                                )
                            )

            if all_assignments:
                # Sort: None due_at at the end, then ascending
                all_assignments.sort(key=lambda a: a.due_at or datetime.datetime.max.astimezone())
                self._assignments_cache = all_assignments
                return all_assignments
        except Exception:
            pass

        return self._get_demo_assignments()

    def get_today_deadlines(self) -> List[CanvasAssignment]:
        """Return assignments due today."""
        assignments = self.get_upcoming_assignments()
        now = datetime.datetime.now().astimezone()
        return [
            a for a in assignments
            if a.due_at and a.due_at.date() == now.date()
        ]

    def _get_demo_courses(self) -> List[CanvasCourse]:
        return [
            CanvasCourse(id=101, name="Data Structures & Algorithms", course_code="CS 2110"),
            CanvasCourse(id=102, name="Linear Algebra", course_code="MATH 3010"),
            CanvasCourse(id=103, name="Introductory Physics II", course_code="PHYS 2211"),
            CanvasCourse(id=104, name="Database Systems Design", course_code="CS 4400"),
        ]

    def _get_demo_assignments(self) -> List[CanvasAssignment]:
        now = datetime.datetime.now().astimezone()
        today = now.date()
        tz = now.tzinfo

        return [
            CanvasAssignment(
                id=1,
                course_id=101,
                course_code="CS 2110",
                name="HW 4: Dynamic Memory Allocator (malloc/free)",
                due_at=datetime.datetime.combine(today, datetime.time(23, 59), tzinfo=tz),
                points_possible=100.0,
                submission_types=["online_upload"],
            ),
            CanvasAssignment(
                id=2,
                course_id=102,
                course_code="MATH 3010",
                name="Problem Set 5: Eigenvalues & Diagonalization",
                due_at=datetime.datetime.combine(today + datetime.timedelta(days=1), datetime.time(17, 0), tzinfo=tz),
                points_possible=50.0,
                submission_types=["online_upload"],
            ),
            CanvasAssignment(
                id=3,
                course_id=101,
                course_code="CS 2110",
                name="Timed Lab 3: LC-3 Assembly Subroutines",
                due_at=datetime.datetime.combine(today + datetime.timedelta(days=2), datetime.time(20, 0), tzinfo=tz),
                points_possible=75.0,
                submission_types=["online_quiz"],
            ),
            CanvasAssignment(
                id=4,
                course_id=103,
                course_code="PHYS 2211",
                name="WebAssign 06: Biot-Savart & Ampere's Law",
                due_at=datetime.datetime.combine(today + datetime.timedelta(days=3), datetime.time(23, 59), tzinfo=tz),
                points_possible=40.0,
                submission_types=["external_tool"],
            ),
            CanvasAssignment(
                id=5,
                course_id=104,
                course_code="CS 4400",
                name="Phase 2: Relational Schema & 3NF Normalization",
                due_at=datetime.datetime.combine(today + datetime.timedelta(days=5), datetime.time(23, 59), tzinfo=tz),
                points_possible=150.0,
                submission_types=["online_upload"],
            ),
        ]
