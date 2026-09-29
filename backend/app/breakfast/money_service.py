import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from app.breakfast.model import (
    BreakfastMoneyTransaction,
    BreakfastFundRequest,
    BreakfastSetting
)
from app.breakfast.date_utils import get_kolkata_date_string, get_kolkata_now
from app.core.exceptions import ValidationError, InsufficientFundError, FundLimitExceededError, NotFoundError

def get_fund_limit(db: Session) -> float:
    setting = db.query(BreakfastSetting).first()
    return float(setting.breakfast_fund_limit) if setting and setting.breakfast_fund_limit else 2500.0

def get_money_balance_metrics(db: Session) -> Dict[str, Any]:
    fund_limit = get_fund_limit(db)

    latest_txn = db.query(BreakfastMoneyTransaction).order_by(
        desc(BreakfastMoneyTransaction.created_at)
    ).first()
    current_balance = float(latest_txn.balance_after_transaction) if latest_txn else 0.0

    totals = db.query(
        BreakfastMoneyTransaction.type,
        func.sum(BreakfastMoneyTransaction.amount)
    ).group_by(BreakfastMoneyTransaction.type).all()

    total_received = 0.0
    total_spent = 0.0
    total_adjustments = 0.0
    total_reversals = 0.0

    for txn_type, amt_sum in totals:
        val = float(amt_sum or 0.0)
        if txn_type == "MONEY_RECEIVED":
            total_received = val
        elif txn_type == "BREAKFAST_EXPENSE":
            total_spent = val
        elif txn_type == "ADJUSTMENT":
            total_adjustments = val
        elif txn_type == "REVERSAL":
            total_reversals = val

    recommended_request = max(0.0, fund_limit - current_balance)
    low_balance_warning = current_balance < 100.0

    return {
        "fundLimit": fund_limit,
        "currentBalance": current_balance,
        "totalReceived": total_received,
        "totalSpent": total_spent,
        "totalAdjustments": total_adjustments,
        "totalReversals": total_reversals,
        "recommendedRequest": recommended_request,
        "lowBalanceWarning": low_balance_warning
    }

