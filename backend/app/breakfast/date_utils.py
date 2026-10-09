from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, Tuple, Dict, Any, Union

try:
    import zoneinfo
    KOLKATA_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")
except Exception:
    KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30))

def get_kolkata_now() -> datetime:
    """Returns the current datetime in Asia/Kolkata (IST, UTC+05:30) timezone."""
    return datetime.now(KOLKATA_TZ)

def to_kolkata_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures datetime is timezone-aware and set to Asia/Kolkata."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # If naive, treat as UTC and convert to IST
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KOLKATA_TZ)

def get_kolkata_date_string(dt: Optional[datetime] = None) -> str:
    """Returns YYYY-MM-DD string in Asia/Kolkata timezone."""
    if dt is None:
        dt = get_kolkata_now()
    else:
        dt = to_kolkata_datetime(dt)
    return dt.strftime("%Y-%m-%d")

def get_kolkata_time_string(dt: Optional[datetime] = None, format_str: str = "%I:%M %p") -> str:
    """Returns formatted time string in Asia/Kolkata timezone (e.g. '05:30 PM')."""
    if dt is None:
        dt = get_kolkata_now()
    else:
        dt = to_kolkata_datetime(dt)
    return dt.strftime(format_str)

def get_formatted_date_and_day(dt: Optional[datetime] = None) -> dict:
    if dt is None:
        dt = get_kolkata_now()
    else:
        dt = to_kolkata_datetime(dt)

    date_str = dt.strftime("%Y-%m-%d")
    day_of_week = dt.strftime("%A")
    display_string = dt.strftime("%d %B %Y, %A")
    return {
        "dateStr": date_str,
        "dayOfWeek": day_of_week,
        "displayString": display_string
    }

def getNextDayDate(dt: Optional[datetime] = None) -> datetime:
    if dt is None:
        dt = get_kolkata_now()
    return dt + timedelta(days=1)

# =========================================================================
# Breakfast Request Window Logic (Overnight Period)
# Rule for breakfast date D:
#   Request Start: D - 1 day at 17:30 IST
#   Request End:   D at 08:20 IST
# Validation rule: window_start <= now < window_end
# =========================================================================

def get_request_window_for_date(target_date: Union[date, str]) -> Tuple[datetime, datetime]:
    """
    Returns (window_start, window_end) in Asia/Kolkata timezone for a given breakfast date D:
    - window_start: (D - 1 day) at 17:30:00 IST
    - window_end:   D at 08:20:00 IST
    """
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date.strip(), "%Y-%m-%d").date()

    window_start = datetime(
        target_date.year, target_date.month, target_date.day,
        17, 30, 0, 0, tzinfo=KOLKATA_TZ
    ) - timedelta(days=1)

    window_end = datetime(
        target_date.year, target_date.month, target_date.day,
        8, 20, 0, 0, tzinfo=KOLKATA_TZ
    )
    return window_start, window_end

def is_request_window_open(target_date: Union[date, str], now: Optional[datetime] = None) -> bool:
    """
    Checks if current IST time is within the request window for target_date.
    Rule: window_start <= now < window_end
    Therefore:
      08:19:59 IST -> Allowed (True)
      08:20:00 IST -> Closed  (False)
    """
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date.strip(), "%Y-%m-%d").date()

    if now is None:
        now = get_kolkata_now()
    else:
        now = to_kolkata_datetime(now)

    window_start, window_end = get_request_window_for_date(target_date)
    return window_start <= now < window_end

def get_applicable_breakfast_date(now: Optional[datetime] = None) -> date:
    """
    Intelligently determines the active breakfast date based on IST:
    - If now.time() < 08:20:00:
        Today's breakfast date (now.date()). The window opened yesterday at 17:30
        and remains open until 08:20:00 today.
    - If now.time() >= 08:20:00:
        Today's request window closed at 08:20:00.
        The upcoming breakfast date is tomorrow (now.date() + 1 day).
        Its window opens today at 17:30 and closes tomorrow at 08:20.
    """
    if now is None:
        now = get_kolkata_now()
    else:
        now = to_kolkata_datetime(now)

    # 08:20:00 cutoff time for same-day breakfast request
    cutoff_time = time(8, 20, 0)
    if now.time() < cutoff_time:
        return now.date()
    else:
        return (now + timedelta(days=1)).date()

def get_breakfast_window_details(target_date: Optional[date] = None, now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Builds a full descriptor of the breakfast request window for API response and UI display.
    """
    if now is None:
        now = get_kolkata_now()
    else:
        now = to_kolkata_datetime(now)

    if target_date is None:
        target_date = get_applicable_breakfast_date(now)

    window_start, window_end = get_request_window_for_date(target_date)
    is_open = window_start <= now < window_end

    # Determine status string
    if is_open:
        status_code = "OPEN"
        status_label = "OPEN"
    elif now < window_start:
        status_code = "UPCOMING"
        status_label = "CLOSED (Opens at 05:30 PM)"
    else:
        status_code = "CLOSED"
        status_label = "CLOSED"

    # Display formats
    # Example: "07 Oct 2026 05:30 PM"
    start_display = window_start.strftime("%d %b %Y %I:%M %p")
    # Example: "08 Oct 2026 08:20 AM"
    end_display = window_end.strftime("%d %b %Y %I:%M %p")
    date_display = target_date.strftime("%d %b %Y")
    full_date_display = target_date.strftime("%d %B %Y, %A")

    return {
        "targetDate": target_date.strftime("%Y-%m-%d"),
        "targetDateFormatted": date_display,
        "targetDateFullFormatted": full_date_display,
        "windowStart": window_start.isoformat(),
        "windowEnd": window_end.isoformat(),
        "windowStartDisplay": start_display,
        "windowEndDisplay": end_display,
        "isOpen": is_open,
        "statusCode": status_code,
        "statusLabel": status_label,
        "currentIstTime": now.strftime("%d %b %Y %I:%M:%S %p %Z"),
        "timezone": "Asia/Kolkata (IST, UTC+05:30)"
    }

def is_after_cutoff(cutoff_time: str = "12:00") -> bool:
    """Legacy helper kept for backward compatibility."""
    now = get_kolkata_now()
    try:
        parts = cutoff_time.split(":")
        cutoff_hour = int(parts[0])
        cutoff_min = int(parts[1]) if len(parts) > 1 else 0
        cutoff_dt = now.replace(hour=cutoff_hour, minute=cutoff_min, second=0, microsecond=0)
        return now >= cutoff_dt
    except Exception:
        return now.hour >= 12

