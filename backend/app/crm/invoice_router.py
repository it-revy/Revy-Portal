import os
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Any

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.users.model import User
from app.crm.invoice_service import ProformaInvoiceService
from app.crm.invoice_schema import (
    CompanySettingsResponse,
    CompanySettingsUpdate,
    ProformaInvoicePreviewRequest,
    ProformaInvoiceCreate,
    ProformaInvoiceRevisionCreate,
    ProformaInvoiceUpdate,
    ProformaInvoiceDetailResponse,
    ProformaInvoiceRevisionResponse,
    CollateralListResponse
)
from app.crm.permissions import require_crm_read, require_crm_write

router = APIRouter(prefix="/crm", tags=["CRM Collateral & Proforma Invoices"])


# =============================================================================
# 1. COMPANY & INVOICE SETTINGS
# =============================================================================
@router.get("/company-settings", response_model=CompanySettingsResponse)
def get_company_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_read)
):
    service = ProformaInvoiceService(db)
    settings = service.get_company_settings()
    return settings


@router.put("/company-settings", response_model=CompanySettingsResponse)
def update_company_settings(
    payload: CompanySettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_write)
):
    service = ProformaInvoiceService(db)
    try:
        updated = service.update_company_settings(current_user, payload, request)
        return updated
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/company-settings/signature", response_model=CompanySettingsResponse)
async def upload_company_signature(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_write)
):
    service = ProformaInvoiceService(db)
    try:
        content = await file.read()
        updated = service.upload_signature_image(
            actor=current_user,
            file_bytes=content,
            filename=file.filename or "signature.png",
            content_type=file.content_type or "image/png",
            request=request
        )
        return updated
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/company-settings/signature", response_model=CompanySettingsResponse)
def delete_company_signature(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_write)
):
    service = ProformaInvoiceService(db)
    try:
        updated = service.delete_signature_image(actor=current_user, request=request)
        return updated
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/company-settings/signature/image")
def get_company_signature_image(
    db: Session = Depends(get_db)
):
    """Publicly servable signature image endpoint for invoices and company settings preview."""
    service = ProformaInvoiceService(db)
    settings = service.get_company_settings()
    if not settings.signature_image_url:
        raise HTTPException(status_code=404, detail="No signature image has been configured.")

    # 1. Check uploads/signatures for latest uploaded image
    uploads_dir = os.path.join(os.path.abspath("uploads"), "signatures")
    if os.path.exists(uploads_dir):
        sig_files = sorted(
            [os.path.join(uploads_dir, f) for f in os.listdir(uploads_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))],
            key=lambda p: os.path.getmtime(p),
            reverse=True
        )
        if sig_files:
            latest = sig_files[0]
            ext = os.path.splitext(latest)[1].lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            with open(latest, "rb") as f:
                data = f.read()
            return Response(content=data, media_type=mime, headers={"Cache-Control": "public, max-age=86400"})

    # 2. Check static default image
    static_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images", "signature.png")
    if os.path.exists(static_file):
        with open(static_file, "rb") as f:
            data = f.read()
        return Response(content=data, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

    raise HTTPException(status_code=404, detail="Signature image file not found.")


# =============================================================================
# 2. COLLATERAL VIEWS
# =============================================================================
@router.get("/collateral", response_model=CollateralListResponse)
def get_collateral(
    view: str = Query("all", regex="^(all|quotations|invoices)$"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_read)
):
    service = ProformaInvoiceService(db)
    result = service.get_collateral_summary(view_type=view, search=search, page=page, page_size=page_size)
    return result


# =============================================================================
# 3. PROFORMA INVOICE PREVIEW (NO SEQUENCE NUMBER CONSUMED)
# =============================================================================
@router.post("/proforma-invoices/preview")
def preview_proforma_invoice(
    payload: ProformaInvoicePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_read)
):
    service = ProformaInvoiceService(db)
    try:
        preview = service.preview_proforma_invoice(current_user, payload)
        return preview
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/proforma-invoices/preview-tab", response_class=HTMLResponse)
def preview_proforma_invoice_tab(
    payload: ProformaInvoicePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_read)
):
    """
    Renders preview directly as HTML for opening in a new browser tab.
    """
    service = ProformaInvoiceService(db)
    try:
        preview = service.preview_proforma_invoice(current_user, payload)
        return HTMLResponse(content=preview["html"])
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# 4. CREATE / REVISE / DIRECT EDIT PROFORMA INVOICES
# =============================================================================
@router.post("/proforma-invoices")
def create_proforma_invoice(
    payload: ProformaInvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_write)
):
    service = ProformaInvoiceService(db)
    try:
        pi = service.create_proforma_invoice(current_user, payload, request)
        return {
            "success": True,
            "message": f"Proforma Invoice {pi.pi_number} created successfully.",
            "proformaInvoiceId": pi.id,
            "piNumber": pi.pi_number
        }
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/proforma-invoices/{pi_id}/revisions")
def create_proforma_invoice_revision(
    pi_id: str,
    payload: ProformaInvoiceRevisionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_write)
):
    service = ProformaInvoiceService(db)
    try:
        rev = service.create_invoice_revision(current_user, pi_id, payload, request)
        return {
            "success": True,
            "message": f"Revision {rev.revision_number} for {rev.pi_number} created successfully.",
            "revisionNumber": rev.revision_number,
            "proformaInvoiceId": pi_id
        }
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/proforma-invoices/{pi_id}")
def update_proforma_invoice(
    pi_id: str,
    payload: ProformaInvoiceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_write)
):
    service = ProformaInvoiceService(db)
    try:
        pi = service.update_proforma_invoice(current_user, pi_id, payload, request)
        return {
            "success": True,
            "message": f"Proforma Invoice {pi.pi_number} updated successfully.",
            "proformaInvoiceId": pi.id,
            "piNumber": pi.pi_number
        }
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proforma-invoices/{pi_id}")
def get_proforma_invoice(
    pi_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_read)
):
    service = ProformaInvoiceService(db)
    pi = service.get_proforma_invoice(pi_id)
    if not pi:
        raise HTTPException(status_code=404, detail=f"Proforma Invoice '{pi_id}' not found.")

    revisions_data = []
    for r in pi.revisions:
        revisions_data.append({
            "id": r.id,
            "proformaInvoiceId": r.proforma_invoice_id,
            "revisionNumber": r.revision_number,
            "piNumber": r.pi_number,
            "piDate": r.pi_date,
            "financialYear": r.financial_year,
            "status": r.status,
            "referenceNote": r.reference_note,
            "currency": r.currency,
            "subtotal": float(r.subtotal),
            "taxType": r.tax_type,
            "cgstRate": float(r.cgst_rate),
            "cgstAmount": float(r.cgst_amount),
            "sgstRate": float(r.sgst_rate),
            "sgstAmount": float(r.sgst_amount),
            "igstRate": float(r.igst_rate),
            "igstAmount": float(r.igst_amount),
            "totalTax": float(r.total_tax),
            "grandTotal": float(r.grand_total),
            "companySnapshot": r.company_snapshot,
            "customerSnapshot": r.customer_snapshot,
            "termsSnapshot": r.terms_snapshot,
            "notes": r.notes,
            "createdAt": r.created_at,
            "items": [
                {
                    "id": it.id,
                    "srNo": it.sr_no,
                    "itemType": it.item_type,
                    "serviceId": it.service_id,
                    "packageId": it.package_id,
                    "itemCode": it.item_code,
                    "name": it.item_name,
                    "description": it.description,
                    "quantity": float(it.quantity),
                    "unit": it.unit,
                    "rate": float(it.rate),
                    "amount": float(it.amount),
                    "notes": it.notes
                }
                for it in r.items
            ]
        })

    current_rev = revisions_data[0] if revisions_data else None

    return {
        "success": True,
        "proformaInvoice": {
            "id": pi.id,
            "piNumber": pi.pi_number,
            "opportunityId": pi.opportunity_id,
            "opportunityNumber": pi.opportunity.opportunity_id if pi.opportunity else "",
            "opportunityName": pi.opportunity.name if pi.opportunity else "",
            "quotationId": pi.quotation_id,
            "quotationNumber": pi.quotation.quotation_number if pi.quotation else "",
            "accountId": pi.account_id,
            "accountName": pi.account.name if pi.account else "",
            "currentRevisionNumber": pi.current_revision_number,
            "financialYear": pi.financial_year,
            "status": pi.status,
            "createdAt": pi.created_at,
            "updatedAt": pi.updated_at,
            "currentRevision": current_rev,
            "revisions": revisions_data
        }
    }