def record_money_received(
    transaction_date: Optional[str],
    transaction_time: Optional[str],
    amount: float,
    source: str = "Finance Team",
    reference_type: str = "MONEY_RECEIVED",
    reference_id: Optional[str] = None,
    note: str = "",
    created_by: str = "System",
    db: Session = None
) -> Tuple[BreakfastMoneyTransaction, float]:
    parsed_amount = float(amount)
    if parsed_amount <= 0:
        raise ValidationError("Amount must be a positive number")

    date_str = transaction_date or get_kolkata_date_string()
    time_str = transaction_time or get_kolkata_now().strftime("%I:%M %p")

    metrics = get_money_balance_metrics(db)
    new_balance = metrics["currentBalance"] + parsed_amount

    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    transaction_id = f"TXN-RECV-{date_str.replace('-', '')}-{str(now_ts)[-6:]}"

    txn = BreakfastMoneyTransaction(
        transaction_id=transaction_id,
        transaction_date=date_str,
        transaction_time=time_str,
        type="MONEY_RECEIVED",
        amount=parsed_amount,
        balance_after_transaction=new_balance,
        source=source,
        reference_type=reference_type,
        reference_id=reference_id or transaction_id,
        expense_category="MONEY_RECEIVED",
        description=f"Received ₹{parsed_amount:,.2f} from {source}",
        note=note or "",
        created_by=created_by,
        created_at=datetime.now(timezone.utc)
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return txn, new_balance

def record_expense(
    transaction_date: Optional[str],
    transaction_time: Optional[str],
    amount: float,
    source: str = "Breakfast Operations",
    reference_type: str = "MANUAL_EXPENSE",
    reference_id: Optional[str] = None,
    expense_category: str = "OTHER_BREAKFAST_EXPENSE",
    expense_purpose: str = "EMPLOYEE",
    description: str = "",
    note: str = "",
    created_by: str = "System",
    allow_negative: bool = False,
    db: Session = None
) -> Tuple[BreakfastMoneyTransaction, float]:
    parsed_amount = float(amount)
    if parsed_amount <= 0:
        raise ValidationError("Expense amount must be a positive number")

    metrics = get_money_balance_metrics(db)
    current_balance = metrics["currentBalance"]

    if not allow_negative and current_balance < parsed_amount:
        shortfall = parsed_amount - current_balance
        raise InsufficientFundError(available=current_balance, required=parsed_amount, shortfall=shortfall)

    date_str = transaction_date or get_kolkata_date_string()
    time_str = transaction_time or get_kolkata_now().strftime("%I:%M %p")

    new_balance = current_balance - parsed_amount
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    transaction_id = f"TXN-EXP-{date_str.replace('-', '')}-{str(now_ts)[-6:]}"

    txn = BreakfastMoneyTransaction(
        transaction_id=transaction_id,
        transaction_date=date_str,
        transaction_time=time_str,
        type="BREAKFAST_EXPENSE",
        amount=parsed_amount,
        balance_after_transaction=new_balance,
        source=source,
        reference_type=reference_type,
        reference_id=reference_id or transaction_id,
        expense_category=expense_category,
        expense_purpose=expense_purpose,
        description=description or f"Breakfast expense: ₹{parsed_amount:,.2f}",
        note=note or "",
        created_by=created_by,
        created_at=datetime.now(timezone.utc)
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return txn, new_balance

def process_daily_entry_expense(
    business_date: str,
    new_total_cost: float,
    created_by: str,
    db: Session
) -> Optional[BreakfastMoneyTransaction]:
    new_cost = float(new_total_cost)
    if new_cost <= 0:
        return None

    # Check for existing expense transaction for this daily entry
    existing_txn = db.query(BreakfastMoneyTransaction).filter(
        BreakfastMoneyTransaction.reference_type == "DAILY_ENTRY",
        BreakfastMoneyTransaction.reference_id == business_date
    ).order_by(desc(BreakfastMoneyTransaction.created_at)).first()

    metrics = get_money_balance_metrics(db)
    current_balance = metrics["currentBalance"]

    if not existing_txn:
        # Initial expense
        if current_balance < new_cost:
            raise InsufficientFundError(available=current_balance, required=new_cost, shortfall=new_cost - current_balance)

        txn, _ = record_expense(
            transaction_date=business_date,
            transaction_time="12:00 PM",
            amount=new_cost,
            source="Daily Breakfast Entry",
            reference_type="DAILY_ENTRY",
            reference_id=business_date,
            expense_category="DAILY_BREAKFAST",
            expense_purpose="EMPLOYEE",
            description=f"Daily breakfast expense for {business_date} (₹{new_cost:,.2f})",
            created_by=created_by,
            db=db
        )
        return txn
    else:
        # Update / difference
        previous_cost = float(existing_txn.amount)
        cost_diff = new_cost - previous_cost

        if cost_diff > 0:
            if current_balance < cost_diff:
                raise InsufficientFundError(available=current_balance, required=cost_diff, shortfall=cost_diff - current_balance)

            new_balance = current_balance - cost_diff
            now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
            txn_id = f"TXN-ADJ-{business_date.replace('-', '')}-{str(now_ts)[-6:]}"
            adj_txn = BreakfastMoneyTransaction(
                transaction_id=txn_id,
                transaction_date=business_date,
                transaction_time=get_kolkata_now().strftime("%I:%M %p"),
                type="BREAKFAST_EXPENSE",
                amount=cost_diff,
                balance_after_transaction=new_balance,
                source="Daily Breakfast Entry (Update)",
                reference_type="DAILY_ENTRY",
                reference_id=business_date,
                expense_category="DAILY_BREAKFAST",
                expense_purpose="EMPLOYEE",
                description=f"Additional expense for daily entry {business_date} (₹{previous_cost:,.2f} -> ₹{new_cost:,.2f})",
                created_by=created_by,
                created_at=datetime.now(timezone.utc)
            )
            db.add(adj_txn)
            db.commit()
            db.refresh(adj_txn)
            return adj_txn
        elif cost_diff < 0:
            refund_amount = abs(cost_diff)
            new_balance = current_balance + refund_amount
            now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
            txn_id = f"TXN-REV-{business_date.replace('-', '')}-{str(now_ts)[-6:]}"
            rev_txn = BreakfastMoneyTransaction(
                transaction_id=txn_id,
                transaction_date=business_date,
                transaction_time=get_kolkata_now().strftime("%I:%M %p"),
                type="REVERSAL",
                amount=refund_amount,
                balance_after_transaction=new_balance,
                source="Daily Breakfast Entry (Cost Reduction)",
                reference_type="DAILY_ENTRY",
                reference_id=business_date,
                expense_category="DAILY_BREAKFAST",
                expense_purpose="EMPLOYEE",
                description=f"Reversal for reduced daily entry cost on {business_date} (₹{previous_cost:,.2f} -> ₹{new_cost:,.2f})",
                created_by=created_by,
                created_at=datetime.now(timezone.utc)
            )
            db.add(rev_txn)
            db.commit()
            db.refresh(rev_txn)
            return rev_txn
        return existing_txn

def process_additional_order_expense(
    order_id: str,
    business_date: str,
    order_title: str,
    total_cost: float,
    created_by: str,
    db: Session
) -> Optional[BreakfastMoneyTransaction]:
    cost = float(total_cost)
    if cost <= 0:
        return None

    metrics = get_money_balance_metrics(db)
    if metrics["currentBalance"] < cost:
        raise InsufficientFundError(available=metrics["currentBalance"], required=cost, shortfall=cost - metrics["currentBalance"])

    txn, _ = record_expense(
        transaction_date=business_date,
        transaction_time=get_kolkata_now().strftime("%I:%M %p"),
        amount=cost,
        source=f"Additional Order: {order_title}",
        reference_type="ADDITIONAL_ORDER",
        reference_id=order_id,
        expense_category="ADDITIONAL_ORDER",
        expense_purpose="EMPLOYEE",
        description=f"Additional order ({order_title}) on {business_date} - ₹{cost:,.2f}",
        created_by=created_by,
        db=db
    )
    return txn

def process_additional_order_update(
    order_id: str,
    business_date: str,
    order_title: str,
    new_total_cost: float,
    created_by: str,
    db: Session
) -> Dict[str, Any]:
    new_cost = float(new_total_cost)

    existing_txns = db.query(BreakfastMoneyTransaction).filter(
        BreakfastMoneyTransaction.reference_type == "ADDITIONAL_ORDER",
        BreakfastMoneyTransaction.reference_id == order_id
    ).all()

    total_previously_charged = 0.0
    for t in existing_txns:
        if t.type in ["BREAKFAST_EXPENSE", "ADJUSTMENT"]:
            total_previously_charged += t.amount
        elif t.type == "REVERSAL":
            total_previously_charged -= t.amount

    cost_diff = new_cost - total_previously_charged
    metrics = get_money_balance_metrics(db)

    if cost_diff > 0:
        if metrics["currentBalance"] < cost_diff:
            raise InsufficientFundError(available=metrics["currentBalance"], required=cost_diff, shortfall=cost_diff - metrics["currentBalance"])

        new_balance = metrics["currentBalance"] - cost_diff
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        txn_id = f"TXN-ADJ-{business_date.replace('-', '')}-{str(now_ts)[-6:]}"
        adj_txn = BreakfastMoneyTransaction(
            transaction_id=txn_id,
            transaction_date=business_date,
            transaction_time=get_kolkata_now().strftime("%I:%M %p"),
            type="ADJUSTMENT",
            amount=cost_diff,
            balance_after_transaction=new_balance,
            source=f"Additional Order Adjustment ({order_title})",
            reference_type="ADDITIONAL_ORDER",
            reference_id=order_id,
            expense_category="ADDITIONAL_ORDER",
            expense_purpose="EMPLOYEE",
            description=f"Adjustment for order {order_id} (+₹{cost_diff:,.2f})",
            created_by=created_by,
            created_at=datetime.now(timezone.utc)
        )
        db.add(adj_txn)
        db.commit()
        return {"adjusted": True, "financialImpact": cost_diff}

    elif cost_diff < 0:
        refund_amount = abs(cost_diff)
        new_balance = metrics["currentBalance"] + refund_amount
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        txn_id = f"TXN-REV-{business_date.replace('-', '')}-{str(now_ts)[-6:]}"
        rev_txn = BreakfastMoneyTransaction(
            transaction_id=txn_id,
            transaction_date=business_date,
            transaction_time=get_kolkata_now().strftime("%I:%M %p"),
            type="REVERSAL",
            amount=refund_amount,
            balance_after_transaction=new_balance,
            source=f"Additional Order Reversal ({order_title})",
            reference_type="ADDITIONAL_ORDER",
            reference_id=order_id,
            expense_category="ADDITIONAL_ORDER",
            expense_purpose="EMPLOYEE",
            description=f"Reversal for order {order_id} (-₹{refund_amount:,.2f})",
            created_by=created_by,
            created_at=datetime.now(timezone.utc)
        )
        db.add(rev_txn)
        db.commit()
        return {"adjusted": True, "financialImpact": cost_diff}

    return {"adjusted": False, "financialImpact": 0.0}

def reverse_additional_order_expense(
    order_id: str,
    business_date: str,
    order_title: str,
    created_by: str,
    db: Session
) -> Optional[Dict[str, Any]]:
    existing_txns = db.query(BreakfastMoneyTransaction).filter(
        BreakfastMoneyTransaction.reference_type == "ADDITIONAL_ORDER",
        BreakfastMoneyTransaction.reference_id == order_id
    ).all()

    total_spent = 0.0
    for t in existing_txns:
        if t.type in ["BREAKFAST_EXPENSE", "ADJUSTMENT"]:
            total_spent += t.amount
        elif t.type == "REVERSAL":
            total_spent -= t.amount

    if total_spent <= 0:
        return None

    metrics = get_money_balance_metrics(db)
    new_balance = metrics["currentBalance"] + total_spent

    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    txn_id = f"TXN-REV-{business_date.replace('-', '')}-{str(now_ts)[-6:]}"

    rev_txn = BreakfastMoneyTransaction(
        transaction_id=txn_id,
        transaction_date=business_date,
        transaction_time=get_kolkata_now().strftime("%I:%M %p"),
        type="REVERSAL",
        amount=total_spent,
        balance_after_transaction=new_balance,
        source=f"Order Deletion Reversal ({order_title})",
        reference_type="ADDITIONAL_ORDER",
        reference_id=order_id,
        expense_category="ADDITIONAL_ORDER",
        expense_purpose="EMPLOYEE",
        description=f"Reversal of ₹{total_spent:,.2f} for deleted order {order_id}",
        created_by=created_by,
        created_at=datetime.now(timezone.utc)
    )
    db.add(rev_txn)
    db.commit()
    db.refresh(rev_txn)

    return {"newBalance": new_balance, "reversalAmount": total_spent}

def create_fund_request(
    requested_amount: float,
    reason: str,
    requested_by: str,
    db: Session
) -> BreakfastFundRequest:
    amt = float(requested_amount)
    if amt <= 0:
        raise ValidationError("Requested amount must be greater than 0")

    fund_limit = get_fund_limit(db)
    metrics = get_money_balance_metrics(db)
    current_balance = metrics["currentBalance"]

    if (current_balance + amt) > fund_limit:
        raise FundLimitExceededError(
            fund_limit=fund_limit,
            current_balance=current_balance,
            requested_amount=amt
        )

    # Check for active existing requests
    existing = get_active_fund_request(db)
    if existing:
        raise ValidationError(f"There is already an active fund request ({existing.request_id}) with status {existing.status}")

    now_kolkata = get_kolkata_now()
    date_str = now_kolkata.strftime("%Y-%m-%d")
    time_str = now_kolkata.strftime("%I:%M %p")
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    request_id = f"REQ-{date_str.replace('-', '')}-{str(now_ts)[-4:]}"

    freq = BreakfastFundRequest(
        request_id=request_id,
        requested_by=requested_by,
        request_date=date_str,
        request_time=time_str,
        current_balance=current_balance,
        fund_limit=fund_limit,
        requested_amount=amt,
        expected_balance=current_balance + amt,
        reason=reason or "",
        status="PENDING_APPROVAL",
        created_at=datetime.now(timezone.utc)
    )
    db.add(freq)
    db.commit()
    db.refresh(freq)

    return freq

def get_active_fund_request(db: Session) -> Optional[BreakfastFundRequest]:
    active_statuses = [
        "SUBMITTED",
        "PENDING_APPROVAL",
        "APPROVED",
        "MONEY_PROVIDED",
        "RECEIPT_PENDING"
    ]
    return db.query(BreakfastFundRequest).filter(
        BreakfastFundRequest.status.in_(active_statuses)
    ).order_by(desc(BreakfastFundRequest.created_at)).first()

def get_fund_requests(status: Optional[str], search: Optional[str], db: Session) -> List[BreakfastFundRequest]:
    q = db.query(BreakfastFundRequest)
    if status and status != "ALL":
        q = q.filter(BreakfastFundRequest.status == status)
    if search and search.strip():
        s = f"%{search.strip()}%"
        q = q.filter(
            or_(
                BreakfastFundRequest.request_id.ilike(s),
                BreakfastFundRequest.requested_by.ilike(s),
                BreakfastFundRequest.reason.ilike(s)
            )
        )
    return q.order_by(desc(BreakfastFundRequest.created_at)).all()

def approve_fund_request(
    request_id: str,
    approved_amount: Optional[float],
    approved_by: str,
    db: Session
) -> BreakfastFundRequest:
    freq = db.query(BreakfastFundRequest).filter(BreakfastFundRequest.request_id == request_id).first()
    if not freq:
        raise NotFoundError("Fund request not found")

    amt = float(approved_amount) if approved_amount is not None else float(freq.requested_amount)
    if amt <= 0:
        raise ValidationError("Approved amount must be greater than 0")

    freq.status = "APPROVED"
    freq.approved_amount = amt
    freq.approved_by = approved_by
    freq.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(freq)

    return freq

def reject_fund_request(
    request_id: str,
    rejection_reason: str,
    rejected_by: str,
    db: Session
) -> BreakfastFundRequest:
    freq = db.query(BreakfastFundRequest).filter(BreakfastFundRequest.request_id == request_id).first()
    if not freq:
        raise NotFoundError("Fund request not found")

    freq.status = "REJECTED"
    freq.rejection_reason = rejection_reason
    db.commit()
    db.refresh(freq)

    return freq

def provide_fund_money(
    request_id: str,
    provided_amount: float,
    provided_date: Optional[str],
    provided_time: Optional[str],
    reference: Optional[str],
    note: Optional[str],
    provided_by: str,
    db: Session
) -> BreakfastFundRequest:
    freq = db.query(BreakfastFundRequest).filter(BreakfastFundRequest.request_id == request_id).first()
    if not freq:
        raise NotFoundError("Fund request not found")

    amt = float(provided_amount)
    if amt <= 0:
        raise ValidationError("Provided amount must be greater than 0")

    freq.status = "RECEIPT_PENDING"
    freq.provided_amount = amt
    freq.provided_by = provided_by
    freq.provided_at = datetime.now(timezone.utc)
    freq.provided_date = provided_date or get_kolkata_date_string()
    freq.provided_time = provided_time or get_kolkata_now().strftime("%I:%M %p")
    freq.reference = reference
    freq.provided_note = note
    db.commit()
    db.refresh(freq)

    return freq

def verify_fund_receipt(
    request_id: str,
    verified_amount: float,
    difference_note: Optional[str],
    verified_by: str,
    db: Session
) -> Dict[str, Any]:
    freq = db.query(BreakfastFundRequest).filter(BreakfastFundRequest.request_id == request_id).first()
    if not freq:
        raise NotFoundError("Fund request not found")

    amt = float(verified_amount)
    if amt <= 0:
        raise ValidationError("Verified amount must be greater than 0")

    freq.status = "RECEIVED_VERIFIED"
    freq.verified_amount = amt
    freq.verified_by = verified_by
    freq.verified_at = datetime.now(timezone.utc)

    provided = float(freq.provided_amount or freq.approved_amount or freq.requested_amount)
    diff = amt - provided
    freq.difference_reported = {
        "reported": diff != 0,
        "expectedAmount": provided,
        "receivedAmount": amt,
        "differenceAmount": diff,
        "note": difference_note or ""
    }
    db.commit()

    # Create MONEY_RECEIVED transaction into ledger
    txn, new_balance = record_money_received(
        transaction_date=freq.provided_date or get_kolkata_date_string(),
        transaction_time=freq.provided_time or get_kolkata_now().strftime("%I:%M %p"),
        amount=amt,
        source="Finance Replenishment",
        reference_type="BREAKFAST_FUND_REQUEST",
        reference_id=freq.request_id,
        note=f"Replenishment verified by {verified_by}. {difference_note or ''}".strip(),
        created_by=verified_by,
        db=db
    )

    return {"request": freq, "transaction": txn, "newBalance": new_balance}

def get_daily_money_statement(target_date: str, db: Session) -> Dict[str, Any]:
    # Prior closing balance
    prior_txn = db.query(BreakfastMoneyTransaction).filter(
        BreakfastMoneyTransaction.transaction_date < target_date
    ).order_by(desc(BreakfastMoneyTransaction.created_at)).first()
    opening_balance = float(prior_txn.balance_after_transaction) if prior_txn else 0.0

    txns = db.query(BreakfastMoneyTransaction).filter(
        BreakfastMoneyTransaction.transaction_date == target_date
    ).order_by(BreakfastMoneyTransaction.created_at.asc()).all()

    money_received = sum(t.amount for t in txns if t.type == "MONEY_RECEIVED")
    expenses = sum(t.amount for t in txns if t.type == "BREAKFAST_EXPENSE")
    adjustments = sum(t.amount for t in txns if t.type == "ADJUSTMENT")
    reversals = sum(t.amount for t in txns if t.type == "REVERSAL")

    net_spent = expenses - (adjustments + reversals)

    latest_day_txn = txns[-1] if txns else None
    closing_balance = float(latest_day_txn.balance_after_transaction) if latest_day_txn else (opening_balance + money_received - net_spent)

    return {
        "date": target_date,
        "openingBalance": opening_balance,
        "moneyReceived": money_received,
        "expenses": expenses,
        "adjustments": adjustments,
        "reversals": reversals,
        "netSpent": net_spent,
        "closingBalance": closing_balance,
        "transactions": [
            {
                "transactionId": t.transaction_id,
                "time": t.transaction_time,
                "type": t.type,
                "amount": t.amount,
                "balanceAfter": t.balance_after_transaction,
                "description": t.description,
                "source": t.source
            }
            for t in txns
        ]
    }

def get_monthly_money_statement(target_month: str, db: Session) -> Dict[str, Any]:
    start_date = f"{target_month}-01"
    end_date = f"{target_month}-31"

    prior_txn = db.query(BreakfastMoneyTransaction).filter(
        BreakfastMoneyTransaction.transaction_date < start_date
    ).order_by(desc(BreakfastMoneyTransaction.created_at)).first()
    opening_balance = float(prior_txn.balance_after_transaction) if prior_txn else 0.0

    txns = db.query(BreakfastMoneyTransaction).filter(
        BreakfastMoneyTransaction.transaction_date >= start_date,
        BreakfastMoneyTransaction.transaction_date <= end_date
    ).order_by(BreakfastMoneyTransaction.created_at.asc()).all()

    money_received = sum(t.amount for t in txns if t.type == "MONEY_RECEIVED")
    expenses = sum(t.amount for t in txns if t.type == "BREAKFAST_EXPENSE")
    adjustments = sum(t.amount for t in txns if t.type == "ADJUSTMENT")
    reversals = sum(t.amount for t in txns if t.type == "REVERSAL")

    net_spent = expenses - (adjustments + reversals)

    latest_month_txn = txns[-1] if txns else None
    closing_balance = float(latest_month_txn.balance_after_transaction) if latest_month_txn else (opening_balance + money_received - net_spent)

    return {
        "month": target_month,
        "openingBalance": opening_balance,
        "moneyReceived": money_received,
        "expenses": expenses,
        "adjustments": adjustments,
        "reversals": reversals,
        "netSpent": net_spent,
        "closingBalance": closing_balance,
        "transactionCount": len(txns)
    }
