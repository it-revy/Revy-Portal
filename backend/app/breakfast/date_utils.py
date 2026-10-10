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
# =========================================================================
# Breakfast Request Window Logic (Configurable Period)
# Rule for breakfast date D:
#   By default (overnight):
#     Request Start: D - 1 day at open_time (17:30) IST
#     Request End:   D at close_time (08:20) IST
#   Validation rule: window_start <= now < window_end
# =========================================================================

def parse_time_str(time_str: str, default_hour: int = 8, default_min: int = 20) -> Tuple[int, int]:
    """Parses 'HH:mm' string into (hour, minute)."""
    try:
        parts = time_str.strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return (max(0, min(23, h)), max(0, min(59, m)))
    except Exception:
        return (default_hour, default_min)

def get_breakfast_cycle_settings(db: Optional[Any] = None) -> Tuple[str, str, str]:
    """
    Loads saved (request_open_time, request_close_time, timezone) from DB.
    Defaults to ('17:30', '08:20', 'Asia/Kolkata').
    """
    from app.breakfast.model import BreakfastSetting
    if db is not None:
        try:
            s = db.query(BreakfastSetting).first()
            if s:
                open_t = s.request_open_time or "17:30"
                close_t = s.request_close_time or s.cutoff_time or "08:20"
                tz_str = s.timezone or "Asia/Kolkata"
                return open_t, close_t, tz_str
        except Exception:
            pass
    return "17:30", "08:20", "Asia/Kolkata"

def get_request_window_for_date(
    target_date: Union[date, str],
    open_time: str = "17:30",
    close_time: str = "08:20"
) -> Tuple[datetime, datetime]:
    """
    Returns (window_start, window_end) in Asia/Kolkata timezone for a given breakfast date D:
    - If open_time > close_time (overnight cycle):
        window_start: (D - 1 day) at open_time:00 IST
        window_end:   D at close_time:00 IST
    - If open_time < close_time (same-day cycle):
        window_start: D at open_time:00 IST
        window_end:   D at close_time:00 IST
    """
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date.strip(), "%Y-%m-%d").date()

    open_h, open_m = parse_time_str(open_time, 17, 30)
    close_h, close_m = parse_time_str(close_time, 8, 20)

    # Determine if overnight cycle
    is_overnight = (open_h, open_m) > (close_h, close_m)

    if is_overnight:
        window_start = datetime(
            target_date.year, target_date.month, target_date.day,
            open_h, open_m, 0, 0, tzinfo=KOLKATA_TZ
        ) - timedelta(days=1)
    else:
        window_start = datetime(
            target_date.year, target_date.month, target_date.day,
            open_h, open_m, 0, 0, tzinfo=KOLKATA_TZ
        )

    window_end = datetime(
        target_date.year, target_date.month, target_date.day,
        close_h, close_m, 0, 0, tzinfo=KOLKATA_TZ
    )
    return window_start, window_end

def is_request_window_open(
    target_date: Union[date, str],
    now: Optional[datetime] = None,
    open_time: str = "17:30",
    close_time: str = "08:20"
) -> bool:
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

    window_start, window_end = get_request_window_for_date(target_date, open_time, close_time)
    return window_start <= now < window_end

