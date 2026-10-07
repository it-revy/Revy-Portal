from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.employees.model import Employee, Department
from app.users.model import User
from app.roles.model import Role

class EmployeeRepository:
    def __init__(self, db: Session):
        self.db = db

    def generate_next_employee_id(self) -> str:
        count = self.db.query(Employee).count()
        return f"EMP-{(count + 1):04d}"

    def get_by_employee_id(self, employee_id: str, include_deleted: bool = False) -> Optional[Employee]:
        q = self.db.query(Employee).filter(Employee.employee_id == employee_id.upper())
        if not include_deleted:
            q = q.filter(Employee.is_hard_deleted == False)
        return q.first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username.lower(), User.is_hard_deleted == False).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.lower(), User.is_hard_deleted == False).first()

    def list_employees(
        self,
        search: Optional[str] = None,
        department: Optional[str] = None,
        status: Optional[str] = None,
        participation_type: Optional[str] = None
    ) -> List[Employee]:
        from sqlalchemy.orm import joinedload
        from app.modules.model import Module, UserModuleMembership

        bms_user_ids = self.db.query(UserModuleMembership.user_id)\
            .join(Module, UserModuleMembership.module_id == Module.id)\
            .filter(Module.code == "BMS", UserModuleMembership.is_active == True)

        query = self.db.query(Employee).options(
            joinedload(Employee.user).joinedload(User.roles)
        ).filter(
            Employee.is_hard_deleted == False,
            Employee.user_id.in_(bms_user_ids)
        )

        if search and search.strip():
            s = f"%{search.strip()}%"
            query = query.outerjoin(User, Employee.user_id == User.id).filter(
                or_(
                    User.username.ilike(s),
                    Employee.employee_id.ilike(s),
                    Employee.name.ilike(s),
                    Employee.email.ilike(s),
                    Employee.department.ilike(s),
                    Employee.designation.ilike(s)
                )
            )

        if department and department.strip() != "ALL":
            query = query.filter(func.lower(Employee.department) == department.strip().lower())

        if status and status.strip() != "ALL":
            query = query.filter(func.lower(Employee.status) == status.strip().lower())

        if participation_type and participation_type.strip() != "ALL":
            pt = participation_type.strip().upper()
            if pt in ["PERMANENT_NOT_TAKING", "PERMANENT_NON_TAKER", "NON_TAKER"]:
                query = query.filter(func.upper(Employee.breakfast_participation_type).in_(["PERMANENT_NOT_TAKING", "PERMANENT_NON_TAKER", "NON_TAKER"]))
            elif pt in ["NORMAL", "REGULAR", "REGULAR_TAKER"]:
                query = query.filter(func.upper(Employee.breakfast_participation_type).in_(["NORMAL", "REGULAR", "REGULAR_TAKER"]))
            else:
                query = query.filter(func.upper(Employee.breakfast_participation_type) == pt)

        return query.order_by(Employee.employee_id.asc()).all()

    def get_roles_by_codes(self, role_codes: List[str]) -> List[Role]:
        from app.roles.model import Role, Permission
        norm_codes = [c.strip() for c in role_codes if c and c.strip()]
        lookup_codes = set(norm_codes) | {c.upper().replace(" ", "_") for c in norm_codes}
        roles = self.db.query(Role).filter(
            or_(
                Role.code.in_(lookup_codes),
                Role.name.in_(norm_codes)
            )
        ).all()
        # If FINANCE_MANAGER was requested and not found in DB, auto-create it with permissions
        has_fin = any(c.upper() in ["FINANCE_MANAGER", "FINANCE MANAGER"] for c in norm_codes)
        if has_fin and not any(r.code == "FINANCE_MANAGER" for r in roles):
            fin_role = self.db.query(Role).filter(Role.code == "FINANCE_MANAGER").first()
            if not fin_role:
                fin_role = Role(
                    code="FINANCE_MANAGER",
                    name="Finance Manager",
                    description="Manages fund approvals, provisions, and financial reports"
                )
                perms = self.db.query(Permission).filter(
                    Permission.code.in_([
                        "finance.breakfast_fund.view", "finance.breakfast_fund.request.view",
                        "finance.breakfast_fund.request.approve", "finance.breakfast_fund.request.reject",
                        "finance.breakfast_fund.provide", "finance.breakfast_fund.report",
                        "breakfast.money.view", "breakfast.money.report", "breakfast.report", "breakfast.view_own",
                        "breakfast.submit", "breakfast.history_own"
                    ])
                ).all()
                fin_role.permissions = perms
                self.db.add(fin_role)
                self.db.flush()
            roles.append(fin_role)

        # If DIRECTOR_ANALYTICS was requested and not found in DB, auto-create it with permissions
        has_dir = any(c.upper() in ["DIRECTOR_ANALYTICS", "DIRECTOR ANALYTICS"] for c in norm_codes)
        if has_dir and not any(r.code == "DIRECTOR_ANALYTICS" for r in roles):
            dir_role = self.db.query(Role).filter(Role.code == "DIRECTOR_ANALYTICS").first()
            if not dir_role:
                dir_role = Role(
                    code="DIRECTOR_ANALYTICS",
                    name="Director Analytics",
                    description="Access executive management insights and Director Analytics dashboard"
                )
                perms = self.db.query(Permission).filter(
                    Permission.code.in_([
                        "breakfast.dashboard.view", "breakfast.view_own", "breakfast.submit", "breakfast.history_own"
                    ])
                ).all()
                dir_role.permissions = perms
                self.db.add(dir_role)
                self.db.flush()
            roles.append(dir_role)

        return roles

