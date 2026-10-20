"""
Unit tests for Calendar and Canvas services, countdowns, and relative badges.
"""

import datetime
from jz_cli.services.calendar_service import CalendarEvent, CalendarService
from jz_cli.services.canvas_service import CanvasAssignment, CanvasService


def test_calendar_event_badges():
    now = datetime.datetime.now().astimezone()

    # Ongoing event
    ev_ongoing = CalendarEvent(
        id="1",
        title="Ongoing Class",
        start_time=now - datetime.timedelta(minutes=20),
        end_time=now + datetime.timedelta(minutes=30),
    )
    badge, style = ev_ongoing.get_status_badge(now)
    assert badge == "[Ongoing]"
    assert "green" in style

    # In 15m
    ev_soon = CalendarEvent(
        id="2",
        title="Upcoming Class",
        start_time=now + datetime.timedelta(minutes=10),
        end_time=now + datetime.timedelta(minutes=60),
    )
    badge, _ = ev_soon.get_status_badge(now)
    assert "In 10m" in badge or "In" in badge

    # Past event
    ev_past = CalendarEvent(
        id="3",
        title="Past Class",
        start_time=now - datetime.timedelta(hours=2),
        end_time=now - datetime.timedelta(hours=1),
    )
    badge, _ = ev_past.get_status_badge(now)
    assert badge == "[Done]"


def test_canvas_assignment_countdown():
    now = datetime.datetime.now().astimezone()

    # Due tonight
    tonight_dt = datetime.datetime.combine(now.date(), datetime.time(23, 59), tzinfo=now.tzinfo)
    assign_tonight = CanvasAssignment(
        id=1,
        course_id=101,
        course_code="CS 2110",
        name="HW 4: Memory Allocator",
        due_at=tonight_dt,
        points_possible=100.0,
    )
    countdown, _ = assign_tonight.get_due_countdown(now)
    assert "Due tonight" in countdown or "Due in" in countdown

    # Overdue
    assign_overdue = CanvasAssignment(
        id=2,
        course_id=102,
        course_code="MATH 3010",
        name="Quiz 1",
        due_at=now - datetime.timedelta(days=1),
        points_possible=20.0,
    )
    countdown, style = assign_overdue.get_due_countdown(now)
    assert "OVERDUE" in countdown
    assert "red" in style


def test_calendar_service_time_block():
    cal = CalendarService(demo_mode=True)
    ok, msg = cal.create_time_block("Study Algorithms", 90)
    assert ok is True
    assert "Study Algorithms" in msg
    assert "90m" in msg


def test_calendar_service_free_slots():
    cal = CalendarService(demo_mode=True)
    slots = cal.find_free_slots(days=2)
    assert isinstance(slots, list)
    assert len(slots) > 0
    start, end, duration = slots[0]
    assert duration >= 45
