from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, and_

from app.breakfast.beverage_model import BmsBeverage, BmsBeverageEntry
from app.breakfast.beverage_schema import (
    BeverageCreateRequest,
    BeverageUpdateRequest,
    BeverageEntrySubmitRequest,
    BeverageAdminEntryCreateRequest,
    BeverageAdminEntryUpdateRequest,
    BeverageItemResponse,
    BeverageEntryResponse
)
from app.employees.model import Employee
from app.breakfast.date_utils import get_kolkata_now, get_kolkata_date_string
from app.core.exceptions import ValidationError, NotFoundError, PermissionDeniedError
from app.audit.service import AuditService


class BeverageService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    # =========================================================================
    # 1. CATALOGUE ADMINISTRATION
    # =========================================================================

    def get_catalogue(self, active_only: bool = False) -> List[BeverageItemResponse]:
        query = self.db.query(BmsBeverage)
        if active_only:
            query = query.filter(BmsBeverage.is_active == True)
        beverages = query.order_by(BmsBeverage.display_order.asc(), BmsBeverage.name.asc()).all()
        return [self._to_catalogue_item(b) for b in beverages]

    def get_beverage_by_id(self, beverage_id: str) -> BmsBeverage:
        bev = self.db.query(BmsBeverage).filter(BmsBeverage.id == beverage_id).first()
        if not bev:
            raise NotFoundError(f"Beverage with ID '{beverage_id}' not found.")
        return bev

    def create_beverage(self, actor: Any, payload: BeverageCreateRequest) -> BeverageItemResponse:
        existing = self.db.query(BmsBeverage).filter(
            func.lower(BmsBeverage.name) == payload.name.lower()
        ).first()
        if existing:
            raise ValidationError(f"A beverage with name '{payload.name}' already exists.")

        new_bev = BmsBeverage(
            name=payload.name,
            description=payload.description,
            unit="Cups",
            display_order=payload.displayOrder,
            is_active=payload.isActive
        )
        self.db.add(new_bev)
        self.db.flush()

        # Audit Log
        self.audit_service.log(
            action="BMS_BEVERAGE_CATALOGUE_CREATE",
            target_info={
                "recordId": str(new_bev.id),
                "details": f"Created beverage '{new_bev.name}' (Order: {new_bev.display_order}, Active: {new_bev.is_active})"
            },
            after_state={
                "id": str(new_bev.id),
                "name": new_bev.name,
                "display_order": new_bev.display_order,
                "is_active": new_bev.is_active
            },
            performed_by_employee_id=getattr(actor, "employee_id", None),
            performed_by_name=getattr(actor, "name", None),
            role_used=getattr(actor, "active_role", None)
        )
        self.db.commit()
        return self._to_catalogue_item(new_bev)

    def update_beverage(self, actor: Any, beverage_id: str, payload: BeverageUpdateRequest) -> BeverageItemResponse:
        bev = self.get_beverage_by_id(beverage_id)

        before_state = {
            "name": bev.name,
            "description": bev.description,
            "display_order": bev.display_order,
            "is_active": bev.is_active
        }

        if payload.name and payload.name.lower() != bev.name.lower():
            dup = self.db.query(BmsBeverage).filter(
                func.lower(BmsBeverage.name) == payload.name.lower(),
                BmsBeverage.id != beverage_id
            ).first()
            if dup:
                raise ValidationError(f"A beverage with name '{payload.name}' already exists.")
            bev.name = payload.name

        if payload.description is not None:
            bev.description = payload.description
        if payload.displayOrder is not None:
            bev.display_order = payload.displayOrder
        if payload.isActive is not None:
            bev.is_active = payload.isActive

        bev.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        # Audit Log
        self.audit_service.log(
            action="BMS_BEVERAGE_CATALOGUE_UPDATE",
            target_info={
                "recordId": str(bev.id),
                "details": f"Updated beverage '{bev.name}'"
            },
            before_state=before_state,
            after_state={
                "name": bev.name,
                "description": bev.description,
                "display_order": bev.display_order,
                "is_active": bev.is_active
            },
            performed_by_employee_id=getattr(actor, "employee_id", None),
            performed_by_name=getattr(actor, "name", None),
            role_used=getattr(actor, "active_role", None)
        )
        self.db.commit()
        return self._to_catalogue_item(bev)

    def toggle_beverage_status(self, actor: Any, beverage_id: str, is_active: bool) -> BeverageItemResponse:
        bev = self.get_beverage_by_id(beverage_id)
        before_state = {"is_active": bev.is_active}
        bev.is_active = is_active
        bev.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        self.audit_service.log(
            action="BMS_BEVERAGE_CATALOGUE_STATUS_UPDATE",
            target_info={
                "recordId": str(bev.id),
                "details": f"Changed beverage '{bev.name}' status to {'ACTIVE' if is_active else 'INACTIVE'}"
            },
            before_state=before_state,
            after_state={"is_active": bev.is_active},
            performed_by_employee_id=getattr(actor, "employee_id", None),
            performed_by_name=getattr(actor, "name", None),
            role_used=getattr(actor, "active_role", None)
        )
        self.db.commit()
        return self._to_catalogue_item(bev)

    # =========================================================================
    # 2. EMPLOYEE BEVERAGE CONSUMPTION
    # =========================================================================

    def submit_employee_entry(self, actor: Any, payload: BeverageEntrySubmitRequest) -> BeverageEntryResponse:
        emp = self._resolve_actor_employee(actor)
        if not emp or emp.status != "active" or emp.is_hard_deleted:
            raise PermissionDeniedError("Active BMS employee profile required to submit beverage entries.")

        # Business Date validation: strictly today in Asia/Kolkata
        today_kolkata_str = get_kolkata_date_string()
        if payload.businessDate and payload.businessDate.strip() != today_kolkata_str:
            raise ValidationError("Employees can submit beverage entries for today's date only.")

        target_date = today_kolkata_str
        session_code = payload.session.upper()
        if session_code not in ("MORNING", "EVENING"):
            raise ValidationError("Session must be either 'MORNING' or 'EVENING'.")

        # Validate Beverage
        bev = self.get_beverage_by_id(payload.beverageId)
        if not bev.is_active:
            raise ValidationError(f"The beverage '{bev.name}' is currently deactivated and not available for new entries.")

        # Check existing entry for (employee_id, business_date, session)
        existing_entry = self.db.query(BmsBeverageEntry).filter(
            BmsBeverageEntry.employee_id == emp.employee_id,
            BmsBeverageEntry.business_date == target_date,
            BmsBeverageEntry.session == session_code
        ).first()

        if existing_entry:
            if not existing_entry.is_deleted:
                raise ValidationError(
                    f"A beverage entry ({existing_entry.beverage_name_snapshot}, {existing_entry.quantity} {existing_entry.unit}) "
                    f"has already been submitted for the {session_code} session on {target_date}. Duplicate submissions are prevented."
                )
            else:
                # Revive soft-deleted entry to preserve UNIQUE constraint safely
                existing_entry.beverage_id = bev.id
                existing_entry.beverage_name_snapshot = bev.name
                existing_entry.employee_name_snapshot = emp.name
                existing_entry.quantity = payload.quantity
                existing_entry.unit = "Cups"
                existing_entry.source = "EMPLOYEE"
                existing_entry.notes = payload.notes
                existing_entry.is_deleted = False
                existing_entry.deleted_at = None
                existing_entry.deleted_by = None
                existing_entry.deletion_reason = None
                existing_entry.updated_by = emp.name
                existing_entry.updated_at = datetime.now(timezone.utc)
                self.db.flush()
                self.db.commit()
                return self._to_entry_response(existing_entry)

        # Create new entry
        entry = BmsBeverageEntry(
            employee_id=emp.employee_id,
            employee_name_snapshot=emp.name,
            beverage_id=bev.id,
            beverage_name_snapshot=bev.name,
            business_date=target_date,
            session=session_code,
            quantity=payload.quantity,
            unit="Cups",
            source="EMPLOYEE",
            notes=payload.notes,
            created_by=emp.name
        )
        self.db.add(entry)
        self.db.flush()
        self.db.commit()
        return self._to_entry_response(entry)

    def get_my_entries(
        self,
        actor: Any,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[BeverageEntryResponse]:
        emp = self._resolve_actor_employee(actor)
        if not emp:
            return []

        query = self.db.query(BmsBeverageEntry).filter(
            BmsBeverageEntry.employee_id == emp.employee_id,
            BmsBeverageEntry.is_deleted == False
        )
        if from_date:
            query = query.filter(BmsBeverageEntry.business_date >= from_date)
        if to_date:
            query = query.filter(BmsBeverageEntry.business_date <= to_date)

        records = query.order_by(
            BmsBeverageEntry.business_date.desc(),
            BmsBeverageEntry.session.asc()
        ).all()
        return [self._to_entry_response(r) for r in records]

    def get_employee_today_status(self, actor: Any) -> Dict[str, Any]:
        emp = self._resolve_actor_employee(actor)
        today_str = get_kolkata_date_string()
        now_dt = get_kolkata_now()

        active_beverages = self.get_catalogue(active_only=True)

        morning_entry = None
        evening_entry = None

        if emp:
            entries = self.db.query(BmsBeverageEntry).filter(
                BmsBeverageEntry.employee_id == emp.employee_id,
                BmsBeverageEntry.business_date == today_str,
                BmsBeverageEntry.is_deleted == False
            ).all()

            for e in entries:
                if e.session == "MORNING":
                    morning_entry = self._to_entry_response(e)
                elif e.session == "EVENING":
                    evening_entry = self._to_entry_response(e)

        return {
            "businessDate": today_str,
            "currentTime": now_dt.strftime("%I:%M %p"),
            "timezone": "Asia/Kolkata",
            "activeBeverages": active_beverages,
            "morningEntry": morning_entry,
            "eveningEntry": evening_entry,
            "isMorningSubmitted": morning_entry is not None,
            "isEveningSubmitted": evening_entry is not None,
            "employee": {
                "employeeId": emp.employee_id if emp else "",
                "name": emp.name if emp else getattr(actor, "name", ""),
                "department": emp.department if emp else ""
            } if emp else None
        }

    # =========================================================================
    # 3. ADMIN CONSUMPTION MANAGEMENT
    # =========================================================================

    def admin_get_entries(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        date: Optional[str] = None,
        employee_id: Optional[str] = None,
        beverage_id: Optional[str] = None,
        session: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 200,
        offset: int = 0
    ) -> Dict[str, Any]:
        query = self.db.query(BmsBeverageEntry)

        if not include_deleted:
            query = query.filter(BmsBeverageEntry.is_deleted == False)

        if date:
            query = query.filter(BmsBeverageEntry.business_date == date)
        else:
            if from_date:
                query = query.filter(BmsBeverageEntry.business_date >= from_date)
            if to_date:
                query = query.filter(BmsBeverageEntry.business_date <= to_date)

        if employee_id and employee_id != "ALL":
            query = query.filter(BmsBeverageEntry.employee_id == employee_id)
        if beverage_id and beverage_id != "ALL":
            query = query.filter(BmsBeverageEntry.beverage_id == beverage_id)
        if session and session != "ALL":
            query = query.filter(BmsBeverageEntry.session == session.upper())

        total_count = query.count()
        records = query.order_by(
            BmsBeverageEntry.business_date.desc(),
            BmsBeverageEntry.session.asc(),
            BmsBeverageEntry.created_at.desc()
        ).offset(offset).limit(limit).all()

        # Summary statistics for the filtered dataset (excluding deleted)
        active_entries = [r for r in records if not r.is_deleted]
        total_cups = sum(r.quantity for r in active_entries)
        morning_cups = sum(r.quantity for r in active_entries if r.session == "MORNING")
        evening_cups = sum(r.quantity for r in active_entries if r.session == "EVENING")
        unique_employees = len(set(r.employee_id for r in active_entries))

        return {
            "total": total_count,
            "metrics": {
                "totalCups": total_cups,
                "morningCups": morning_cups,
                "eveningCups": evening_cups,
                "uniqueEmployees": unique_employees,
                "recordsCount": len(records)
            },
            "records": [self._to_entry_response(r) for r in records]
        }

    def admin_create_entry(self, actor: Any, payload: BeverageAdminEntryCreateRequest) -> BeverageEntryResponse:
        # Validate target employee
        emp = self.db.query(Employee).filter(
            Employee.employee_id == payload.employeeId,
            Employee.is_hard_deleted == False
        ).first()
        if not emp:
            raise NotFoundError(f"Employee with ID '{payload.employeeId}' not found.")

        # Validate beverage
        bev = self.get_beverage_by_id(payload.beverageId)
        if not bev.is_active:
            raise ValidationError(f"The beverage '{bev.name}' is inactive and cannot be selected for consumption.")

        session_code = payload.session.upper()
        target_date = payload.businessDate

        # Check existing entry for (employee_id, business_date, session)
        existing = self.db.query(BmsBeverageEntry).filter(
            BmsBeverageEntry.employee_id == emp.employee_id,
            BmsBeverageEntry.business_date == target_date,
            BmsBeverageEntry.session == session_code
        ).first()

        creator_name = getattr(actor, "name", None) or "Admin"
        creator_emp_id = getattr(actor, "employee_id", None)
        role_used = getattr(actor, "active_role", None)

        if existing:
            if not existing.is_deleted:
                raise ValidationError(
                    f"A beverage entry already exists for {emp.name} ({emp.employee_id}) "
                    f"on {target_date} for {session_code} session ({existing.beverage_name_snapshot}, {existing.quantity} Cups)."
                )
            else:
                # Revive and update soft-deleted row
                existing.beverage_id = bev.id
                existing.beverage_name_snapshot = bev.name
                existing.employee_name_snapshot = emp.name
                existing.quantity = payload.quantity
                existing.unit = "Cups"
                existing.source = "ADMIN"
                existing.notes = payload.notes
                existing.is_deleted = False
                existing.deleted_at = None
                existing.deleted_by = None
                existing.deletion_reason = None
                existing.updated_by = creator_name
                existing.updated_at = datetime.now(timezone.utc)
                self.db.flush()

                self.audit_service.log(
                    action="BMS_BEVERAGE_ADMIN_CREATE",
                    target_info={
                        "recordId": str(existing.id),
                        "targetEmployeeId": emp.employee_id,
                        "targetEmployeeName": emp.name,
                        "details": f"Admin revived & created entry: {payload.quantity} Cups of {bev.name} for {emp.name} on {target_date} ({session_code})"
                    },
                    after_state={
                        "id": str(existing.id),
                        "employee_id": emp.employee_id,
                        "business_date": target_date,
                        "session": session_code,
                        "beverage": bev.name,
                        "quantity": payload.quantity
                    },
                    performed_by_employee_id=creator_emp_id,
                    performed_by_name=creator_name,
                    role_used=role_used
                )
                self.db.commit()
                return self._to_entry_response(existing)

        # Create new record
        entry = BmsBeverageEntry(
            employee_id=emp.employee_id,
            employee_name_snapshot=emp.name,
            beverage_id=bev.id,
            beverage_name_snapshot=bev.name,
            business_date=target_date,
            session=session_code,
            quantity=payload.quantity,
            unit="Cups",
            source="ADMIN",
            notes=payload.notes,
            created_by=creator_name
        )
        self.db.add(entry)
        self.db.flush()

        self.audit_service.log(
            action="BMS_BEVERAGE_ADMIN_CREATE",
            target_info={
                "recordId": str(entry.id),
                "targetEmployeeId": emp.employee_id,
                "targetEmployeeName": emp.name,
                "details": f"Admin created entry: {payload.quantity} Cups of {bev.name} for {emp.name} on {target_date} ({session_code})"
            },
            after_state={
                "id": str(entry.id),
                "employee_id": emp.employee_id,
                "business_date": target_date,
                "session": session_code,
                "beverage": bev.name,
                "quantity": payload.quantity
            },
            performed_by_employee_id=creator_emp_id,
            performed_by_name=creator_name,
            role_used=role_used
        )
        self.db.commit()
        return self._to_entry_response(entry)

    def admin_update_entry(self, actor: Any, entry_id: str, payload: BeverageAdminEntryUpdateRequest) -> BeverageEntryResponse:
        entry = self.db.query(BmsBeverageEntry).filter(BmsBeverageEntry.id == entry_id).first()
        if not entry or entry.is_deleted:
            raise NotFoundError(f"Beverage entry with ID '{entry_id}' not found or has been deleted.")

        before_state = {
            "beverage_id": entry.beverage_id,
            "beverage_name": entry.beverage_name_snapshot,
            "session": entry.session,
            "quantity": entry.quantity,
            "notes": entry.notes
        }

        # If changing session, check uniqueness
        if payload.session and payload.session.upper() != entry.session:
            new_session = payload.session.upper()
            conflict = self.db.query(BmsBeverageEntry).filter(
                BmsBeverageEntry.employee_id == entry.employee_id,
                BmsBeverageEntry.business_date == entry.business_date,
                BmsBeverageEntry.session == new_session,
                BmsBeverageEntry.id != entry.id,
                BmsBeverageEntry.is_deleted == False
            ).first()
            if conflict:
                raise ValidationError(f"An active entry already exists for {entry.employee_name_snapshot} on {entry.business_date} for {new_session} session.")
            entry.session = new_session

        # If changing beverage
        if payload.beverageId and payload.beverageId != entry.beverage_id:
            bev = self.get_beverage_by_id(payload.beverageId)
            if not bev.is_active:
                raise ValidationError(f"Beverage '{bev.name}' is inactive and cannot be selected.")
            entry.beverage_id = bev.id
            entry.beverage_name_snapshot = bev.name

        if payload.quantity is not None:
            entry.quantity = payload.quantity

        if payload.notes is not None:
            entry.notes = payload.notes

        admin_name = getattr(actor, "name", None) or "Admin"
        entry.updated_by = admin_name
        entry.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        after_state = {
            "beverage_id": entry.beverage_id,
            "beverage_name": entry.beverage_name_snapshot,
            "session": entry.session,
            "quantity": entry.quantity,
            "notes": entry.notes
        }

        self.audit_service.log(
            action="BMS_BEVERAGE_ADMIN_UPDATE",
            target_info={
                "recordId": str(entry.id),
                "targetEmployeeId": entry.employee_id,
                "targetEmployeeName": entry.employee_name_snapshot,
                "details": f"Admin updated beverage entry for {entry.employee_name_snapshot} ({entry.business_date}, {entry.session})"
            },
            before_state=before_state,
            after_state=after_state,
            performed_by_employee_id=getattr(actor, "employee_id", None),
            performed_by_name=admin_name,
            role_used=getattr(actor, "active_role", None)
        )
        self.db.commit()
        return self._to_entry_response(entry)

    def admin_delete_entry(self, actor: Any, entry_id: str, reason: Optional[str] = None) -> BeverageEntryResponse:
        entry = self.db.query(BmsBeverageEntry).filter(BmsBeverageEntry.id == entry_id).first()
        if not entry or entry.is_deleted:
            raise NotFoundError(f"Beverage entry with ID '{entry_id}' not found or already deleted.")

        before_state = {
            "id": entry.id,
            "employee_id": entry.employee_id,
            "business_date": entry.business_date,
            "session": entry.session,
            "beverage_name": entry.beverage_name_snapshot,
            "quantity": entry.quantity
        }

        admin_name = getattr(actor, "name", None) or "Admin"
        entry.is_deleted = True
        entry.deleted_at = datetime.now(timezone.utc)
        entry.deleted_by = admin_name
        entry.deletion_reason = reason or "Deleted by administrator"
        entry.updated_by = admin_name
        entry.updated_at = datetime.now(timezone.utc)
        self.db.flush()

        self.audit_service.log(
            action="BMS_BEVERAGE_ADMIN_DELETE",
            target_info={
                "recordId": str(entry.id),
                "targetEmployeeId": entry.employee_id,
                "targetEmployeeName": entry.employee_name_snapshot,
                "details": f"Soft-deleted beverage entry for {entry.employee_name_snapshot} on {entry.business_date}. Reason: {entry.deletion_reason}"
            },
            before_state=before_state,
            performed_by_employee_id=getattr(actor, "employee_id", None),
            performed_by_name=admin_name,
            role_used=getattr(actor, "active_role", None)
        )
        self.db.commit()
        return self._to_entry_response(entry)

    # =========================================================================
    # 4. REPORTING / DASHBOARD HELPER
    # =========================================================================

    def get_beverage_dashboard_overview(
        self,
        target_date: str,
        current_month: str,
        total_active_employees: int
    ) -> Dict[str, Any]:
        """
        Computes Beverage Overview for the Director Dashboard.
        Strictly excludes soft-deleted records.
        Separates Morning and Evening sessions and computes beverage-wise quantities.
        """
        # 1. Day metrics for target_date
        day_entries = self.db.query(BmsBeverageEntry).filter(
            BmsBeverageEntry.business_date == target_date,
            BmsBeverageEntry.is_deleted == False
        ).all()

        day_total_cups = sum(e.quantity for e in day_entries)
        day_morning_cups = sum(e.quantity for e in day_entries if e.session == "MORNING")
        day_evening_cups = sum(e.quantity for e in day_entries if e.session == "EVENING")
        day_unique_drinkers = len(set(e.employee_id for e in day_entries))
        day_participation_rate = round((day_unique_drinkers / total_active_employees) * 100, 1) if total_active_employees > 0 else 0.0

        # Beverage-wise breakdown for target_date
        all_beverages = self.db.query(BmsBeverage).order_by(BmsBeverage.display_order.asc(), BmsBeverage.name.asc()).all()
        beverage_names = [b.name for b in all_beverages]

        # In case there are historical snapshots not in catalogue
        day_snap_names = set(e.beverage_name_snapshot for e in day_entries)
        for s in day_snap_names:
            if s not in beverage_names:
                beverage_names.append(s)

        day_beverage_stats = []
        for b_name in beverage_names:
            b_entries = [e for e in day_entries if e.beverage_name_snapshot == b_name]
            b_morning = sum(e.quantity for e in b_entries if e.session == "MORNING")
            b_evening = sum(e.quantity for e in b_entries if e.session == "EVENING")
            b_total = b_morning + b_evening
            day_beverage_stats.append({
                "name": b_name,
                "unit": "Cups",
                "morningCups": b_morning,
                "eveningCups": b_evening,
                "totalCups": b_total
            })

        # 2. Month metrics for current_month
        month_entries = self.db.query(BmsBeverageEntry).filter(
            BmsBeverageEntry.business_date.like(f"{current_month}%"),
            BmsBeverageEntry.is_deleted == False
        ).all()

        month_total_cups = sum(e.quantity for e in month_entries)
        month_morning_cups = sum(e.quantity for e in month_entries if e.session == "MORNING")
        month_evening_cups = sum(e.quantity for e in month_entries if e.session == "EVENING")
        month_unique_drinkers = len(set(e.employee_id for e in month_entries))

        # Month beverage-wise breakdown
        month_snap_names = set(e.beverage_name_snapshot for e in month_entries)
        for s in month_snap_names:
            if s not in beverage_names:
                beverage_names.append(s)

        month_beverage_stats = []
        for b_name in beverage_names:
            b_entries = [e for e in month_entries if e.beverage_name_snapshot == b_name]
            b_morning = sum(e.quantity for e in b_entries if e.session == "MORNING")
            b_evening = sum(e.quantity for e in b_entries if e.session == "EVENING")
            b_total = b_morning + b_evening
            month_beverage_stats.append({
                "name": b_name,
                "unit": "Cups",
                "morningCups": b_morning,
                "eveningCups": b_evening,
                "totalCups": b_total
            })

        # 3. Daily trend across the month
        dates_in_month = sorted(list(set(e.business_date for e in month_entries)))
        daily_trends = []
        for d_str in dates_in_month:
            d_records = [e for e in month_entries if e.business_date == d_str]
            d_morning = sum(e.quantity for e in d_records if e.session == "MORNING")
            d_evening = sum(e.quantity for e in d_records if e.session == "EVENING")
            d_drinkers = len(set(e.employee_id for e in d_records))
            daily_trends.append({
                "date": d_str,
                "morningCups": d_morning,
                "eveningCups": d_evening,
                "totalCups": d_morning + d_evening,
                "uniqueEmployees": d_drinkers
            })

        # 4. Employee-wise consumption ranking / history for current_month
        emp_records_map: Dict[str, List[BmsBeverageEntry]] = {}
        for e in month_entries:
            emp_records_map.setdefault(e.employee_id, []).append(e)

        # Get employee department info
        all_emps = {emp.employee_id: emp for emp in self.db.query(Employee).all()}

        employee_consumption_list = []
        for emp_id, records_for_emp in emp_records_map.items():
            emp_obj = all_emps.get(emp_id)
            emp_name = records_for_emp[0].employee_name_snapshot
            dept = emp_obj.department if emp_obj else "General"
            emp_m_cups = sum(e.quantity for e in records_for_emp if e.session == "MORNING")
            emp_e_cups = sum(e.quantity for e in records_for_emp if e.session == "EVENING")
            emp_total_cups = emp_m_cups + emp_e_cups

            # Find preferred beverage
            bev_count: Dict[str, int] = {}
            for e in records_for_emp:
                bev_count[e.beverage_name_snapshot] = bev_count.get(e.beverage_name_snapshot, 0) + e.quantity
            fav_bev = max(bev_count.items(), key=lambda x: x[1])[0] if bev_count else "-"

            employee_consumption_list.append({
                "employeeId": emp_id,
                "employeeName": emp_name,
                "department": dept,
                "morningCups": emp_m_cups,
                "eveningCups": emp_e_cups,
                "totalCups": emp_total_cups,
                "preferredBeverage": fav_bev,
                "daysActive": len(set(e.business_date for e in records_for_emp))
            })

        # Sort employees by total cups descending
        employee_consumption_list.sort(key=lambda x: x["totalCups"], reverse=True)

        return {
            "selectedDate": target_date,
            "currentMonth": current_month,
            "unit": "Cups",
            "daySummary": {
                "totalCups": day_total_cups,
                "morningCups": day_morning_cups,
                "eveningCups": day_evening_cups,
                "uniqueDrinkers": day_unique_drinkers,
                "totalEmployees": total_active_employees,
                "participationRate": day_participation_rate,
                "beverages": day_beverage_stats
            },
            "monthSummary": {
                "totalCups": month_total_cups,
                "morningCups": month_morning_cups,
                "eveningCups": month_evening_cups,
                "uniqueDrinkers": month_unique_drinkers,
                "beverages": month_beverage_stats
            },
            "dailyTrend": daily_trends,
            "employeeConsumption": employee_consumption_list
        }

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _resolve_actor_employee(self, actor: Any) -> Optional[Employee]:
        if not actor:
            return None
        emp_id = getattr(actor, "employee_id", None)
        if emp_id:
            emp = self.db.query(Employee).filter(
                Employee.employee_id == emp_id,
                Employee.is_hard_deleted == False
            ).first()
            if emp:
                return emp

        # Check linked user
        user = getattr(actor, "user", None)
        user_id = getattr(user, "id", None) or getattr(actor, "id", None)
        if user_id:
            emp = self.db.query(Employee).filter(
                Employee.user_id == user_id,
                Employee.is_hard_deleted == False
            ).first()
            if emp:
                return emp
        return None

    def _to_catalogue_item(self, b: BmsBeverage) -> BeverageItemResponse:
        return BeverageItemResponse(
            id=str(b.id),
            name=b.name,
            description=b.description,
            unit=b.unit,
            displayOrder=b.display_order,
            isActive=b.is_active,
            createdAt=b.created_at.isoformat() if b.created_at else None,
            updatedAt=b.updated_at.isoformat() if b.updated_at else None
        )

    def _to_entry_response(self, r: BmsBeverageEntry) -> BeverageEntryResponse:
        return BeverageEntryResponse(
            id=str(r.id),
            employeeId=r.employee_id,
            employeeNameSnapshot=r.employee_name_snapshot,
            beverageId=str(r.beverage_id),
            beverageNameSnapshot=r.beverage_name_snapshot,
            businessDate=r.business_date,
            session=r.session,
            quantity=r.quantity,
            unit=r.unit,
            source=r.source,
            notes=r.notes,
            isDeleted=r.is_deleted,
            deletedAt=r.deleted_at.isoformat() if r.deleted_at else None,
            deletedBy=r.deleted_by,
            deletionReason=r.deletion_reason,
            createdBy=r.created_by,
            updatedBy=r.updated_by,
            createdAt=r.created_at.isoformat() if r.created_at else None,
            updatedAt=r.updated_at.isoformat() if r.updated_at else None
        )
