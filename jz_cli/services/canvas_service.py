"""
Canvas LMS service supporting personal access tokens, iCal feeds,
course enrollment queries, upcoming assignments, and caching.
"""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dateutil import parser as date_parser

from jz_cli.config import AppConfig, get_base_dir


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
        if not self.due_at:
            return ("No due date", "dim")

        if now is None:
            now = datetime.datetime.now(self.due_at.tzinfo or datetime.timezone.utc)

        if self.due_at.tzinfo is not None and now.tzinfo is None:
            now = now.astimezone(self.due_at.tzinfo)
        elif self.due_at.tzinfo is None and now.tzinfo is not None:
            self.due_at = self.due_at.replace(tzinfo=now.tzinfo)

        if now > self.due_at:
            diff_overdue = now - self.due_at
            hours = int(diff_overdue.total_seconds() // 3600)
            if hours < 24:
                return (f"[OVERDUE {hours}h ago]", "bold red")
            days = int(hours // 24)
            return (f"[OVERDUE {days}d ago]", "bold red")

        diff = self.due_at - now
        total_seconds = diff.total_seconds()
        days = total_seconds / 86400.0

        due_time_str = self.due_at.strftime("%I:%M %p")
        if self.due_at.date() == now.date():
            if total_seconds < 7200:
                mins = int(total_seconds // 60)
                return (f"Due in {mins}m ({due_time_str})", "bold red")
            return (f"Due tonight at {due_time_str}", "bold yellow")
        elif self.due_at.date() == (now + datetime.timedelta(days=1)).date():
            return (f"Due tomorrow at {due_time_str}", "yellow")
        elif days < 7:
            day_name = self.due_at.strftime("%a")
            return (f"Due {day_name} ({int(days)}d left)", "cyan")
        else:
            return (f"Due {self.due_at.strftime('%b %d')}", "blue")


def parse_ics_canvas_feed(ics_text: str) -> List[CanvasAssignment]:
    """Parse Canvas iCal calendar feed into CanvasAssignment objects."""
    unfolded = re.sub(r"\r?\n[ \t]", "", ics_text)
    assignments: List[CanvasAssignment] = []
    vevent_matches = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", unfolded, re.DOTALL)

    for i, block in enumerate(vevent_matches):
        props: dict[str, str] = {}
        for line in block.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k_norm = k.split(";")[0].strip().upper()
                props[k_norm] = v.strip()

        summary = props.get("SUMMARY", "Assignment")
        url = props.get("URL", "")
        dtend_raw = props.get("DTEND") or props.get("DTSTART")
        if not dtend_raw:
            continue

        try:
            due_dt = date_parser.parse(dtend_raw)
            if due_dt.tzinfo is None:
                due_dt = due_dt.astimezone()
        except Exception:
            continue

        # Extract course code from summary e.g. "Assignment Title [CS 2110]"
        course_code = "Canvas"
        match = re.search(r"\[([A-Z0-9\s\-]+)\]$", summary)
        clean_name = summary
        if match:
            course_code = match.group(1).strip()
            clean_name = summary[: match.start()].strip()

        assignments.append(
            CanvasAssignment(
                id=i + 1,
                course_id=1,
                course_code=course_code,
                name=clean_name,
                due_at=due_dt,
                points_possible=100.0,
                html_url=url,
            )
        )

    assignments.sort(key=lambda a: a.due_at or datetime.datetime.max.astimezone())
    return assignments


class CanvasService:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config
        self._cache_path = get_base_dir() / "cache_canvas.json"

    @property
    def is_configured(self) -> bool:
        if not self.config:
            return False
        has_api = bool(self.config.canvas_url and self.config.canvas_token)
        has_feed = bool(self.config.canvas_ical_url)
        return has_api or has_feed

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
        if not self.config:
            return False, "Configuration not initialized", {}

        # 1. Test iCal feed if set
        if self.config.canvas_ical_url:
            try:
                with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                    resp = client.get(self.config.canvas_ical_url)
                    if resp.status_code == 200 and "BEGIN:VCALENDAR" in resp.text:
                        assigns = parse_ics_canvas_feed(resp.text)
                        return True, f"Connected to Canvas iCal feed ({len(assigns)} events found)", {}
            except Exception as e:
                return False, f"Canvas iCal feed error: {e}", {}

        # 2. Test REST API
        if not self.config.canvas_url or not self.config.canvas_token:
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
                    return False, f"Canvas API status {resp.status_code}", {}
        except Exception as e:
            return False, f"Network error: {e}", {}

    def get_courses(self) -> List[CanvasCourse]:
        if self.config and self.config.demo_mode:
            return self._get_demo_courses()

        if not self.is_configured:
            return []

        if not (self.config and self.config.canvas_url and self.config.canvas_token):
            return []

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
                        code = c.get("course_code") or c.get("name", "Course")
                        name = c.get("name", code)
                        cid = c.get("id")
                        if cid and code:
                            courses.append(CanvasCourse(id=cid, name=name, course_code=code))
                    return courses
        except Exception:
            pass
        return []

    def get_upcoming_assignments(self) -> List[CanvasAssignment]:
        if self.config and self.config.demo_mode:
            return self._get_demo_assignments()

        if not self.is_configured:
            return []

        # 1. Fetch from iCal feed
        if self.config and self.config.canvas_ical_url:
            try:
                with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                    resp = client.get(self.config.canvas_ical_url)
                    if resp.status_code == 200:
                        assigns = parse_ics_canvas_feed(resp.text)
                        self._save_cache(assigns)
                        return assigns
            except Exception:
                return self._load_cache()

        # 2. Fetch from REST API
        if not (self.config and self.config.canvas_url and self.config.canvas_token):
            return []

        courses = self.get_courses()
        base_url = self._normalize_url(self.config.canvas_url)
        all_assignments: List[CanvasAssignment] = []

        try:
            with httpx.Client(timeout=15.0) as client:
                for course in courses:
                    endpoint = f"{base_url}/api/v1/courses/{course.id}/assignments"
                    params = {"bucket": "upcoming", "order_by": "due_at", "per_page": 20}
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
                all_assignments.sort(key=lambda a: a.due_at or datetime.datetime.max.astimezone())
                self._save_cache(all_assignments)
                return all_assignments
        except Exception:
            return self._load_cache()

        return []

    def get_today_deadlines(self) -> List[CanvasAssignment]:
        assignments = self.get_upcoming_assignments()
        now = datetime.datetime.now().astimezone()
        return [a for a in assignments if a.due_at and a.due_at.date() == now.date()]

    def _save_cache(self, assigns: List[CanvasAssignment]) -> None:
        try:
            data = [
                {
                    "id": a.id,
                    "course_id": a.course_id,
                    "course_code": a.course_code,
                    "name": a.name,
                    "due_at": a.due_at.isoformat() if a.due_at else None,
                    "points": a.points_possible,
                    "submitted": a.has_submitted,
                    "url": a.html_url,
                }
                for a in assigns
            ]
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_cache(self) -> List[CanvasAssignment]:
        if not self._cache_path.exists():
            return []
        try:
            with open(self._cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [
                CanvasAssignment(
                    id=d["id"],
                    course_id=d["course_id"],
                    course_code=d["course_code"],
                    name=d["name"],
                    due_at=date_parser.parse(d["due_at"]) if d["due_at"] else None,
                    points_possible=d.get("points", 0.0),
                    has_submitted=d.get("submitted", False),
                    html_url=d.get("url", ""),
                )
                for d in data
            ]
        except Exception:
            return []

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
                name="HW 4: Dynamic Memory Allocator",
                due_at=datetime.datetime.combine(today, datetime.time(23, 59), tzinfo=tz),
                points_possible=100.0,
            ),
            CanvasAssignment(
                id=2,
                course_id=102,
                course_code="MATH 3010",
                name="Problem Set 5: Eigenvalues",
                due_at=datetime.datetime.combine(today + datetime.timedelta(days=1), datetime.time(17, 0), tzinfo=tz),
                points_possible=50.0,
            ),
            CanvasAssignment(
                id=3,
                course_id=101,
                course_code="CS 2110",
                name="Timed Lab 3: LC-3 Assembly",
                due_at=datetime.datetime.combine(today + datetime.timedelta(days=2), datetime.time(20, 0), tzinfo=tz),
                points_possible=75.0,
            ),
            CanvasAssignment(
                id=4,
                course_id=103,
                course_code="PHYS 2211",
                name="WebAssign 06: Biot-Savart Law",
                due_at=datetime.datetime.combine(today + datetime.timedelta(days=3), datetime.time(23, 59), tzinfo=tz),
                points_possible=40.0,
            ),
            CanvasAssignment(
                id=5,
                course_id=104,
                course_code="CS 4400",
                name="Phase 2: Relational Schema & 3NF",
                due_at=datetime.datetime.combine(today + datetime.timedelta(days=5), datetime.time(23, 59), tzinfo=tz),
                points_possible=150.0,
            ),
        ]
