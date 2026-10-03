from typing import Dict, Any, List, Set, Optional, Tuple
from sqlalchemy.orm import Session
from app.employees.model import Employee
from app.breakfast.model import BreakfastRecord, BreakfastNonParticipationPeriod, BreakfastTemporaryRequest

def get_daily_breakfast_employees(business_date: str, db: Session) -> Dict[str, Any]:
    """
    Calculates applicable employees for Daily Entry.
    Rule:
    - Normal takers are included (unless on leave).
    - Permanent non-takers (PERMANENT_NOT_TAKING) are normally excluded,
      UNLESS they have submitted a valid one-day temporary request for this business_date.
    - Daily Expected/Requested Quantity = Regular Taker Requirements + Valid One-Day Requests.
    - Actual Response Quantity = Quantity actually provided/served (actualStatus == 'TAKEN').
    - Total Quantity = Actual Response Quantity.
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

    # Fetch active one-day temporary requests for this business_date
    temp_requests = db.query(BreakfastTemporaryRequest).filter(
        BreakfastTemporaryRequest.requested_date == business_date,
        BreakfastTemporaryRequest.status != "CANCELLED"
    ).all()
    temp_req_map = {tr.employee_id.upper(): tr for tr in temp_requests}

    perm_excluded = []
    leave_excluded = []
    applicable: List[Tuple[Employee, Optional[BreakfastTemporaryRequest]]] = []

    for emp in all_active:
        emp_id_upper = emp.employee_id.upper()
        is_perm = (emp.breakfast_participation_type or "").upper() in ["PERMANENT_NOT_TAKING", "PERMANENT_NON_TAKER", "NON_TAKER"]
        temp_req = temp_req_map.get(emp_id_upper)

        if is_perm and not temp_req:
            perm_excluded.append(emp)
        elif emp_id_upper in leave_emp_ids and not temp_req:
            leave_excluded.append(emp)
        else:
            applicable.append((emp, temp_req))

    daily_records = db.query(BreakfastRecord).filter(
        BreakfastRecord.business_date == business_date
    ).all()
    record_map = {r.employee_id.upper(): r for r in daily_records if r.employee_id}

    taking_count = 0
    not_taking_count = 0
    no_response_count = 0
    total_requested_quantity = 0.0
    total_actual_quantity = 0.0

    employee_statuses = []
    for emp, temp_req in applicable:
        rec = record_map.get(emp.employee_id.upper())
        is_temp = temp_req is not None
        req_qty = float(temp_req.quantity) if (temp_req and temp_req.quantity is not None) else 1.0

        if is_temp:
            # Permanent non-taker with an approved/confirmed one-day request
            response = "TAKING"
            actual_status = rec.actual_status if (rec and rec.actual_status) else "TAKEN"
            actual_status_source = rec.actual_status_source if rec else "TEMPORARY_REQUEST"
            reason_code = "ONE_DAY_REQUEST"
            reason_text = f"One-day request ({req_qty} portion{'s' if req_qty != 1 else ''})"
            taking_count += 1
            total_requested_quantity += req_qty
            if actual_status == "TAKEN":
                total_actual_quantity += req_qty
        elif rec:
            if rec.response in ["YES", "TAKING"] or rec.employee_response == "TAKING":
                response = "TAKING"
                actual_status = rec.actual_status or "TAKEN"
                taking_count += 1
                total_requested_quantity += 1.0
                if actual_status == "TAKEN":
                    total_actual_quantity += 1.0
            elif rec.response in ["NO", "NOT_TAKING"] or rec.employee_response == "NOT_TAKING":
                response = "NOT_TAKING"
                actual_status = rec.actual_status or "NOT_TAKEN"
                not_taking_count += 1
            else:
                response = "NO_RESPONSE"
                actual_status = rec.actual_status or "NO_RESPONSE"
                no_response_count += 1
            actual_status_source = rec.actual_status_source
            reason_code = rec.reason_code
            reason_text = rec.reason_text
        else:
            response = "NO_RESPONSE"
            actual_status = "NO_RESPONSE"
            actual_status_source = "EMPLOYEE_RESPONSE"
            reason_code = None
            reason_text = None
            no_response_count += 1

        employee_statuses.append({
            "employeeId": emp.employee_id,
            "employeeName": emp.name,
            "department": emp.department,
            "designation": emp.designation,
            "participationType": emp.breakfast_participation_type,
            "isTemporaryRequest": is_temp,
            "temporaryRequestId": temp_req.request_id if temp_req else None,
            "requestedQuantity": req_qty if is_temp else (1.0 if response == "TAKING" else 0.0),
            "response": response,
            "actualStatus": actual_status,
            "actualStatusSource": actual_status_source,
            "reasonCode": reason_code,
            "reasonText": reason_text
        })

    total_actual_quantity = sum(
        (e["requestedQuantity"] if e["isTemporaryRequest"] else 1.0)
        for e in employee_statuses if e["actualStatus"] == "TAKEN"
    )
    actual_taken_count = sum(1 for e in employee_statuses if e["actualStatus"] == "TAKEN")
    actual_not_taken_count = sum(1 for e in employee_statuses if e["actualStatus"] == "NOT_TAKEN")
    actual_no_response_count = sum(1 for e in employee_statuses if e["actualStatus"] == "NO_RESPONSE")

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
            "noResponseCount": no_response_count,
            "temporaryRequestsCount": len(temp_requests),
            "temporaryRequestsQuantity": round(sum(float(tr.quantity or 1.0) for tr in temp_requests), 2),
            "employeeRequestQuantity": round(total_requested_quantity, 2),
            "actualResponseQuantity": round(total_actual_quantity, 2),
            "totalQuantity": round(total_actual_quantity, 2),
            "actualTakenCount": actual_taken_count,
            "actualNotTakenCount": actual_not_taken_count,
            "actualNoResponseCount": actual_no_response_count
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
