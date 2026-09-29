from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, desc
from app.breakfast.model import (
    BreakfastMoneyTransaction,
    BreakfastDailyEntry,
    BreakfastAdditionalOrder,
    BreakfastRecord,
    BreakfastNonParticipationPeriod
)
from app.employees.model import Employee
from app.breakfast.date_utils import get_kolkata_date_string, get_kolkata_now
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

        monthly_summary = []
        for m_obj in months_to_process:
            ym = m_obj["yearMonth"]
            s_date = f"{ym}-01"
            e_date = f"{ym}-31"

            txns = self.db.query(BreakfastMoneyTransaction).filter(
                BreakfastMoneyTransaction.transaction_date >= s_date,
                BreakfastMoneyTransaction.transaction_date <= e_date
            ).order_by(BreakfastMoneyTransaction.created_at.asc()).all()

            received = sum(t.amount for t in txns if t.type == "MONEY_RECEIVED")
            expenses = sum(t.amount for t in txns if t.type == "BREAKFAST_EXPENSE")
            adjustments = sum(t.amount for t in txns if t.type == "ADJUSTMENT")
            reversals = sum(t.amount for t in txns if t.type == "REVERSAL")

            total_spent = expenses - (adjustments + reversals)

            end_txn = self.db.query(BreakfastMoneyTransaction).filter(
                BreakfastMoneyTransaction.transaction_date <= e_date
            ).order_by(desc(BreakfastMoneyTransaction.created_at)).first()
            closing_bal = float(end_txn.balance_after_transaction) if end_txn else (running_opening_balance + received - total_spent)

            monthly_summary.append({
                "year": m_obj["year"],
                "month": m_obj["month"],
                "yearMonth": ym,
                "monthName": m_obj["monthName"],
                "openingBalance": running_opening_balance,
                "moneyReceived": received,
                "totalSpent": total_spent,
                "closingBalance": closing_bal
            })
            running_opening_balance = closing_bal

        tot_received = sum(r["moneyReceived"] for r in monthly_summary)
        tot_spent = sum(r["totalSpent"] for r in monthly_summary)
        final_closing = monthly_summary[-1]["closingBalance"] if monthly_summary else running_opening_balance

        yearly_total = {
            "totalMoneyReceived": tot_received,
            "totalSpent": tot_spent,
            "closingBalance": final_closing
        }

        # 2. Employee Monthly Report
        emp_q = self.db.query(Employee).filter(Employee.is_hard_deleted == False)
        if selected_dept and selected_dept != "ALL":
            emp_q = emp_q.filter(Employee.department == selected_dept)
        employees = emp_q.order_by(Employee.employee_id.asc()).all()

        emp_target_months = [selected_month] if (selected_month and selected_month != "ALL") else [m["yearMonth"] for m in months_to_process]
        month_summaries = {ym: get_month_calendar_summary(ym, self.db) for ym in emp_target_months}

        all_leaves = self.db.query(BreakfastNonParticipationPeriod).all()

        rec_q = self.db.query(BreakfastRecord)
        if selected_month and selected_month != "ALL":
            rec_q = rec_q.filter(BreakfastRecord.business_date.like(f"{selected_month}%"))
        elif selected_year != "all":
            rec_q = rec_q.filter(BreakfastRecord.business_date.like(f"{selected_year}%"))
        records = rec_q.all()

        emp_records_map = {}
        for r in records:
            emp_records_map.setdefault(r.employee_id.upper(), []).append(r)

        employee_report = []
        for emp in employees:
            is_perm = (emp.breakfast_participation_type == "PERMANENT_NOT_TAKING")
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
                "takenCount": 0 if is_perm else taken_count,
                "notTakenCount": 0 if is_perm else not_taken_count,
                "noResponseCount": no_response,
                "reasonBreakdown": {"Permanent Non-Participant": total_working_days} if is_perm else reason_breakdown
            })

        # 3. Order Summary
        daily_q = self.db.query(BreakfastDailyEntry)
        add_q = self.db.query(BreakfastAdditionalOrder)
        if selected_month and selected_month != "ALL":
            daily_q = daily_q.filter(BreakfastDailyEntry.business_date.like(f"{selected_month}%"))
            add_q = add_q.filter(BreakfastAdditionalOrder.business_date.like(f"{selected_month}%"))
        elif selected_year != "all":
            daily_q = daily_q.filter(BreakfastDailyEntry.business_date.like(f"{selected_year}%"))
            add_q = add_q.filter(BreakfastAdditionalOrder.business_date.like(f"{selected_year}%"))

        daily_entries = daily_q.order_by(desc(BreakfastDailyEntry.business_date)).all()
        additional_orders = add_q.order_by(desc(BreakfastAdditionalOrder.business_date)).all()

        def format_items(items):
            if not items:
                return ""
            return ", ".join(f"{i.get('name')} ({i.get('quantity')} x ₹{i.get('unitPrice')} = ₹{i.get('total')})" for i in items if i and i.get("name"))

        order_summary = []
        for de in daily_entries:
            order_summary.append({
                "orderId": f"DAILY-{de.business_date}",
                "businessDate": de.business_date,
                "orderType": "DAILY BREAKFAST",
                "orderTitle": "Daily Breakfast Entry",
                "orderTime": "10:00 AM",
                "applicableCount": (de.summary or {}).get("applicableCount", 0),
                "breakfastItems": format_items(de.breakfast_items),
                "commonItems": format_items(de.common_items),
                "totalCost": de.total_cost or 0.0,
                "createdBy": de.created_by or "System",
                "createdAt": de.created_at.isoformat() if de.created_at else None
            })

        for ao in additional_orders:
            order_summary.append({
                "orderId": ao.order_id,
                "businessDate": ao.business_date,
                "orderType": "ADDITIONAL ORDER",
                "orderTitle": ao.order_title or "Additional Order",
                "orderTime": ao.order_time or "",
                "applicableCount": ao.applicable_employee_count or 0,
                "breakfastItems": format_items(ao.breakfast_items),
                "commonItems": format_items(ao.common_items),
                "totalCost": ao.total_cost or 0.0,
                "createdBy": ao.created_by or "System",
                "createdAt": ao.created_at.isoformat() if ao.created_at else None
            })

        order_summary.sort(key=lambda o: o["businessDate"], reverse=True)

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

    def get_ceo_report(self) -> Dict[str, Any]:
        today_str = get_kolkata_date_string()
        current_month = today_str[:7]

        active_emps = self.db.query(Employee).filter(
            Employee.status == "active",
            Employee.is_hard_deleted == False
        ).all()
        total_employees = len(active_emps)
        normal_count = sum(1 for e in active_emps if e.breakfast_participation_type == "NORMAL")
        perm_not_taking_count = sum(1 for e in active_emps if e.breakfast_participation_type == "PERMANENT_NOT_TAKING")

        today_records = self.db.query(BreakfastRecord).filter(
            BreakfastRecord.business_date == today_str
        ).all()
        today_yes = sum(1 for r in today_records if r.response in ["YES", "TAKING"] or r.employee_response == "TAKING")
        today_no = sum(1 for r in today_records if r.response in ["NO", "NOT_TAKING"] or r.employee_response == "NOT_TAKING")
        today_responded = {r.employee_id.upper() for r in today_records}
        today_pending = max(0, normal_count - len(today_responded))

        month_records = self.db.query(BreakfastRecord).filter(
            BreakfastRecord.business_date.like(f"{current_month}%")
        ).all()

        daily_entries = self.db.query(BreakfastDailyEntry).filter(
            BreakfastDailyEntry.business_date.like(f"{current_month}%")
        ).all()
        additional_orders = self.db.query(BreakfastAdditionalOrder).filter(
            BreakfastAdditionalOrder.business_date.like(f"{current_month}%")
        ).all()

        today_entry = next((e for e in daily_entries if e.business_date == today_str), None)
        today_additional = [o for o in additional_orders if o.business_date == today_str]
        today_cost = (today_entry.total_cost if today_entry else 0.0) + sum(o.total_cost for o in today_additional)

        total_monthly_cost = sum(e.total_cost for e in daily_entries) + sum(o.total_cost for o in additional_orders)

        daily_trend_map = {}
        reason_distribution = {}

        for r in month_records:
            if r.business_date not in daily_trend_map:
                daily_trend_map[r.business_date] = {"date": r.business_date, "yes": 0, "no": 0}
            trend_item = daily_trend_map[r.business_date]
            if r.response in ["YES", "TAKING"] or r.employee_response == "TAKING":
                trend_item["yes"] += 1
            else:
                trend_item["no"] += 1
                reason = r.reason_text or r.reason_code or "Other"
                reason_distribution[reason] = reason_distribution.get(reason, 0) + 1

        daily_trend = sorted(list(daily_trend_map.values()), key=lambda x: x["date"])

        return {
            "currentMonth": current_month,
            "executiveSummary": {
                "totalEmployees": total_employees,
                "normalCount": normal_count,
                "permNotTakingCount": perm_not_taking_count,
                "todayYes": today_yes,
                "todayNo": today_no,
                "todayPending": today_pending,
                "todayCost": today_cost,
                "totalMonthlyCost": total_monthly_cost,
                "overallParticipationRate": round((today_yes / normal_count) * 100) if normal_count > 0 else 0
            },
            "dailyTrend": daily_trend,
            "reasonDistribution": reason_distribution
        }
