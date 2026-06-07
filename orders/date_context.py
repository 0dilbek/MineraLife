from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date


ORDER_DATE_SESSION_KEY = "orders_working_date"


def parse_date_safe(value):
    if not value:
        return None

    parsed = parse_date(value)
    if parsed:
        return parsed

    for fmt in ("%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def preset_to_date(preset):
    today = timezone.localdate()
    if preset == "yesterday":
        return today - timedelta(days=1)
    if preset == "tomorrow":
        return today + timedelta(days=1)
    if preset == "today":
        return today
    return None


def preset_for_date(value):
    today = timezone.localdate()
    if value == today - timedelta(days=1):
        return "yesterday"
    if value == today:
        return "today"
    if value == today + timedelta(days=1):
        return "tomorrow"
    return ""


def resolve_order_date_range(request):
    preset = (request.GET.get("preset") or "").lower()
    has_date_query = any(key in request.GET for key in ("preset", "start_date", "end_date", "date"))

    if preset in {"yesterday", "today", "tomorrow"}:
        start = end = preset_to_date(preset)
    else:
        start = parse_date_safe(request.GET.get("start_date") or request.GET.get("date"))
        end = parse_date_safe(request.GET.get("end_date"))

        if not start and not end and has_date_query:
            start = end = timezone.localdate()
        elif not start and not end:
            session_date = parse_date_safe(request.session.get(ORDER_DATE_SESSION_KEY))
            start = end = session_date or timezone.localdate()

        if start and not end:
            end = start
        if end and not start:
            start = end
        if start and end and end < start:
            start, end = end, start

        preset = preset_for_date(start) if start == end else ""

    if has_date_query and start:
        request.session[ORDER_DATE_SESSION_KEY] = start.isoformat()

    return start, end, preset


def resolve_order_working_date(request):
    start, _, _ = resolve_order_date_range(request)
    return start or timezone.localdate()


def order_date_query(value):
    if not value:
        return ""
    return f"start_date={value.isoformat()}&end_date={value.isoformat()}"
