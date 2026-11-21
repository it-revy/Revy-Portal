import React, { useState, useEffect, useMemo } from 'react';
import {
  FileText,
  Printer,
  CheckCircle,
  AlertTriangle,
  X,
  Plus,
  Trash2,
  ExternalLink,
  DollarSign,
  HelpCircle,
  ShieldAlert,
  Send,
  Eye,
  Edit3,
  Calendar,
  Building,
  Info
} from 'lucide-react';
import { invoiceService } from '../../services/invoiceService';
import catalogueService from '../../services/catalogueService';

export default function InvoicePreparationModal({
  isOpen,
  onClose,
  opportunity,
  quotation,
  editingInvoice = null,
  onInvoiceCreated,
  onInvoiceUpdated
}) {
  const isEditMode = Boolean(editingInvoice?.id);

  const [loading, setLoading] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [warnings, setWarnings] = useState([]);

  // Form State
  const [items, setItems] = useState([]);
  const [taxType, setTaxType] = useState('INTRA_STATE');
  const [taxConfigurations, setTaxConfigurations] = useState([]);
  const [selectedTaxConfigId, setSelectedTaxConfigId] = useState('');
  const [invoiceDate, setInvoiceDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [referenceNote, setReferenceNote] = useState('');
  const [terms, setTerms] = useState([]);
  const [newTerm, setNewTerm] = useState('');
  const [overrideReason, setOverrideReason] = useState('');

  // Active Tax Configuration matching current taxType and/or selectedTaxConfigId
  const activeTaxConfig = useMemo(() => {
    if (selectedTaxConfigId) {
      const match = taxConfigurations.find(t => t.id === selectedTaxConfigId);
      if (match && (match.taxType || match.tax_type) === taxType) {
        return match;
      }
    }
    return taxConfigurations.find(t => (t.taxType || t.tax_type) === taxType) || null;
  }, [taxConfigurations, selectedTaxConfigId, taxType]);

  // Dynamically extract rates from active configuration with robust fallbacks
  const { cgstRate, sgstRate, igstRate } = useMemo(() => {
    let c = 9;
    let s = 9;
    let i = 18;

    if (activeTaxConfig && Array.isArray(activeTaxConfig.rates) && activeTaxConfig.rates.length > 0) {
      activeTaxConfig.rates.forEach(r => {
        const name = (r.rateName || r.componentName || r.component_name || '').toUpperCase();
        const pct = Number(r.percentage !== undefined ? r.percentage : r.ratePercentage || r.rate_percentage || 0);
        if (name.includes('CGST')) c = pct;
        else if (name.includes('SGST')) s = pct;
        else if (name.includes('IGST')) i = pct;
      });
    }

    return { cgstRate: c, sgstRate: s, igstRate: i };
  }, [activeTaxConfig]);

  // Synchronize tax type and corresponding tax configuration ID
  const handleTaxTypeChange = (newTaxType) => {
    setTaxType(newTaxType);
    const matching = taxConfigurations.find(t => (t.taxType || t.tax_type) === newTaxType);
    if (matching) {
      setSelectedTaxConfigId(matching.id);
    }
  };

  // State mismatch detection for GST compliance
  const account = opportunity?.account || {};
  const customerGstin = account.gstin || '';
  const customerState = account.billingState || account.state || '';

  const stateMismatchNotice = useMemo(() => {
    // REVY Home State is Gujarat (GST State Code 24)
    if (customerGstin && customerGstin.length >= 2) {
      const stateCode = customerGstin.trim().substring(0, 2);
      if (stateCode !== '24' && taxType === 'INTRA_STATE') {
        return `GST State Notice: Customer GSTIN starts with "${stateCode}" (outside Gujarat 24). Intra-State GST (CGST + SGST) is currently selected. For inter-state supply, Inter-State (IGST 18%) is recommended.`;
      }
      if (stateCode === '24' && taxType === 'INTER_STATE') {
        return 'GST State Notice: Customer GSTIN indicates Gujarat (24). Inter-State (IGST) is currently selected. For intra-state supply within Gujarat, Intra-State (CGST + SGST) is recommended.';
      }
    } else if (customerState) {
      const isGujarat = customerState.toLowerCase().includes('gujarat');
      if (!isGujarat && taxType === 'INTRA_STATE') {
        return `Location Notice: Customer billing state is recorded as "${customerState}". For supplies outside Gujarat, Inter-State (IGST 18%) is recommended.`;
      }
    }
    return null;
  }, [customerGstin, customerState, taxType]);

  // Initialize from editing invoice or source quotation
  useEffect(() => {
    if (!isOpen) return;

    if (isEditMode && editingInvoice) {
      // Edit mode: populate from existing issued PI
      const piItems = editingInvoice.items || [];
      const mappedItems = piItems.map((item, idx) => ({
        srNo: item.srNo || item.sr_no || idx + 1,
        itemType: item.itemType || item.item_type || 'SERVICE',
        serviceId: item.serviceId || item.service_id,
        packageId: item.packageId || item.package_id,
        itemCode: item.itemCode || item.item_code,
        name: item.name || item.itemName || item.item_name || 'Service Item',
        description: item.description || '',
        quantity: Number(item.quantity) || 1,
        unit: item.unit || item.billingUnit || 'Test',
        rate: Number(item.unitPrice !== undefined ? item.unitPrice : item.rate || 0),
        discountAmount: Number(item.discountAmount !== undefined ? item.discountAmount : item.discount_amount || 0),
        notes: item.notes || ''
      }));
      setItems(mappedItems);
      const incomingTaxType = editingInvoice.taxType || editingInvoice.tax_type || 'INTRA_STATE';
      setTaxType(incomingTaxType);
      setSelectedTaxConfigId(editingInvoice.taxConfigurationId || editingInvoice.tax_configuration_id || '');
      setInvoiceDate(editingInvoice.piDate ? editingInvoice.piDate.split('T')[0] : new Date().toISOString().split('T')[0]);
      setReferenceNote(editingInvoice.referenceNote || editingInvoice.reference_note || '');
      setTerms(editingInvoice.terms || []);
      setOverrideReason('');
      loadDefaults(false, incomingTaxType);
    } else if (quotation) {
      // Creation mode: populate from approved commercial quotation
      const quoteItems = quotation.items || [];
      const mappedItems = quoteItems.map((item, idx) => ({
        srNo: idx + 1,
        itemType: item.itemType || 'SERVICE',
        serviceId: item.serviceId,
        packageId: item.packageId,
        itemCode: item.itemCode,
        name: item.itemName || item.name || 'Service Item',
        description: item.description || '',
        quantity: Number(item.quantity) || 1,
        unit: item.billingUnit || item.unit || 'Test',
        rate: Number(item.negotiatedUnitPrice !== null && item.negotiatedUnitPrice !== undefined ? item.negotiatedUnitPrice : item.unitPrice || item.rate || 0),
        discountAmount: Number(item.discountAmount || 0),
        notes: ''
      }));
      setItems(mappedItems);
      const incomingTaxType = quotation.taxType || 'INTRA_STATE';
      setTaxType(incomingTaxType);
      setSelectedTaxConfigId(quotation.taxConfigurationId || '');
      setInvoiceDate(new Date().toISOString().split('T')[0]);
      setReferenceNote(quotation.title ? `Quotation Ref: ${quotation.quotationNumber} - ${quotation.title}` : `Quotation Ref: ${quotation.quotationNumber}`);
      loadDefaults(true, incomingTaxType);
    }
  }, [isOpen, quotation, editingInvoice, isEditMode]);

  const loadDefaults = async (loadTerms = true, currentTaxType = 'INTRA_STATE') => {
    setLoading(true);
    try {
      const [compRes, taxRes] = await Promise.all([
        invoiceService.getCompanySettings(),
        catalogueService.getTaxConfigurations({ includeInactive: false })
      ]);

      if (loadTerms && compRes.data) {
        const defaultTerms = compRes.data.defaultTerms || [
          '100 % Advance alongwith PO or Work order',
          'Payment to be made in Favour of " REVY Environmental Solutions Pvt.Ltd."',
          'Transportation cost for delivery or rendering services will be charged extra as actual',
          'We will not be storing any sample provided by client after 7 days post analysis'
        ];
        setTerms(defaultTerms);
      }

      if (taxRes.data?.taxConfigurations || taxRes.data?.success) {
        const taxes = taxRes.data?.taxConfigurations || taxRes.data?.data || [];
        setTaxConfigurations(taxes);
        // Match the tax configuration to current tax type
        const matching = taxes.find(t => (t.taxType || t.tax_type) === currentTaxType) || taxes.find(t => t.isDefault) || taxes[0];
        if (matching) {
          setSelectedTaxConfigId(matching.id);
        }
      }
    } catch (err) {
      console.error('Error loading invoice defaults:', err);
    } finally {
      setLoading(false);
    }
  };

  // Authoritative calculations matching FinancialCalculator (Paise Rounding)
  const grossSubtotal = useMemo(() => {
    return items.reduce((acc, it) => acc + (Number(it.quantity || 1) * Number(it.rate || 0)), 0);
  }, [items]);

  const totalDiscount = useMemo(() => {
    return items.reduce((acc, it) => acc + Number(it.discountAmount || 0), 0);
  }, [items]);

  const taxableSubtotal = useMemo(() => {
    return Math.max(0, grossSubtotal - totalDiscount);
  }, [grossSubtotal, totalDiscount]);

  const { cgstAmount, sgstAmount, igstAmount, totalTax, grandTotal } = useMemo(() => {
    let cgst = 0;
    let sgst = 0;
    let igst = 0;
    let tax = 0;

    if (taxType === 'INTRA_STATE') {
      cgst = Math.round(taxableSubtotal * (cgstRate / 100) * 100) / 100;
      sgst = Math.round(taxableSubtotal * (sgstRate / 100) * 100) / 100;
      tax = cgst + sgst;
    } else if (taxType === 'INTER_STATE') {
      igst = Math.round(taxableSubtotal * (igstRate / 100) * 100) / 100;
      tax = igst;
    }

    return {
      cgstAmount: cgst,
      sgstAmount: sgst,
      igstAmount: igst,
      totalTax: tax,
      grandTotal: taxableSubtotal + tax
    };
  }, [taxableSubtotal, taxType, cgstRate, sgstRate, igstRate]);

  // Handle item property changes
  const handleItemChange = (index, field, value) => {
    const updated = [...items];
    const item = { ...updated[index] };

    if (field === 'quantity') {
      item.quantity = Math.max(1, Number(value) || 1);
    } else if (field === 'rate') {
      item.rate = Math.max(0, Number(value) || 0);
    } else if (field === 'discountAmount') {
      const gross = Number(item.quantity || 1) * Number(item.rate || 0);
      item.discountAmount = Math.max(0, Math.min(Number(value) || 0, gross));
    } else {
      item[field] = value;
    }

    updated[index] = item;
    setItems(updated);
  };

  const handleRemoveItem = (index) => {
    if (items.length <= 1) {
      alert('A Proforma Invoice must have at least one line item.');
      return;
    }
    const updated = items.filter((_, i) => i !== index).map((item, idx) => ({
      ...item,
      srNo: idx + 1
    }));
    setItems(updated);
  };

  const handleAddTerm = () => {
    if (!newTerm.trim()) return;
    setTerms([...terms, newTerm.trim()]);
    setNewTerm('');
  };

  const handleRemoveTerm = (index) => {
    setTerms(terms.filter((_, i) => i !== index));
  };

  // Preview in New Tab
  const handlePreview = async () => {
    setPreviewing(true);
    setError(null);
    try {
      const payload = {
        opportunity_id: opportunity.id,
        opportunityId: opportunity.id,
        quotation_id: quotation?.id || editingInvoice?.quotationId || editingInvoice?.quotation_id,
        quotationId: quotation?.id || editingInvoice?.quotationId || editingInvoice?.quotation_id,
        tax_type: taxType,
        taxType: taxType,
        tax_configuration_id: activeTaxConfig?.id || selectedTaxConfigId || undefined,
        taxConfigurationId: activeTaxConfig?.id || selectedTaxConfigId || undefined,
        pi_date: invoiceDate,
        piDate: invoiceDate,
        reference_note: referenceNote,
        referenceNote: referenceNote,
        terms: terms,
        items: items.map(it => ({
          sr_no: it.srNo,
          item_type: it.itemType,
          service_id: it.serviceId,
          package_id: it.packageId,
          name: it.name,
          description: it.description,
          quantity: Number(it.quantity),
          unit: it.unit,
          rate: Number(it.rate),
          discount_amount: Number(it.discountAmount || 0),
          notes: it.notes
        }))
      };

      const res = await invoiceService.previewProformaInvoice(payload);
      if (res.data?.success) {
        if (res.data.warnings && res.data.warnings.length > 0) {
          setWarnings(res.data.warnings);
        }
        invoiceService.openPreviewInNewTab(res.data.html);
      }
    } catch (err) {
      console.error('Preview error:', err);
      setError(err.response?.data?.detail || err.response?.data?.message || 'Failed to generate invoice preview.');
    } finally {
      setPreviewing(false);
    }
  };

  // Save / Update PI
  const handleSaveInvoice = async () => {
    if (items.length === 0) {
      alert('A Proforma Invoice must have at least one line item.');
      return;
    }

    if (isEditMode && !overrideReason.trim()) {
      alert('Please provide a mandatory reason for editing this issued Proforma Invoice.');
      return;
    }

    const confirmMsg = isEditMode
      ? `Save modifications to issued Proforma Invoice ${editingInvoice.piNumber}?`
      : 'Generate Proforma Invoice? This will assign the next sequential invoice number.';

    if (!window.confirm(confirmMsg)) {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        opportunity_id: opportunity.id,
        opportunityId: opportunity.id,
        quotation_id: quotation?.id || editingInvoice?.quotationId || editingInvoice?.quotation_id,
        quotationId: quotation?.id || editingInvoice?.quotationId || editingInvoice?.quotation_id,
        tax_type: taxType,
        taxType: taxType,
        tax_configuration_id: activeTaxConfig?.id || selectedTaxConfigId || undefined,
        taxConfigurationId: activeTaxConfig?.id || selectedTaxConfigId || undefined,
        pi_date: invoiceDate,
        piDate: invoiceDate,
        reference_note: referenceNote,
        referenceNote: referenceNote,
        terms: terms,
        override_reason: isEditMode ? overrideReason.trim() : undefined,
        overrideReason: isEditMode ? overrideReason.trim() : undefined,
        items: items.map(it => ({
          sr_no: it.srNo,
          item_type: it.itemType,
          service_id: it.serviceId,
          package_id: it.packageId,
          name: it.name,
          description: it.description,
          quantity: Number(it.quantity),
          unit: it.unit,
          rate: Number(it.rate),
          discount_amount: Number(it.discountAmount || 0),
          notes: it.notes
        }))
      };

      if (isEditMode) {
        const res = await invoiceService.updateProformaInvoice(editingInvoice.id, payload);
        if (res.data?.success) {
          alert(`Proforma Invoice ${res.data.piNumber || editingInvoice.piNumber} updated successfully.`);
          if (onInvoiceUpdated) {
            onInvoiceUpdated(res.data);
          } else if (onInvoiceCreated) {
            onInvoiceCreated(res.data);
          }
          onClose();
        }
      } else {
        const res = await invoiceService.createProformaInvoice(payload);
        if (res.data?.success) {
          alert(`Proforma Invoice ${res.data.piNumber} generated successfully!`);
          if (onInvoiceCreated) {
            onInvoiceCreated(res.data);
          }
          onClose();
        }
      }
    } catch (err) {
      console.error('Invoice save error:', err);
      setError(err.response?.data?.detail || err.response?.data?.message || 'Failed to save Proforma Invoice.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen || !opportunity) return null;

  const quoteNumber = quotation?.quotationNumber || editingInvoice?.quotationNumber || 'QT-00001';
  const quoteRevision = quotation?.revisionNumber || editingInvoice?.revisionNumber || 1;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.65)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1050,
      padding: '1.25rem'
    }}>
      <div style={{
        backgroundColor: '#ffffff',
        borderRadius: '8px',
        border: '1px solid #e2e8f0',
        width: '100%',
        maxWidth: '1180px',
        maxHeight: '92vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        color: '#0f172a',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '1.25rem 1.75rem',
          borderBottom: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#f8fafc'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
            <div style={{
              backgroundColor: isEditMode ? '#d97706' : '#0284c7',
              width: '42px',
              height: '42px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              flexShrink: 0
            }}>
              {isEditMode ? <Edit3 size={22} /> : <FileText size={22} />}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                <h2 style={{ fontSize: '1.18rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>
                  {isEditMode ? `Edit Proforma Invoice: ${editingInvoice.piNumber}` : 'Prepare Proforma Invoice'}
                </h2>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  backgroundColor: '#e0f2fe',
                  color: '#0369a1',
                  fontFamily: 'monospace'
                }}>
                  {quoteNumber}
                </span>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  backgroundColor: '#ede9fe',
                  color: '#6d28d9'
                }}>
                  Rev R{quoteRevision}
                </span>
                {isEditMode && (
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    backgroundColor: '#fef3c7',
                    color: '#b45309'
                  }}>
                    Issued PI Revision
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.8rem', color: '#64748b', margin: '3px 0 0' }}>
                Opportunity: <strong>{opportunity.name}</strong> • Customer: <strong>{opportunity.accountName || account.name || 'Valued Client'}</strong>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#64748b',
              cursor: 'pointer',
              padding: '0.35rem',
              borderRadius: '6px'
            }}
            title="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '1.5rem 1.75rem', overflowY: 'auto', flex: 1 }}>
          {error && (
            <div style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '6px',
              padding: '0.75rem 1rem',
              marginBottom: '1rem',
              color: '#b91c1c',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          )}

          {stateMismatchNotice && (
            <div style={{
              backgroundColor: '#fffbeb',
              border: '1px solid #fde68a',
              borderRadius: '6px',
              padding: '0.65rem 0.9rem',
              marginBottom: '1rem',
              color: '#92400e',
              fontSize: '0.82rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <Info size={16} style={{ flexShrink: 0, color: '#d97706' }} />
              <span>{stateMismatchNotice}</span>
            </div>
          )}

          {/* EDIT REASON FOR ISSUED PI */}
          {isEditMode && (
            <div style={{
              backgroundColor: '#fffbeb',
              border: '1px solid #fde68a',
              borderRadius: '6px',
              padding: '1rem',
              marginBottom: '1.25rem'
            }}>
              <label style={{ fontSize: '0.8rem', fontWeight: 700, color: '#92400e', display: 'block', marginBottom: '4px' }}>
                Reason for Editing Issued Proforma Invoice * (Mandatory for Audit Trail)
              </label>
              <input
                type="text"
                value={overrideReason}
                onChange={e => setOverrideReason(e.target.value)}
                placeholder="e.g. Client requested quantity adjustment, negotiated price override, or updated scope..."
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #f59e0b',
                  borderRadius: '4px',
                  fontSize: '0.85rem',
                  backgroundColor: '#ffffff'
                }}
              />
            </div>
          )}

          {/* Configuration Row */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '1rem',
            marginBottom: '1.25rem'
          }}>
            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Tax Regime
              </label>
              <select
                value={taxType}
                onChange={e => handleTaxTypeChange(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  backgroundColor: '#ffffff',
                  color: '#0f172a'
                }}
              >
                <option value="INTRA_STATE">Intra-State (CGST 9% + SGST 9%)</option>
                <option value="INTER_STATE">Inter-State (IGST 18%)</option>
                <option value="EXEMPT">Exempt / Zero Tax</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Invoice Date
              </label>
              <input
                type="date"
                value={invoiceDate}
                onChange={e => setInvoiceDate(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  backgroundColor: '#ffffff',
                  color: '#0f172a'
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Reference Note
              </label>
              <input
                type="text"
                value={referenceNote}
                onChange={e => setReferenceNote(e.target.value)}
                placeholder="e.g. Quotation Ref / Work Order #"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  backgroundColor: '#ffffff',
                  color: '#0f172a'
                }}
              />
            </div>
          </div>

          {/* Line Items Table */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.92rem', fontWeight: 700, color: '#0f172a' }}>
              Invoice Line Items ({items.length})
            </h4>

            <div style={{ overflowX: 'auto', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
                    <th style={{ padding: '8px 12px', width: '38px', textAlign: 'center' }}>#</th>
                    <th style={{ padding: '8px 12px', minWidth: '180px' }}>Description / Service</th>
                    <th style={{ padding: '8px 12px', width: '80px', textAlign: 'right' }}>Qty</th>
                    <th style={{ padding: '8px 12px', width: '70px' }}>Unit</th>
                    <th style={{ padding: '8px 12px', width: '100px', textAlign: 'right' }}>Rate (₹)</th>
                    <th style={{ padding: '8px 12px', width: '90px', textAlign: 'right' }}>Discount (₹)</th>
                    <th style={{ padding: '8px 12px', width: '110px', textAlign: 'right' }}>Amount (₹)</th>
                    <th style={{ padding: '8px 12px', width: '40px', textAlign: 'center' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, idx) => {
                    const gross = Number(item.quantity || 1) * Number(item.rate || 0);
                    const taxable = Math.max(0, gross - Number(item.discountAmount || 0));

                    return (
                      <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '8px 12px', textAlign: 'center', color: '#64748b' }}>
                          {idx + 1}
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <input
                            type="text"
                            value={item.name}
                            onChange={e => handleItemChange(idx, 'name', e.target.value)}
                            style={{
                              width: '100%',
                              padding: '4px 6px',
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px',
                              fontSize: '0.825rem',
                              fontWeight: 600
                            }}
                          />
                          <input
                            type="text"
                            value={item.description}
                            onChange={e => handleItemChange(idx, 'description', e.target.value)}
                            placeholder="Optional description"
                            style={{
                              width: '100%',
                              padding: '3px 6px',
                              border: '1px solid #e2e8f0',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              marginTop: '2px',
                              color: '#64748b'
                            }}
                          />
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                          <input
                            type="number"
                            min="1"
                            value={item.quantity}
                            onChange={e => handleItemChange(idx, 'quantity', e.target.value)}
                            style={{
                              width: '65px',
                              padding: '4px 6px',
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px',
                              textAlign: 'right',
                              fontSize: '0.825rem'
                            }}
                          />
                        </td>
                        <td style={{ padding: '8px 12px' }}>
                          <input
                            type="text"
                            value={item.unit}
                            onChange={e => handleItemChange(idx, 'unit', e.target.value)}
                            style={{
                              width: '65px',
                              padding: '4px 6px',
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px',
                              fontSize: '0.825rem'
                            }}
                          />
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                          <input
                            type="number"
                            min="0"
                            value={item.rate}
                            onChange={e => handleItemChange(idx, 'rate', e.target.value)}
                            style={{
                              width: '90px',
                              padding: '4px 6px',
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px',
                              textAlign: 'right',
                              fontSize: '0.825rem'
                            }}
                          />
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                          <input
                            type="number"
                            min="0"
                            max={gross}
                            value={item.discountAmount}
                            onChange={e => handleItemChange(idx, 'discountAmount', e.target.value)}
                            style={{
                              width: '80px',
                              padding: '4px 6px',
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px',
                              textAlign: 'right',
                              fontSize: '0.825rem',
                              color: item.discountAmount > 0 ? '#b91c1c' : '#0f172a'
                            }}
                          />
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700, color: '#0f172a' }}>
                          ₹{taxable.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                          <button
                            type="button"
                            onClick={() => handleRemoveItem(idx)}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#dc2626',
                              cursor: 'pointer',
                              padding: '4px'
                            }}
                            title="Remove item"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Terms & Financial Summary */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 360px',
            gap: '1.5rem',
            alignItems: 'start'
          }}>
            {/* Terms block */}
            <div>
              <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.88rem', fontWeight: 700, color: '#0f172a' }}>
                Service &amp; Supply Terms
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '0.75rem' }}>
                {terms.map((term, idx) => (
                  <div key={idx} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '5px 8px',
                    backgroundColor: '#f8fafc',
                    borderRadius: '4px',
                    fontSize: '0.78rem',
                    border: '1px solid #f1f5f9'
                  }}>
                    <span>{idx + 1}. {term}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveTerm(idx)}
                      style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '2px' }}
                    >
                      <X size={13} />
                    </button>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="text"
                  value={newTerm}
                  onChange={e => setNewTerm(e.target.value)}
                  placeholder="Add custom invoice term..."
                  style={{
                    flex: 1,
                    padding: '5px 8px',
                    border: '1px solid #cbd5e1',
                    borderRadius: '4px',
                    fontSize: '0.8rem'
                  }}
                  onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); handleAddTerm(); } }}
                />
                <button
                  type="button"
                  onClick={handleAddTerm}
                  style={{
                    padding: '5px 12px',
                    backgroundColor: '#ffffff',
                    border: '1px solid #cbd5e1',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Add
                </button>
              </div>
            </div>

            {/* Financial Summary */}
            <div style={{
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '1.25rem'
            }}>
              <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.9rem', fontWeight: 700, color: '#0f172a' }}>
                Financial Summary
              </h4>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', fontSize: '0.825rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#475569' }}>
                  <span>Gross Subtotal:</span>
                  <span style={{ fontWeight: 600 }}>₹{grossSubtotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>

                {totalDiscount > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#b91c1c' }}>
                    <span>Total Discount:</span>
                    <span style={{ fontWeight: 600 }}>-₹{totalDiscount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#0f172a', fontWeight: 600, borderTop: '1px dashed #cbd5e1', paddingTop: '4px' }}>
                  <span>Taxable Amount:</span>
                  <span>₹{taxableSubtotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>

                {taxType === 'INTRA_STATE' ? (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#475569' }}>
                      <span>CGST ({cgstRate}%):</span>
                      <span>₹{cgstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#475569' }}>
                      <span>SGST ({sgstRate}%):</span>
                      <span>₹{sgstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                  </>
                ) : taxType === 'INTER_STATE' ? (
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#475569' }}>
                    <span>IGST ({igstRate}%):</span>
                    <span>₹{igstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                  </div>
                ) : (
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#475569' }}>
                    <span>Tax (Exempt):</span>
                    <span>₹0.00</span>
                  </div>
                )}

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  borderTop: '2px solid #0f172a',
                  paddingTop: '0.5rem',
                  marginTop: '0.4rem',
                  fontSize: '1.05rem',
                  fontWeight: 800,
                  color: '#0284c7'
                }}>
                  <span>Grand Total:</span>
                  <span>₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div style={{
          padding: '1rem 1.75rem',
          borderTop: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#f8fafc'
        }}>
          <button
            type="button"
            onClick={handlePreview}
            disabled={previewing || items.length === 0}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              backgroundColor: '#ffffff',
              border: '1px solid #cbd5e1',
              color: '#334155',
              padding: '0.5rem 0.85rem',
              borderRadius: '6px',
              fontSize: '0.825rem',
              fontWeight: 600,
              cursor: previewing || items.length === 0 ? 'not-allowed' : 'pointer'
            }}
          >
            <Eye size={15} />
            <span>{previewing ? 'Rendering Preview...' : 'Preview in New Tab'}</span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #cbd5e1',
                color: '#475569',
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                fontSize: '0.85rem',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>

            <button
              type="button"
              onClick={handleSaveInvoice}
              disabled={submitting || items.length === 0}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                backgroundColor: isEditMode ? '#d97706' : '#059669',
                color: '#ffffff',
                border: 'none',
                padding: '0.5rem 1.25rem',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontWeight: 700,
                cursor: submitting || items.length === 0 ? 'not-allowed' : 'pointer',
                opacity: submitting || items.length === 0 ? 0.7 : 1
              }}
            >
              <Send size={15} />
              <span>{submitting ? 'Processing...' : isEditMode ? 'Save PI Changes' : 'Generate Proforma Invoice'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
