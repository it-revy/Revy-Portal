import calendar
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.breakfast.model import PublicHoliday, BreakfastNonParticipationPeriod
from app.employees.model import Employee

def get_business_day_status(date_str: str, db: Session) -> Dict[str, Any]:
    year, month, day = map(int, date_str.split("-"))
    date_obj = datetime(year, month, day)

    # 0 = Monday, 6 = Sunday in Python calendar
    day_of_week_idx = date_obj.weekday()
    is_sunday = (day_of_week_idx == 6)
    day_of_week = date_obj.strftime("%A")

    holiday_doc = db.query(PublicHoliday).filter(
        PublicHoliday.date == date_str,
        PublicHoliday.status == "active"
    ).first()

    is_public_holiday = bool(holiday_doc)
    public_holiday_name = holiday_doc.name if holiday_doc else None
    is_working_day = (not is_sunday) and (not is_public_holiday)

    return {
        "date": date_str,
        "dayOfWeek": day_of_week,
        "isSunday": is_sunday,
        "isPublicHoliday": is_public_holiday,
        "publicHolidayName": public_holiday_name,
        "isWorkingDay": is_working_day
    }

def get_month_calendar_summary(year_month_str: str, db: Session) -> Dict[str, Any]:
    year, month = map(int, year_month_str.split("-"))
    total_calendar_days = calendar.monthrange(year, month)[1]

    start_date_str = f"{year_month_str}-01"
    end_date_str = f"{year_month_str}-{total_calendar_days:02d}"

    active_holidays = db.query(PublicHoliday).filter(
        PublicHoliday.date >= start_date_str,
        PublicHoliday.date <= end_date_str,
        PublicHoliday.status == "active"
    ).all()

    holiday_map = {h.date: h.name for h in active_holidays}

    sundays_count = 0
    public_holidays_count = 0
    working_dates = []
    non_working_dates = []

    for day in range(1, total_calendar_days + 1):
        d_str = f"{year_month_str}-{day:02d}"
        d_obj = datetime(year, month, day)
        is_sun = (d_obj.weekday() == 6)
        is_holiday = d_str in holiday_map

        if is_sun:
            sundays_count += 1
            non_working_dates.append({"date": d_str, "reason": "Sunday"})
        elif is_holiday:
            public_holidays_count += 1
            non_working_dates.append({"date": d_str, "reason": f"Public Holiday: {holiday_map[d_str]}"})
        else:
            working_dates.append(d_str)

    working_days_count = total_calendar_days - (sundays_count + public_holidays_count)

    return {
        "yearMonth": year_month_str,
        "totalCalendarDays": total_calendar_days,
        "sundaysCount": sundays_count,
        "publicHolidaysCount": public_holidays_count,
        "workingDaysCount": working_days_count,
        "workingDates": working_dates,
        "nonWorkingDates": non_working_dates
    }

def get_employee_business_day_status(employee_id: str, date_str: str, db: Session) -> Dict[str, Any]:
    base_status = get_business_day_status(date_str, db)

    employee = db.query(Employee).filter(
        Employee.employee_id == employee_id.upper(),
        Employee.is_hard_deleted == False
    ).first()

    if not employee:
        return {
            **base_status,
            "isEmployeeLeave": False,
            "isPermanentNotTaking": False,
            "isApplicableForBreakfast": False
        }

    is_permanent_not_taking = (employee.breakfast_participation_type == "PERMANENT_NOT_TAKING")

    leave_period = db.query(BreakfastNonParticipationPeriod).filter(
        BreakfastNonParticipationPeriod.employee_id == employee.employee_id,
        BreakfastNonParticipationPeriod.from_date <= date_str,
        BreakfastNonParticipationPeriod.to_date >= date_str
    ).first()

    is_employee_leave = bool(leave_period)
    is_applicable = base_status["isWorkingDay"] and (not is_employee_leave) and (not is_permanent_not_taking)

    return {
        **base_status,
        "isEmployeeLeave": is_employee_leave,
        "leaveReason": leave_period.reason_text if leave_period else None,
        "isPermanentNotTaking": is_permanent_not_taking,
        "isApplicableForBreakfast": is_applicable
    }
