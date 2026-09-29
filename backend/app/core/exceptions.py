from typing import Any, Optional, Dict
from fastapi import HTTPException, status


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        message: str = "An error occurred",
        error_code: str = "APP_ERROR",
        details: Optional[Any] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.error_code = error_code
        self.details = details
        self.extra_fields = extra_fields or {}


class AuthenticationError(AppException):
    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            error_code="AUTHENTICATION_FAILED"
        )


class PermissionDeniedError(AppException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            error_code="PERMISSION_DENIED"
        )


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            error_code="NOT_FOUND"
        )


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", details: Optional[Any] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            error_code="VALIDATION_ERROR",
            details=details
        )


class InsufficientFundError(AppException):
    def __init__(
        self,
        available: float,
        required: float,
        shortfall: float,
        message: Optional[str] = None
    ):
        msg = message or f"Insufficient breakfast fund balance. Available: ₹{available:.2f}, Required: ₹{required:.2f}, Shortfall: ₹{shortfall:.2f}"
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=msg,
            error_code="INSUFFICIENT_FUNDS",
            extra_fields={
                "isInsufficient": True,
                "available": available,
                "required": required,
                "shortfall": shortfall,
            }
        )


class FundLimitExceededError(AppException):
    def __init__(
        self,
        fund_limit: float,
        current_balance: float,
        requested_amount: float,
        message: Optional[str] = None
    ):
        msg = message or f"Requested amount ₹{requested_amount} exceeds allowable fund limit (Limit: ₹{fund_limit}, Current: ₹{current_balance})"
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=msg,
            error_code="FUND_LIMIT_EXCEEDED",
            extra_fields={
                "exceedsLimit": True,
                "fundLimit": fund_limit,
                "currentBalance": current_balance,
                "requestedAmount": requested_amount
            }
        )
