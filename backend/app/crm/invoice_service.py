import json
import base64
import os
import uuid
import io
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date as py_date, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, func

from app.core.database import Base
from app.users.model import User
from app.audit.service import AuditService
from app.crm.model import (
    Opportunity,
    Account,
    Contact,
    OpportunityQuotation,
    CrmSequence,
    User
)
from app.crm.catalogue_model import (
    TaxConfiguration,
    TaxRate,
    Service,
    Package
)
from app.crm.invoice_model import (
    CrmCompanySettings,
    ProformaInvoice,
    ProformaInvoiceRevision,
    ProformaInvoiceItem
)
from app.crm.invoice_schema import (
    CompanySettingsUpdate,
    ProformaInvoicePreviewRequest,
    ProformaInvoiceCreate,
    ProformaInvoiceRevisionCreate
)
from app.crm.service import get_next_sequence_id

CENT = Decimal("0.01")


def money(val: Any) -> Decimal:
    """Paise rounding: 2 decimal places with HALF_UP."""
    if val is None:
        val = 0
    return Decimal(str(val)).quantize(CENT, rounding=ROUND_HALF_UP)


def format_inr(value: Any, places: int = 2) -> str:
    """Format money with Indian digit grouping: e.g. 1,95,408.00"""
    if value is None:
        value = 0
    val = Decimal(str(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    sign = "-" if val < 0 else ""
    whole, _, frac = f"{abs(val):f}".partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{sign}{whole}.{frac}" if places else f"{sign}{whole}"


def format_qty(value: Any) -> str:
    if value is None:
        return "0"
    dec = Decimal(str(value))
    return f"{dec.normalize():f}" if dec != dec.to_integral() else str(int(dec))


def get_financial_year(target_date: Optional[py_date] = None) -> str:
    dt = target_date or py_date.today()
    year = dt.year
    if dt.month >= 4:
        return f"{year}-{(year + 1) % 100:02d}"
    else:
        return f"{year - 1}-{year % 100:02d}"


def get_image_as_data_uri(file_path: str) -> Optional[str]:
    """Helper to convert static image file into base64 data URI for standalone HTML rendering."""
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(file_path)[1].lower().replace(".", "")
        mime = f"image/{ext}" if ext in ("png", "jpeg", "jpg", "svg+xml") else "image/png"
        encoded = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return None


class ProformaInvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    # =========================================================================
    # 1. COMPANY & INVOICE SETTINGS
    # =========================================================================
    def get_company_settings(self) -> CrmCompanySettings:
        settings = self.db.query(CrmCompanySettings).first()
        if not settings:
            # Seed default REVY company settings
            settings = CrmCompanySettings(
                company_name="REVY Environmental Solutions Pvt. Ltd.",
                wordmark="REVY Environmental Solutions",
                tagline="Committed for a Greener Earth!",
                address_lines=[
                    "313-314, Siddharth Upscale Vasna Road",
                    "Vadodara-390007, Gujarat, India"
                ],
                email="mail@revy.co.in",
                phone="+91-9876543210",
                website="www.revy.co.in",
                gstin="24AAICR4401M1ZD",
                pan="AAICR4401M",
                logo_url="/images/logo.png",
                bank_name="Bank Of Baroda, Alkapuri Branch",
                bank_account_number="01880200001183",
                bank_ifsc="BARB0ALKAPU",
                bank_branch="Alkapuri Branch",
                service_description="Technical Testing & Analysis Services",
                sac_code="998346",
                signatory_name="Vanita Prasad",
                signatory_title="Authorised Signatory",
                signatory_company_label="For REVY Environmental Solutions Pvt. Ltd.",
                signature_image_url="/images/signature.png",
                default_terms=[
                    "100 % Advance alongwith PO or Work order",
                    'Payment to be made in Favour of " REVY Environmental Solutions Pvt.Ltd.',
                    "Transportation cost for delivery or rendering services will be charged extra as actual",
                    "We will not be any storing sample provided by client after 7 days post  analysis"
                ],
                footer_text="REVY Environmental Solutions Pvt. Ltd. | 313-314, Siddharth Upscale Vasna Road, Vadodara-390007, Gujarat, India | www.revy.co.in"
            )
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update_company_settings(
        self,
        actor: Any,
        payload: CompanySettingsUpdate,
        request: Any = None
    ) -> CrmCompanySettings:
        # Check permissions: CRM_ADMIN or Global Admin required
        is_admin = False
        roles = getattr(actor, "roles", []) or []
        if "CRM_ADMIN" in roles or "IT_ADMIN" in roles or "SUPER_ADMIN" in roles:
            is_admin = True
        if getattr(actor, "is_admin", False) or getattr(actor, "is_superuser", False):
            is_admin = True

        if not is_admin:
            raise PermissionError("Only CRM Admins may update Company & Invoice Configuration.")

        settings = self.get_company_settings()
        changes = {}

        fields = [
            ("companyName", "company_name"),
            ("wordmark", "wordmark"),
            ("tagline", "tagline"),
            ("addressLines", "address_lines"),
            ("email", "email"),
            ("phone", "phone"),
            ("website", "website"),
            ("gstin", "gstin"),
            ("pan", "pan"),
            ("logoUrl", "logo_url"),
            ("bankName", "bank_name"),
            ("bankAccountNumber", "bank_account_number"),
            ("bankIfsc", "bank_ifsc"),
            ("bankBranch", "bank_branch"),
            ("serviceDescription", "service_description"),
            ("sacCode", "sac_code"),
            ("signatoryName", "signatory_name"),
            ("signatoryTitle", "signatory_title"),
            ("signatoryCompanyLabel", "signatory_company_label"),
            ("signatureImageUrl", "signature_image_url"),
            ("defaultTerms", "default_terms"),
            ("footerText", "footer_text"),
        ]

        for p_field, db_field in fields:
            val = getattr(payload, p_field, None)
            if val is not None:
                old_val = getattr(settings, db_field)
                if old_val != val:
                    changes[db_field] = {"old": old_val, "new": val}
                    setattr(settings, db_field, val)

        settings.updated_by_id = str(actor.id) if getattr(actor, "id", None) else None
        settings.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(settings)

        try:
            self.audit_service.log(
                action="CRM_COMPANY_SETTINGS_UPDATED",
                request=request,
                performed_by_employee_id=str(actor.id) if getattr(actor, "id", None) else None,
                performed_by_name=getattr(actor, "name", None) or getattr(actor, "username", "Unknown"),
                role_used=getattr(actor, "active_role", "CRM_ADMIN"),
                target_info={"settings_id": settings.id, "changes": changes}
            )
        except Exception:
            pass

        return settings

    def upload_signature_image(
        self,
        actor: Any,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        request: Any = None
    ) -> CrmCompanySettings:
        # Check permissions: CRM_ADMIN or Global Admin required
        is_admin = False
        roles = getattr(actor, "roles", []) or []
        if any(r in roles for r in ["CRM_ADMIN", "IT_ADMIN", "SUPER_ADMIN", "Admin", "SuperAdmin"]):
            is_admin = True
        if getattr(actor, "is_admin", False) or getattr(actor, "is_superuser", False):
            is_admin = True
        permissions = getattr(actor, "permissions", []) or []
        if "*" in permissions or "crm.settings.manage" in permissions or "crm.user.manage" in permissions:
            is_admin = True

        if not is_admin:
            raise PermissionError("Only CRM Administrators have permission to upload company signature.")

        # Validate file size (max 5MB)
        if len(file_bytes) > 5 * 1024 * 1024:
            raise ValueError("Signature image exceeds maximum allowed size of 5MB.")

        # Validate format
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".png", ".jpg", ".jpeg"] and content_type not in ["image/png", "image/jpeg", "image/jpg"]:
            raise ValueError("Unsupported file format. Please upload a PNG, JPG, or JPEG image.")

        if ext not in [".png", ".jpg", ".jpeg"]:
            ext = ".png" if "png" in content_type else ".jpg"

        # Save to storage
        from app.files.storage import get_storage_provider
        storage = get_storage_provider()
        unique_id = uuid.uuid4().hex
        stored_filename = f"signatures/signature_{unique_id}{ext}"
        
        storage.save_file(io.BytesIO(file_bytes), stored_filename)

        settings = self.get_company_settings()
        new_val = f"/api/v1/crm/company-settings/signature/image?v={unique_id[:8]}"
        settings.signature_image_url = new_val
        settings.updated_by_id = str(actor.id) if getattr(actor, "id", None) else None
        settings.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(settings)

        try:
            self.audit_service.log(
                action="CRM_COMPANY_SIGNATURE_UPLOADED",
                request=request,
                performed_by_employee_id=str(actor.id) if getattr(actor, "id", None) else None,
                performed_by_name=getattr(actor, "name", None) or getattr(actor, "username", "Unknown"),
                role_used=getattr(actor, "active_role", "CRM_ADMIN"),
                target_info={"settings_id": settings.id, "filename": stored_filename}
            )
        except Exception:
            pass

        return settings

    def delete_signature_image(
        self,
        actor: Any,
        request: Any = None
    ) -> CrmCompanySettings:
        # Check permissions: CRM_ADMIN or Global Admin required
        is_admin = False
        roles = getattr(actor, "roles", []) or []
        if any(r in roles for r in ["CRM_ADMIN", "IT_ADMIN", "SUPER_ADMIN", "Admin", "SuperAdmin"]):
            is_admin = True
        if getattr(actor, "is_admin", False) or getattr(actor, "is_superuser", False):
            is_admin = True
        permissions = getattr(actor, "permissions", []) or []
        if "*" in permissions or "crm.settings.manage" in permissions or "crm.user.manage" in permissions:
            is_admin = True

        if not is_admin:
            raise PermissionError("Only CRM Administrators have permission to remove company signature.")

        settings = self.get_company_settings()
        settings.signature_image_url = None
        settings.updated_by_id = str(actor.id) if getattr(actor, "id", None) else None
        settings.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(settings)

        try:
            self.audit_service.log(
                action="CRM_COMPANY_SIGNATURE_REMOVED",
                request=request,
                performed_by_employee_id=str(actor.id) if getattr(actor, "id", None) else None,
                performed_by_name=getattr(actor, "name", None) or getattr(actor, "username", "Unknown"),
                role_used=getattr(actor, "active_role", "CRM_ADMIN"),
                target_info={"settings_id": settings.id}
            )
        except Exception:
            pass

        return settings

    # =========================================================================
    # 2. SEQUENCE NUMBER GENERATION
    # =========================================================================
    def get_next_pi_number(self, target_date: Optional[py_date] = None, commit: bool = False) -> Tuple[str, str]:
        """
        Generates sequential, concurrency-safe PI number: REVY/PI/2026-27/0001
        Returns tuple: (pi_number, financial_year)
        """
        fy = get_financial_year(target_date)
        entity_name = f"PI_{fy}"
        seq = self.db.query(CrmSequence).filter(CrmSequence.entity_name == entity_name).with_for_update().first()
        if not seq:
            seq = CrmSequence(entity_name=entity_name, current_value=1)
            self.db.add(seq)
            val = 1
        else:
            seq.current_value += 1
            val = seq.current_value
        if commit:
            self.db.commit()
        else:
            self.db.flush()
        num = f"REVY/PI/{fy}/{val:04d}"
        return num, fy

    # =========================================================================
    # 3. CALCULATIONS & TAXES
    # =========================================================================
    def calculate_invoice_totals(
        self,
        items: List[Any],
        tax_type: str = "INTRA_STATE",
        tax_configuration_id: Optional[str] = None
    ) -> Dict[str, Any]:
        lines = []
        subtotal = Decimal("0.00")

        for idx, item in enumerate(items, start=1):
            qty = Decimal(str(getattr(item, "quantity", 1)))
            rate = Decimal(str(getattr(item, "rate", 0)))
            amt = money(qty * rate)
            subtotal += amt
            lines.append({
                "sr_no": getattr(item, "sr_no", idx) or idx,
                "item_type": getattr(item, "item_type", "SERVICE"),
                "service_id": getattr(item, "service_id", None),
                "package_id": getattr(item, "package_id", None),
                "item_code": getattr(item, "item_code", None),
                "name": getattr(item, "name", "") or getattr(item, "item_name", "Item"),
                "description": getattr(item, "description", None),
                "quantity": qty,
                "quantity_formatted": format_qty(qty),
                "unit": getattr(item, "unit", None),
                "rate": rate,
                "rate_formatted": format_inr(rate),
                "amount": amt,
                "amount_formatted": format_inr(amt),
                "notes": getattr(item, "notes", None)
            })

        cgst_rate = Decimal("0.0")
        cgst_amt = Decimal("0.00")
        sgst_rate = Decimal("0.0")
        sgst_amt = Decimal("0.00")
        igst_rate = Decimal("0.0")
        igst_amt = Decimal("0.00")

        # Tax rates from tax config if provided, otherwise standard Indian GST defaults (9% + 9% or 18%)
        tax_config = None
        if tax_configuration_id:
            tax_config = self.db.query(TaxConfiguration).options(
                joinedload(TaxConfiguration.rates)
            ).filter(TaxConfiguration.id == tax_configuration_id).first()

        clean_tax_type = (tax_type or "INTRA_STATE").upper()

        if clean_tax_type == "INTRA_STATE":
            if tax_config and tax_config.rates:
                for r in tax_config.rates:
                    if not r.is_active:
                        continue
                    pct = Decimal(str(r.rate_percentage))
                    name = r.component_name.upper()
                    if "CGST" in name:
                        cgst_rate = pct
                    elif "SGST" in name or "UTGST" in name:
                        sgst_rate = pct
            else:
                cgst_rate = Decimal("9.0")
                sgst_rate = Decimal("9.0")

            cgst_amt = money(subtotal * (cgst_rate / Decimal("100.0")))
            sgst_amt = money(subtotal * (sgst_rate / Decimal("100.0")))
            total_tax = cgst_amt + sgst_amt

        elif clean_tax_type == "INTER_STATE":
            if tax_config and tax_config.rates:
                for r in tax_config.rates:
                    if not r.is_active:
                        continue
                    pct = Decimal(str(r.rate_percentage))
                    name = r.component_name.upper()
                    if "IGST" in name:
                        igst_rate = pct
            else:
                igst_rate = Decimal("18.0")

            igst_amt = money(subtotal * (igst_rate / Decimal("100.0")))
            total_tax = igst_amt

        else:  # EXEMPT
            total_tax = Decimal("0.00")

        grand_total = subtotal + total_tax

        return {
            "lines": lines,
            "subtotal": subtotal,
            "subtotal_formatted": format_inr(subtotal),
            "tax_type": clean_tax_type,
            "cgst_rate": cgst_rate,
            "cgst_rate_formatted": format_qty(cgst_rate),
            "cgst_amount": cgst_amt,
            "cgst_amount_formatted": format_inr(cgst_amt),
            "sgst_rate": sgst_rate,
            "sgst_rate_formatted": format_qty(sgst_rate),
            "sgst_amount": sgst_amt,
            "sgst_amount_formatted": format_inr(sgst_amt),
            "igst_rate": igst_rate,
            "igst_rate_formatted": format_qty(igst_rate),
            "igst_amount": igst_amt,
            "igst_amount_formatted": format_inr(igst_amt),
            "total_tax": total_tax,
            "total_tax_formatted": format_inr(total_tax),
            "grand_total": grand_total,
            "grand_total_formatted": format_inr(grand_total)
        }

    # =========================================================================
    # 4. RENDER HTML DOCUMENT
    # =========================================================================
    def render_invoice_html(
        self,
        pi_number: str,
        pi_date: Any,
        financial_year: str,
        revision_number: int,
        opportunity: Opportunity,
        account: Account,
        calculated_totals: Dict[str, Any],
        company_snapshot: Dict[str, Any],
        terms: List[str],
        reference_note: Optional[str] = None,
        is_preview: bool = False
    ) -> str:
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"])
        )
        template = env.get_template("proforma_invoice.html")

        # Prepare logo and signature data URIs if files exist
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images")
        logo_path = os.path.join(static_dir, "logo.png")
        sig_path = os.path.join(static_dir, "signature.png")

        logo_uri = get_image_as_data_uri(logo_path) or company_snapshot.get("logo_url") or "/images/logo.png"

        # Resolve signature URI: respects uploaded signature, fallback static image, or empty when removed
        stored_sig = (company_snapshot.get("signatory", {}) or {}).get("signature_image_url") or company_snapshot.get("signature_image_url")
        signature_uri = None
        if stored_sig and str(stored_sig).strip():
            if str(stored_sig).startswith("data:image/"):
                signature_uri = str(stored_sig)
            else:
                uploads_sig_dir = os.path.join(os.path.abspath("uploads"), "signatures")
                if os.path.exists(uploads_sig_dir):
                    sig_files = sorted(
                        [os.path.join(uploads_sig_dir, f) for f in os.listdir(uploads_sig_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))],
                        key=lambda p: os.path.getmtime(p),
                        reverse=True
                    )
                    if sig_files:
                        signature_uri = get_image_as_data_uri(sig_files[0])
                if not signature_uri and os.path.exists(sig_path):
                    signature_uri = get_image_as_data_uri(sig_path)
                if not signature_uri:
                    signature_uri = str(stored_sig)

        # Customer address
        cust_address_lines = []
        if account.billing_address:
            cust_address_lines = [l.strip() for l in account.billing_address.split("\n") if l.strip()]
        elif account.address:
            cust_address_lines = [l.strip() for l in account.address.split("\n") if l.strip()]
        if account.city or account.state:
            cust_address_lines.append(f"{account.city or ''}, {account.state or ''} {account.country or ''}".strip(" ,"))

        # Primary contact person
        primary_contact = None
        if account.contacts:
            primary_contact = next((c for c in account.contacts if c.is_primary), account.contacts[0])

        customer_info = {
            "name": account.name,
            "customer_id": account.customer_id or account.account_id,
            "address_lines": cust_address_lines,
            "gstin": account.gst_number,
            "contact_person": f"{primary_contact.first_name} {primary_contact.last_name or ''}".strip() if primary_contact else None,
            "email": account.email or (primary_contact.email if primary_contact else None),
            "phone": account.phone or (primary_contact.mobile_number if primary_contact else None),
        }

        date_str = pi_date.strftime("%d-%b-%Y") if hasattr(pi_date, "strftime") else str(pi_date)

        rendered = template.render(
            invoice_title="PROFORMA INVOICE",
            pi_number=pi_number,
            pi_date=date_str,
            financial_year=financial_year,
            revision_number=revision_number,
            opportunity_number=opportunity.opportunity_id,
            reference_text=reference_note or opportunity.name,
            currency_symbol="₹",
            logo_uri=logo_uri,
            signature_uri=signature_uri,
            company=company_snapshot,
            customer=customer_info,
            bank=company_snapshot.get("bank", {}),
            signatory=company_snapshot.get("signatory", {}),
            lines=calculated_totals["lines"],
            terms=terms,
            subtotal_formatted=calculated_totals["subtotal_formatted"],
            tax_type=calculated_totals["tax_type"],
            cgst_rate_formatted=calculated_totals["cgst_rate_formatted"],
            cgst_amount_formatted=calculated_totals["cgst_amount_formatted"],
            sgst_rate_formatted=calculated_totals["sgst_rate_formatted"],
            sgst_amount_formatted=calculated_totals["sgst_amount_formatted"],
            igst_rate_formatted=calculated_totals["igst_rate_formatted"],
            igst_amount_formatted=calculated_totals["igst_amount_formatted"],
            grand_total_formatted=calculated_totals["grand_total_formatted"],
            is_preview=is_preview
        )
        return rendered

    # =========================================================================
    # 5. PREVIEW PROFORMA INVOICE (NO SEQUENCE NUMBER CONSUMED)
    # =========================================================================
    def preview_proforma_invoice(
        self,
        actor: Any,
        payload: ProformaInvoicePreviewRequest
    ) -> Dict[str, Any]:
        """
        Generates a live preview without consuming a sequential PI number or saving to DB.
        """
        quotation = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.id == payload.quotationId
        ).first()
        if not quotation:
            raise ValueError(f"Quotation '{payload.quotationId}' not found.")

        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account).joinedload(Account.contacts)
        ).filter(Opportunity.id == payload.opportunityId).first()
        if not opp or not opp.account:
            raise ValueError(f"Opportunity or associated Account not found for ID '{payload.opportunityId}'.")

        company = self.get_company_settings()
        company_snapshot = self._build_company_snapshot(company)

        # Warnings for missing customer details
        warnings = []
        if not opp.account.address and not opp.account.billing_address:
            warnings.append("Account billing address is missing. It is recommended to update the account address.")
        if not opp.account.gst_number:
            warnings.append("Account GSTIN is missing.")
        if not opp.account.customer_id:
            warnings.append("Account customer ID is not set. The account reference ID will be used.")

        # Tax calculation
        totals = self.calculate_invoice_totals(
            items=payload.items,
            tax_type=payload.taxType,
            tax_configuration_id=payload.taxConfigurationId
        )

        # GSTIN state mismatch warning
        if opp.account.gst_number and company.gstin:
            cust_state = opp.account.gst_number[:2]
            comp_state = company.gstin[:2]
            if cust_state == comp_state and payload.taxType == "INTER_STATE":
                warnings.append(f"Customer GSTIN ({cust_state}) and Company GSTIN ({comp_state}) share the same state code, but tax supply type is set to INTER_STATE (IGST).")
            elif cust_state != comp_state and payload.taxType == "INTRA_STATE":
                warnings.append(f"Customer GSTIN state code ({cust_state}) differs from Company state code ({comp_state}), but tax supply type is set to INTRA_STATE (CGST+SGST).")

        pi_date = payload.piDate or py_date.today()
        fy = get_financial_year(pi_date)
        terms = payload.terms if payload.terms is not None else (company.default_terms or [])

        # Render HTML with draft watermark/toolbar
        rendered_html = self.render_invoice_html(
            pi_number="DRAFT-PREVIEW",
            pi_date=pi_date,
            financial_year=fy,
            revision_number=1,
            opportunity=opp,
            account=opp.account,
            calculated_totals=totals,
            company_snapshot=company_snapshot,
            terms=terms,
            reference_note=payload.referenceNote,
            is_preview=True
        )

        return {
            "success": True,
            "previewNumber": "DRAFT-PREVIEW",
            "financialYear": fy,
            "totals": totals,
            "warnings": warnings,
            "html": rendered_html
        }

    # =========================================================================
    # 6. CREATE PROFORMA INVOICE (PERSISTENT & SEQUENTIAL)
    # =========================================================================
    def create_proforma_invoice(
        self,
        actor: Any,
        payload: ProformaInvoiceCreate,
        request: Any = None
    ) -> ProformaInvoice:
        """
        Creates a permanent Proforma Invoice with sequential numbering and Revision 1.
        """
        quotation = self.db.query(OpportunityQuotation).filter(
            OpportunityQuotation.id == payload.quotationId
        ).first()
        if not quotation:
            raise ValueError(f"Source quotation '{payload.quotationId}' not found. An invoice cannot be created without a quotation.")

        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account).joinedload(Account.contacts)
        ).filter(Opportunity.id == payload.opportunityId).first()
        if not opp or not opp.account:
            raise ValueError(f"Opportunity or associated Account not found for ID '{payload.opportunityId}'.")

        # Approve quotation automatically if in draft / review
        if quotation.status in ("Draft", "Internal Review"):
            quotation.status = "Approved"
            quotation.approved_by_id = str(actor.id) if getattr(actor, "id", None) else None
            quotation.approved_at = datetime.now(timezone.utc)

        pi_date = payload.piDate or py_date.today()
        pi_number, fy = self.get_next_pi_number(pi_date, commit=False)

        company = self.get_company_settings()
        company_snapshot = self._build_company_snapshot(company)
        customer_snapshot = self._build_customer_snapshot(opp.account)
        terms = payload.terms if payload.terms is not None else (company.default_terms or [])

        totals = self.calculate_invoice_totals(
            items=payload.items,
            tax_type=payload.taxType,
            tax_configuration_id=payload.taxConfigurationId
        )

        # 1. Proforma Invoice Master Record
        pi = ProformaInvoice(
            pi_number=pi_number,
            opportunity_id=opp.id,
            quotation_id=quotation.id,
            account_id=opp.account.id,
            current_revision_number=1,
            financial_year=fy,
            status="Issued",
            created_by_id=str(actor.id) if getattr(actor, "id", None) else None
        )
        self.db.add(pi)
        self.db.flush()

        # 2. Revision 1 Record
        rev = ProformaInvoiceRevision(
            proforma_invoice_id=pi.id,
            revision_number=1,
            pi_number=pi_number,
            pi_date=pi_date,
            financial_year=fy,
            status="Issued",
            reference_note=payload.referenceNote,
            currency="INR",
            subtotal=totals["subtotal"],
            tax_type=totals["tax_type"],
            tax_configuration_id=payload.taxConfigurationId,
            cgst_rate=totals["cgst_rate"],
            cgst_amount=totals["cgst_amount"],
            sgst_rate=totals["sgst_rate"],
            sgst_amount=totals["sgst_amount"],
            igst_rate=totals["igst_rate"],
            igst_amount=totals["igst_amount"],
            total_tax=totals["total_tax"],
            grand_total=totals["grand_total"],
            company_snapshot=company_snapshot,
            customer_snapshot=customer_snapshot,
            terms_snapshot=terms,
            notes=payload.notes,
            created_by_id=str(actor.id) if getattr(actor, "id", None) else None
        )
        self.db.add(rev)
        self.db.flush()

        # 3. Items
        for line in totals["lines"]:
            item = ProformaInvoiceItem(
                revision_id=rev.id,
                sr_no=line["sr_no"],
                item_type=line["item_type"],
                service_id=line["service_id"],
                package_id=line["package_id"],
                item_code=line["item_code"],
                item_name=line["name"],
                description=line["description"],
                quantity=line["quantity"],
                unit=line["unit"],
                rate=line["rate"],
                amount=line["amount"],
                notes=line["notes"]
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(pi)

        try:
            self.audit_service.log(
                action="CRM_PROFORMA_INVOICE_CREATED",
                request=request,
                performed_by_employee_id=str(actor.id) if getattr(actor, "id", None) else None,
                performed_by_name=getattr(actor, "name", None) or getattr(actor, "username", "Unknown"),
                role_used=getattr(actor, "active_role", "CRM_USER"),
                target_info={
                    "proforma_invoice_id": pi.id,
                    "pi_number": pi.pi_number,
                    "opportunity_id": opp.opportunity_id,
                    "grand_total": float(totals["grand_total"])
                }
            )
        except Exception:
            pass

        return pi

    # =========================================================================
    # 7. CREATE NEW REVISION (IMMUTABLE PREVIOUS REVISIONS)
    # =========================================================================
    def create_invoice_revision(
        self,
        actor: Any,
        pi_id: str,
        payload: ProformaInvoiceRevisionCreate,
        request: Any = None
    ) -> ProformaInvoiceRevision:
        pi = self.db.query(ProformaInvoice).filter(
            ProformaInvoice.id == pi_id
        ).with_for_update().first()
        if not pi:
            raise ValueError(f"Proforma Invoice '{pi_id}' not found.")

        opp = self.db.query(Opportunity).options(
            joinedload(Opportunity.account).joinedload(Account.contacts)
        ).filter(Opportunity.id == pi.opportunity_id).first()

        new_rev_num = pi.current_revision_number + 1
        pi.current_revision_number = new_rev_num
        pi.updated_at = datetime.now(timezone.utc)

        company = self.get_company_settings()
        company_snapshot = self._build_company_snapshot(company)
        customer_snapshot = self._build_customer_snapshot(opp.account)
        terms = payload.terms if payload.terms is not None else (company.default_terms or [])

        totals = self.calculate_invoice_totals(
            items=payload.items,
            tax_type=payload.taxType,
            tax_configuration_id=payload.taxConfigurationId
        )

        pi_date = payload.piDate or py_date.today()

        rev = ProformaInvoiceRevision(
            proforma_invoice_id=pi.id,
            revision_number=new_rev_num,
            pi_number=pi.pi_number,
            pi_date=pi_date,
            financial_year=pi.financial_year,
            status="Issued",
            reference_note=payload.referenceNote,
            currency="INR",
            subtotal=totals["subtotal"],
            tax_type=totals["tax_type"],
            tax_configuration_id=payload.taxConfigurationId,
            cgst_rate=totals["cgst_rate"],
            cgst_amount=totals["cgst_amount"],
            sgst_rate=totals["sgst_rate"],
            sgst_amount=totals["sgst_amount"],
            igst_rate=totals["igst_rate"],
            igst_amount=totals["igst_amount"],
            total_tax=totals["total_tax"],
            grand_total=totals["grand_total"],
            company_snapshot=company_snapshot,
            customer_snapshot=customer_snapshot,
            terms_snapshot=terms,
            notes=payload.notes,
            created_by_id=str(actor.id) if getattr(actor, "id", None) else None
        )
        self.db.add(rev)
        self.db.flush()

        for line in totals["lines"]:
            item = ProformaInvoiceItem(
                revision_id=rev.id,
                sr_no=line["sr_no"],
                item_type=line["item_type"],
                service_id=line["service_id"],
                package_id=line["package_id"],
                item_code=line["item_code"],
                item_name=line["name"],
                description=line["description"],
                quantity=line["quantity"],
                unit=line["unit"],
                rate=line["rate"],
                amount=line["amount"],
                notes=line["notes"]
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(rev)

        try:
            self.audit_service.log(
                action="CRM_PROFORMA_INVOICE_REVISED",
                request=request,
                performed_by_employee_id=str(actor.id) if getattr(actor, "id", None) else None,
                performed_by_name=getattr(actor, "name", None) or getattr(actor, "username", "Unknown"),
                role_used=getattr(actor, "active_role", "CRM_USER"),
                target_info={
                    "proforma_invoice_id": pi.id,
                    "pi_number": pi.pi_number,
                    "revision_number": new_rev_num,
                    "grand_total": float(totals["grand_total"])
                }
            )
        except Exception:
            pass

        return rev

    # =========================================================================
    # 8. GET & RENDER EXISTING PI REVISION
    # =========================================================================
    def get_proforma_invoice(self, pi_id: str) -> Optional[ProformaInvoice]:
        return self.db.query(ProformaInvoice).options(
            joinedload(ProformaInvoice.opportunity),
            joinedload(ProformaInvoice.account),
            joinedload(ProformaInvoice.quotation),
            joinedload(ProformaInvoice.revisions).joinedload(ProformaInvoiceRevision.items)
        ).filter(
            or_(ProformaInvoice.id == pi_id, ProformaInvoice.pi_number == pi_id)
        ).first()

    def render_stored_revision_html(self, pi_id: str, revision_number: Optional[int] = None) -> str:
        pi = self.get_proforma_invoice(pi_id)
        if not pi:
            raise ValueError(f"Proforma Invoice '{pi_id}' not found.")

        if revision_number:
            rev = next((r for r in pi.revisions if r.revision_number == revision_number), None)
            if not rev:
                raise ValueError(f"Revision {revision_number} not found for PI '{pi.pi_number}'.")
        else:
            rev = next((r for r in pi.revisions if r.revision_number == pi.current_revision_number), pi.revisions[0] if pi.revisions else None)
            if not rev:
                raise ValueError(f"No revisions found for PI '{pi.pi_number}'.")

        totals = {
            "lines": [
                {
                    "sr_no": it.sr_no,
                    "name": it.item_name,
                    "description": it.description,
                    "quantity": it.quantity,
                    "quantity_formatted": format_qty(it.quantity),
                    "unit": it.unit,
                    "rate": it.rate,
                    "rate_formatted": format_inr(it.rate),
                    "amount": it.amount,
                    "amount_formatted": format_inr(it.amount),
                    "notes": it.notes
                }
                for it in rev.items
            ],
            "subtotal_formatted": format_inr(rev.subtotal),
            "tax_type": rev.tax_type,
            "cgst_rate_formatted": format_qty(rev.cgst_rate),
            "cgst_amount_formatted": format_inr(rev.cgst_amount),
            "sgst_rate_formatted": format_qty(rev.sgst_rate),
            "sgst_amount_formatted": format_inr(rev.sgst_amount),
            "igst_rate_formatted": format_qty(rev.igst_rate),
            "igst_amount_formatted": format_inr(rev.igst_amount),
            "grand_total_formatted": format_inr(rev.grand_total)
        }

        return self.render_invoice_html(
            pi_number=rev.pi_number,
            pi_date=rev.pi_date,
            financial_year=rev.financial_year,
            revision_number=rev.revision_number,
            opportunity=pi.opportunity,
            account=pi.account,
            calculated_totals=totals,
            company_snapshot=rev.company_snapshot,
            terms=rev.terms_snapshot or [],
            reference_note=rev.reference_note,
            is_preview=False
        )

    # =========================================================================
    # 9. COLLATERAL LISTING
    # =========================================================================
    def get_collateral_summary(
        self,
        view_type: str = "all",
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> Dict[str, Any]:
        """
        Returns opportunities that have at least one quotation OR Proforma Invoice.
        Filtered by view_type: 'quotations', 'invoices', or 'all'.
        """
        # Base query: Opportunities with quotations or PIs
        query = self.db.query(Opportunity).options(
            joinedload(Opportunity.account),
            joinedload(Opportunity.assigned_to),
            joinedload(Opportunity.created_by),
            joinedload(Opportunity.quotations),
            joinedload(Opportunity.proforma_invoices).joinedload(ProformaInvoice.revisions)
        )

        if view_type == "quotations":
            query = query.filter(Opportunity.quotations.any(OpportunityQuotation.is_active == True))
        elif view_type == "invoices":
            query = query.filter(Opportunity.proforma_invoices.any())
        else:
            query = query.filter(
                or_(
                    Opportunity.quotations.any(OpportunityQuotation.is_active == True),
                    Opportunity.proforma_invoices.any()
                )
            )

        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Opportunity.name.ilike(s),
                    Opportunity.opportunity_id.ilike(s),
                    Opportunity.account.has(Account.name.ilike(s)),
                    Opportunity.quotations.any(OpportunityQuotation.quotation_number.ilike(s)),
                    Opportunity.proforma_invoices.any(ProformaInvoice.pi_number.ilike(s))
                )
            )

        total_count = query.count()
        opps = query.order_by(desc(Opportunity.updated_at)).offset((page - 1) * page_size).limit(page_size).all()

        items = []
        for opp in opps:
            # Active quotation
            active_q = next((q for q in opp.quotations if q.is_active), None) or (opp.quotations[0] if opp.quotations else None)
            # Latest PI
            latest_pi = opp.proforma_invoices[0] if opp.proforma_invoices else None
            latest_rev = latest_pi.revisions[0] if (latest_pi and latest_pi.revisions) else None

            # Calculate latest updated date among opportunity, quotation, and PI
            dates = [opp.updated_at or opp.created_at]
            if active_q:
                dates.append(active_q.updated_at or active_q.created_at)
            if latest_pi:
                dates.append(latest_pi.updated_at or latest_pi.created_at)
            last_date = max(dates)

            owner_user = opp.assigned_to or opp.created_by
            owner_name = getattr(owner_user, "name", None) or getattr(owner_user, "username", "Unassigned") if owner_user else "Unassigned"

            items.append({
                "opportunityId": opp.id,
                "opportunityNumber": opp.opportunity_id,
                "opportunityName": opp.name,
                "accountId": opp.account.id if opp.account else "",
                "accountName": opp.account.name if opp.account else "N/A",
                "customerId": opp.account.customer_id or (opp.account.account_id if opp.account else None),
                "ownerName": owner_name,
                "quotationId": active_q.id if active_q else None,
                "quotationNumber": active_q.quotation_number if active_q else None,
                "quotationStatus": active_q.status if active_q else None,
                "quotationAmount": float(active_q.amount) if active_q else None,
                "piId": latest_pi.id if latest_pi else None,
                "piNumber": latest_pi.pi_number if latest_pi else None,
                "piStatus": latest_pi.status if latest_pi else None,
                "piRevisionNumber": latest_pi.current_revision_number if latest_pi else None,
                "piAmount": float(latest_rev.grand_total) if latest_rev else None,
                "lastUpdatedDate": last_date
            })

        return {
            "success": True,
            "totalCount": total_count,
            "page": page,
            "pageSize": page_size,
            "items": items
        }

    # =========================================================================
    # 10. EMAIL-READY FORMATTED QUOTATION TEXT
    # =========================================================================
    def generate_quotation_email_text(self, quotation_id: str) -> Dict[str, Any]:
        """
        Generates clean, professional email-ready text for a quotation.
        """
        quotation = self.db.query(OpportunityQuotation).options(
            joinedload(OpportunityQuotation.opportunity).joinedload(Opportunity.account),
            joinedload(OpportunityQuotation.items)
        ).filter(
            or_(OpportunityQuotation.id == quotation_id, OpportunityQuotation.quotation_number == quotation_id)
        ).first()

        if not quotation:
            raise ValueError(f"Quotation '{quotation_id}' not found.")

        opp = quotation.opportunity
        account = opp.account if opp else None

        customer_name = account.name if account else "Valued Client"
        opp_ref = f"{opp.opportunity_id} - {opp.name}" if opp else "Quotation"
        q_num = quotation.quotation_number
        q_date = quotation.quotation_date.strftime("%d-%b-%Y") if quotation.quotation_date else py_date.today().strftime("%d-%b-%Y")
        validity = quotation.valid_until_date.strftime("%d-%b-%Y") if quotation.valid_until_date else "30 days from date of issue"

        lines = [
            f"Subject: Quotation {q_num} for {customer_name} | REVY Environmental Solutions",
            "",
            f"Dear {customer_name},",
            "",
            "Thank you for reaching out to REVY Environmental Solutions Pvt. Ltd.",
            "Please find below the detailed quotation for your requirements:",
            "",
            "============================================================",
            f"QUOTATION DETAILS",
            "============================================================",
            f"Quotation No: {q_num}",
            f"Date:         {q_date}",
            f"Opportunity:  {opp_ref}",
            f"Validity:     Until {validity}",
            "------------------------------------------------------------",
            f"{'Sr':<3} | {'Service / Item':<35} | {'Qty':<6} | {'Rate (₹)':<10} | {'Amount (₹)':<12}",
            "------------------------------------------------------------"
        ]

        subtotal = Decimal("0.00")
        for idx, item in enumerate(quotation.items, start=1):
            qty = Decimal(str(item.quantity))
            rate = Decimal(str(item.unit_price))
            amt = money(qty * rate)
            subtotal += amt
            unit_str = f" {item.billing_unit}" if item.billing_unit else ""
            qty_str = f"{format_qty(qty)}{unit_str}"
            name = (item.item_name[:32] + "...") if len(item.item_name) > 35 else item.item_name
            lines.append(f"{idx:<3} | {name:<35} | {qty_str:<6} | {format_inr(rate):<10} | {format_inr(amt):<12}")

        total_tax = Decimal(str(quotation.total_tax or 0.0))
        grand_total = Decimal(str(quotation.amount or (subtotal + total_tax)))

        lines.extend([
            "------------------------------------------------------------",
            f"{'Subtotal:':<58} ₹{format_inr(subtotal)}",
        ])

        if quotation.tax_type == "INTRA_STATE":
            cgst = Decimal(str(quotation.cgst_amount or 0.0))
            sgst = Decimal(str(quotation.sgst_amount or 0.0))
            lines.append(f"{'CGST (9%):':<58} ₹{format_inr(cgst)}")
            lines.append(f"{'SGST (9%):':<58} ₹{format_inr(sgst)}")
        elif quotation.tax_type == "INTER_STATE":
            igst = Decimal(str(quotation.igst_amount or total_tax))
            lines.append(f"{'IGST (18%):':<58} ₹{format_inr(igst)}")
        else:
            lines.append(f"{'Tax:':<58} Exempt")

        lines.extend([
            "============================================================",
            f"{'GRAND TOTAL (INR):':<58} ₹{format_inr(grand_total)}",
            "============================================================",
            "",
            "TERMS & CONDITIONS:",
        ])

        if quotation.terms_and_conditions:
            lines.append(quotation.terms_and_conditions)
        else:
            company = self.get_company_settings()
            for i, term in enumerate(company.default_terms or [], start=1):
                lines.append(f"{i}. {term}")

        if quotation.notes:
            lines.extend(["", "NOTES:", quotation.notes])

        lines.extend([
            "",
            "Warm regards,",
            "REVY Environmental Solutions Pvt. Ltd.",
            "Vadodara, Gujarat, India | www.revy.co.in | mail@revy.co.in"
        ])

        full_text = "\n".join(lines)
        return {
            "success": True,
            "quotationNumber": q_num,
            "emailText": full_text
        }

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================
    def _build_company_snapshot(self, company: CrmCompanySettings) -> Dict[str, Any]:
        return {
            "name": company.company_name,
            "wordmark": company.wordmark,
            "tagline": company.tagline,
            "address_lines": company.address_lines or [],
            "email": company.email,
            "phone": company.phone,
            "website": company.website,
            "gstin": company.gstin,
            "pan": company.pan,
            "logo_url": company.logo_url,
            "bank": {
                "bank_name": company.bank_name,
                "bank_account_number": company.bank_account_number,
                "bank_ifsc": company.bank_ifsc,
                "bank_branch": company.bank_branch,
                "service_description": company.service_description,
                "sac_code": company.sac_code
            },
            "signatory": {
                "name": company.signatory_name,
                "title": company.signatory_title,
                "company_label": company.signatory_company_label,
                "signature_image_url": company.signature_image_url
            }
        }

    def _build_customer_snapshot(self, account: Account) -> Dict[str, Any]:
        addr_lines = []
        if account.billing_address:
            addr_lines = [l.strip() for l in account.billing_address.split("\n") if l.strip()]
        elif account.address:
            addr_lines = [l.strip() for l in account.address.split("\n") if l.strip()]
        if account.city or account.state:
            addr_lines.append(f"{account.city or ''}, {account.state or ''} {account.country or ''}".strip(" ,"))

        primary_contact = None
        if account.contacts:
            primary_contact = next((c for c in account.contacts if c.is_primary), account.contacts[0])

        return {
            "id": account.id,
            "name": account.name,
            "customer_id": account.customer_id or account.account_id,
            "address_lines": addr_lines,
            "gstin": account.gst_number,
            "pan": account.pan_number,
            "contact_person": f"{primary_contact.first_name} {primary_contact.last_name or ''}".strip() if primary_contact else None,
            "email": account.email or (primary_contact.email if primary_contact else None),
            "phone": account.phone or (primary_contact.mobile_number if primary_contact else None),
        }
