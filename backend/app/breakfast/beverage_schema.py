from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class BeverageCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Beverage name (e.g. Tea, Coffee)")
    description: Optional[str] = Field(None, max_length=500)
    displayOrder: int = Field(0, description="Sorting display order")
    isActive: bool = Field(True, description="Whether beverage is active for orders")
    unit: str = Field("Cups", description="Measurement unit (strictly Cups)")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        if v.strip().lower() != "cups":
            raise ValueError("All beverages strictly use 'Cups' as unit of measurement.")
        return "Cups"

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Beverage name cannot be empty.")
        return clean


class BeverageUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    displayOrder: Optional[int] = None
    isActive: Optional[bool] = None
    unit: Optional[str] = Field("Cups", description="Measurement unit (strictly Cups)")

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip().lower() != "cups":
            raise ValueError("All beverages strictly use 'Cups' as unit of measurement.")
        return "Cups"

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("Beverage name cannot be empty.")
            return clean
        return v


class BeverageStatusUpdateRequest(BaseModel):
    isActive: bool


class BeverageItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    unit: str = "Cups"
    displayOrder: int = 0
    isActive: bool = True
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class BeverageEntrySubmitRequest(BaseModel):
    beverageId: str = Field(..., min_length=1, description="ID of active beverage")
    session: str = Field(..., description="Session: MORNING or EVENING")
    quantity: int = Field(..., description="Number of cups consumed (positive integer >= 1)")
    businessDate: Optional[str] = Field(None, description="Must be today's date in Asia/Kolkata if specified")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("session")
    @classmethod
    def validate_session(cls, v: str) -> str:
        upper = v.strip().upper()
        if upper not in ("MORNING", "EVENING"):
            raise ValueError("Session must be either 'MORNING' or 'EVENING'.")
        return upper

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError("Quantity must be a positive integer.")
        if v <= 0:
            raise ValueError("Quantity must be a positive integer greater than zero (minimum 1 cup).")
        return v


class BeverageAdminEntryCreateRequest(BaseModel):
    employeeId: str = Field(..., min_length=1, description="Employee code e.g. EMP001")
    beverageId: str = Field(..., min_length=1, description="ID of configured beverage")
    businessDate: str = Field(..., description="Target business date (YYYY-MM-DD)")
    session: str = Field(..., description="Session: MORNING or EVENING")
    quantity: int = Field(..., description="Positive integer cups >= 1")
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("session")
    @classmethod
    def validate_session(cls, v: str) -> str:
        upper = v.strip().upper()
        if upper not in ("MORNING", "EVENING"):
            raise ValueError("Session must be either 'MORNING' or 'EVENING'.")
        return upper

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError("Quantity must be a positive integer.")
        if v <= 0:
            raise ValueError("Quantity must be a positive integer greater than zero (minimum 1 cup).")
        return v

    @field_validator("businessDate")
    @classmethod
    def validate_business_date(cls, v: str) -> str:
        clean = v.strip()
        from datetime import datetime
        try:
            datetime.strptime(clean, "%Y-%m-%d")
        except Exception:
            raise ValueError("Invalid businessDate format. Expected YYYY-MM-DD.")
        return clean


class BeverageAdminEntryUpdateRequest(BaseModel):
    beverageId: Optional[str] = None
    session: Optional[str] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("session")
    @classmethod
    def validate_session(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            upper = v.strip().upper()
            if upper not in ("MORNING", "EVENING"):
                raise ValueError("Session must be either 'MORNING' or 'EVENING'.")
            return upper
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if not isinstance(v, int) or isinstance(v, bool):
                raise ValueError("Quantity must be a positive integer.")
            if v <= 0:
                raise ValueError("Quantity must be a positive integer greater than zero (minimum 1 cup).")
        return v


class BeverageAdminEntryDeleteRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500, description="Reason for soft-deleting entry")


class BeverageEntryResponse(BaseModel):
    id: str
    employeeId: str
    employeeNameSnapshot: str
    beverageId: str
    beverageNameSnapshot: str
    businessDate: str
    session: str
    quantity: int
    unit: str = "Cups"
    source: str = "EMPLOYEE"
    notes: Optional[str] = None
    isDeleted: bool = False
    deletedAt: Optional[str] = None
    deletedBy: Optional[str] = None
    deletionReason: Optional[str] = None
    createdBy: Optional[str] = None
    updatedBy: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None
