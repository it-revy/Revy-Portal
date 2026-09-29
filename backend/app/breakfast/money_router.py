from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.core.dependencies import require_permission, CurrentUser
from app.core.exceptions import ValidationError, NotFoundError
from app.breakfast.model import BreakfastMoneyTransaction, BreakfastFundRequest
from app.breakfast import money_service
from app.breakfast.date_utils import get_kolkata_date_string
from app.audit.service import AuditService

router = APIRouter(prefix="/breakfast/money", tags=["Breakfast Money"])

class CreateFundRequestPayload(BaseModel):
    requestedAmount: float
    reason: Optional[str] = ""

class ApproveFundRequestPayload(BaseModel):
    approvedAmount: Optional[float] = None

class RejectFundRequestPayload(BaseModel):
    rejectionReason: str

class ProvideFundMoneyPayload(BaseModel):
    providedAmount: float
    providedDate: Optional[str] = None
    providedTime: Optional[str] = None
    reference: Optional[str] = None
    note: Optional[str] = None

class VerifyFundReceiptPayload(BaseModel):
    verifiedAmount: float
    differenceNote: Optional[str] = None

class ReceiveMoneyPayload(BaseModel):
    transactionDate: Optional[str] = None
    transactionTime: Optional[str] = None
    amount: float
    source: Optional[str] = "Finance Team"
    note: Optional[str] = ""

class RecordExpensePayload(BaseModel):
    transactionDate: Optional[str] = None
    transactionTime: Optional[str] = None
    amount: float
    source: Optional[str] = "Manual Expense"
    expenseCategory: Optional[str] = "OTHER_BREAKFAST_EXPENSE"
    expensePurpose: Optional[str] = "EMPLOYEE"
    description: Optional[str] = ""
    note: Optional[str] = ""

def serialize_fund_request(r: Optional[BreakfastFundRequest]):
    if not r:
        return None
    return {
        "_id": r.id,
        "id": r.id,
        "requestId": r.request_id,
        "requestedBy": r.requested_by,
        "requestDate": r.request_date,
        "requestTime": r.request_time,
        "currentBalance": r.current_balance,
        "fundLimit": r.fund_limit,
        "requestedAmount": r.requested_amount,
        "expectedBalance": r.expected_balance,
        "reason": r.reason,
        "status": r.status,
        "approvedAmount": r.approved_amount,
        "approvedBy": r.approved_by,
        "approvedAt": r.approved_at.isoformat() if r.approved_at else None,
        "providedAmount": r.provided_amount,
        "providedBy": r.provided_by,
        "providedAt": r.provided_at.isoformat() if r.provided_at else None,
        "providedDate": r.provided_date,
        "providedTime": r.provided_time,
        "reference": r.reference,
        "providedNote": r.provided_note,
        "verifiedAmount": r.verified_amount,
        "verifiedBy": r.verified_by,
        "verifiedAt": r.verified_at.isoformat() if r.verified_at else None,
        "rejectionReason": r.rejection_reason,
        "differenceReported": r.difference_reported or {"reported": False, "expectedAmount": 0, "receivedAmount": 0, "differenceAmount": 0, "note": ""},
        "createdAt": r.created_at.isoformat() if r.created_at else None
    }

def serialize_transaction(t: BreakfastMoneyTransaction):
    return {
        "_id": t.id,
        "id": t.id,
        "transactionId": t.transaction_id,
        "transactionDate": t.transaction_date,
        "transactionTime": t.transaction_time,
        "type": t.type,
        "amount": t.amount,
        "balanceAfterTransaction": t.balance_after_transaction,
        "source": t.source,
        "referenceType": t.reference_type,
        "referenceId": t.reference_id,
        "expenseCategory": t.expense_category,
        "expensePurpose": t.expense_purpose,
        "description": t.description,
        "note": t.note,
        "createdBy": t.created_by,
        "createdAt": t.created_at.isoformat() if t.created_at else None
    }

@router.get("/balance")
def get_money_balance(
    current_user: CurrentUser = Depends(require_permission("breakfast.money.view")),
    db: Session = Depends(get_db)
):
    metrics = money_service.get_money_balance_metrics(db)
    active_req = money_service.get_active_fund_request(db)
    return {
        "success": True,
        "metrics": metrics,
        "activeRequest": serialize_fund_request(active_req)
    }

@router.post("/requests")
def post_create_fund_request(
    payload: CreateFundRequestPayload,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.money.request")),
    db: Session = Depends(get_db)
):
    freq = money_service.create_fund_request(
        requested_amount=payload.requestedAmount,
        reason=payload.reason or "",
        requested_by=current_user.name,
        db=db
    )
    serialized = serialize_fund_request(freq)

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_MONEY_REQUEST_CREATED",
        request=request,
        target_info={
            "requestId": freq.request_id,
            "requestedAmount": freq.requested_amount,
            "currentBalance": freq.current_balance,
            "fundLimit": freq.fund_limit,
            "details": f"Requested ₹{freq.requested_amount} fund replenishment ({payload.reason or 'No reason'})"
        },
        after_state=serialized
    )

    return {
        "success": True,
        "message": f"Fund request {freq.request_id} for ₹{freq.requested_amount} submitted successfully",
        "fundRequest": serialized
    }

