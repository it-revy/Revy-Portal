from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
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
        query = self.db.query(Employee).filter(Employee.is_hard_deleted == False)

        if search and search.strip():
            s = f"%{search.strip()}%"
            query = query.join(User).filter(
                or_(
                    User.username.ilike(s),
                    Employee.employee_id.ilike(s),
                    Employee.name.ilike(s),
                    Employee.email.ilike(s),
                    Employee.department.ilike(s),
                    Employee.designation.ilike(s)
                )
            )

        if department and department != "ALL":
            query = query.filter(Employee.department == department)

        if status and status != "ALL":
            query = query.filter(Employee.status == status)

        if participation_type and participation_type != "ALL":
            query = query.filter(Employee.breakfast_participation_type == participation_type)

        return query.order_by(Employee.employee_id.asc()).all()

    def get_roles_by_codes(self, role_codes: List[str]) -> List[Role]:
        return self.db.query(Role).filter(Role.code.in_(role_codes)).all()