@router.get("/opportunities/{opp_id}/proforma-invoices")
def get_opportunity_proforma_invoices(
    opp_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_read)
):
    """Returns all proforma invoices linked to a given opportunity."""
    from app.crm.invoice_model import ProformaInvoice
    from app.crm.model import Opportunity
    from sqlalchemy import or_

    opp = db.query(Opportunity).filter(
        or_(Opportunity.id == opp_id, Opportunity.opportunity_id == opp_id)
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity '{opp_id}' not found.")

    pis = db.query(ProformaInvoice).filter(
        ProformaInvoice.opportunity_id == opp.id
    ).order_by(ProformaInvoice.created_at.desc()).all()

    results = []
    for pi in pis:
        latest_rev = pi.revisions[0] if pi.revisions else None
        results.append({
            "id": pi.id,
            "piNumber": pi.pi_number,
            "currentRevisionNumber": pi.current_revision_number,
            "status": pi.status,
            "financialYear": pi.financial_year,
            "createdAt": pi.created_at.isoformat() if pi.created_at else None,
            "updatedAt": pi.updated_at.isoformat() if pi.updated_at else None,
            "grandTotal": float(latest_rev.grand_total) if latest_rev and latest_rev.grand_total is not None else 0.0,
            "subtotal": float(latest_rev.subtotal) if latest_rev and latest_rev.subtotal is not None else 0.0,
            "totalTax": float(latest_rev.total_tax) if latest_rev and latest_rev.total_tax is not None else 0.0,
            "currency": latest_rev.currency if latest_rev else "INR",
            "piDate": latest_rev.pi_date.isoformat() if latest_rev and latest_rev.pi_date else None,
            "revisionCount": len(pi.revisions)
        })

    return {"success": True, "proformaInvoices": results}


@router.get("/proforma-invoices/{pi_id}/html", response_class=HTMLResponse)
def get_proforma_invoice_html(
    pi_id: str,
    revision: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_read)
):
    service = ProformaInvoiceService(db)
    try:
        html = service.render_stored_revision_html(pi_id, revision_number=revision)
        return HTMLResponse(content=html)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# 5. QUOTATION EMAIL TEXT & SINGLE-QUOTATION WORKFLOW
# =============================================================================
@router.get("/quotations/{quotation_id}/email-text")
def get_quotation_email_text(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_crm_read)
):
    service = ProformaInvoiceService(db)
    try:
        return service.generate_quotation_email_text(quotation_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