@router.get("/requests")
def get_fund_requests_controller(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_permission("breakfast.money.view")),
    db: Session = Depends(get_db)
):
    requests = money_service.get_fund_requests(status=status, search=search, db=db)
    metrics = money_service.get_money_balance_metrics(db)
    return {
        "success": True,
        "metrics": metrics,
        "requests": [serialize_fund_request(r) for r in requests]
    }

@router.get("/requests/active")
def get_active_fund_request_controller(
    current_user: CurrentUser = Depends(require_permission("breakfast.money.view")),
    db: Session = Depends(get_db)
):
    active_req = money_service.get_active_fund_request(db)
    return {
        "success": True,
        "activeRequest": serialize_fund_request(active_req)
    }

@router.put("/requests/{id}/approve")
def post_approve_fund_request(
    id: str,
    payload: ApproveFundRequestPayload,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("finance.breakfast_fund.request.approve")),
    db: Session = Depends(get_db)
):
    freq = money_service.approve_fund_request(
        request_id=id,
        approved_amount=payload.approvedAmount,
        approved_by=current_user.name,
        db=db
    )
    serialized = serialize_fund_request(freq)

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_MONEY_REQUEST_APPROVED",
        request=request,
        target_info={
            "requestId": freq.request_id,
            "approvedAmount": freq.approved_amount,
            "approvedBy": current_user.name,
            "details": f"Approved fund request {freq.request_id} for ₹{freq.approved_amount}"
        },
        after_state=serialized
    )

    return {
        "success": True,
        "message": f"Fund request {freq.request_id} approved for ₹{freq.approved_amount}. Note: Balance will be updated when Breakfast Admin confirms receipt.",
        "fundRequest": serialized
    }

@router.put("/requests/{id}/reject")
def post_reject_fund_request(
    id: str,
    payload: RejectFundRequestPayload,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("finance.breakfast_fund.request.reject")),
    db: Session = Depends(get_db)
):
    if not payload.rejectionReason or not payload.rejectionReason.strip():
        raise ValidationError("Rejection reason is required")

    freq = money_service.reject_fund_request(
        request_id=id,
        rejection_reason=payload.rejectionReason.strip(),
        rejected_by=current_user.name,
        db=db
    )
    serialized = serialize_fund_request(freq)

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_MONEY_REQUEST_REJECTED",
        request=request,
        target_info={
            "requestId": freq.request_id,
            "rejectionReason": payload.rejectionReason.strip(),
            "rejectedBy": current_user.name,
            "details": f"Rejected fund request {freq.request_id}: {payload.rejectionReason.strip()}"
        },
        after_state=serialized
    )

    return {
        "success": True,
        "message": f"Fund request {freq.request_id} rejected",
        "fundRequest": serialized
    }

@router.put("/requests/{id}/provide")
def post_provide_fund_money(
    id: str,
    payload: ProvideFundMoneyPayload,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("finance.breakfast_fund.provide")),
    db: Session = Depends(get_db)
):
    freq = money_service.provide_fund_money(
        request_id=id,
        provided_amount=payload.providedAmount,
        provided_date=payload.providedDate,
        provided_time=payload.providedTime,
        reference=payload.reference,
        note=payload.note,
        provided_by=current_user.name,
        db=db
    )
    serialized = serialize_fund_request(freq)

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_MONEY_PROVIDED",
        request=request,
        target_info={
            "requestId": freq.request_id,
            "providedAmount": freq.provided_amount,
            "reference": freq.reference,
            "providedBy": current_user.name,
            "details": f"Recorded provision of ₹{freq.provided_amount} for request {freq.request_id}"
        },
        after_state=serialized
    )

    return {
        "success": True,
        "message": f"Money provision of ₹{freq.provided_amount} recorded. Pending Breakfast Admin verification receipt.",
        "fundRequest": serialized
    }

