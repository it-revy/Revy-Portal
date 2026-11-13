import React, { useState, useEffect } from 'react';
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
  ShieldAlert
} from 'lucide-react';
import { invoiceService } from '../../services/invoiceService';
import catalogueService from '../../services/catalogueService';
import { Button, StatusBadge } from '../ui';

export default function InvoicePreparationModal({
  isOpen,
  onClose,
  opportunity,
  quotation,
  onInvoiceCreated
}) {
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
  const [referenceNote, setReferenceNote] = useState('');
  const [terms, setTerms] = useState([]);
  const [newTerm, setNewTerm] = useState('');

  // Computed Totals
  const [subtotal, setSubtotal] = useState(0);
  const [cgstRate, setCgstRate] = useState(9);
  const [cgstAmount, setCgstAmount] = useState(0);
  const [sgstRate, setSgstRate] = useState(9);
  const [sgstAmount, setSgstAmount] = useState(0);
  const [igstRate, setIgstRate] = useState(18);
  const [igstAmount, setIgstAmount] = useState(0);
  const [totalTax, setTotalTax] = useState(0);
  const [grandTotal, setGrandTotal] = useState(0);

  // Initialize from source quotation
  useEffect(() => {
    if (!isOpen || !quotation) return;

    // Load line items from quotation
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
      rate: Number(item.unitPrice) || Number(item.rate) || 0,
      notes: ''
    }));
    setItems(mappedItems);

    setTaxType(quotation.taxType || 'INTRA_STATE');
    setSelectedTaxConfigId(quotation.taxConfigurationId || '');
    setReferenceNote(quotation.title ? `Quotation Ref: ${quotation.quotationNumber} - ${quotation.title}` : `Quotation Ref: ${quotation.quotationNumber}`);

    // Load company defaults for terms & taxes
    loadDefaults();
  }, [isOpen, quotation]);

  const loadDefaults = async () => {
    setLoading(true);
    try {
      const [compRes, taxRes] = await Promise.all([
        invoiceService.getCompanySettings(),
        catalogueService.getTaxConfigurations({ includeInactive: false })
      ]);

      if (compRes.data) {
        const defaultTerms = compRes.data.defaultTerms || [
          '100 % Advance alongwith PO or Work order',
          'Payment to be made in Favour of " REVY Environmental Solutions Pvt.Ltd.',
          'Transportation cost for delivery or rendering services will be charged extra as actual',
          'We will not be any storing sample provided by client after 7 days post analysis'
        ];
        setTerms(defaultTerms);
      }

      if (taxRes.data?.success) {
        const taxes = taxRes.data.taxConfigurations || [];
        setTaxConfigurations(taxes);
        if (!selectedTaxConfigId && taxes.length > 0) {
          const def = taxes.find(t => t.taxType === taxType) || taxes[0];
          if (def) setSelectedTaxConfigId(def.id);
        }
      }
    } catch (err) {
      console.error('Error loading invoice defaults:', err);
    } finally {
      setLoading(false);
    }
  };

  // Recalculate Totals whenever items or tax config changes
  useEffect(() => {
    const sum = items.reduce((acc, it) => acc + (Number(it.quantity || 0) * Number(it.rate || 0)), 0);
    setSubtotal(sum);

    let cgst = 0;
    let sgst = 0;
    let igst = 0;
    let taxSum = 0;

    if (taxType === 'INTRA_STATE') {
      cgst = Math.round(sum * (cgstRate / 100) * 100) / 100;
      sgst = Math.round(sum * (sgstRate / 100) * 100) / 100;
      taxSum = cgst + sgst;
    } else if (taxType === 'INTER_STATE') {
      igst = Math.round(sum * (igstRate / 100) * 100) / 100;
      taxSum = igst;
    } else {
      taxSum = 0;
    }

    setCgstAmount(cgst);
    setSgstAmount(sgst);
    setIgstAmount(igst);
    setTotalTax(taxSum);
    setGrandTotal(sum + taxSum);
  }, [items, taxType, cgstRate, sgstRate, igstRate]);

  // Handle item property changes
  const handleItemChange = (index, field, value) => {
    const updated = [...items];
    updated[index] = { ...updated[index], [field]: value };
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

  // Preview in New Tab (Without Saving)
  const handlePreview = async () => {
    setPreviewing(true);
    setError(null);
    try {
      const payload = {
        opportunity_id: opportunity.id,
        quotation_id: quotation.id,
        tax_type: taxType,
        tax_configuration_id: selectedTaxConfigId || undefined,
        reference_note: referenceNote,
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
      setError(err.response?.data?.detail || 'Failed to generate invoice preview.');
    } finally {
      setPreviewing(false);
    }
  };

  // Confirm and Save Permanent PI
  const handleSaveInvoice = async () => {
    if (!window.confirm('Are you sure you want to approve this quotation and generate the permanent Proforma Invoice? This will assign the next sequential invoice number.')) {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        opportunity_id: opportunity.id,
        quotation_id: quotation.id,
        tax_type: taxType,
        tax_configuration_id: selectedTaxConfigId || undefined,
        reference_note: referenceNote,
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
          notes: it.notes
        }))
      };

      const res = await invoiceService.createProformaInvoice(payload);
      if (res.data?.success) {
        alert(`Proforma Invoice ${res.data.piNumber} generated successfully!`);
        if (onInvoiceCreated) {
          onInvoiceCreated(res.data);
        }
        onClose();
      }
    } catch (err) {
      console.error('Invoice creation error:', err);
      setError(err.response?.data?.detail || 'Failed to create Proforma Invoice.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen || !opportunity) return null;

  const account = opportunity.account || {};

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.75)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1050,
      padding: '1.5rem'
    }}>
      <div style={{
        background: 'var(--card-bg, #1e293b)',
        borderRadius: '12px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        width: '100%',
        maxWidth: '1100px',
        maxHeight: '92vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        color: '#f8fafc'
      }}>
        {/* Header */}
        <div style={{
          padding: '1.25rem 1.75rem',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(90deg, rgba(0, 176, 240, 0.12), transparent)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              background: '#00B0F0',
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <FileText size={20} color="white" />
            </div>
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0 }}>
                Approve Quotation &amp; Prepare Proforma Invoice
              </h2>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                Source: Quotation {quotation?.quotationNumber || 'N/A'} for {opportunity.name}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '0.25rem'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '1.5rem 1.75rem', overflowY: 'auto', flex: 1 }}>
          {error && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid #ef4444',
              borderRadius: '8px',
              padding: '0.85rem 1rem',
              marginBottom: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.65rem',
              color: '#fca5a5'
            }}>
              <AlertTriangle size={18} />
              <span>{error}</span>
            </div>
          )}

          {warnings.length > 0 && (
            <div style={{
              background: 'rgba(245, 158, 11, 0.12)',
              border: '1px solid #f59e0b',
              borderRadius: '8px',
              padding: '0.85rem 1rem',
              marginBottom: '1.25rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fbbf24', fontWeight: 600, fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                <AlertTriangle size={16} /> Attention / Non-blocking Warnings:
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#cbd5e1' }}>
                {warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Customer & Document Information Summary Card */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1rem',
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.07)',
            borderRadius: '8px',
            padding: '1rem 1.25rem',
            marginBottom: '1.5rem'
          }}>
            <div>
              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700 }}>
                Client / Account
              </div>
              <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#38bdf8', marginTop: '2px' }}>
                {account.name || 'N/A'}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '2px' }}>
                Customer ID: <strong>{account.customerId || account.accountId || 'Auto'}</strong>
              </div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                GSTIN: {account.gstNumber || <span style={{ color: '#f59e0b' }}>Missing</span>}
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700 }}>
                Opportunity Reference
              </div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', marginTop: '2px' }}>
                {opportunity.opportunityId} – {opportunity.name}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '2px' }}>
                Source Quote: <strong>{quotation?.quotationNumber || 'N/A'}</strong>
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.72rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700, display: 'block', marginBottom: '4px' }}>
                Tax Type (Supply Configuration)
              </label>
              <select
                value={taxType}
                onChange={(e) => setTaxType(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.45rem 0.65rem',
                  borderRadius: '6px',
                  background: '#0f172a',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  color: '#fff',
                  fontSize: '0.85rem'
                }}
              >
                <option value="INTRA_STATE">Intra-State: CGST (9%) + SGST (9%) [Total 18%]</option>
                <option value="INTER_STATE">Inter-State: IGST (18%)</option>
                <option value="EXEMPT">Exempt / Zero Rated (0%)</option>
              </select>
            </div>
          </div>

          {/* Reference Note */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem', color: '#cbd5e1' }}>
              Invoice Reference Note (Printed below customer block):
            </label>
            <input
              type="text"
              value={referenceNote}
              onChange={(e) => setReferenceNote(e.target.value)}
              placeholder="e.g. Samples Received from Himmatnagar on 24.10.26"
              style={{
                width: '100%',
                padding: '0.55rem 0.85rem',
                borderRadius: '6px',
                background: '#0f172a',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: '#fff',
                fontSize: '0.85rem'
              }}
            />
          </div>

          {/* Line Items Table */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#94a3b8' }}>
                Invoice Line Items ({items.length})
              </div>
              <span style={{ fontSize: '0.78rem', color: '#64748b' }}>
                * Quantities and Rates can be edited for this Proforma Invoice without modifying catalogue prices.
              </span>
            </div>

            <div style={{
              overflowX: 'auto',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px'
            }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ background: 'rgba(0, 176, 240, 0.2)', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <th style={{ padding: '0.65rem 0.85rem', width: '50px', textAlign: 'center' }}>Sr.</th>
                    <th style={{ padding: '0.65rem 0.85rem' }}>Service / Product</th>
                    <th style={{ padding: '0.65rem 0.85rem', width: '90px' }}>Unit</th>
                    <th style={{ padding: '0.65rem 0.85rem', width: '100px', textAlign: 'right' }}>Qty</th>
                    <th style={{ padding: '0.65rem 0.85rem', width: '130px', textAlign: 'right' }}>Rate (₹)</th>
                    <th style={{ padding: '0.65rem 0.85rem', width: '130px', textAlign: 'right' }}>Amount (₹)</th>
                    <th style={{ padding: '0.65rem 0.85rem', width: '50px', textAlign: 'center' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, idx) => {
                    const lineAmount = (Number(item.quantity || 0) * Number(item.rate || 0)).toFixed(2);
                    return (
                      <tr
                        key={idx}
                        style={{
                          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                          background: idx % 2 === 0 ? 'rgba(255, 255, 255, 0.015)' : 'transparent'
                        }}
                      >
                        <td style={{ padding: '0.65rem', textAlign: 'center', color: '#94a3b8' }}>
                          {item.srNo}
                        </td>
                        <td style={{ padding: '0.65rem' }}>
                          <div style={{ fontWeight: 600 }}>{item.name}</div>
                          {item.description && item.description !== item.name && (
                            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                              {item.description}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '0.65rem', color: '#94a3b8' }}>
                          {item.unit}
                        </td>
                        <td style={{ padding: '0.65rem', textAlign: 'right' }}>
                          <input
                            type="number"
                            min="0.1"
                            step="any"
                            value={item.quantity}
                            onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                            style={{
                              width: '75px',
                              padding: '0.35rem 0.45rem',
                              borderRadius: '4px',
                              background: '#0f172a',
                              border: '1px solid rgba(255, 255, 255, 0.15)',
                              color: '#fff',
                              textAlign: 'right',
                              fontSize: '0.85rem'
                            }}
                          />
                        </td>
                        <td style={{ padding: '0.65rem', textAlign: 'right' }}>
                          <input
                            type="number"
                            min="0"
                            step="any"
                            value={item.rate}
                            onChange={(e) => handleItemChange(idx, 'rate', e.target.value)}
                            style={{
                              width: '105px',
                              padding: '0.35rem 0.45rem',
                              borderRadius: '4px',
                              background: '#0f172a',
                              border: '1px solid rgba(255, 255, 255, 0.15)',
                              color: '#fff',
                              textAlign: 'right',
                              fontSize: '0.85rem'
                            }}
                          />
                        </td>
                        <td style={{ padding: '0.65rem', textAlign: 'right', fontWeight: 600, color: '#38bdf8' }}>
                          ₹{Number(lineAmount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td style={{ padding: '0.65rem', textAlign: 'center' }}>
                          <button
                            onClick={() => handleRemoveItem(idx)}
                            title="Remove line item"
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#ef4444',
                              cursor: 'pointer',
                              padding: '2px'
                            }}
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Bottom Grid: Terms & Bank vs Totals */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '1.5rem',
            marginBottom: '1rem'
          }}>
            {/* Terms & Conditions list */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid rgba(255, 255, 255, 0.06)',
              borderRadius: '8px',
              padding: '1rem'
            }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', color: '#94a3b8', marginBottom: '0.5rem' }}>
                Service &amp; Supply Terms
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: '160px', overflowY: 'auto' }}>
                {terms.map((term, tIdx) => (
                  <div key={tIdx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', color: '#cbd5e1', padding: '0.25rem 0.4rem', background: 'rgba(0,0,0,0.2)', borderRadius: '4px' }}>
                    <span>{tIdx + 1}. {term}</span>
                    <button
                      onClick={() => handleRemoveTerm(tIdx)}
                      style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', marginLeft: '6px' }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.65rem' }}>
                <input
                  type="text"
                  placeholder="Add custom term..."
                  value={newTerm}
                  onChange={(e) => setNewTerm(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddTerm()}
                  style={{
                    flex: 1,
                    padding: '0.35rem 0.65rem',
                    borderRadius: '4px',
                    background: '#0f172a',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    color: '#fff',
                    fontSize: '0.8rem'
                  }}
                />
                <button
                  onClick={handleAddTerm}
                  style={{
                    background: '#00B0F0',
                    border: 'none',
                    color: '#fff',
                    borderRadius: '4px',
                    padding: '0.35rem 0.75rem',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    fontWeight: 600
                  }}
                >
                  Add
                </button>
              </div>
            </div>

            {/* Calculations and Totals Summary */}
            <div style={{
              background: 'rgba(0, 176, 240, 0.05)',
              border: '1px solid rgba(0, 176, 240, 0.25)',
              borderRadius: '8px',
              padding: '1.25rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.35rem 0', fontSize: '0.9rem' }}>
                <span style={{ color: '#94a3b8' }}>Subtotal:</span>
                <span style={{ fontWeight: 600 }}>₹{subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>

              {taxType === 'INTRA_STATE' && (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.35rem 0', fontSize: '0.85rem' }}>
                    <span style={{ color: '#94a3b8' }}>CGST ({cgstRate}%):</span>
                    <span>₹{cgstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.35rem 0', fontSize: '0.85rem' }}>
                    <span style={{ color: '#94a3b8' }}>SGST ({sgstRate}%):</span>
                    <span>₹{sgstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                </>
              )}

              {taxType === 'INTER_STATE' && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.35rem 0', fontSize: '0.85rem' }}>
                  <span style={{ color: '#94a3b8' }}>IGST ({igstRate}%):</span>
                  <span>₹{igstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
              )}

              {taxType === 'EXEMPT' && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.35rem 0', fontSize: '0.85rem', color: '#10b981' }}>
                  <span>Tax:</span>
                  <span>Exempt (0.00)</span>
                </div>
              )}

              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '0.75rem 0 0',
                marginTop: '0.5rem',
                borderTop: '2px solid rgba(0, 176, 240, 0.4)',
                fontSize: '1.15rem',
                fontWeight: 700,
                color: '#38bdf8'
              }}>
                <span>Grand Total:</span>
                <span>₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div style={{
          padding: '1.25rem 1.75rem',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(0, 0, 0, 0.2)'
        }}>
          <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            ℹ️ Generating PI creates an immutable Revision 1 and sequential PI number.
          </div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <Button
              variant="outline"
              onClick={onClose}
              disabled={submitting || previewing}
            >
              Cancel
            </Button>
            <Button
              variant="secondary"
              onClick={handlePreview}
              disabled={submitting || previewing || items.length === 0}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', background: '#334155' }}
            >
              <ExternalLink size={16} />
              {previewing ? 'Generating Preview...' : 'Preview in New Tab'}
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveInvoice}
              disabled={submitting || previewing || items.length === 0}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                background: '#00B0F0',
                borderColor: '#00B0F0',
                color: 'white',
                fontWeight: 700
              }}
            >
              <CheckCircle size={16} />
              {submitting ? 'Creating Invoice...' : 'Confirm & Issue PI'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
