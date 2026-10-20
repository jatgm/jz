"""
Google Calendar API service with OAuth2 local flow, private iCal feed support,
time-blocking, free-slot analysis, and caching.
"""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
from dateutil import parser as date_parser

from jz_cli.config import get_base_dir, get_client_secrets_path, get_tokens_path

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
        if now is None:
            now = datetime.datetime.now(self.start_time.tzinfo or datetime.timezone.utc)

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


def parse_ics_events(ics_text: str) -> List[CalendarEvent]:
    """Parse raw iCalendar text into CalendarEvent objects."""
    # Unfold continuation lines
    unfolded = re.sub(r"\r?\n[ \t]", "", ics_text)
    events: List[CalendarEvent] = []

    # Find VEVENT blocks
    vevent_matches = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", unfolded, re.DOTALL)
    for block in vevent_matches:
        props: dict[str, str] = {}
        for line in block.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                k_norm = k.split(";")[0].strip().upper()
                props[k_norm] = v.strip()

        summary = props.get("SUMMARY", "Event")
        uid = props.get("UID", f"ev-{len(events)}")
        location = props.get("LOCATION", "")
        url = props.get("URL", "")

        dtstart_raw = props.get("DTSTART")
        if not dtstart_raw:
            continue

        try:
            start_dt = date_parser.parse(dtstart_raw)
            if start_dt.tzinfo is None:
                start_dt = start_dt.astimezone()
        except Exception:
            continue

        dtend_raw = props.get("DTEND")
        if dtend_raw:
            try:
                end_dt = date_parser.parse(dtend_raw)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.astimezone()
            except Exception:
                end_dt = start_dt + datetime.timedelta(hours=1)
        else:
            end_dt = start_dt + datetime.timedelta(hours=1)

        is_all_day = len(dtstart_raw) <= 8 or "VALUE=DATE" in block
        events.append(
            CalendarEvent(
                id=uid,
                title=summary,
                start_time=start_dt,
                end_time=end_dt,
                location=location,
                meet_url=url,
                is_all_day=is_all_day,
            )
        )

    events.sort(key=lambda x: x.start_time)
    return events