@router.put("/requests/{id}/verify")
def post_verify_fund_receipt(
    id: str,
    payload: VerifyFundReceiptPayload,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.money.receipt.verify")),
    db: Session = Depends(get_db)
):
    result = money_service.verify_fund_receipt(
        request_id=id,
        verified_amount=payload.verifiedAmount,
        difference_note=payload.differenceNote,
        verified_by=current_user.name,
        db=db
    )
    freq = result["request"]
    txn = result["transaction"]
    new_bal = result["newBalance"]

    serialized_freq = serialize_fund_request(freq)
    serialized_txn = serialize_transaction(txn)

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_MONEY_RECEIPT_VERIFIED",
        request=request,
        target_info={
            "requestId": freq.request_id,
            "verifiedAmount": freq.verified_amount,
            "newBalance": new_bal,
            "verifiedBy": current_user.name,
            "details": f"Verified receipt of ₹{freq.verified_amount} for {freq.request_id}. Available balance updated to ₹{new_bal}"
        },
        after_state=serialized_freq
    )

    return {
        "success": True,
        "message": f"Receipt of ₹{freq.verified_amount} verified successfully. New Available Balance: ₹{new_bal}",
        "fundRequest": serialized_freq,
        "transaction": serialized_txn,
        "newBalance": new_bal
    }

@router.post("/receive")
def post_receive_money(
    payload: ReceiveMoneyPayload,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.money.receive")),
    db: Session = Depends(get_db)
):
    txn, new_bal = money_service.record_money_received(
        transaction_date=payload.transactionDate,
        transaction_time=payload.transactionTime,
        amount=payload.amount,
        source=payload.source or "Finance Team",
        note=payload.note or "",
        created_by=current_user.name,
        db=db
    )
    serialized_txn = serialize_transaction(txn)

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_MONEY_RECEIVED",
        request=request,
        target_info={
            "transactionId": txn.transaction_id,
            "amount": txn.amount,
            "source": txn.source,
            "newBalance": new_bal,
            "details": f"Received ₹{txn.amount} from {txn.source}"
        },
        after_state=serialized_txn
    )

    return {
        "success": True,
        "message": f"Successfully recorded ₹{txn.amount} received from {txn.source}",
        "transaction": serialized_txn,
        "newBalance": new_bal
    }

@router.post("/expense")
def post_record_expense(
    payload: RecordExpensePayload,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("breakfast.money.expense.create")),
    db: Session = Depends(get_db)
):
    txn, new_bal = money_service.record_expense(
        transaction_date=payload.transactionDate,
        transaction_time=payload.transactionTime,
        amount=payload.amount,
        source=payload.source or "Manual Expense",
        reference_type="MANUAL_EXPENSE",
        expense_category=payload.expenseCategory or "OTHER_BREAKFAST_EXPENSE",
        expense_purpose=payload.expensePurpose or "EMPLOYEE",
        description=payload.description or "",
        note=payload.note or "",
        created_by=current_user.name,
        db=db
    )
    serialized_txn = serialize_transaction(txn)

    audit_service = AuditService(db)
    audit_service.log(
        action="BREAKFAST_EXPENSE_CREATED",
        request=request,
        target_info={
            "transactionId": txn.transaction_id,
            "amount": txn.amount,
            "newBalance": new_bal,
            "details": f"Recorded manual expense of ₹{txn.amount} ({payload.description or 'No description'})"
        },
        after_state=serialized_txn
    )

    return {
        "success": True,
        "message": f"Successfully recorded expense of ₹{txn.amount}",
        "transaction": serialized_txn,
        "newBalance": new_bal
    }

@router.get("/transactions")
def get_transactions(
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_permission("breakfast.money.view")),
    db: Session = Depends(get_db)
):
    q = db.query(BreakfastMoneyTransaction)
    if startDate and endDate:
        q = q.filter(BreakfastMoneyTransaction.transaction_date >= startDate, BreakfastMoneyTransaction.transaction_date <= endDate)
    elif startDate:
        q = q.filter(BreakfastMoneyTransaction.transaction_date >= startDate)
    elif endDate:
        q = q.filter(BreakfastMoneyTransaction.transaction_date <= endDate)

    if type and type != "ALL":
        q = q.filter(BreakfastMoneyTransaction.type == type)

    txns = q.order_by(desc(BreakfastMoneyTransaction.created_at)).all()

    if search and search.strip():
        s = search.strip().lower()
        txns = [
            t for t in txns
            if s in t.transaction_id.lower()
            or s in t.description.lower()
            or s in t.source.lower()
            or (t.created_by and s in t.created_by.lower())
        ]

    metrics = money_service.get_money_balance_metrics(db)
    return {
        "success": True,
        "metrics": metrics,
        "transactions": [serialize_transaction(t) for t in txns]
    }

@router.get("/statement/daily")
def get_daily_statement(
    date: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_permission("breakfast.money.report")),
    db: Session = Depends(get_db)
):
    target_date = date or get_kolkata_date_string()
    stmt = money_service.get_daily_money_statement(target_date, db)
    return {"success": True, "statement": stmt}

@router.get("/statement/monthly")
def get_monthly_statement(
    month: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_permission("breakfast.money.report")),
    db: Session = Depends(get_db)
):
    target_month = month or get_kolkata_date_string()[:7]
    stmt = money_service.get_monthly_money_statement(target_month, db)
    return {"success": True, "statement": stmt}
