import uuid
from typing import Optional, List, Union
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission, require_any_permission, require_module_access, CurrentUser
from app.core.exceptions import ValidationError, NotFoundError
from app.breakfast.model import BreakfastOrder, BreakfastOrderItem, BreakfastDailyEntry, BreakfastAdditionalOrder
from app.employees.model import Employee
from app.breakfast.date_utils import get_kolkata_date_string
from app.audit.service import AuditService

router = APIRouter(prefix="/orders", tags=["Breakfast Orders"], dependencies=[Depends(require_module_access("BMS"))])

class OrderItemInput(BaseModel):
    orderType: Optional[str] = "INDIVIDUAL"
    employeeId: Optional[str] = None
    itemName: str
    price: float
    quantity: Optional[Union[float, int, str]] = 1.0

class CreateOrderRequest(BaseModel):
    businessDate: Optional[str] = None
    vendorName: Optional[str] = "Internal Catering / Vendor"
    notes: Optional[str] = ""
    items: List[OrderItemInput]

def serialize_order(o: BreakfastOrder):
    return {
        "_id": o.id,
        "id": o.id,
        "orderId": o.order_id,
        "businessDate": o.business_date,
        "vendorName": o.vendor_name,
        "notes": o.notes,
        "createdBy": {
            "employeeId": o.created_by_employee_id,
            "employeeName": o.created_by_employee_name
        },
        "createdAt": o.created_at.isoformat() if o.created_at else None
    }

def serialize_item(i: BreakfastOrderItem):
    return {
        "_id": i.id,
        "id": i.id,
        "itemId": i.item_id,
        "orderId": i.order_id,
        "businessDate": i.business_date,
        "orderType": i.order_type,
        "employeeId": i.employee_id,
        "employeeName": i.employee_name,
        "itemName": i.item_name,
        "price": i.price,
        "quantity": i.quantity,
        "total": i.total,
        "createdAt": i.created_at.isoformat() if i.created_at else None
    }

@router.get("")
@router.get("/")
def get_orders_by_date(
    date: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.view", "breakfast.orders.view"])),
    db: Session = Depends(get_db)
):
    target_date = date or get_kolkata_date_string()
    orders = db.query(BreakfastOrder).filter(BreakfastOrder.business_date == target_date).order_by(BreakfastOrder.created_at.desc()).all()
    order_items = db.query(BreakfastOrderItem).filter(BreakfastOrderItem.business_date == target_date).all()

    individual_total = sum(i.total for i in order_items if i.order_type == "INDIVIDUAL")
    common_total = sum(i.total for i in order_items if i.order_type != "INDIVIDUAL")

    daily_entry = db.query(BreakfastDailyEntry).filter(BreakfastDailyEntry.business_date == target_date).first()
    daily_entry_total = float(daily_entry.total_cost or 0.0) if daily_entry else 0.0

    additional_orders = db.query(BreakfastAdditionalOrder).filter(BreakfastAdditionalOrder.business_date == target_date).all()
    additional_orders_total = float(sum(o.total_cost or 0.0 for o in additional_orders))

    grand_total = round(individual_total + common_total + daily_entry_total + additional_orders_total, 2)

    return {
        "success": True,
        "businessDate": target_date,
        "summary": {
            "totalOrders": len(orders),
            "individualTotal": individual_total,
            "commonTotal": common_total,
            "dailyBreakfastTotal": daily_entry_total,
            "additionalOrdersTotal": additional_orders_total,
            "grandTotal": grand_total
        },
        "orders": [serialize_order(o) for o in orders],
        "orderItems": [serialize_item(i) for i in order_items]
    }

@router.post("")
@router.post("/")
def create_order(
    payload: CreateOrderRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    target_date = payload.businessDate or get_kolkata_date_string()
    if not payload.items or len(payload.items) == 0:
        raise ValidationError("At least one order item is required")

    now_ts = int(uuid.uuid4().hex[:4], 16)
    order_id = f"ORD-{target_date.replace('-', '')}-{str(now_ts)[-4:]}"

    new_order = BreakfastOrder(
        order_id=order_id,
        business_date=target_date,
        vendor_name=(payload.vendorName or "Internal Catering / Vendor").strip(),
        notes=(payload.notes or "").strip(),
        created_by_employee_id=current_user.employee_id or "ADMIN",
        created_by_employee_name=current_user.name
    )
    db.add(new_order)
    db.flush()

    created_items = []
    for item in payload.items:
        price = float(item.price)
        quantity = float(item.quantity or 1.0)
        total = round(price * quantity, 2)

        emp_name = None
        if item.orderType == "INDIVIDUAL" and item.employeeId:
            emp = db.query(Employee).filter(Employee.employee_id == item.employeeId.strip().upper()).first()
            if emp:
                emp_name = emp.name

        item_id = f"ITM-{str(uuid.uuid4())[:8]}"
        order_item = BreakfastOrderItem(
            item_id=item_id,
            order_id=order_id,
            business_date=target_date,
            order_type=item.orderType or "INDIVIDUAL",
            employee_id=item.employeeId.strip().upper() if (item.orderType == "INDIVIDUAL" and item.employeeId) else None,
            employee_name=emp_name,
            item_name=item.itemName.strip(),
            price=price,
            quantity=quantity,
            total=total
        )
        db.add(order_item)
        created_items.append(order_item)

    db.commit()
    db.refresh(new_order)

    serialized_order = serialize_order(new_order)
    serialized_items = [serialize_item(i) for i in created_items]

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_ORDER_CREATED",
        request=request,
        target_info={
            "recordId": order_id,
            "details": f"Created breakfast purchase order on {target_date} with {len(created_items)} items"
        },
        after_state={"order": serialized_order, "items": serialized_items}
    )

    return {
        "success": True,
        "message": "Breakfast purchase order created successfully",
        "order": serialized_order,
        "items": serialized_items
    }

@router.delete("/{id}")
def delete_order(
    id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.manage")),
    db: Session = Depends(get_db)
):
    order = db.query(BreakfastOrder).filter(
        (BreakfastOrder.order_id == id) | (BreakfastOrder.id == id)
    ).first()
    if not order:
        raise NotFoundError("Order not found")

    before_state = serialize_order(order)
    db.query(BreakfastOrderItem).filter(BreakfastOrderItem.order_id == order.order_id).delete()
    db.delete(order)
    db.commit()

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_ORDER_DELETED",
        request=request,
        target_info={"recordId": id, "details": f"Deleted order {id}"},
        before_state=before_state
    )

    return {
        "success": True,
        "message": "Breakfast order deleted successfully"
    }
