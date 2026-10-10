from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, distinct, desc
import app.models  # noqa: F401
from app.users.model import User  # Ensure User mapper is registered
from app.breakfast.model import (
    BreakfastMoneyTransaction,
    BreakfastDailyEntry,
    BreakfastAdditionalOrder,
    BreakfastRecord,
    BreakfastNonParticipationPeriod
)
from app.employees.model import Employee
from app.breakfast.date_utils import get_kolkata_date_string, get_kolkata_now, serialize_utc_timestamp
from app.breakfast.calendar_service import get_month_calendar_summary

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def get_available_years(self) -> Dict[str, Any]:
        current_date = get_kolkata_date_string()
        current_year = current_date[:4]

        txn_dates = [d[0] for d in self.db.query(distinct(BreakfastMoneyTransaction.transaction_date)).all() if d[0]]
        daily_dates = [d[0] for d in self.db.query(distinct(BreakfastDailyEntry.business_date)).all() if d[0]]
        add_dates = [d[0] for d in self.db.query(distinct(BreakfastAdditionalOrder.business_date)).all() if d[0]]
        rec_dates = [d[0] for d in self.db.query(distinct(BreakfastRecord.business_date)).all() if d[0]]

        years_set = {current_year}
        for d in txn_dates + daily_dates + add_dates + rec_dates:
            if d and len(d) >= 4 and d[:4].isdigit():
                years_set.add(d[:4])

        return {
            "years": sorted(list(years_set)),
            "defaultYear": current_year
        }

    def build_report_data(
        self,
        year: Optional[str] = None,
        month: Optional[str] = None,
        department: Optional[str] = None
    ) -> Dict[str, Any]:
        current_date = get_kolkata_date_string()
        current_year = current_date[:4]
        current_month_str = current_date[:7]

        selected_year = year or current_year
        selected_month = month or current_month_str
        selected_dept = department or "ALL"

        # 1. Determine months to process
        months_to_process = []
        if selected_year == "all":
            all_years = self.get_available_years()["years"]
            min_y = int(all_years[0]) if all_years else int(current_year)
            max_y = int(current_year)
            for y in range(min_y, max_y + 1):
                last_m = int(current_date[5:7]) if y == max_y else 12
                for m in range(1, last_m + 1):
                    m_str = f"{m:02d}"
                    months_to_process.append({
                        "year": str(y),
                        "month": m_str,
                        "yearMonth": f"{y}-{m_str}",
                        "monthName": f"{y} {MONTH_NAMES[m - 1][:3]}"
                    })
        else:
            target_y = int(selected_year)
            is_curr_y = (selected_year == current_year)
            max_m = int(current_date[5:7]) if is_curr_y else 12
            for m in range(1, max_m + 1):
                m_str = f"{m:02d}"
                months_to_process.append({
                    "year": selected_year,
                    "month": m_str,
                    "yearMonth": f"{selected_year}-{m_str}",
                    "monthName": MONTH_NAMES[m - 1]
                })

        first_ym = months_to_process[0]["yearMonth"] if months_to_process else f"{current_year}-01"
        first_start = f"{first_ym}-01"

        prior_txn = self.db.query(BreakfastMoneyTransaction).filter(
            BreakfastMoneyTransaction.transaction_date < first_start
        ).order_by(desc(BreakfastMoneyTransaction.created_at)).first()
        running_opening_balance = float(prior_txn.balance_after_transaction) if prior_txn else 0.0

        # Batch query transactions and historical records across processed period
        txn_batch = self.db.query(BreakfastMoneyTransaction).filter(
            BreakfastMoneyTransaction.transaction_date >= first_start
        ).order_by(BreakfastMoneyTransaction.transaction_date.asc(), BreakfastMoneyTransaction.created_at.asc()).all()

        txns_by_month = {}
        for t in txn_batch:
            m_key = t.transaction_date[:7] if t.transaction_date else ""
            txns_by_month.setdefault(m_key, []).append(t)

        hist_batch = self.db.query(BreakfastRecord).filter(
            BreakfastRecord.business_date >= first_start,
            BreakfastRecord.record_type == "HISTORICAL"
        ).all()
        hist_by_month = {}
        for hr in hist_batch:
            m_key = hr.business_date[:7] if hr.business_date else ""
            hist_by_month.setdefault(m_key, []).append(hr)

        monthly_summary = []
        for m_obj in months_to_process:
            ym = m_obj["yearMonth"]
            txns = txns_by_month.get(ym, [])
            received = sum(t.amount for t in txns if t.type == "MONEY_RECEIVED")
            expenses = sum(t.amount for t in txns if t.type == "BREAKFAST_EXPENSE")
            adjustments = sum(t.amount for t in txns if t.type == "ADJUSTMENT")
            reversals = sum(t.amount for t in txns if t.type == "REVERSAL")
            operational_spent = expenses - (adjustments + reversals)

            hist_recs = hist_by_month.get(ym, [])
            historical_spent = sum(float(r.total_cost or 0.0) for r in hist_recs)
            total_spent = operational_spent + historical_spent

            end_txn = txns[-1] if txns else None
            closing_bal = float(end_txn.balance_after_transaction) if (end_txn and end_txn.balance_after_transaction is not None) else (running_opening_balance + received - operational_spent)

            monthly_summary.append({
                "year": m_obj["year"],
                "month": m_obj["month"],
                "yearMonth": ym,
                "monthName": m_obj["monthName"],
                "openingBalance": running_opening_balance,
                "moneyReceived": received,
                "totalSpent": total_spent,
                "operationalSpent": operational_spent,
                "historicalSpent": historical_spent,
                "closingBalance": closing_bal
            })
            running_opening_balance = closing_bal

        tot_received = sum(r["moneyReceived"] for r in monthly_summary)
        tot_spent = sum(r["totalSpent"] for r in monthly_summary)
        tot_hist = sum(r["historicalSpent"] for r in monthly_summary)
        tot_op = sum(r["operationalSpent"] for r in monthly_summary)
        final_closing = monthly_summary[-1]["closingBalance"] if monthly_summary else running_opening_balance

        yearly_total = {
            "totalMoneyReceived": tot_received,
            "totalSpent": tot_spent,
            "totalOperationalSpent": tot_op,
            "totalHistoricalSpent": tot_hist,
            "closingBalance": final_closing
        }

        # 2. Employee Monthly Report (strictly CURRENT records with known employees)
        emp_q = self.db.query(Employee).options(joinedload(Employee.user)).filter(Employee.is_hard_deleted == False)
        if selected_dept and selected_dept != "ALL":
            emp_q = emp_q.filter(Employee.department == selected_dept)
        employees = emp_q.order_by(Employee.employee_id.asc()).all()

        if selected_month and selected_month != "ALL":
            target_ym = selected_month if "-" in selected_month else f"{selected_year}-{selected_month.zfill(2)}"
            emp_target_months = [target_ym]
        else:
            emp_target_months = [m["yearMonth"] for m in months_to_process]

        from app.breakfast.model import PublicHoliday
        import calendar
        from datetime import datetime as dt_cls
        all_active_holidays = self.db.query(PublicHoliday).filter(PublicHoliday.status == "active").all()
        holiday_date_set = {h.date for h in all_active_holidays}

        month_summaries = {}
        for ym in emp_target_months:
            y, m = map(int, ym.split("-"))
            num_days = calendar.monthrange(y, m)[1]
            w_dates = []
            for d in range(1, num_days + 1):
                d_str = f"{ym}-{d:02d}"
                d_obj = dt_cls(y, m, d)
                if d_obj.weekday() != 6 and d_str not in holiday_date_set:
                    w_dates.append(d_str)
            month_summaries[ym] = {"workingDates": w_dates}

        all_leaves = self.db.query(BreakfastNonParticipationPeriod).all()

        rec_q = self.db.query(BreakfastRecord).filter(BreakfastRecord.record_type == "CURRENT")
        if selected_month and selected_month != "ALL":
            target_prefix = selected_month if "-" in selected_month else f"{selected_year}-{selected_month.zfill(2)}"
            rec_q = rec_q.filter(BreakfastRecord.business_date.like(f"{target_prefix}%"))
        elif selected_year != "all":
            rec_q = rec_q.filter(BreakfastRecord.business_date.like(f"{selected_year}%"))
        records = rec_q.all()

        emp_records_map = {}
        for r in records:
            if r.employee_id:
                emp_records_map.setdefault(r.employee_id.upper(), []).append(r)

        employee_report = []
        for emp in employees:
            is_perm = (emp.breakfast_participation_type or "").upper() in ["PERMANENT_NOT_TAKING", "PERMANENT_NON_TAKER", "NON_TAKER"]
            recs = emp_records_map.get(emp.employee_id.upper(), [])
            emp_leaves = [l for l in all_leaves if l.employee_id.upper() == emp.employee_id.upper()]

            total_working_days = 0
            for ym, m_summ in month_summaries.items():
                for d_str in m_summ["workingDates"]:
                    on_leave = any(l.from_date <= d_str <= l.to_date for l in emp_leaves)
                    if not on_leave:
                        total_working_days += 1

            taken_count = 0
            not_taken_count = 0
            reason_breakdown = {}

            for r in recs:
                if r.response in ["YES", "TAKING"] or r.employee_response == "TAKING":
                    taken_count += 1
                elif r.response in ["NO", "NOT_TAKING"] or r.employee_response == "NOT_TAKING":
                    not_taken_count += 1
                    r_key = r.reason_text or r.reason_code or "Other"
                    reason_breakdown[r_key] = reason_breakdown.get(r_key, 0) + 1

            no_response = 0 if is_perm else max(0, total_working_days - (taken_count + not_taken_count))

            employee_report.append({
                "employeeId": emp.employee_id,
                "username": emp.user.username if emp.user else "",
                "name": emp.name,
                "department": emp.department,
                "designation": emp.designation,
                "participationType": emp.breakfast_participation_type,
                "isPermanentNotTaking": is_perm,
                "totalDays": total_working_days,
                "takenCount": taken_count,
                "notTakenCount": 0 if (is_perm and taken_count == 0) else not_taken_count,
                "noResponseCount": no_response,
                "reasonBreakdown": ({"Permanent Non-Participant": total_working_days} if (is_perm and taken_count == 0) else reason_breakdown)
            })


        # 3. Order Summary
        daily_q = self.db.query(BreakfastDailyEntry)
        add_q = self.db.query(BreakfastAdditionalOrder)
        hist_q = self.db.query(BreakfastRecord).filter(BreakfastRecord.record_type == "HISTORICAL")

        if selected_month and selected_month != "ALL":
            daily_q = daily_q.filter(BreakfastDailyEntry.business_date.like(f"{selected_month}%"))
            add_q = add_q.filter(BreakfastAdditionalOrder.business_date.like(f"{selected_month}%"))
            hist_q = hist_q.filter(BreakfastRecord.business_date.like(f"{selected_month}%"))
        elif selected_year != "all":
            daily_q = daily_q.filter(BreakfastDailyEntry.business_date.like(f"{selected_year}%"))
            add_q = add_q.filter(BreakfastAdditionalOrder.business_date.like(f"{selected_year}%"))
            hist_q = hist_q.filter(BreakfastRecord.business_date.like(f"{selected_year}%"))

        daily_entries = daily_q.order_by(BreakfastDailyEntry.business_date.asc()).all()
        additional_orders = add_q.order_by(BreakfastAdditionalOrder.business_date.asc()).all()
        hist_entries = hist_q.order_by(BreakfastRecord.business_date.asc()).all()

        def format_items(items):
            if not items:
                return ""
            return ", ".join(f"{i.get('name')} ({i.get('quantity')} x ₹{i.get('unitPrice')} = ₹{i.get('total')})" for i in items if i and i.get("name"))

        order_summary = []
        for de in daily_entries:
            summary = de.summary or {}
            actual_qty = summary.get("actualResponseQuantity", summary.get("actualTakenCount", 0))
            req_qty = summary.get("employeeRequestQuantity", summary.get("takingCount", 0))
            tot_qty = getattr(de, "total_quantity", None) or summary.get("totalQuantity", actual_qty)
            order_summary.append({
                "orderId": f"DAILY-{de.business_date}",
                "businessDate": de.business_date,
                "orderType": "DAILY BREAKFAST",
                "orderTitle": f"Daily Breakfast ({de.business_date})",
                "orderTime": "10:00 AM",
                "applicableCount": summary.get("applicableCount", 0),
                "systemEmployeeCount": summary.get("applicableCount", 0),
                "employeeRequestQuantity": float(req_qty),
                "actualResponseQuantity": float(actual_qty),
                "totalQuantity": float(tot_qty),
                "isHistorical": getattr(de, "record_type", "CURRENT") == "HISTORICAL",
                "breakfastItems": format_items(de.breakfast_items),
                "commonItems": format_items(de.common_items),
                "totalCost": de.total_cost or 0.0,
                "createdBy": de.created_by or "System",
                "createdAt": serialize_utc_timestamp(de.created_at)
            })

        for ao in additional_orders:
            order_summary.append({
                "orderId": ao.order_id,
                "businessDate": ao.business_date,
                "orderType": "ADDITIONAL ORDER",
                "orderTitle": ao.order_title or "Additional Order",
                "clientName": ao.client_name,
                "headCount": ao.head_count,
                "orderTime": ao.order_time or "",
                "applicableCount": ao.head_count if ao.head_count is not None else (ao.applicable_employee_count or 0),
                "systemEmployeeCount": ao.applicable_employee_count or 0,
                "isHistorical": False,
                "breakfastItems": format_items(ao.breakfast_items),
                "commonItems": format_items(ao.common_items),
                "totalCost": ao.total_cost or 0.0,
                "createdBy": ao.created_by or "System",
                "createdAt": serialize_utc_timestamp(ao.created_at)
            })

        for hr in hist_entries:
            bf_str = f"Snack: {hr.snack} ({hr.snack_quantity or ''}) ₹{hr.snack_cost or 0}" if hr.snack else ""
            cm_str = f"Fruit: {hr.fruit} ({hr.fruit_quantity or ''}) ₹{hr.fruit_cost or 0}" if hr.fruit else ""
            order_summary.append({
                "orderId": hr.source_id or hr.record_id,
                "businessDate": hr.business_date,
                "orderType": "HISTORICAL BREAKFAST",
                "orderTitle": f"Historical Breakfast ({hr.business_date})",
                "orderTime": "12:00 PM",
                "applicableCount": 0,
                "systemEmployeeCount": 0,
                "isHistorical": True,
                "recordType": "HISTORICAL",
                "employeeName": "Not Recorded",
                "breakfastItems": bf_str,
                "commonItems": cm_str,
                "snack": hr.snack,
                "snackQuantity": hr.snack_quantity,
                "snackCost": hr.snack_cost or 0.0,
                "fruit": hr.fruit,
                "fruitQuantity": hr.fruit_quantity,
                "fruitCost": hr.fruit_cost or 0.0,
                "paidBy": hr.paid_by,
                "paymentType": hr.payment_type,
                "totalCost": hr.total_cost or 0.0,
                "createdBy": f"{hr.paid_by} ({hr.payment_type})" if (hr.paid_by and hr.payment_type) else (hr.paid_by or "Historical Import"),
                "createdAt": serialize_utc_timestamp(hr.created_at)
            })

        order_summary.sort(key=lambda o: (o["businessDate"], o.get("orderId") or ""), reverse=False)

        # 4. Money Transactions
        txn_q = self.db.query(BreakfastMoneyTransaction)
        if selected_month and selected_month != "ALL":
            txn_q = txn_q.filter(BreakfastMoneyTransaction.transaction_date.like(f"{selected_month}%"))
        elif selected_year != "all":
            txn_q = txn_q.filter(BreakfastMoneyTransaction.transaction_date.like(f"{selected_year}%"))
        money_txns = txn_q.order_by(BreakfastMoneyTransaction.transaction_date.asc(), BreakfastMoneyTransaction.created_at.asc()).all()

        formatted_txns = [
            {
                "transactionId": t.transaction_id,
                "transactionDate": t.transaction_date,
                "transactionTime": t.transaction_time,
                "type": t.type,
                "amount": t.amount,
                "balanceAfterTransaction": t.balance_after_transaction,
                "source": t.source,
                "description": t.description,
                "createdBy": t.created_by
            }
            for t in money_txns
        ]

        return {
            "selectedYear": selected_year,
            "selectedMonth": selected_month,
            "selectedDepartment": selected_dept,
            "monthlySummary": monthly_summary,
            "yearlyTotal": yearly_total,
            "employeeReport": employee_report,
            "orderSummary": order_summary,
            "moneyTransactions": formatted_txns
        }

    def get_ceo_report(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        from datetime import datetime, timedelta
        from app.breakfast.model import BreakfastTemporaryRequest
        from app.breakfast import service as bf_service
        from app.breakfast import money_service

        today_dt = get_kolkata_now()
        today_default_str = get_kolkata_date_string(today_dt)
        selected_date_str = target_date.strip() if (target_date and len(target_date.strip()) == 10) else today_default_str
        current_month = selected_date_str[:7]
        try:
            selected_dt = datetime.strptime(selected_date_str, "%Y-%m-%d")
        except Exception:
            selected_dt = today_dt
            selected_date_str = today_default_str
            current_month = selected_date_str[:7]

        active_emps = self.db.query(Employee).filter(
            Employee.status == "active",
            Employee.is_hard_deleted == False
        ).all()
        total_employees = len(active_emps)
        normal_count = sum(1 for e in active_emps if (e.breakfast_participation_type or "").upper() in ["NORMAL", "REGULAR", "REGULAR_TAKER"])
        perm_not_taking_count = sum(1 for e in active_emps if (e.breakfast_participation_type or "").upper() in ["PERMANENT_NOT_TAKING", "PERMANENT_NON_TAKER", "NON_TAKER"])

        # Daily breakfast metrics for selected_date_str (incorporates regular + one-day requests)
        daily_bf_data = bf_service.get_daily_breakfast_employees(selected_date_str, self.db)
        daily_summary = daily_bf_data["summary"]

        daily_taking_count = daily_summary.get("takingCount", 0)
        daily_not_taking_count = daily_summary.get("notTakingCount", 0)
        daily_pending_count = daily_summary.get("noResponseCount", 0)
        daily_temp_req_count = daily_summary.get("temporaryRequestsCount", 0)

        # Selected date's costs and daily entry
        daily_entry = self.db.query(BreakfastDailyEntry).filter(BreakfastDailyEntry.business_date == selected_date_str).first()
        daily_additional = self.db.query(BreakfastAdditionalOrder).filter(BreakfastAdditionalOrder.business_date == selected_date_str).all()
        daily_cost = round((daily_entry.total_cost if daily_entry else 0.0) + sum(o.total_cost for o in daily_additional), 2)

        if daily_entry:
            daily_act_qty = float(daily_entry.total_quantity if daily_entry.total_quantity is not None else daily_entry.summary.get("actualResponseQuantity", 0.0))
            if daily_entry.summary and isinstance(daily_entry.summary, dict) and daily_entry.summary.get("employeeRequestQuantity") is not None:
                daily_req_qty = float(daily_entry.summary.get("employeeRequestQuantity"))
            else:
                daily_req_qty = float(daily_summary.get("employeeRequestQuantity", 0.0))
        else:
            daily_req_qty = float(daily_summary.get("employeeRequestQuantity", 0.0))
            daily_act_qty = float(daily_summary.get("actualResponseQuantity", 0.0))

        daily_diff = round(daily_req_qty - daily_act_qty, 2)
        daily_participation_rate = round((daily_act_qty / normal_count) * 100, 1) if normal_count > 0 else 0.0

        # Money ledger metrics
        ledger_metrics = money_service.get_money_balance_metrics(self.db)
        current_balance = ledger_metrics.get("currentBalance", 0.0)
        fund_limit = ledger_metrics.get("fundLimit", 2500.0)

        # Month records, daily entries, and additional orders
        month_records = self.db.query(BreakfastRecord).filter(
            BreakfastRecord.business_date.like(f"{current_month}%")
        ).all()

        month_daily_entries = self.db.query(BreakfastDailyEntry).filter(
            BreakfastDailyEntry.business_date.like(f"{current_month}%")
        ).all()
        month_entry_map = {e.business_date: e for e in month_daily_entries}

        month_additional_orders = self.db.query(BreakfastAdditionalOrder).filter(
            BreakfastAdditionalOrder.business_date.like(f"{current_month}%")
        ).all()
        month_add_map = {}
        for o in month_additional_orders:
            month_add_map.setdefault(o.business_date, []).append(o)

        month_temp_requests = self.db.query(BreakfastTemporaryRequest).filter(
            BreakfastTemporaryRequest.requested_date.like(f"{current_month}%"),
            BreakfastTemporaryRequest.status != "CANCELLED"
        ).all()

        # Month totals
        total_monthly_cost = round(
            sum(e.total_cost for e in month_daily_entries) + sum(o.total_cost for o in month_additional_orders),
            2
        )

        # Total breakfast requests in month (regular employee TAKING records + temporary one-day requests, avoiding double counting)
        regular_yes_recs = [r for r in month_records if r.employee_id and r.source != "TEMPORARY_REQUEST" and (r.response in ["YES", "TAKING"] or r.employee_response == "TAKING")]
        total_breakfast_requests_month = len(regular_yes_recs) + len(month_temp_requests)

        # Unique employees who took breakfast this month
        month_unique_takers = len({r.employee_id.upper() for r in month_records if r.employee_id and r.actual_status == "TAKEN"})

        # Group records by date for trends and comparisons
        dates_with_activity = sorted(list(
            {r.business_date for r in month_records} |
            {e.business_date for e in month_daily_entries} |
            {selected_date_str}
        ))

        daily_comparisons = []
        trend_series = []
        reason_distribution = {}
        total_month_requested_qty = 0.0
        total_month_actual_qty = 0.0

        for d_str in dates_with_activity:
            day_recs = [r for r in month_records if r.business_date == d_str]
            day_entry = month_entry_map.get(d_str)
            day_add = month_add_map.get(d_str, [])
            day_cost = round((day_entry.total_cost if day_entry else 0.0) + sum(o.total_cost for o in day_add), 2)

            day_entry_summary = day_entry.summary if (day_entry and isinstance(day_entry.summary, dict)) else {}

            if d_str == selected_date_str:
                d_req_qty = daily_req_qty
                d_act_qty = daily_act_qty
                d_not_taking = daily_not_taking_count
            elif day_entry_summary.get("employeeRequestQuantity") is not None:
                d_req_qty = float(day_entry_summary.get("employeeRequestQuantity", 0.0))
                d_act_qty = float(day_entry_summary.get("actualResponseQuantity", day_entry.total_quantity or 0.0))
                d_not_taking = day_entry_summary.get("notTakingCount", 0)
            else:
                d_req_qty = float(sum(1 for r in day_recs if r.response in ["YES", "TAKING"] or r.employee_response == "TAKING"))
                d_act_qty = float(sum(1 for r in day_recs if r.actual_status == "TAKEN"))
                d_not_taking = sum(1 for r in day_recs if r.response in ["NO", "NOT_TAKING"] or r.employee_response == "NOT_TAKING")

            d_diff = round(d_req_qty - d_act_qty, 2)
            d_rate = round((d_act_qty / normal_count) * 100, 1) if normal_count > 0 else 0.0

            total_month_requested_qty += d_req_qty
            total_month_actual_qty += d_act_qty

            status_label = "Balanced"
            if d_diff > 0:
                status_label = "Over-prepared"
            elif d_diff < 0:
                status_label = "Extra Served"

            daily_comparisons.append({
                "date": d_str,
                "requestedQuantity": d_req_qty,
                "actualQuantity": d_act_qty,
                "difference": d_diff,
                "dailyCost": day_cost,
                "participationRate": d_rate,
                "status": status_label
            })

            trend_series.append({
                "date": d_str,
                "requested": d_req_qty,
                "actual": d_act_qty,
                "optedOut": d_not_taking,
                "cost": day_cost
            })

            for r in day_recs:
                if r.response in ["NO", "NOT_TAKING"] or r.employee_response == "NOT_TAKING":
                    reason = r.reason_text or r.reason_code or "Other"
                    reason_distribution[reason] = reason_distribution.get(reason, 0) + 1

        daily_comparisons.sort(key=lambda x: x["date"], reverse=True)

        # Weekly Summary (last 7 days up to selected_date_str)
        seven_days_ago_dt = selected_dt - timedelta(days=6)
        seven_days_ago_str = get_kolkata_date_string(seven_days_ago_dt)
        week_items = [c for c in daily_comparisons if seven_days_ago_str <= c["date"] <= selected_date_str]
        week_req = round(sum(c["requestedQuantity"] for c in week_items), 2)
        week_act = round(sum(c["actualQuantity"] for c in week_items), 2)
        week_cost = round(sum(c["dailyCost"] for c in week_items), 2)
        week_diff = round(week_req - week_act, 2)
        week_active_days = len(week_items)
        week_avg_takers = round(week_act / week_active_days, 1) if week_active_days > 0 else 0.0
        week_avg_cost = round(week_cost / week_active_days, 2) if week_active_days > 0 else 0.0

        # Monthly Summary
        active_days_count = len(daily_comparisons)
        month_diff = round(total_month_requested_qty - total_month_actual_qty, 2)
        month_avg_daily_takers = round(total_month_actual_qty / active_days_count, 1) if active_days_count > 0 else 0.0
        month_avg_daily_cost = round(total_monthly_cost / active_days_count, 2) if active_days_count > 0 else 0.0
        avg_cost_per_meal = round(total_monthly_cost / total_month_actual_qty, 2) if total_month_actual_qty > 0 else 0.0

        # Department Participation Breakdown
        dept_map = {}
        for emp in active_emps:
            dept = emp.department or "General"
            dept_map.setdefault(dept, {"department": dept, "total": 0, "normal": 0, "permNotTaking": 0, "takingToday": 0})
            dept_map[dept]["total"] += 1
            if emp.breakfast_participation_type == "NORMAL":
                dept_map[dept]["normal"] += 1
            else:
                dept_map[dept]["permNotTaking"] += 1

        for emp_status in daily_bf_data.get("applicableEmployees", []):
            if emp_status.get("actualStatus") == "TAKEN":
                d_name = emp_status.get("department") or "General"
                if d_name in dept_map:
                    dept_map[d_name]["takingToday"] += 1

        department_breakdown = []
        for d_info in dept_map.values():
            n = d_info["normal"]
            d_info["participationRate"] = round((d_info["takingToday"] / n) * 100, 1) if n > 0 else 0.0
            department_breakdown.append(d_info)
        department_breakdown.sort(key=lambda x: x["total"], reverse=True)

        daily_summary_obj = {
            "date": selected_date_str,
            "requestedQuantity": daily_req_qty,
            "actualQuantity": daily_act_qty,
            "actualServedQuantity": daily_act_qty,
            "difference": daily_diff,
            "cost": daily_cost,
            "expenditure": daily_cost,
            "participationRate": daily_participation_rate,
            "optOutCount": daily_not_taking_count,
            "pendingCount": daily_pending_count
        }

        weekly_summary_obj = {
            "startDate": seven_days_ago_str,
            "endDate": selected_date_str,
            "totalRequestedQuantity": week_req,
            "totalActualQuantity": week_act,
            "totalActualServedQuantity": week_act,
            "difference": week_diff,
            "weeklyDifference": week_diff,
            "totalCost": week_cost,
            "totalWeeklySpend": week_cost,
            "activeDays": week_active_days,
            "avgDailyTakers": week_avg_takers,
            "averageDailyTakers": week_avg_takers,
            "avgDailyCost": week_avg_cost
        }

        monthly_summary_obj = {
            "month": current_month,
            "totalRequestedQuantity": round(total_month_requested_qty, 2),
            "totalMonthRequested": round(total_month_requested_qty, 2),
            "totalActualQuantity": round(total_month_actual_qty, 2),
            "totalMonthActualServed": round(total_month_actual_qty, 2),
            "difference": month_diff,
            "totalMonthDifference": month_diff,
            "totalCost": total_monthly_cost,
            "totalMonthlySpend": total_monthly_cost,
            "activeDays": active_days_count,
            "avgDailyTakers": month_avg_daily_takers,
            "avgDailyCost": month_avg_daily_cost,
            "avgCostPerMeal": avg_cost_per_meal,
            "averageCostPerMeal": avg_cost_per_meal
        }

        avg_monthly_part_rate = round(sum(c["participationRate"] for c in daily_comparisons) / len(daily_comparisons), 1) if daily_comparisons else daily_participation_rate

        executive_summary = {
            "totalEmployees": total_employees,
            "totalRequests": total_breakfast_requests_month,
            "regularTakers": normal_count,
            "permanentNonTakers": perm_not_taking_count,
            "todayRequestedQty": daily_req_qty,
            "todayActualServedQty": daily_act_qty,
            "requestActualDifference": daily_diff,
            "participationRate": daily_participation_rate,
            "normalCount": normal_count,
            "permNotTakingCount": perm_not_taking_count,
            "totalBreakfastTakers": normal_count,
            "totalNonTakers": perm_not_taking_count,
            "totalBreakfastRequestsMonth": total_breakfast_requests_month,
            "totalUniqueTakersMonth": month_unique_takers,
            "dailyRequestedQuantity": daily_req_qty,
            "dailyActualQuantity": daily_act_qty,
            "quantityDifference": daily_diff,
            "todayYes": daily_taking_count,
            "todayNo": daily_not_taking_count,
            "todayTaken": int(daily_act_qty),
            "todayPending": daily_pending_count,
            "todayTemporaryRequestsCount": daily_temp_req_count,
            "todayCost": daily_cost,
            "totalMonthlyCost": total_monthly_cost,
            "overallParticipationRate": daily_participation_rate,
            "avgMonthlyParticipationRate": avg_monthly_part_rate,
            "currentFundBalance": current_balance,
            "fundLimit": fund_limit,
            "avgCostPerMeal": avg_cost_per_meal
        }

        return {
            "success": True,
            "currentMonth": current_month,
            "todayDate": today_default_str,
            "selectedDate": selected_date_str,
            "totalEmployees": total_employees,
            "totalRequests": total_breakfast_requests_month,
            "regularTakers": normal_count,
            "permanentNonTakers": perm_not_taking_count,
            "todayRequestedQty": daily_req_qty,
            "todayActualServedQty": daily_act_qty,
            "requestActualDifference": daily_diff,
            "participationRate": daily_participation_rate,
            "executiveSummary": executive_summary,
            "dailySummary": daily_summary_obj,
            "weeklySummary": weekly_summary_obj,
            "monthlySummary": monthly_summary_obj,
            "summaries": {
                "daily": daily_summary_obj,
                "weekly": weekly_summary_obj,
                "monthly": monthly_summary_obj
            },
            "requestVsActualComparison": daily_comparisons,
            "consumptionTrends": trend_series,
            "dailyTrend": trend_series,
            "reasonDistribution": reason_distribution,
            "departmentBreakdown": department_breakdown,
            "temporaryRequests": [
                {
                    "id": tr.id,
                    "requestId": tr.request_id,
                    "employeeId": tr.employee_id,
                    "employeeName": tr.employee_name,
                    "requestedDate": tr.requested_date,
                    "quantity": float(tr.quantity or 1.0),
                    "status": tr.status,
                    "notes": tr.notes or ""
                }
                for tr in month_temp_requests
            ]
        }

