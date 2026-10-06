from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_permission, require_any_permission, require_role, CurrentUser
from app.reports.service import ReportService
from app.reports.excel_generator import generate_report_excel
from datetime import datetime

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/years")
def get_years(
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.report", "breakfast.money.report"])),
    db: Session = Depends(get_db)
):
    service = ReportService(db)
    result = service.get_available_years()
    return {"success": True, **result}

@router.get("/monthly")
def get_monthly_report(
    year: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.report", "breakfast.money.report"])),
    db: Session = Depends(get_db)
):
    service = ReportService(db)
    result = service.build_report_data(year=year, month=month, department=department)
    return {"success": True, **result}

@router.get("/export-excel")
def export_monthly_report_excel(
    year: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_any_permission(["breakfast.report", "breakfast.money.report"])),
    db: Session = Depends(get_db)
):
    service = ReportService(db)
    data = service.build_report_data(year=year, month=month, department=department)
    excel_stream = generate_report_excel(data)

    year_label = "All_Years" if data.get("selectedYear") == "all" else data.get("selectedYear", "")
    filename = f"Breakfast_Money_Report_{year_label}_{int(datetime.now().timestamp()*1000)}.xlsx"

    return StreamingResponse(
        excel_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/ceo")
def get_ceo_report(
    date: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_role("CEO")),
    db: Session = Depends(get_db)
):
    service = ReportService(db)
    result = service.get_ceo_report(target_date=date)
    return {"success": True, **result}


@router.get("/director-analytics")
def get_director_analytics_report(
    date: Optional[str] = Query(None),
    current_user: CurrentUser = Depends(require_role("DIRECTOR_ANALYTICS")),
    db: Session = Depends(get_db)
):
    service = ReportService(db)
    result = service.get_ceo_report(target_date=date)
    return {"success": True, **result}
