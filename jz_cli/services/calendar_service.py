"""
Google Calendar API service with OAuth2 local flow, token persistence,
time-blocking, free-slot analysis, and demo fallback.
"""

from __future__ import annotations

import datetime
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from dateutil import parser as date_parser

from jz_cli.config import get_tokens_path, get_client_secrets_path

# Google API Scopes
SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
]


@dataclass
class CalendarEvent:
    id: str
    title: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    location: str = ""
    meet_url: str = ""
    is_all_day: bool = False
    color_id: str = "1"
    is_time_block: bool = False

    @property
    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() / 60)

    def get_status_badge(self, now: Optional[datetime.datetime] = None) -> Tuple[str, str]:
        """
        Returns (badge_text, style_class_or_color)
        Badges: [Ongoing], [In 15m], [In 2h], [Done], [Later], [All-day]
        """
        if now is None:
            now = datetime.datetime.now(self.start_time.tzinfo or datetime.timezone.utc)

        # Ensure tz-awareness compatibility
        if self.start_time.tzinfo is not None and now.tzinfo is None:
            now = now.astimezone(self.start_time.tzinfo)
        elif self.start_time.tzinfo is None and now.tzinfo is not None:
            self.start_time = self.start_time.replace(tzinfo=now.tzinfo)
            self.end_time = self.end_time.replace(tzinfo=now.tzinfo)

        if self.is_all_day:
            return ("[All-Day]", "cyan")

        if now > self.end_time:
            return ("[Done]", "dim")

        if self.start_time <= now <= self.end_time:
            return ("[Ongoing]", "bold green")

        diff = self.start_time - now
        total_seconds = diff.total_seconds()

        if total_seconds < 0:
            return ("[Done]", "dim")

        minutes = int(total_seconds // 60)
        hours = int(minutes // 60)
        days = int(hours // 24)

        if minutes <= 15:
            return (f"[In {minutes}m]", "bold yellow")
        elif minutes < 60:
            return (f"[In {minutes}m]", "yellow")
        elif hours < 5:
            rem_min = minutes % 60
            if rem_min > 0 and hours < 2:
                return (f"[In {hours}h {rem_min}m]", "cyan")
            return (f"[In {hours}h]", "cyan")
        elif days == 0:
            return (f"[At {self.start_time.strftime('%I:%M %p')}]", "blue")
        elif days == 1:
            return ("[Tomorrow]", "magenta")
        else:
            return (f"[In {days}d]", "dim")


class CalendarService:
    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self._service = None
        self._tokens_path = get_tokens_path()
        self._authenticated = False

        if not self.demo_mode and self._tokens_path.exists():
            self._try_init_service()

    @property
    def is_connected(self) -> bool:
        return self._authenticated and self._service is not None

    def _try_init_service(self) -> bool:
        """Attempt to restore credentials from tokens.json."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            if self._tokens_path.exists():
                creds = Credentials.from_authorized_user_file(str(self._tokens_path), SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    with open(self._tokens_path, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())

                if creds and creds.valid:
                    self._service = build("calendar", "v3", credentials=creds)
                    self._authenticated = True
                    return True
        except Exception as e:
            # Token issue or offline
            self._authenticated = False
            self._service = None
        return False

    def authenticate_interactive(self, credentials_file: Optional[str] = None) -> Tuple[bool, str]:
        """
        Run local OAuth2 loopback server to authorize Google Calendar access.
        Saves tokens to tokens.json.
        """
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            creds_path = credentials_file or get_client_secrets_path()
            if not Path(creds_path).exists():
                return False, f"Credentials file not found at {creds_path}. Place client secret JSON there."

            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)

            # Persist tokens
            with open(self._tokens_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())

            self._try_init_service()
            return True, "Successfully authenticated with Google Calendar!"
        except Exception as e:
            return False, f"Authentication error: {e}"

    def get_today_events(self) -> List[CalendarEvent]:
        """Fetch today's events from Google Calendar or return realistic demo schedule."""
        now = datetime.datetime.now().astimezone()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        if not self.is_connected:
            return self._get_demo_today_events(now)

        try:
            events_result = (
                self._service.events()
                .list(
                    calendarId="primary",
                    timeMin=start_of_day.isoformat(),
                    timeMax=end_of_day.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            items = events_result.get("items", [])
            return [self._parse_google_event(item) for item in items]
        except Exception:
            # Fall back to demo/cached events on network error
            return self._get_demo_today_events(now)

    def get_upcoming_events(self, days: int = 7) -> List[CalendarEvent]:
        """Fetch upcoming events for the next N days."""
        now = datetime.datetime.now().astimezone()
        end_time = now + datetime.timedelta(days=days)

        if not self.is_connected:
            return self._get_demo_upcoming_events(now, days)

        try:
            events_result = (
                self._service.events()
                .list(
                    calendarId="primary",
                    timeMin=now.isoformat(),
                    timeMax=end_time.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            items = events_result.get("items", [])
            return [self._parse_google_event(item) for item in items]
        except Exception:
            return self._get_demo_upcoming_events(now, days)

    def create_time_block(
        self,
        title: str,
        duration_minutes: int,
        start_time: Optional[datetime.datetime] = None,
    ) -> Tuple[bool, str]:
        """
        Quick time-blocking (e.g. `/block 2h study for exam`).
        Creates an event in Google Calendar (or simulated in demo mode).
        """
        now = datetime.datetime.now().astimezone()
        if start_time is None:
            # Default to nearest 15-minute slot
            start_time = now + datetime.timedelta(minutes=(15 - now.minute % 15) % 15)
            if start_time < now:
                start_time += datetime.timedelta(minutes=15)

        end_time = start_time + datetime.timedelta(minutes=duration_minutes)

        if not self.is_connected:
            # Simulate block creation
            time_str = start_time.strftime("%I:%M %p")
            end_str = end_time.strftime("%I:%M %p")
            return (
                True,
                f"⚡ [Demo Block Scheduled] '{title}' blocked today {time_str} - {end_str} ({duration_minutes}m).",
            )

        try:
            event_body = {
                "summary": f"🎯 [JZ Focus] {title}",
                "description": "Scheduled via jz CLI time-blocking",
                "start": {"dateTime": start_time.isoformat()},
                "end": {"dateTime": end_time.isoformat()},
                "colorId": "5",  # Yellow / Banana in GCal
            }
            self._service.events().insert(calendarId="primary", body=event_body).execute()
            time_str = start_time.strftime("%I:%M %p")
            end_str = end_time.strftime("%I:%M %p")
            return True, f"✓ Calendar event created: '{title}' from {time_str} to {end_str}."
        except Exception as e:
            return False, f"Failed to create Google Calendar event: {e}"

    def find_free_slots(self, days: int = 2) -> List[Tuple[datetime.datetime, datetime.datetime, int]]:
        """
        Finds open time windows (between 8:00 AM and 10:00 PM) that have at least 45 minutes of free time.
        Returns list of (start_time, end_time, free_minutes).
        """
        events = self.get_upcoming_events(days=days)
        now = datetime.datetime.now().astimezone()
        free_slots = []

        for d in range(days):
            day_base = now + datetime.timedelta(days=d)
            day_start = day_base.replace(hour=9, minute=0, second=0, microsecond=0)
            day_end = day_base.replace(hour=21, minute=0, second=0, microsecond=0)

            if d == 0 and now > day_start:
                day_start = now + datetime.timedelta(minutes=15)

            if day_start >= day_end:
                continue

            day_events = [
                e for e in events
                if not e.is_all_day and e.start_time.date() == day_start.date()
            ]
            day_events.sort(key=lambda x: x.start_time)

            curr_pointer = day_start
            for ev in day_events:
                if ev.start_time > curr_pointer:
                    diff_mins = int((ev.start_time - curr_pointer).total_seconds() / 60)
                    if diff_mins >= 45:
                        free_slots.append((curr_pointer, ev.start_time, diff_mins))
                if ev.end_time > curr_pointer:
                    curr_pointer = ev.end_time

            if curr_pointer < day_end:
                diff_mins = int((day_end - curr_pointer).total_seconds() / 60)
                if diff_mins >= 45:
                    free_slots.append((curr_pointer, day_end, diff_mins))

        return free_slots

    def _parse_google_event(self, item: dict) -> CalendarEvent:
        start_raw = item.get("start", {})
        end_raw = item.get("end", {})

        is_all_day = "date" in start_raw and "dateTime" not in start_raw
        if is_all_day:
            start_time = datetime.datetime.fromisoformat(start_raw["date"]).astimezone()
            end_time = datetime.datetime.fromisoformat(end_raw["date"]).astimezone()
        else:
            start_time = date_parser.parse(start_raw.get("dateTime", datetime.datetime.now().isoformat()))
            end_time = date_parser.parse(end_raw.get("dateTime", (start_time + datetime.timedelta(hours=1)).isoformat()))

        location = item.get("location", "")
        hangout_link = item.get("hangoutLink", "")

        return CalendarEvent(
            id=item.get("id", ""),
            title=item.get("summary", "(No Title)"),
            start_time=start_time,
            end_time=end_time,
            location=location,
            meet_url=hangout_link,
            is_all_day=is_all_day,
            color_id=item.get("colorId", "1"),
        )

    def _get_demo_today_events(self, now: datetime.datetime) -> List[CalendarEvent]:
        """Realistic student schedule for demo and offline experience."""
        today = now.date()
        tz = now.tzinfo

        return [
            CalendarEvent(
                id="demo-1",
                title="CS 2110: Data Structures & Algorithms",
                start_time=datetime.datetime.combine(today, datetime.time(9, 30), tzinfo=tz),
                end_time=datetime.datetime.combine(today, datetime.time(10, 45), tzinfo=tz),
                location="Klaus Advanced Computing 1443",
                meet_url="",
            ),
            CalendarEvent(
                id="demo-2",
                title="MATH 3010: Linear Algebra Lecture",
                start_time=datetime.datetime.combine(today, datetime.time(11, 0), tzinfo=tz),
                end_time=datetime.datetime.combine(today, datetime.time(12, 15), tzinfo=tz),
                location="Skiles Classroom Bldg 202",
                meet_url="",
            ),
            CalendarEvent(
                id="demo-3",
                title="CS Senior Capstone: Sprint Planning",
                start_time=datetime.datetime.combine(today, datetime.time(14, 0), tzinfo=tz),
                end_time=datetime.datetime.combine(today, datetime.time(15, 0), tzinfo=tz),
                location="Student Center 312 / Meet",
                meet_url="https://meet.google.com/abc-jz-demo",
            ),
            CalendarEvent(
                id="demo-4",
                title="Office Hours: Prof. Martinez",
                start_time=datetime.datetime.combine(today, datetime.time(16, 30), tzinfo=tz),
                end_time=datetime.datetime.combine(today, datetime.time(17, 30), tzinfo=tz),
                location="College of Computing 328",
                meet_url="",
            ),
        ]

    def _get_demo_upcoming_events(self, now: datetime.datetime, days: int) -> List[CalendarEvent]:
        events = self._get_demo_today_events(now)
        tz = now.tzinfo

        for d in range(1, days):
            day_date = (now + datetime.timedelta(days=d)).date()
            if day_date.weekday() < 5:  # Weekday
                events.extend([
                    CalendarEvent(
                        id=f"demo-wk-{d}-1",
                        title="CS 2110: Recitation & Lab",
                        start_time=datetime.datetime.combine(day_date, datetime.time(10, 0), tzinfo=tz),
                        end_time=datetime.datetime.combine(day_date, datetime.time(11, 30), tzinfo=tz),
                        location="CCB Lab 102",
                    ),
                    CalendarEvent(
                        id=f"demo-wk-{d}-2",
                        title="PHYS 2211: Physics II Lab",
                        start_time=datetime.datetime.combine(day_date, datetime.time(13, 0), tzinfo=tz),
                        end_time=datetime.datetime.combine(day_date, datetime.time(15, 0), tzinfo=tz),
                        location="Howey Physics N101",
                    ),
                ])
            else:
                events.append(
                    CalendarEvent(
                        id=f"demo-we-{d}",
                        title="Hackathon Prep & Study Group",
                        start_time=datetime.datetime.combine(day_date, datetime.time(13, 0), tzinfo=tz),
                        end_time=datetime.datetime.combine(day_date, datetime.time(16, 0), tzinfo=tz),
                        location="Crosland Tower 4th Floor",
                    )
                )
        events.sort(key=lambda x: x.start_time)
        return events
