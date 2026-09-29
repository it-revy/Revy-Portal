from datetime import datetime, timedelta, timezone

try:
    import zoneinfo
    KOLKATA_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")
except Exception:
    KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30))

def get_kolkata_now() -> datetime:
    return datetime.now(KOLKATA_TZ)

def get_kolkata_date_string(dt: datetime = None) -> str:
    if dt is None:
        dt = get_kolkata_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=KOLKATA_TZ)
    else:
        dt = dt.astimezone(KOLKATA_TZ)
    return dt.strftime("%Y-%m-%d")

def get_formatted_date_and_day(dt: datetime = None) -> dict:
    if dt is None:
        dt = get_kolkata_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=KOLKATA_TZ)
    else:
        dt = dt.astimezone(KOLKATA_TZ)

    date_str = dt.strftime("%Y-%m-%d")
    day_of_week = dt.strftime("%A")
    display_string = dt.strftime("%d %B %Y, %A")
    return {
        "dateStr": date_str,
        "dayOfWeek": day_of_week,
        "displayString": display_string
    }

def is_after_cutoff(cutoff_time: str = "12:00") -> bool:
    now = get_kolkata_now()
    try:
        parts = cutoff_time.split(":")
        cutoff_hour = int(parts[0])
        cutoff_min = int(parts[1]) if len(parts) > 1 else 0
        cutoff_dt = now.replace(hour=cutoff_hour, minute=cutoff_min, second=0, microsecond=0)
        return now >= cutoff_dt
    except Exception:
        return now.hour >= 12

def getNextDayDate(dt: datetime = None) -> datetime:
    if dt is None:
        dt = get_kolkata_now()
    return dt + timedelta(days=1)