def serialize_utc_timestamp(dt: Optional[datetime]) -> Optional[str]:
    """
    Serializes a datetime to an explicit UTC ISO-8601 string ending with 'Z'.
    - If dt is naive, it assumes UTC.
    - If dt is aware, it converts to UTC first.
    Always includes trailing 'Z' so client parsers unambiguously interpret it as UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")

def get_applicable_breakfast_date(
    now: Optional[datetime] = None,
    open_time: str = "17:30",
    close_time: str = "08:20"
) -> date:
    """
    Authoritatively determines the active breakfast business date based on Asia/Kolkata (IST):
    - In an overnight cycle (open_time > close_time, e.g. 17:30 to 08:20):
      - When now.time() >= open_time:
        The request window for tomorrow's breakfast is active/open. Active date is tomorrow (now.date() + 1 day).
      - When now.time() < open_time:
        The active breakfast business date is today (now.date()). This applies overnight (midnight to closing)
        as well as throughout daytime after closing until the next cycle opens at open_time.
    - In a same-day cycle (open_time <= close_time):
      - The active business date is today (now.date()).
    """
    if now is None:
        now = get_kolkata_now()
    else:
        now = to_kolkata_datetime(now)

    open_h, open_m = parse_time_str(open_time, 17, 30)
    close_h, close_m = parse_time_str(close_time, 8, 20)
    is_overnight = (open_h, open_m) > (close_h, close_m)

    if is_overnight:
        open_t = time(open_h, open_m, 0)
        if now.time() >= open_t:
            return (now + timedelta(days=1)).date()
        else:
            return now.date()
    else:
        return now.date()

def get_authoritative_breakfast_date(
    db: Optional[Any] = None,
    now: Optional[datetime] = None
) -> str:
    """
    Authoritative single-source-of-truth helper used across all backend endpoints.
    Retrieves configured cycle settings and returns active breakfast business date as 'YYYY-MM-DD'.
    """
    open_t, close_t, _ = get_breakfast_cycle_settings(db)
    active_date = get_applicable_breakfast_date(now=now, open_time=open_t, close_time=close_t)
    return active_date.strftime("%Y-%m-%d")

def get_breakfast_window_details(
    target_date: Optional[date] = None,
    now: Optional[datetime] = None,
    open_time: str = "17:30",
    close_time: str = "08:20"
) -> Dict[str, Any]:
    """
    Builds a full descriptor of the breakfast request window for API response and UI display.
    """
    if now is None:
        now = get_kolkata_now()
    else:
        now = to_kolkata_datetime(now)

    if target_date is None:
        target_date = get_applicable_breakfast_date(now, open_time, close_time)

    window_start, window_end = get_request_window_for_date(target_date, open_time, close_time)
    is_open = window_start <= now < window_end

    # Determine status string
    if is_open:
        status_code = "OPEN"
        status_label = "OPEN"
    elif now < window_start:
        status_code = "UPCOMING"
        status_label = f"CLOSED (Opens at {window_start.strftime('%I:%M %p')})"
    else:
        status_code = "CLOSED"
        status_label = "CLOSED"

    start_display = window_start.strftime("%d %b %Y, %I:%M %p")
    end_display = window_end.strftime("%d %b %Y, %I:%M %p")
    date_display = target_date.strftime("%d %b %Y")
    full_date_display = target_date.strftime("%d %B %Y, %A")

    return {
        "targetDate": target_date.strftime("%Y-%m-%d"),
        "targetDateFormatted": date_display,
        "targetDateFullFormatted": full_date_display,
        "windowStart": window_start.isoformat(),
        "windowEnd": window_end.isoformat(),
        "opensAt": window_start.isoformat(),
        "closesAt": window_end.isoformat(),
        "windowStartDisplay": start_display,
        "windowEndDisplay": end_display,
        "requestOpenTime": open_time,
        "requestCloseTime": close_time,
        "cutoffTime": close_time,
        "isOpen": is_open,
        "statusCode": status_code,
        "statusLabel": status_label,
        "currentIstTime": now.strftime("%d %b %Y, %I:%M:%S %p %Z"),
        "timezone": "Asia/Kolkata (IST, UTC+05:30)"
    }

def is_after_cutoff(cutoff_time: str = "08:20") -> bool:
    """Legacy helper kept for backward compatibility."""
    now = get_kolkata_now()
    try:
        parts = cutoff_time.split(":")
        cutoff_hour = int(parts[0])
        cutoff_min = int(parts[1]) if len(parts) > 1 else 0
        cutoff_dt = now.replace(hour=cutoff_hour, minute=cutoff_min, second=0, microsecond=0)
        return now >= cutoff_dt
    except Exception:
        return now.hour >= 8