class CalendarService:
    def __init__(self, demo_mode: bool = False, gcal_ical_url: str = ""):
        self.demo_mode = demo_mode
        self.gcal_ical_url = gcal_ical_url.strip()
        self._service = None
        self._tokens_path = get_tokens_path()
        self._cache_path = get_base_dir() / "cache_calendar.json"
        self._authenticated = False

        if not self.demo_mode and self._tokens_path.exists():
            self._try_init_service()

    @property
    def is_connected(self) -> bool:
        return self._authenticated or bool(self.gcal_ical_url)

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
        except Exception:
            self._authenticated = False
            self._service = None
        return False

    def authenticate_interactive(self, credentials_file: Optional[str] = None) -> Tuple[bool, str]:
        """Authorize via browser loopback server."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            creds_path = credentials_file or get_client_secrets_path()
            if not Path(creds_path).exists():
                return False, f"Credentials file not found at {creds_path}."

            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)

            with open(self._tokens_path, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())

            self._try_init_service()
            return True, "Successfully authenticated with Google Calendar!"
        except Exception as e:
            return False, f"Authentication error: {e}"

    def fetch_ical_events(self) -> List[CalendarEvent]:
        """Fetch events via private iCal URL."""
        if not self.gcal_ical_url:
            return []
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(self.gcal_ical_url)
                if resp.status_code == 200:
                    events = parse_ics_events(resp.text)
                    self._save_cache(events)
                    return events
        except Exception:
            pass
        return self._load_cache()

    def get_today_events(self) -> List[CalendarEvent]:
        """Fetch today's events from active integration, cache, or demo."""
        now = datetime.datetime.now().astimezone()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        if self.demo_mode:
            return self._get_demo_today_events(now)

        if not self.is_connected:
            return []

        # 1. Check iCal URL
        if self.gcal_ical_url:
            all_ev = self.fetch_ical_events()
            return [
                e for e in all_ev
                if e.start_time.date() == now.date() or (e.start_time <= end_of_day and e.end_time >= start_of_day)
            ]

        # 2. Check Google API service
        if self._service:
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
                ev_list = [self._parse_google_event(item) for item in items]
                self._save_cache(ev_list)
                return ev_list
            except Exception:
                return self._load_cache(today_only=True)

        return []

    def get_upcoming_events(self, days: int = 7) -> List[CalendarEvent]:
        """Fetch upcoming events for next N days."""
        now = datetime.datetime.now().astimezone()
        end_time = now + datetime.timedelta(days=days)

        if self.demo_mode:
            return self._get_demo_upcoming_events(now, days)

        if not self.is_connected:
            return []

        if self.gcal_ical_url:
            all_ev = self.fetch_ical_events()
            return [e for e in all_ev if now <= e.end_time <= end_time]

        if self._service:
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
                ev_list = [self._parse_google_event(item) for item in items]
                self._save_cache(ev_list)
                return ev_list
            except Exception:
                return self._load_cache()

        return []

    def create_time_block(
        self,
        title: str,
        duration_minutes: int,
        start_time: Optional[datetime.datetime] = None,
    ) -> Tuple[bool, str]:
        now = datetime.datetime.now().astimezone()
        if start_time is None:
            start_time = now + datetime.timedelta(minutes=(15 - now.minute % 15) % 15)
            if start_time < now:
                start_time += datetime.timedelta(minutes=15)

        end_time = start_time + datetime.timedelta(minutes=duration_minutes)

        if not self.is_connected or not self._service:
            time_str = start_time.strftime("%I:%M %p")
            end_str = end_time.strftime("%I:%M %p")
            return (
                True,
                f"Block scheduled: '{title}' today {time_str} - {end_str} ({duration_minutes}m).",
            )

        try:
            event_body = {
                "summary": f"[JZ Focus] {title}",
                "description": "Scheduled via jz CLI time-blocking",
                "start": {"dateTime": start_time.isoformat()},
                "end": {"dateTime": end_time.isoformat()},
            }
            self._service.events().insert(calendarId="primary", body=event_body).execute()
            time_str = start_time.strftime("%I:%M %p")
            end_str = end_time.strftime("%I:%M %p")
            return True, f"Calendar event created: '{title}' from {time_str} to {end_str}."
        except Exception as e:
            return False, f"Failed to create Google Calendar event: {e}"

    def find_free_slots(self, days: int = 2) -> List[Tuple[datetime.datetime, datetime.datetime, int]]:
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

        return CalendarEvent(
            id=item.get("id", ""),
            title=item.get("summary", "(No Title)"),
            start_time=start_time,
            end_time=end_time,
            location=item.get("location", ""),
            meet_url=item.get("hangoutLink", ""),
            is_all_day=is_all_day,
            color_id=item.get("colorId", "1"),
        )

    def _save_cache(self, events: List[CalendarEvent]) -> None:
        try:
            data = [
                {
                    "id": e.id,
                    "title": e.title,
                    "start": e.start_time.isoformat(),
                    "end": e.end_time.isoformat(),
                    "location": e.location,
                    "meet_url": e.meet_url,
                    "is_all_day": e.is_all_day,
                }
                for e in events
            ]
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_cache(self, today_only: bool = False) -> List[CalendarEvent]:
        if not self._cache_path.exists():
            return []
        try:
            with open(self._cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            now = datetime.datetime.now().astimezone()
            events = []
            for d in data:
                ev = CalendarEvent(
                    id=d["id"],
                    title=d["title"],
                    start_time=date_parser.parse(d["start"]),
                    end_time=date_parser.parse(d["end"]),
                    location=d.get("location", ""),
                    meet_url=d.get("meet_url", ""),
                    is_all_day=d.get("is_all_day", False),
                )
                if today_only and ev.start_time.date() != now.date():
                    continue
                events.append(ev)
            return events
        except Exception:
            return []

    def _get_demo_today_events(self, now: datetime.datetime) -> List[CalendarEvent]:
        today = now.date()
        tz = now.tzinfo
        return [
            CalendarEvent(
                id="demo-1",
                title="CS 2110: Data Structures & Algorithms",
                start_time=datetime.datetime.combine(today, datetime.time(9, 30), tzinfo=tz),
                end_time=datetime.datetime.combine(today, datetime.time(10, 45), tzinfo=tz),
                location="Klaus Computing 1443",
            ),
            CalendarEvent(
                id="demo-2",
                title="MATH 3010: Linear Algebra Lecture",
                start_time=datetime.datetime.combine(today, datetime.time(11, 0), tzinfo=tz),
                end_time=datetime.datetime.combine(today, datetime.time(12, 15), tzinfo=tz),
                location="Skiles Bldg 202",
            ),
            CalendarEvent(
                id="demo-3",
                title="CS Senior Capstone Sprint",
                start_time=datetime.datetime.combine(today, datetime.time(14, 0), tzinfo=tz),
                end_time=datetime.datetime.combine(today, datetime.time(15, 0), tzinfo=tz),
                location="Student Center 312",
            ),
            CalendarEvent(
                id="demo-4",
                title="Office Hours: Prof. Martinez",
                start_time=datetime.datetime.combine(today, datetime.time(16, 30), tzinfo=tz),
                end_time=datetime.datetime.combine(today, datetime.time(17, 30), tzinfo=tz),
                location="CoC 328",
            ),
        ]

    def _get_demo_upcoming_events(self, now: datetime.datetime, days: int) -> List[CalendarEvent]:
        events = self._get_demo_today_events(now)
        tz = now.tzinfo
        for d in range(1, days):
            day_date = (now + datetime.timedelta(days=d)).date()
            events.append(
                CalendarEvent(
                    id=f"demo-wk-{d}",
                    title="CS 2110 Recitation & Lab",
                    start_time=datetime.datetime.combine(day_date, datetime.time(10, 0), tzinfo=tz),
                    end_time=datetime.datetime.combine(day_date, datetime.time(11, 30), tzinfo=tz),
                    location="CCB Lab 102",
                )
            )
        events.sort(key=lambda x: x.start_time)
        return events
