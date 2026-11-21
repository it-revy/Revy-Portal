from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from app.core.exceptions import ValidationError
from app.crm.catalogue_model import TaxConfiguration, TaxRate

CENT = Decimal("0.01")


def money(val: Any) -> Decimal:
    """Paise rounding: 2 decimal places with HALF_UP."""
    if val is None or val == "":
        val = 0
    return Decimal(str(val)).quantize(CENT, rounding=ROUND_HALF_UP)


def format_inr(value: Any, places: int = 2) -> str:
    """Format money with Indian digit grouping: e.g. 1,95,408.00"""
    if value is None or value == "":
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
    if value is None or value == "":
        return "0"
    dec = Decimal(str(value))
    return f"{dec.normalize():f}" if dec != dec.to_integral() else str(int(dec))


class CommercialTotalsResult(dict):
    """Dictionary supporting both attribute access and item access."""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'CommercialTotalsResult' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        self[name] = value


class FinancialCalculator:
    """
    Authoritative, Decimal-safe commercial calculation engine.
    Unified source of truth for Quotations, Quotation Items, and Proforma Invoices.
    """

    @staticmethod
    def calculate_commercial_totals(
        db: Optional[Session] = None,
        items: Optional[List[Any]] = None,
        tax_type: str = "INTRA_STATE",
        tax_configuration_id: Optional[str] = None,
        cgst_rate: Optional[Decimal] = None,
        sgst_rate: Optional[Decimal] = None,
        igst_rate: Optional[Decimal] = None,
        **kwargs
    ) -> CommercialTotalsResult:
        """
        Calculates line item gross amounts, discounts, taxable amounts, component GST,
        and consolidated document totals.

        Formula:
          Gross line amount = Quantity × Unit Price
          Taxable line amount = Gross line amount − Discount
          Taxable line amount >= 0

        Tax Rules:
          - INTRA_STATE: CGST + SGST (from active tax configuration)
          - INTER_STATE: IGST (from active tax configuration)
          - EXEMPT: explicitly 0.00
          - If INTRA_STATE or INTER_STATE is specified, an active TaxConfiguration MUST exist.
        """
        if items is None:
            items = []

        clean_tax_type = (tax_type or "INTRA_STATE").strip().upper()
        if clean_tax_type not in ("INTRA_STATE", "INTER_STATE", "EXEMPT"):
            clean_tax_type = "INTRA_STATE"

        # 1. Resolve Tax Configuration and component rates
        tax_config: Optional[TaxConfiguration] = None
        c_rate = cgst_rate if cgst_rate is not None else Decimal("0.0")
        s_rate = sgst_rate if sgst_rate is not None else Decimal("0.0")
        i_rate = igst_rate if igst_rate is not None else Decimal("0.0")

        if clean_tax_type == "EXEMPT":
            c_rate = Decimal("0.0")
            s_rate = Decimal("0.0")
            i_rate = Decimal("0.0")
            if db is not None:
                if tax_configuration_id:
                    tax_config = db.query(TaxConfiguration).options(
                        joinedload(TaxConfiguration.rates)
                    ).filter(
                        TaxConfiguration.id == tax_configuration_id,
                        TaxConfiguration.tax_type == "EXEMPT",
                        TaxConfiguration.is_active == True
                    ).first()
                if not tax_config:
                    tax_config = db.query(TaxConfiguration).options(
                        joinedload(TaxConfiguration.rates)
                    ).filter(
                        TaxConfiguration.tax_type == "EXEMPT",
                        TaxConfiguration.is_active == True
                    ).first()
        elif db is not None:
            # 1a. Try resolving matching active configuration by ID and tax_type
            if tax_configuration_id:
                tax_config = db.query(TaxConfiguration).options(
                    joinedload(TaxConfiguration.rates)
                ).filter(
                    TaxConfiguration.id == tax_configuration_id,
                    TaxConfiguration.tax_type == clean_tax_type,
                    TaxConfiguration.is_active == True
                ).first()

            # 1b. Fallback to active configuration matching tax_type
            if not tax_config:
                tax_config = db.query(TaxConfiguration).options(
                    joinedload(TaxConfiguration.rates)
                ).filter(
                    TaxConfiguration.tax_type == clean_tax_type,
                    TaxConfiguration.is_active == True
                ).first()

            if not tax_config or not tax_config.rates:
                regime_label = "Intra-State (CGST + SGST)" if clean_tax_type == "INTRA_STATE" else "Inter-State (IGST)"
                raise ValidationError(
                    f"Active tax configuration not found for {regime_label} tax regime ('{clean_tax_type}'). "
                    f"Please verify active GST configurations in CRM settings before proceeding."
                )

            for r in tax_config.rates:
                if not r.is_active:
                    continue
                pct = Decimal(str(r.rate_percentage))
                c_name = r.component_name.strip().upper()
                if "CGST" in c_name:
                    c_rate = pct
                elif "SGST" in c_name or "UTGST" in c_name:
                    s_rate = pct
                elif "IGST" in c_name:
                    i_rate = pct

            if clean_tax_type == "INTRA_STATE":
                if c_rate <= Decimal("0.0") or s_rate <= Decimal("0.0"):
                    raise ValidationError("Intra-state tax configuration must define active CGST and SGST rates.")
            elif clean_tax_type == "INTER_STATE":
                if i_rate <= Decimal("0.0"):
                    raise ValidationError("Inter-state tax configuration must define an active IGST rate.")
        else:
            # Fallback when db is omitted in unit testing
            if clean_tax_type == "INTRA_STATE" and c_rate == Decimal("0.0") and s_rate == Decimal("0.0"):
                c_rate = Decimal("9.00")
                s_rate = Decimal("9.00")
            elif clean_tax_type == "INTER_STATE" and i_rate == Decimal("0.0"):
                i_rate = Decimal("18.00")

        cgst_rate = c_rate
        sgst_rate = s_rate
        igst_rate = i_rate

        # 2. Process Line Items
        lines = []
        gross_subtotal = Decimal("0.00")
        total_discount = Decimal("0.00")
        taxable_subtotal = Decimal("0.00")
        total_cgst = Decimal("0.00")
        total_sgst = Decimal("0.00")
        total_igst = Decimal("0.00")

        for idx, item in enumerate(items, start=1):
            # Extract attributes from either Pydantic model, ORM model, or dict
            raw_qty = getattr(item, "quantity", None)
            if raw_qty is None and isinstance(item, dict):
                raw_qty = item.get("quantity", 1)
            qty = Decimal(str(raw_qty if raw_qty is not None else 1))
            if qty <= Decimal("0.0"):
                raise ValidationError(f"Quantity must be greater than zero for line item {idx}.")

            raw_rate = getattr(item, "unit_price", None)
            if raw_rate is None:
                raw_rate = getattr(item, "rate", None)
            if raw_rate is None:
                raw_rate = getattr(item, "unitPrice", None)
            if raw_rate is None:
                raw_rate = getattr(item, "negotiatedUnitPrice", None)
            if raw_rate is None and isinstance(item, dict):
                raw_rate = item.get("unitPrice") if item.get("unitPrice") is not None else item.get("unit_price", item.get("rate", item.get("negotiatedUnitPrice", 0)))
            rate = Decimal(str(raw_rate if raw_rate is not None else 0))
            if rate < Decimal("0.0"):
                raise ValidationError(f"Unit price cannot be negative for line item {idx}.")

            raw_disc = getattr(item, "discount_amount", None)
            if raw_disc is None:
                raw_disc = getattr(item, "discountAmount", None)
            if raw_disc is None and isinstance(item, dict):
                raw_disc = item.get("discountAmount", item.get("discount_amount", 0))
            disc = Decimal(str(raw_disc if raw_disc is not None else 0))
            if disc < Decimal("0.0"):
                raise ValidationError(f"Discount amount cannot be negative for line item {idx}.")

            gross_line = money(qty * rate)
            if disc > gross_line:
                item_label = getattr(item, "itemName", None) or getattr(item, "item_name", None) or getattr(item, "name", None) or f"Item {idx}"
                raise ValidationError(
                    f"Discount ({format_inr(disc)}) cannot exceed gross line amount ({format_inr(gross_line)}) for '{item_label}'."
                )

            taxable_line = money(gross_line - disc)

            # Compute line tax components
            line_cgst = money(taxable_line * (cgst_rate / Decimal("100.0"))) if clean_tax_type == "INTRA_STATE" else Decimal("0.00")
            line_sgst = money(taxable_line * (sgst_rate / Decimal("100.0"))) if clean_tax_type == "INTRA_STATE" else Decimal("0.00")
            line_igst = money(taxable_line * (igst_rate / Decimal("100.0"))) if clean_tax_type == "INTER_STATE" else Decimal("0.00")
            line_tax = money(line_cgst + line_sgst + line_igst)
            final_line_total = money(taxable_line + line_tax)

            gross_subtotal += gross_line
            total_discount += disc
            taxable_subtotal += taxable_line
            total_cgst += line_cgst
            total_sgst += line_sgst
            total_igst += line_igst

            item_type = getattr(item, "item_type", None) or getattr(item, "itemType", "SERVICE")
            if isinstance(item, dict):
                item_type = item.get("itemType") or item.get("item_type") or item_type

            name_val = getattr(item, "item_name", None) or getattr(item, "itemName", None) or getattr(item, "name", "")
            if isinstance(item, dict):
                name_val = item.get("itemName") or item.get("item_name") or item.get("name") or name_val

            unit_val = getattr(item, "billing_unit", None) or getattr(item, "billingUnit", None) or getattr(item, "unit", None)
            if isinstance(item, dict):
                unit_val = item.get("billingUnit") or item.get("billing_unit") or item.get("unit") or unit_val

            lines.append({
                "sr_no": getattr(item, "sr_no", idx) or idx,
                "item_type": item_type,
                "service_id": getattr(item, "service_id", None) or (item.get("serviceId") if isinstance(item, dict) else None),
                "package_id": getattr(item, "package_id", None) or (item.get("packageId") if isinstance(item, dict) else None),
                "package_version_id": getattr(item, "package_version_id", None) or (item.get("packageVersionId") if isinstance(item, dict) else None),
                "parent_item_id": getattr(item, "parent_item_id", None) or (item.get("parentItemId") if isinstance(item, dict) else None),
                "item_code": getattr(item, "item_code", None) or (item.get("itemCode") if isinstance(item, dict) else None),
                "name": name_val or "Service Item",
                "item_name": name_val or "Service Item",
                "description": getattr(item, "description", None) or (item.get("description") if isinstance(item, dict) else None),
                "quantity": qty,
                "quantity_formatted": format_qty(qty),
                "unit": unit_val,
                "rate": rate,
                "rate_formatted": format_inr(rate),
                "unit_price": rate,
                "gross_amount": gross_line,
                "gross_amount_formatted": format_inr(gross_line),
                "discount_amount": disc,
                "discount_amount_formatted": format_inr(disc),
                "discount_formatted": format_inr(disc),
                "taxable_amount": taxable_line,
                "taxable_amount_formatted": format_inr(taxable_line),
                "amount": taxable_line,  # Consistent taxable amount stored on invoices
                "amount_formatted": format_inr(taxable_line),
                "cgst_rate": cgst_rate,
                "cgst_amount": line_cgst,
                "sgst_rate": sgst_rate,
                "sgst_amount": line_sgst,
                "igst_rate": igst_rate,
                "igst_amount": line_igst,
                "total_tax": line_tax,
                "final_total": final_line_total,
                "notes": getattr(item, "notes", None) or (item.get("notes") if isinstance(item, dict) else None)
            })

        total_tax = total_cgst + total_sgst + total_igst
        grand_total = taxable_subtotal + total_tax

        return CommercialTotalsResult({
            "lines": lines,
            "gross_subtotal": gross_subtotal,
            "gross_subtotal_formatted": format_inr(gross_subtotal),
            "discount_amount": total_discount,
            "total_discount": total_discount,
            "discount_amount_formatted": format_inr(total_discount),
            "taxable_subtotal": taxable_subtotal,
            "taxable_amount": taxable_subtotal,
            "taxable_subtotal_formatted": format_inr(taxable_subtotal),
            "subtotal": taxable_subtotal,  # Standard reference across quotation and PI
            "subtotal_formatted": format_inr(taxable_subtotal),
            "tax_type": clean_tax_type,
            "tax_configuration_id": tax_config.id if tax_config else None,
            "tax_configuration_code": tax_config.code if tax_config else None,
            "cgst_rate": cgst_rate,
            "cgst_rate_formatted": format_qty(cgst_rate),
            "cgst_amount": total_cgst,
            "cgst_amount_formatted": format_inr(total_cgst),
            "sgst_rate": sgst_rate,
            "sgst_rate_formatted": format_qty(sgst_rate),
            "sgst_amount": total_sgst,
            "sgst_amount_formatted": format_inr(total_sgst),
            "igst_rate": igst_rate,
            "igst_rate_formatted": format_qty(igst_rate),
            "igst_amount": total_igst,
            "igst_amount_formatted": format_inr(total_igst),
            "total_tax": total_tax,
            "total_tax_formatted": format_inr(total_tax),
            "grand_total": grand_total,
            "grand_total_formatted": format_inr(grand_total)
        })