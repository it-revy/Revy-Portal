from typing import Dict, Any, List, Set
from sqlalchemy.orm import Session
from app.employees.model import Employee
from app.breakfast.model import BreakfastRecord, BreakfastNonParticipationPeriod

def get_daily_breakfast_employees(business_date: str, db: Session) -> Dict[str, Any]:
    """
    Calculates applicable employees for Daily Entry.
    Rule: Excludes PERMANENT_NOT_TAKING and Leave/Non-participation period employees.
    """
    all_active = db.query(Employee).filter(
        Employee.status.in_(["active", "ACTIVE"]),
        Employee.is_hard_deleted == False
    ).order_by(Employee.employee_id.asc()).all()

    active_leaves = db.query(BreakfastNonParticipationPeriod).filter(
        BreakfastNonParticipationPeriod.from_date <= business_date,
        BreakfastNonParticipationPeriod.to_date >= business_date
    ).all()
    leave_emp_ids = {l.employee_id.upper() for l in active_leaves}

    perm_excluded = []
    leave_excluded = []
    applicable = []

    for emp in all_active:
        emp_id_upper = emp.employee_id.upper()
        if emp.breakfast_participation_type == "PERMANENT_NOT_TAKING":
            perm_excluded.append(emp)
        elif emp_id_upper in leave_emp_ids:
            leave_excluded.append(emp)
        else:
            applicable.append(emp)

    daily_records = db.query(BreakfastRecord).filter(
        BreakfastRecord.business_date == business_date
    ).all()
    record_map = {r.employee_id.upper(): r for r in daily_records}

    taking_count = 0
    not_taking_count = 0
    no_response_count = 0

    employee_statuses = []
    for emp in applicable:
        rec = record_map.get(emp.employee_id.upper())
        response = "NO_RESPONSE"
        actual_status = "NO_RESPONSE"
        actual_status_source = rec.actual_status_source if rec else "EMPLOYEE_RESPONSE"
        reason_code = rec.reason_code if rec else None
        reason_text = rec.reason_text if rec else None

        if rec:
            if rec.response in ["YES", "TAKING"] or rec.employee_response == "TAKING":
                response = "TAKING"
                actual_status = rec.actual_status or "TAKEN"
                taking_count += 1
            elif rec.response in ["NO", "NOT_TAKING"] or rec.employee_response == "NOT_TAKING":
                response = "NOT_TAKING"
                actual_status = rec.actual_status or "NOT_TAKEN"
                not_taking_count += 1
            else:
                response = "NO_RESPONSE"
                actual_status = rec.actual_status or "NO_RESPONSE"
                no_response_count += 1
        else:
            response = "NO_RESPONSE"
            actual_status = "NO_RESPONSE"
            no_response_count += 1

        employee_statuses.append({
            "employeeId": emp.employee_id,
            "employeeName": emp.name,
            "department": emp.department,
            "designation": emp.designation,
            "response": response,
            "actualStatus": actual_status,
            "actualStatusSource": actual_status_source,
            "reasonCode": reason_code,
            "reasonText": reason_text
        })

    return {
        "applicableEmployees": employee_statuses,
        "permExcludedEmployees": [{"employeeId": e.employee_id, "name": e.name, "department": e.department} for e in perm_excluded],
        "leaveExcludedEmployees": [{"employeeId": e.employee_id, "name": e.name, "department": e.department} for e in leave_excluded],
        "summary": {
            "totalActive": len(all_active),
            "permanentNotTaking": len(perm_excluded),
            "onLeave": len(leave_excluded),
            "applicableCount": len(applicable),
            "takingCount": taking_count,
            "notTakingCount": not_taking_count,
            "noResponseCount": no_response_count
        }
    }

def get_additional_breakfast_employees(business_date: str, db: Session) -> Dict[str, Any]:
    """
    Calculates applicable employees for Additional BF Orders.
    Rule: INCLUDES PERMANENT_NOT_TAKING employees, EXCLUDES Leave/Non-participation period employees.
    """
    all_active = db.query(Employee).filter(
        Employee.status.in_(["active", "ACTIVE"]),
        Employee.is_hard_deleted == False
    ).order_by(Employee.employee_id.asc()).all()

    active_leaves = db.query(BreakfastNonParticipationPeriod).filter(
        BreakfastNonParticipationPeriod.from_date <= business_date,
        BreakfastNonParticipationPeriod.to_date >= business_date
    ).all()
    leave_emp_ids = {l.employee_id.upper() for l in active_leaves}

    applicable = []
    leave_excluded = []

    for emp in all_active:
        emp_id_upper = emp.employee_id.upper()
        if emp_id_upper in leave_emp_ids:
            leave_excluded.append(emp)
        else:
            applicable.append(emp)

    return {
        "applicableEmployees": [
            {"employeeId": e.employee_id, "employeeName": e.name, "name": e.name, "department": e.department}
            for e in applicable
        ],
        "leaveExcludedEmployees": [
            {"employeeId": e.employee_id, "employeeName": e.name, "name": e.name, "department": e.department}
            for e in leave_excluded
        ],
        "applicableCount": len(applicable)
    }
