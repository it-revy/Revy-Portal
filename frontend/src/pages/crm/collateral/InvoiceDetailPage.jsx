import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  FileText,
  Printer,
  Edit,
  Plus,
  Trash2,
  ArrowLeft,
  CheckCircle,
  AlertCircle,
  Clock,
  History,
  Building,
  CreditCard,
  Building2,
  ExternalLink,
  ShieldAlert,
  ChevronRight,
  Receipt
} from 'lucide-react';
import { invoiceService } from '../../../services/invoiceService';
import catalogueService from '../../../services/catalogueService';
import { PageHeader, StatusBadge } from '../../../components/ui';

export default function InvoiceDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pi, setPi] = useState(null);
  const [selectedRevisionNumber, setSelectedRevisionNumber] = useState(null);

  // Revision Modal State
  const [showRevisionModal, setShowRevisionModal] = useState(false);
  const [revisionItems, setRevisionItems] = useState([]);
  const [revisionTaxType, setRevisionTaxType] = useState('INTRA_STATE');
  const [revisionTerms, setRevisionTerms] = useState([]);
  const [revisionNote, setRevisionNote] = useState('');
  const [submittingRevision, setSubmittingRevision] = useState(false);
  const [revisionError, setRevisionError] = useState(null);

  useEffect(() => {
    fetchInvoiceDetails();
  }, [id]);

  const fetchInvoiceDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await invoiceService.getProformaInvoice(id);
      if (res.data?.success && res.data.proformaInvoice) {
        const inv = res.data.proformaInvoice;
        setPi(inv);
        setSelectedRevisionNumber(inv.currentRevisionNumber);
      }
    } catch (err) {
      console.error('Failed to load proforma invoice:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to load Proforma Invoice details.');
    } finally {
      setLoading(false);
    }
  };

  // Find active revision snapshot
  const activeRevision = pi?.revisions?.find(r => r.revisionNumber === selectedRevisionNumber) || pi?.currentRevision;

  // Print PI (opens printable HTML template)
  const handlePrint = () => {
    const url = invoiceService.getInvoiceHtmlUrl(id, selectedRevisionNumber);
    window.open(url, '_blank');
  };

  // Open Create Revision Modal
  const handleOpenRevisionModal = () => {
    if (!activeRevision) return;
    // Clone current items for editing in revision
    const clonedItems = (activeRevision.items || []).map((it, idx) => ({
      srNo: idx + 1,
      itemType: it.itemType,
      serviceId: it.serviceId,
      packageId: it.packageId,
      itemCode: it.itemCode,
      name: it.name,
      description: it.description || '',
      quantity: Number(it.quantity) || 1,
      unit: it.unit || 'Test',
      rate: Number(it.rate) || 0,
      notes: it.notes || ''
    }));

    setRevisionItems(clonedItems);
    setRevisionTaxType(activeRevision.taxType || 'INTRA_STATE');
    setRevisionTerms(activeRevision.termsSnapshot || []);
    setRevisionNote(`Revision based on Rev ${activeRevision.revisionNumber}`);
    setShowRevisionModal(true);
  };

  // Save new Revision N+1
  const handleSaveRevision = async () => {
    if (revisionItems.length === 0) {
      alert('At least one line item is required.');
      return;
    }

    setSubmittingRevision(true);
    setRevisionError(null);
    try {
      const payload = {
        tax_type: revisionTaxType,
        reference_note: revisionNote,
        terms: revisionTerms,
        items: revisionItems.map(it => ({
          sr_no: it.srNo,
          item_type: it.itemType,
          service_id: it.serviceId || undefined,
          package_id: it.packageId || undefined,
          name: it.name,
          description: it.description,
          quantity: Number(it.quantity),
          unit: it.unit,
          rate: Number(it.rate),
          notes: it.notes
        }))
      };

      const res = await invoiceService.createInvoiceRevision(id, payload);
      if (res.data?.success) {
        alert(`Revision ${res.data.revisionNumber} created successfully!`);
        setShowRevisionModal(false);
        fetchInvoiceDetails();
      }
    } catch (err) {
      console.error('Failed to create revision:', err);
      setRevisionError(err.response?.data?.detail || err.message || 'Failed to create revision.');
    } finally {
      setSubmittingRevision(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '3.5rem', textAlign: 'center', color: '#94a3b8' }}>
        <p>Loading Proforma Invoice details...</p>
      </div>
    );
  }

  if (error || !pi) {
    return (
      <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
        <div style={{
          padding: '1.25rem',
          backgroundColor: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid #ef4444',
          borderRadius: '8px',
          color: '#fca5a5'
        }}>
          <AlertCircle size={24} style={{ marginBottom: '0.5rem' }} />
          <h3 style={{ margin: 0, fontSize: '1.1rem' }}>Proforma Invoice Not Found</h3>
          <p style={{ margin: '0.5rem 0' }}>{error || 'The requested Proforma Invoice does not exist.'}</p>
          <button
            onClick={() => navigate('/crm/collateral/invoices')}
            style={{
              marginTop: '0.5rem',
              backgroundColor: '#334155',
              border: 'none',
              color: 'white',
              padding: '0.4rem 0.8rem',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            ← Back to Invoices
          </button>
        </div>
      </div>
    );
  }

  const customerSnapshot = activeRevision?.customerSnapshot || {};
  const companySnapshot = activeRevision?.companySnapshot || {};
  const bankSnapshot = companySnapshot.bankDetails || {};
  const signatorySnapshot = companySnapshot.signatory || {};
  const items = activeRevision?.items || [];

  return (
    <div className="crm-page-container" style={{ padding: '1.5rem', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Top Navigation Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', fontSize: '0.85rem', color: '#94a3b8' }}>
        <Link to="/crm/collateral" style={{ color: '#38bdf8', textDecoration: 'none' }}>Collateral</Link>
        <ChevronRight size={14} />
        <Link to="/crm/collateral/invoices" style={{ color: '#38bdf8', textDecoration: 'none' }}>Invoices</Link>
        <ChevronRight size={14} />
        <span style={{ color: '#f8fafc' }}>{pi.piNumber}</span>
      </div>

      {/* Main Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '1.5rem',
        backgroundColor: '#1e293b',
        padding: '1.25rem 1.5rem',
        borderRadius: '8px',
        border: '1px solid #334155'
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
              {pi.piNumber}
            </h1>
            <span style={{
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '0.75rem',
              fontWeight: 700,
              backgroundColor: '#065f46',
              color: '#d1fae5'
            }}>
              {pi.status || 'ISSUED'}
            </span>
            <span style={{
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '0.75rem',
              fontWeight: 600,
              backgroundColor: '#0284c7',
              color: '#e0f2fe'
            }}>
              FY {pi.financialYear}
            </span>
          </div>

          <p style={{ margin: '6px 0 0', fontSize: '0.85rem', color: '#94a3b8' }}>
            Opportunity: <Link to={`/crm/opportunities/${pi.opportunityId}/edit`} style={{ color: '#38bdf8' }}>{pi.opportunityName} ({pi.opportunityNumber})</Link> • Account: <strong>{pi.accountName}</strong>
          </p>
        </div>

        {/* Header Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={handlePrint}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              backgroundColor: '#0284c7',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              padding: '0.6rem 1.1rem',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 4px 10px rgba(2, 132, 199, 0.3)'
            }}
          >
            <Printer size={16} />
            Print / Download PDF
          </button>

          <button
            onClick={handleOpenRevisionModal}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.45rem',
              backgroundColor: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              padding: '0.6rem 1.1rem',
              fontSize: '0.88rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <Plus size={16} />
            Create Revision
          </button>
        </div>
      </div>

      {/* Revision History Switcher */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '1.25rem',
        backgroundColor: '#0f172a',
        padding: '0.6rem 1rem',
        borderRadius: '6px',
        border: '1px solid #334155'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#94a3b8', fontSize: '0.82rem', fontWeight: 600 }}>
          <History size={16} color="#f59e0b" />
          <span>REVISION HISTORY:</span>
        </div>

        <div style={{ display: 'flex', gap: '0.4rem', overflowX: 'auto' }}>
          {pi.revisions?.map((rev) => {
            const isSelected = rev.revisionNumber === selectedRevisionNumber;
            return (
              <button
                key={rev.id}
                onClick={() => setSelectedRevisionNumber(rev.revisionNumber)}
                style={{
                  padding: '4px 12px',
                  borderRadius: '4px',
                  border: isSelected ? '1px solid #38bdf8' : '1px solid #334155',
                  backgroundColor: isSelected ? '#0369a1' : '#1e293b',
                  color: isSelected ? '#ffffff' : '#cbd5e1',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <span>Rev {rev.revisionNumber}</span>
                {rev.revisionNumber === pi.currentRevisionNumber && (
                  <span style={{ fontSize: '0.68rem', opacity: 0.8 }}>(Latest)</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Document View Card (A4 preview layout) */}
      <div style={{
        backgroundColor: '#ffffff',
        color: '#0f172a',
        borderRadius: '8px',
        padding: '2.5rem',
        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.4)',
        border: '1px solid #cbd5e1',
        marginBottom: '2rem'
      }}>
        {/* Document Header (REVY Branding) */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '2px solid #0284c7', paddingBottom: '1.5rem', marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <img
              src="/images/logo.png"
              alt="REVY Environmental Solutions"
              style={{ height: '55px', objectFit: 'contain' }}
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
            <div>
              <h2 style={{ fontSize: '1.3rem', fontWeight: 800, margin: 0, color: '#0f172a' }}>
                {companySnapshot.companyName || 'REVY Environmental Solutions Pvt. Ltd.'}
              </h2>
              <p style={{ margin: '4px 0 0', fontSize: '0.78rem', color: '#64748b', maxWidth: '420px', lineHeight: 1.4 }}>
                {companySnapshot.registeredAddress || 'Vadodara, Gujarat, India'}
              </p>
              <p style={{ margin: '4px 0 0', fontSize: '0.78rem', color: '#475569' }}>
                <strong>GSTIN:</strong> {companySnapshot.gstin || 'N/A'} • <strong>PAN:</strong> {companySnapshot.pan || 'N/A'}
              </p>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{
              display: 'inline-block',
              backgroundColor: '#0284c7',
              color: 'white',
              fontWeight: 800,
              fontSize: '1rem',
              letterSpacing: '0.05em',
              padding: '6px 14px',
              borderRadius: '4px',
              textTransform: 'uppercase'
            }}>
              PROFORMA INVOICE
            </div>
            <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: '#1e293b' }}>
              <div><strong>PI No:</strong> {activeRevision?.piNumber}</div>
              <div><strong>Date:</strong> {activeRevision?.piDate || new Date().toISOString().split('T')[0]}</div>
              <div><strong>Revision:</strong> Rev {activeRevision?.revisionNumber}</div>
              <div><strong>Source Quote:</strong> {pi.quotationNumber || 'N/A'}</div>
            </div>
          </div>
        </div>

        {/* Customer & Billing Address */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '1.5rem', backgroundColor: '#f8fafc', padding: '1rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: '#64748b', letterSpacing: '0.05em' }}>
              BILLED TO / CUSTOMER DETAILS
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0f172a', marginTop: '4px' }}>
              {customerSnapshot.accountName || pi.accountName}
            </div>
            {customerSnapshot.customerId && (
              <div style={{ fontSize: '0.8rem', color: '#d97706', fontWeight: 600 }}>
                Customer ID: {customerSnapshot.customerId}
              </div>
            )}
            <div style={{ fontSize: '0.82rem', color: '#475569', marginTop: '4px', lineHeight: 1.4 }}>
              {customerSnapshot.address || 'Address on file'}
            </div>
            {customerSnapshot.gstin && (
              <div style={{ fontSize: '0.82rem', color: '#1e293b', marginTop: '4px' }}>
                <strong>GSTIN:</strong> {customerSnapshot.gstin}
              </div>
            )}
          </div>

          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', fontWeight: 700, color: '#64748b', letterSpacing: '0.05em' }}>
              CONTACT & PROJECT DETAILS
            </div>
            <div style={{ fontSize: '0.85rem', color: '#1e293b', marginTop: '4px' }}>
              <strong>Contact Person:</strong> {customerSnapshot.contactPerson || 'Authorized Representative'}
            </div>
            {customerSnapshot.email && (
              <div style={{ fontSize: '0.82rem', color: '#475569' }}>
                <strong>Email:</strong> {customerSnapshot.email}
              </div>
            )}
            {customerSnapshot.phone && (
              <div style={{ fontSize: '0.82rem', color: '#475569' }}>
                <strong>Phone:</strong> {customerSnapshot.phone}
              </div>
            )}
            <div style={{ fontSize: '0.82rem', color: '#475569', marginTop: '4px' }}>
              <strong>Opportunity:</strong> {pi.opportunityName}
            </div>
          </div>
        </div>

        {/* Item Table */}
        <div style={{ marginBottom: '1.5rem', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ backgroundColor: '#0284c7', color: 'white', textAlign: 'left' }}>
                <th style={{ padding: '8px 10px', width: '40px' }}>Sr.</th>
                <th style={{ padding: '8px 10px' }}>Service / Product</th>
                <th style={{ padding: '8px 10px' }}>Description</th>
                <th style={{ padding: '8px 10px', width: '70px', textAlign: 'center' }}>Qty</th>
                <th style={{ padding: '8px 10px', width: '70px', textAlign: 'center' }}>Unit</th>
                <th style={{ padding: '8px 10px', width: '110px', textAlign: 'right' }}>Rate (₹)</th>
                <th style={{ padding: '8px 10px', width: '120px', textAlign: 'right' }}>Amount (₹)</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, idx) => (
                <tr key={it.id || idx} style={{ borderBottom: '1px solid #e2e8f0', backgroundColor: idx % 2 === 0 ? '#ffffff' : '#f8fafc' }}>
                  <td style={{ padding: '8px 10px', color: '#64748b' }}>{it.srNo || idx + 1}</td>
                  <td style={{ padding: '8px 10px', fontWeight: 600, color: '#0f172a' }}>{it.name}</td>
                  <td style={{ padding: '8px 10px', color: '#475569', fontSize: '0.8rem' }}>{it.description || '—'}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'center', color: '#0f172a', fontWeight: 600 }}>{it.quantity}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'center', color: '#64748b' }}>{it.unit || 'Test'}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'right', color: '#0f172a' }}>₹{Number(it.rate).toLocaleString('en-IN')}</td>
                  <td style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 700, color: '#0f172a' }}>
                    ₹{Number(it.amount).toLocaleString('en-IN')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Totals & Tax Calculation Breakdown */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '2rem', marginBottom: '1.5rem' }}>
          {/* Bank Account Details */}
          <div style={{ backgroundColor: '#f8fafc', padding: '1rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#0284c7', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
              Bank Account Details for Wire / NEFT Transfer
            </div>
            <div style={{ fontSize: '0.8rem', color: '#334155', lineHeight: 1.5 }}>
              <div><strong>Bank Name:</strong> {bankSnapshot.bankName || 'HDFC Bank'}</div>
              <div><strong>Account Name:</strong> {bankSnapshot.accountName || companySnapshot.companyName}</div>
              <div><strong>Account Number:</strong> {bankSnapshot.accountNumber || '—'}</div>
              <div><strong>IFSC Code:</strong> {bankSnapshot.ifscCode || '—'}</div>
              <div><strong>Branch:</strong> {bankSnapshot.branch || 'Vadodara'}</div>
              {bankSnapshot.upiId && <div><strong>UPI ID:</strong> {bankSnapshot.upiId}</div>}
            </div>
          </div>

          {/* Amount Calculation Summary */}
          <div style={{ backgroundColor: '#f8fafc', padding: '1rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.85rem', color: '#334155' }}>
              <span>Subtotal:</span>
              <span style={{ fontWeight: 600 }}>₹{Number(activeRevision?.subtotal || 0).toLocaleString('en-IN')}</span>
            </div>

            {activeRevision?.taxType === 'INTRA_STATE' && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem', fontSize: '0.8rem', color: '#64748b' }}>
                  <span>CGST ({activeRevision.cgstRate}%):</span>
                  <span>₹{Number(activeRevision.cgstAmount || 0).toLocaleString('en-IN')}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem', fontSize: '0.8rem', color: '#64748b' }}>
                  <span>SGST ({activeRevision.sgstRate}%):</span>
                  <span>₹{Number(activeRevision.sgstAmount || 0).toLocaleString('en-IN')}</span>
                </div>
              </>
            )}

            {activeRevision?.taxType === 'INTER_STATE' && (
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem', fontSize: '0.8rem', color: '#64748b' }}>
                <span>IGST ({activeRevision.igstRate}%):</span>
                <span>₹{Number(activeRevision.igstAmount || 0).toLocaleString('en-IN')}</span>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.85rem', color: '#334155' }}>
              <span>Total Tax:</span>
              <span style={{ fontWeight: 600 }}>₹{Number(activeRevision?.totalTax || 0).toLocaleString('en-IN')}</span>
            </div>

            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              paddingTop: '0.6rem',
              borderTop: '2px solid #0284c7',
              fontSize: '1.1rem',
              fontWeight: 800,
              color: '#0f172a'
            }}>
              <span>Grand Total:</span>
              <span>₹{Number(activeRevision?.grandTotal || 0).toLocaleString('en-IN')}</span>
            </div>
          </div>
        </div>

        {/* Terms & Signatory Section */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 0.7fr', gap: '2rem', borderTop: '1px solid #e2e8f0', paddingTop: '1.25rem' }}>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: '0.4rem' }}>
              Terms & Conditions
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.78rem', color: '#475569', lineHeight: 1.5 }}>
              {(activeRevision?.termsSnapshot || []).map((t, idx) => (
                <li key={idx}>{t}</li>
              ))}
            </ul>
          </div>

          <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end' }}>
            <img
              src="/images/signature.png"
              alt="Authorised Signatory"
              style={{ maxHeight: '60px', marginBottom: '6px' }}
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
            <div style={{ borderTop: '1px solid #94a3b8', width: '180px', paddingTop: '4px' }}>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0f172a' }}>
                {signatorySnapshot.name || 'Authorised Signatory'}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
                {signatorySnapshot.designation || 'REVY Environmental Solutions Pvt. Ltd.'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Revision Modal */}
      {showRevisionModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.8)',
          zIndex: 10000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1.5rem'
        }}>
          <div style={{
            backgroundColor: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '12px',
            width: '100%',
            maxWidth: '900px',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            color: '#f8fafc'
          }}>
            <div style={{
              padding: '1.25rem',
              backgroundColor: '#1e293b',
              borderBottom: '1px solid #334155',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0 }}>
                Create Revision (Rev {(pi.currentRevisionNumber || 1) + 1}) for {pi.piNumber}
              </h3>
              <button
                onClick={() => setShowRevisionModal(false)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem' }}>
              {revisionError && (
                <div style={{
                  padding: '0.75rem',
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid #ef4444',
                  borderRadius: '6px',
                  color: '#fca5a5',
                  marginBottom: '1rem',
                  fontSize: '0.85rem'
                }}>
                  {revisionError}
                </div>
              )}

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>Revision Note / Reason</label>
                <input
                  type="text"
                  value={revisionNote}
                  onChange={e => setRevisionNote(e.target.value)}
                  style={{
                    width: '100%',
                    marginTop: '4px',
                    padding: '0.5rem',
                    backgroundColor: '#1e293b',
                    border: '1px solid #475569',
                    borderRadius: '6px',
                    color: 'white',
                    fontSize: '0.85rem'
                  }}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>Tax Structure</label>
                <select
                  value={revisionTaxType}
                  onChange={e => setRevisionTaxType(e.target.value)}
                  style={{
                    width: '100%',
                    marginTop: '4px',
                    padding: '0.5rem',
                    backgroundColor: '#1e293b',
                    border: '1px solid #475569',
                    borderRadius: '6px',
                    color: 'white',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value="INTRA_STATE">Intra-State (CGST 9% + SGST 9%)</option>
                  <option value="INTER_STATE">Inter-State (IGST 18%)</option>
                  <option value="EXEMPT">Exempt / Zero-Rated (0%)</option>
                </select>
              </div>

              {/* Items editing table */}
              <div style={{ backgroundColor: '#1e293b', borderRadius: '6px', overflow: 'hidden', border: '1px solid #334155' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#0f172a', color: '#94a3b8', textAlign: 'left' }}>
                      <th style={{ padding: '6px 8px' }}>#</th>
                      <th style={{ padding: '6px 8px' }}>Item</th>
                      <th style={{ padding: '6px 8px', width: '80px' }}>Qty</th>
                      <th style={{ padding: '6px 8px', width: '80px' }}>Unit</th>
                      <th style={{ padding: '6px 8px', width: '110px' }}>Rate (₹)</th>
                      <th style={{ padding: '6px 8px', width: '40px' }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {revisionItems.map((it, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #334155' }}>
                        <td style={{ padding: '6px 8px', color: '#94a3b8' }}>{idx + 1}</td>
                        <td style={{ padding: '6px 8px' }}>
                          <input
                            type="text"
                            value={it.name}
                            onChange={e => {
                              const updated = [...revisionItems];
                              updated[idx].name = e.target.value;
                              setRevisionItems(updated);
                            }}
                            style={{ width: '100%', padding: '4px', backgroundColor: '#0f172a', border: '1px solid #475569', color: 'white', borderRadius: '4px' }}
                          />
                        </td>
                        <td style={{ padding: '6px 8px' }}>
                          <input
                            type="number"
                            min="1"
                            value={it.quantity}
                            onChange={e => {
                              const updated = [...revisionItems];
                              updated[idx].quantity = Math.max(1, parseFloat(e.target.value) || 1);
                              setRevisionItems(updated);
                            }}
                            style={{ width: '100%', padding: '4px', backgroundColor: '#0f172a', border: '1px solid #475569', color: 'white', borderRadius: '4px' }}
                          />
                        </td>
                        <td style={{ padding: '6px 8px' }}>
                          <input
                            type="text"
                            value={it.unit}
                            onChange={e => {
                              const updated = [...revisionItems];
                              updated[idx].unit = e.target.value;
                              setRevisionItems(updated);
                            }}
                            style={{ width: '100%', padding: '4px', backgroundColor: '#0f172a', border: '1px solid #475569', color: 'white', borderRadius: '4px' }}
                          />
                        </td>
                        <td style={{ padding: '6px 8px' }}>
                          <input
                            type="number"
                            min="0"
                            value={it.rate}
                            onChange={e => {
                              const updated = [...revisionItems];
                              updated[idx].rate = Math.max(0, parseFloat(e.target.value) || 0);
                              setRevisionItems(updated);
                            }}
                            style={{ width: '100%', padding: '4px', backgroundColor: '#0f172a', border: '1px solid #0284c7', color: '#38bdf8', fontWeight: 600, borderRadius: '4px' }}
                          />
                        </td>
                        <td style={{ padding: '6px 8px' }}>
                          <button
                            type="button"
                            onClick={() => setRevisionItems(revisionItems.filter((_, i) => i !== idx))}
                            style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }}
                          >
                            <Trash2 size={15} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div style={{
              padding: '1rem',
              backgroundColor: '#1e293b',
              borderTop: '1px solid #334155',
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '0.75rem'
            }}>
              <button
                type="button"
                onClick={() => setShowRevisionModal(false)}
                style={{ padding: '0.5rem 1rem', backgroundColor: '#334155', border: 'none', color: '#cbd5e1', borderRadius: '6px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveRevision}
                disabled={submittingRevision}
                style={{
                  padding: '0.5rem 1.25rem',
                  backgroundColor: '#10b981',
                  border: 'none',
                  color: 'white',
                  fontWeight: 600,
                  borderRadius: '6px',
                  cursor: submittingRevision ? 'not-allowed' : 'pointer'
                }}
              >
                {submittingRevision ? 'Creating Revision...' : `Save Revision ${activeRevision.revisionNumber + 1}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
