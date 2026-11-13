import React, { useState, useEffect } from 'react';
import {
  FileText,
  Plus,
  Trash2,
  Copy,
  CheckCircle,
  AlertCircle,
  X,
  Layers,
  Package as PackageIcon,
  FlaskConical,
  Sparkles,
  Info,
  DollarSign,
  HelpCircle,
  Save,
  Check,
  Send
} from 'lucide-react';
import { invoiceService } from '../../services/invoiceService';
import catalogueService from '../../services/catalogueService';
import { useAuth } from '../../context/AuthContext';
import { Button, StatusBadge } from '../ui';

export default function QuotationManagerModal({
  isOpen,
  onClose,
  opportunity,
  onQuotationSaved,
  onApproveAndCreateInvoice
}) {
  const { hasRole, isGlobalAdmin, hasPermission } = useAuth();
  const globalAdminActive = typeof isGlobalAdmin === 'function' ? isGlobalAdmin() : Boolean(isGlobalAdmin);
  const canManageCatalogue = globalAdminActive || hasRole('CRM_ADMIN') || hasPermission('crm.catalogue.manage');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Active Quotation State
  const [quotationId, setQuotationId] = useState(null);
  const [quotationNumber, setQuotationNumber] = useState(null);
  const [title, setTitle] = useState('');
  const [validUntilDays, setValidUntilDays] = useState(30);
  const [validUntilDate, setValidUntilDate] = useState('');
  const [termsAndConditions, setTermsAndConditions] = useState('');
  const [notes, setNotes] = useState('');
  const [currency, setCurrency] = useState('INR');
  const [taxType, setTaxType] = useState('INTRA_STATE');
  const [selectedTaxConfigId, setSelectedTaxConfigId] = useState('');
  const [emailText, setEmailText] = useState('');

  // Items
  const [items, setItems] = useState([]);

  // Catalogue Options
  const [categories, setCategories] = useState([]);
  const [services, setServices] = useState([]);
  const [packages, setPackages] = useState([]);
  const [taxConfigurations, setTaxConfigurations] = useState([]);

  // Item Picker State
  const [showItemPicker, setShowItemPicker] = useState(false);
  const [pickerTab, setPickerTab] = useState('services'); // 'services', 'packages', 'custom'
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState('all');
  const [pickerSearch, setPickerSearch] = useState('');

  // Custom Item Form State
  const [customItemType, setCustomItemType] = useState('CUSTOM_SERVICE'); // 'CUSTOM_SERVICE' or 'CUSTOM_PRODUCT'
  const [customItemName, setCustomItemName] = useState('');
  const [customItemDescription, setCustomItemDescription] = useState('');
  const [customItemUnit, setCustomItemUnit] = useState('Test');
  const [customItemPrice, setCustomItemPrice] = useState('');
  const [customItemQty, setCustomItemQty] = useState(1);
  const [customSavePermanently, setCustomSavePermanently] = useState(false);
  const [customCategoryId, setCustomCategoryId] = useState('');

  // Load Existing Quotation & Catalogue Data
  useEffect(() => {
    if (isOpen && opportunity?.id) {
      loadData();
    }
  }, [isOpen, opportunity?.id]);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [quoteRes, catRes, srvRes, pkgRes, taxRes, compRes] = await Promise.all([
        invoiceService.getCurrentQuotation(opportunity.id),
        catalogueService.getCategories(),
        catalogueService.getServices({ isActive: true, limit: 100 }),
        catalogueService.getPackages({ isActive: true }),
        catalogueService.getTaxConfigurations({ includeInactive: false }),
        invoiceService.getCompanySettings()
      ]);

      // Categories
      if (catRes.data?.success) {
        setCategories(catRes.data.categories || []);
        if (catRes.data.categories?.length > 0) {
          setCustomCategoryId(catRes.data.categories[0].id);
        }
      }

      // Services
      if (srvRes.data?.success) {
        setServices(srvRes.data.services || []);
      }

      // Packages
      if (pkgRes.data?.success) {
        setPackages(pkgRes.data.packages || []);
      }

      // Taxes
      if (taxRes.data?.success) {
        const taxes = taxRes.data.taxConfigurations || [];
        setTaxConfigurations(taxes);
        const def = taxes.find(t => t.isDefault) || taxes[0];
        if (def) setSelectedTaxConfigId(def.id);
      }

      // Company Defaults for Terms
      let defaultTermsText = '';
      if (compRes.data?.defaultTerms) {
        defaultTermsText = compRes.data.defaultTerms.join('\n');
      }

      // Process Existing Quotation if present
      const q = quoteRes.data?.quotation;
      if (q) {
        setQuotationId(q.id);
        setQuotationNumber(q.quotationNumber);
        setTitle(q.title || `Quotation for ${opportunity.name}`);
        setValidUntilDate(q.validUntilDate || '');
        setTermsAndConditions(q.termsAndConditions || defaultTermsText);
        setNotes(q.notes || '');
        setCurrency(q.currency || 'INR');
        setTaxType(q.taxType || 'INTRA_STATE');
        setSelectedTaxConfigId(q.taxConfigurationId || '');
        setEmailText(q.emailText || '');

        const mapped = (q.items || []).map(it => ({
          id: it.id,
          itemType: it.itemType || 'SERVICE',
          serviceId: it.serviceId,
          packageId: it.packageId,
          packageVersionId: it.packageVersionId,
          itemName: it.itemName || it.name,
          itemCode: it.itemCode,
          description: it.description || '',
          billingUnit: it.billingUnit || 'Test',
          standardPrice: Number(it.unitPrice || 0),
          unitPrice: Number(it.negotiatedUnitPrice !== null && it.negotiatedUnitPrice !== undefined ? it.negotiatedUnitPrice : it.unitPrice || 0),
          quantity: Number(it.quantity || 1),
          discountAmount: Number(it.discountAmount || 0),
          savePermanently: false,
          categoryId: null
        }));
        setItems(mapped);
      } else {
        // Draft defaults
        setQuotationId(null);
        setQuotationNumber(null);
        setTitle(`Quotation for ${opportunity.name}`);
        setTermsAndConditions(defaultTermsText || [
          '1. 100% Advance along with Purchase Order / Work Order.',
          '2. Payment to be made in favour of "REVY Environmental Solutions Pvt. Ltd."',
          '3. Transportation cost for delivery or sample collection will be charged extra at actuals.',
          '4. Samples will be stored for a maximum of 7 days post-analysis.',
          '5. Quotation validity: 30 days from date of issue.'
        ].join('\n'));
        setNotes('Thank you for choosing REVY Environmental Solutions. We look forward to working with you.');
        setItems([]);
      }
    } catch (err) {
      console.error('Failed to load quotation data:', err);
      setError(err.response?.data?.message || err.message || 'Failed to load quotation details.');
    } finally {
      setLoading(false);
    }
  };

  // Calculations
  const subtotal = items.reduce((sum, item) => {
    const lineTotal = (Number(item.quantity || 1) * Number(item.unitPrice || 0)) - Number(item.discountAmount || 0);
    return sum + Math.max(0, lineTotal);
  }, 0);

  let cgstAmount = 0;
  let sgstAmount = 0;
  let igstAmount = 0;
  let totalTax = 0;

  if (taxType === 'INTRA_STATE') {
    cgstAmount = Math.round(subtotal * 0.09 * 100) / 100;
    sgstAmount = Math.round(subtotal * 0.09 * 100) / 100;
    totalTax = cgstAmount + sgstAmount;
  } else if (taxType === 'INTER_STATE') {
    igstAmount = Math.round(subtotal * 0.18 * 100) / 100;
    totalTax = igstAmount;
  } else {
    totalTax = 0;
  }

  const grandTotal = subtotal + totalTax;

  // Add standard service from catalogue
  const handleAddService = (srv) => {
    const newItem = {
      itemType: 'SERVICE',
      serviceId: srv.id,
      packageId: null,
      packageVersionId: null,
      itemName: srv.serviceName,
      itemCode: srv.serviceCode,
      description: srv.description || srv.categoryName || '',
      billingUnit: srv.billingUnitName || 'Test',
      standardPrice: Number(srv.standardPrice || 0),
      unitPrice: Number(srv.standardPrice || 0),
      quantity: Number(srv.minimumBillingQuantity || 1),
      discountAmount: 0,
      savePermanently: false,
      categoryId: srv.categoryId
    };
    setItems([...items, newItem]);
    setShowItemPicker(false);
  };

  // Add package from catalogue
  const handleAddPackage = (pkg) => {
    const activeVer = pkg.activeVersion;
    const pkgPrice = Number(activeVer?.packagePrice || 0);
    const newItem = {
      itemType: 'PACKAGE',
      serviceId: null,
      packageId: pkg.id,
      packageVersionId: activeVer?.id || null,
      itemName: pkg.packageName,
      itemCode: pkg.packageCode,
      description: pkg.description || `Package includes ${activeVer?.items?.length || 0} services`,
      billingUnit: 'Package',
      standardPrice: pkgPrice,
      unitPrice: pkgPrice,
      quantity: 1,
      discountAmount: 0,
      savePermanently: false,
      categoryId: null
    };
    setItems([...items, newItem]);
    setShowItemPicker(false);
  };

  // Add custom item
  const handleAddCustomItem = () => {
    if (!customItemName.trim()) {
      alert('Please enter an item name for the custom product/service.');
      return;
    }
    const price = Number(customItemPrice);
    if (isNaN(price) || price < 0) {
      alert('Please enter a valid unit price.');
      return;
    }

    const newItem = {
      itemType: customItemType,
      serviceId: null,
      packageId: null,
      packageVersionId: null,
      itemName: customItemName.trim(),
      itemCode: customItemType === 'CUSTOM_SERVICE' ? 'CUSTOM-SRV' : 'CUSTOM-PRD',
      description: customItemDescription.trim(),
      billingUnit: customItemUnit.trim() || 'Unit',
      standardPrice: price,
      unitPrice: price,
      quantity: Math.max(1, Number(customItemQty) || 1),
      discountAmount: 0,
      savePermanently: customSavePermanently,
      categoryId: customSavePermanently ? customCategoryId : null
    };

    setItems([...items, newItem]);
    // Reset custom form
    setCustomItemName('');
    setCustomItemDescription('');
    setCustomItemPrice('');
    setCustomItemQty(1);
    setCustomSavePermanently(false);
    setShowItemPicker(false);
  };

  // Update Item in place
  const handleItemFieldChange = (index, field, value) => {
    const updated = [...items];
    updated[index] = { ...updated[index], [field]: value };
    setItems(updated);
  };

  const handleRemoveItem = (index) => {
    setItems(items.filter((_, i) => i !== index));
  };

  // Save Quotation to Backend (Single Current Quotation)
  const handleSaveQuotation = async (silent = false) => {
    if (items.length === 0) {
      alert('Please add at least one line item to the quotation before saving.');
      return null;
    }

    setSaving(true);
    setError(null);
    try {
      const payload = {
        title: title || `Quotation for ${opportunity.name}`,
        currency: currency,
        taxType: taxType,
        taxConfigurationId: selectedTaxConfigId || undefined,
        validUntilDate: validUntilDate || undefined,
        termsAndConditions: termsAndConditions,
        notes: notes,
        items: items.map(it => ({
          itemType: it.itemType,
          serviceId: it.serviceId || undefined,
          packageId: it.packageId || undefined,
          packageVersionId: it.packageVersionId || undefined,
          itemName: it.itemName,
          itemCode: it.itemCode,
          description: it.description,
          billingUnit: it.billingUnit,
          quantity: Number(it.quantity || 1),
          unitPrice: Number(it.standardPrice || it.unitPrice || 0),
          negotiatedUnitPrice: Number(it.unitPrice || 0),
          discountAmount: Number(it.discountAmount || 0),
          savePermanently: Boolean(it.savePermanently),
          categoryId: it.categoryId || undefined
        }))
      };

      const res = await invoiceService.saveCurrentQuotation(opportunity.id, payload);
      if (res.data?.success) {
        const savedQuote = res.data.quotation;
        setQuotationId(savedQuote.id);
        setQuotationNumber(savedQuote.quotationNumber);
        setEmailText(savedQuote.emailText || '');
        if (!silent) {
          showToast(`Quotation ${savedQuote.quotationNumber} saved successfully!`);
        }
        if (onQuotationSaved) {
          onQuotationSaved(savedQuote);
        }
        return savedQuote;
      }
    } catch (err) {
      console.error('Failed to save quotation:', err);
      setError(err.response?.data?.message || err.response?.data?.detail || 'Failed to save quotation.');
      return null;
    } finally {
      setSaving(false);
    }
  };

  // Copy Quotation Text (Email-Ready)
  const handleCopyQuotation = async () => {
    let textToCopy = emailText;

    // If quotation is dirty or not saved yet, construct email text dynamically
    if (!textToCopy || items.length > 0) {
      let lines = [];
      lines.push('===========================================================');
      lines.push('REVY ENVIRONMENTAL SOLUTIONS PVT. LTD. - COMMERCIAL QUOTATION');
      lines.push('===========================================================');
      lines.push(`Opportunity: ${opportunity.name} (${opportunity.opportunityId || ''})`);
      lines.push(`Customer: ${opportunity.accountName || opportunity.account?.name || 'Valued Client'}`);
      lines.push(`Quotation Reference: ${quotationNumber || 'DRAFT'}`);
      lines.push(`Date: ${new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}`);
      lines.push('-----------------------------------------------------------');
      lines.push('ITEMS & PRICING:');
      items.forEach((it, idx) => {
        const lineTotal = (Number(it.quantity || 1) * Number(it.unitPrice || 0)) - Number(it.discountAmount || 0);
        lines.push(`${idx + 1}. ${it.itemName}`);
        if (it.description) lines.push(`   Description: ${it.description}`);
        lines.push(`   Qty: ${it.quantity} ${it.billingUnit} @ ₹${Number(it.unitPrice).toLocaleString('en-IN')}`);
        if (Number(it.discountAmount) > 0) {
          lines.push(`   Discount: -₹${Number(it.discountAmount).toLocaleString('en-IN')}`);
        }
        lines.push(`   Line Total: ₹${lineTotal.toLocaleString('en-IN')}`);
      });
      lines.push('-----------------------------------------------------------');
      lines.push(`Subtotal: ₹${subtotal.toLocaleString('en-IN')}`);
      if (taxType === 'INTRA_STATE') {
        lines.push(`CGST (9%): ₹${cgstAmount.toLocaleString('en-IN')}`);
        lines.push(`SGST (9%): ₹${sgstAmount.toLocaleString('en-IN')}`);
      } else if (taxType === 'INTER_STATE') {
        lines.push(`IGST (18%): ₹${igstAmount.toLocaleString('en-IN')}`);
      } else {
        lines.push('Taxes: Exempt / Not Applicable');
      }
      lines.push(`Total Tax: ₹${totalTax.toLocaleString('en-IN')}`);
      lines.push(`GRAND TOTAL: ₹${grandTotal.toLocaleString('en-IN')}`);
      lines.push('-----------------------------------------------------------');
      if (termsAndConditions) {
        lines.push('TERMS & CONDITIONS:');
        lines.push(termsAndConditions);
        lines.push('-----------------------------------------------------------');
      }
      if (notes) {
        lines.push('NOTES:');
        lines.push(notes);
      }
      lines.push('===========================================================');
      textToCopy = lines.join('\n');
    }

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      showToast('Quotation copied to clipboard! Ready to paste into an email.');
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      alert('Unable to copy automatically. Please select and copy manually.');
    }
  };

  // Approve Quotation and Trigger Invoice Preparation Modal
  const handleApproveAndProceedToInvoice = async () => {
    // 1. Save latest changes first
    const savedQuote = await handleSaveQuotation(true);
    if (!savedQuote) return;

    // 2. Call parent callback to open InvoicePreparationModal
    if (onApproveAndCreateInvoice) {
      onApproveAndCreateInvoice(savedQuote);
    }
  };

  // Filtered Services in Picker
  const filteredServices = services.filter(s => {
    const matchesCat = selectedCategoryFilter === 'all' || s.categoryId === selectedCategoryFilter;
    const matchesSearch = !pickerSearch ||
      s.serviceName?.toLowerCase().includes(pickerSearch.toLowerCase()) ||
      s.serviceCode?.toLowerCase().includes(pickerSearch.toLowerCase());
    return matchesCat && matchesSearch;
  });

  if (!isOpen || !opportunity) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '1rem'
    }}>
      <div style={{
        backgroundColor: '#0f172a',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '1150px',
        maxHeight: '94vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        border: '1px solid #334155',
        color: '#f8fafc',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#1e293b'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '8px',
              backgroundColor: '#0284c7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white'
            }}>
              <FileText size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h2 style={{ fontSize: '1.2rem', fontWeight: 600, margin: 0 }}>
                  Quotation Management
                </h2>
                {quotationNumber ? (
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    backgroundColor: '#0369a1',
                    color: '#e0f2fe'
                  }}>
                    {quotationNumber}
                  </span>
                ) : (
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    backgroundColor: '#475569',
                    color: '#cbd5e1'
                  }}>
                    Draft
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.82rem', color: '#94a3b8', margin: '2px 0 0' }}>
                Opportunity: <strong>{opportunity.name}</strong> • Account: <strong>{opportunity.accountName || opportunity.account?.name || 'N/A'}</strong>
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {toastMessage && (
              <span style={{
                fontSize: '0.8rem',
                color: '#34d399',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                padding: '4px 10px',
                borderRadius: '6px'
              }}>
                {toastMessage}
              </span>
            )}

            <button
              onClick={handleCopyQuotation}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                backgroundColor: '#334155',
                color: '#f8fafc',
                border: '1px solid #475569',
                borderRadius: '6px',
                padding: '0.5rem 0.85rem',
                fontSize: '0.85rem',
                fontWeight: 500,
                cursor: 'pointer'
              }}
              title="Copy email-formatted quotation to clipboard"
            >
              {copied ? <Check size={16} color="#34d399" /> : <Copy size={16} />}
              {copied ? 'Copied!' : 'Copy Quotation'}
            </button>

            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                padding: '4px'
              }}
            >
              <X size={22} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {error && (
            <div style={{
              padding: '0.75rem 1rem',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid #ef4444',
              borderRadius: '8px',
              color: '#fca5a5',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          {/* Quotation Header Fields */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '1rem',
            backgroundColor: '#1e293b',
            padding: '1rem',
            borderRadius: '8px',
            border: '1px solid #334155'
          }}>
            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                Quotation Title
              </label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="e.g. Laboratory Analysis Proposal"
                style={{
                  width: '100%',
                  marginTop: '4px',
                  padding: '0.5rem 0.75rem',
                  backgroundColor: '#0f172a',
                  border: '1px solid #475569',
                  borderRadius: '6px',
                  color: 'white',
                  fontSize: '0.85rem'
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                Tax Configuration
              </label>
              <select
                value={taxType}
                onChange={e => setTaxType(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: '4px',
                  padding: '0.5rem 0.75rem',
                  backgroundColor: '#0f172a',
                  border: '1px solid #475569',
                  borderRadius: '6px',
                  color: 'white',
                  fontSize: '0.85rem'
                }}
              >
                <option value="INTRA_STATE">Intra-State (CGST 9% + SGST 9% = 18%)</option>
                <option value="INTER_STATE">Inter-State (IGST 18%)</option>
                <option value="EXEMPT">Exempt / Zero-Rated (0%)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                Valid Until Date
              </label>
              <input
                type="date"
                value={validUntilDate}
                onChange={e => setValidUntilDate(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: '4px',
                  padding: '0.5rem 0.75rem',
                  backgroundColor: '#0f172a',
                  border: '1px solid #475569',
                  borderRadius: '6px',
                  color: 'white',
                  fontSize: '0.85rem'
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                Currency
              </label>
              <input
                type="text"
                value={currency}
                disabled
                style={{
                  width: '100%',
                  marginTop: '4px',
                  padding: '0.5rem 0.75rem',
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '6px',
                  color: '#94a3b8',
                  fontSize: '0.85rem'
                }}
              />
            </div>
          </div>

          {/* Line Items Section */}
          <div style={{ backgroundColor: '#1e293b', borderRadius: '8px', border: '1px solid #334155', overflow: 'hidden' }}>
            <div style={{
              padding: '0.85rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderBottom: '1px solid #334155',
              backgroundColor: '#1e293b'
            }}>
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>
                  Quotation Line Items ({items.length})
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Select from 61 catalogue services across 4 categories, packages, or custom items.
                </span>
              </div>

              <button
                type="button"
                onClick={() => setShowItemPicker(true)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  backgroundColor: '#0284c7',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '0.45rem 0.85rem',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                <Plus size={16} />
                Add Item / Service
              </button>
            </div>

            {items.length === 0 ? (
              <div style={{ padding: '2.5rem', textAlign: 'center', color: '#94a3b8' }}>
                <FlaskConical size={36} style={{ margin: '0 auto 0.75rem', opacity: 0.5 }} />
                <p style={{ margin: 0, fontSize: '0.9rem' }}>No items added to this quotation yet.</p>
                <button
                  type="button"
                  onClick={() => setShowItemPicker(true)}
                  style={{
                    marginTop: '0.75rem',
                    background: 'none',
                    border: '1px dashed #475569',
                    borderRadius: '6px',
                    color: '#38bdf8',
                    padding: '0.5rem 1rem',
                    fontSize: '0.85rem',
                    cursor: 'pointer'
                  }}
                >
                  + Add from Service Catalogue or Custom
                </button>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#0f172a', color: '#94a3b8', textAlign: 'left', borderBottom: '1px solid #334155' }}>
                      <th style={{ padding: '0.65rem 0.75rem', width: '40px' }}>#</th>
                      <th style={{ padding: '0.65rem 0.75rem', width: '90px' }}>Type</th>
                      <th style={{ padding: '0.65rem 0.75rem' }}>Item & Description</th>
                      <th style={{ padding: '0.65rem 0.75rem', width: '90px' }}>Qty</th>
                      <th style={{ padding: '0.65rem 0.75rem', width: '70px' }}>Unit</th>
                      <th style={{ padding: '0.65rem 0.75rem', width: '100px', textAlign: 'right' }}>Std Price</th>
                      <th style={{ padding: '0.65rem 0.75rem', width: '120px', textAlign: 'right' }}>
                        Negotiated Rate (₹)
                      </th>
                      <th style={{ padding: '0.65rem 0.75rem', width: '100px', textAlign: 'right' }}>Discount</th>
                      <th style={{ padding: '0.65rem 0.75rem', width: '120px', textAlign: 'right' }}>Line Total</th>
                      <th style={{ padding: '0.65rem 0.75rem', width: '50px', textAlign: 'center' }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((it, idx) => {
                      const lineTotal = (Number(it.quantity || 1) * Number(it.unitPrice || 0)) - Number(it.discountAmount || 0);
                      if (!isOpen || !opportunity) return null;

  return (
                        <tr key={idx} style={{ borderBottom: '1px solid #334155' }}>
                          <td style={{ padding: '0.65rem 0.75rem', color: '#94a3b8' }}>{idx + 1}</td>
                          <td style={{ padding: '0.65rem 0.75rem' }}>
                            <span style={{
                              fontSize: '0.72rem',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontWeight: 600,
                              backgroundColor: it.itemType === 'PACKAGE' ? '#4338ca' : it.itemType.startsWith('CUSTOM') ? '#b45309' : '#0369a1',
                              color: 'white'
                            }}>
                              {it.itemType.replace('CUSTOM_', 'CST-')}
                            </span>
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem' }}>
                            <div style={{ fontWeight: 600, color: '#f8fafc' }}>{it.itemName}</div>
                            {it.itemCode && <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>[{it.itemCode}] </span>}
                            <input
                              type="text"
                              value={it.description}
                              onChange={e => handleItemFieldChange(idx, 'description', e.target.value)}
                              placeholder="Notes / description for quote"
                              style={{
                                width: '100%',
                                marginTop: '3px',
                                padding: '2px 6px',
                                backgroundColor: '#0f172a',
                                border: '1px solid #334155',
                                borderRadius: '4px',
                                color: '#cbd5e1',
                                fontSize: '0.75rem'
                              }}
                            />
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem' }}>
                            <input
                              type="number"
                              min="1"
                              value={it.quantity}
                              onChange={e => handleItemFieldChange(idx, 'quantity', Math.max(1, parseInt(e.target.value) || 1))}
                              style={{
                                width: '100%',
                                padding: '4px 6px',
                                backgroundColor: '#0f172a',
                                border: '1px solid #475569',
                                borderRadius: '4px',
                                color: 'white',
                                fontSize: '0.85rem',
                                textAlign: 'center'
                              }}
                            />
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem', color: '#94a3b8' }}>
                            {it.billingUnit || 'Test'}
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem', textAlign: 'right', color: '#94a3b8' }}>
                            ₹{Number(it.standardPrice || 0).toLocaleString('en-IN')}
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem', textAlign: 'right' }}>
                            <input
                              type="number"
                              min="0"
                              step="1"
                              value={it.unitPrice}
                              onChange={e => handleItemFieldChange(idx, 'unitPrice', Math.max(0, parseFloat(e.target.value) || 0))}
                              style={{
                                width: '100%',
                                padding: '4px 6px',
                                backgroundColor: '#0f172a',
                                border: '1px solid #0284c7',
                                borderRadius: '4px',
                                color: '#38bdf8',
                                fontWeight: 600,
                                fontSize: '0.85rem',
                                textAlign: 'right'
                              }}
                            />
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem', textAlign: 'right' }}>
                            <input
                              type="number"
                              min="0"
                              step="1"
                              value={it.discountAmount}
                              onChange={e => handleItemFieldChange(idx, 'discountAmount', Math.max(0, parseFloat(e.target.value) || 0))}
                              style={{
                                width: '100%',
                                padding: '4px 6px',
                                backgroundColor: '#0f172a',
                                border: '1px solid #475569',
                                borderRadius: '4px',
                                color: '#fca5a5',
                                fontSize: '0.85rem',
                                textAlign: 'right'
                              }}
                            />
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem', textAlign: 'right', fontWeight: 700, color: '#f8fafc' }}>
                            ₹{Math.max(0, lineTotal).toLocaleString('en-IN')}
                          </td>
                          <td style={{ padding: '0.65rem 0.75rem', textAlign: 'center' }}>
                            <button
                              type="button"
                              onClick={() => handleRemoveItem(idx)}
                              style={{
                                background: 'transparent',
                                border: 'none',
                                color: '#ef4444',
                                cursor: 'pointer',
                                padding: '2px'
                              }}
                              title="Remove item"
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
            )}
          </div>

          {/* Quotation Summary & Calculations */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '1.25rem'
          }}>
            {/* Left: Terms and Conditions */}
            <div style={{ backgroundColor: '#1e293b', padding: '1rem', borderRadius: '8px', border: '1px solid #334155' }}>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase' }}>
                Terms & Conditions
              </label>
              <textarea
                rows={5}
                value={termsAndConditions}
                onChange={e => setTermsAndConditions(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: '6px',
                  padding: '0.5rem',
                  backgroundColor: '#0f172a',
                  border: '1px solid #475569',
                  borderRadius: '6px',
                  color: 'white',
                  fontSize: '0.82rem',
                  fontFamily: 'inherit',
                  resize: 'vertical'
                }}
              />

              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', marginTop: '0.75rem', display: 'block' }}>
                Notes / Special Instructions
              </label>
              <textarea
                rows={2}
                value={notes}
                onChange={e => setNotes(e.target.value)}
                style={{
                  width: '100%',
                  marginTop: '6px',
                  padding: '0.5rem',
                  backgroundColor: '#0f172a',
                  border: '1px solid #475569',
                  borderRadius: '6px',
                  color: 'white',
                  fontSize: '0.82rem',
                  fontFamily: 'inherit',
                  resize: 'vertical'
                }}
              />
            </div>

            {/* Right: Totals Box */}
            <div style={{
              backgroundColor: '#1e293b',
              padding: '1.25rem',
              borderRadius: '8px',
              border: '1px solid #334155',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}>
              <div>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 600, margin: '0 0 1rem', borderBottom: '1px solid #334155', paddingBottom: '0.5rem' }}>
                  Commercial Summary
                </h4>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.6rem', fontSize: '0.85rem' }}>
                  <span style={{ color: '#94a3b8' }}>Subtotal (Excl. Tax):</span>
                  <span style={{ fontWeight: 600 }}>₹{subtotal.toLocaleString('en-IN')}</span>
                </div>

                {taxType === 'INTRA_STATE' && (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.82rem', color: '#94a3b8' }}>
                      <span>CGST (9%):</span>
                      <span>₹{cgstAmount.toLocaleString('en-IN')}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.6rem', fontSize: '0.82rem', color: '#94a3b8' }}>
                      <span>SGST (9%):</span>
                      <span>₹{sgstAmount.toLocaleString('en-IN')}</span>
                    </div>
                  </>
                )}

                {taxType === 'INTER_STATE' && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.6rem', fontSize: '0.82rem', color: '#94a3b8' }}>
                    <span>IGST (18%):</span>
                    <span>₹{igstAmount.toLocaleString('en-IN')}</span>
                  </div>
                )}

                {taxType === 'EXEMPT' && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.6rem', fontSize: '0.82rem', color: '#94a3b8' }}>
                    <span>Taxes:</span>
                    <span>Exempt (0%)</span>
                  </div>
                )}

                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.6rem', fontSize: '0.85rem', color: '#94a3b8' }}>
                  <span>Total Tax:</span>
                  <span style={{ fontWeight: 600, color: '#f8fafc' }}>₹{totalTax.toLocaleString('en-IN')}</span>
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginTop: '0.75rem',
                  paddingTop: '0.75rem',
                  borderTop: '1px solid #475569',
                  fontSize: '1.1rem',
                  fontWeight: 700,
                  color: '#38bdf8'
                }}>
                  <span>Grand Total:</span>
                  <span>₹{grandTotal.toLocaleString('en-IN')}</span>
                </div>
              </div>

              {/* Action Buttons in summary footer */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '1.25rem' }}>
                <button
                  type="button"
                  onClick={handleApproveAndProceedToInvoice}
                  disabled={saving || items.length === 0}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem',
                    backgroundColor: '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '0.75rem',
                    fontSize: '0.92rem',
                    fontWeight: 700,
                    cursor: saving || items.length === 0 ? 'not-allowed' : 'pointer',
                    opacity: saving || items.length === 0 ? 0.6 : 1,
                    boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
                  }}
                >
                  <CheckCircle size={18} />
                  Approve Quotation and Create Invoice
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div style={{
          padding: '1rem 1.5rem',
          borderTop: '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#1e293b'
        }}>
          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
            * Note: REVY CRM maintains only the single current quotation per opportunity. Saving replaces previous quote data.
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                backgroundColor: 'transparent',
                border: '1px solid #475569',
                color: '#cbd5e1',
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
              onClick={() => handleSaveQuotation(false)}
              disabled={saving}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                backgroundColor: '#0284c7',
                color: 'white',
                border: 'none',
                padding: '0.5rem 1.25rem',
                borderRadius: '6px',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: saving ? 'not-allowed' : 'pointer',
                opacity: saving ? 0.7 : 1
              }}
            >
              <Save size={16} />
              {saving ? 'Saving...' : 'Save Current Quotation'}
            </button>
          </div>
        </div>
      </div>

      {/* Item Picker Drawer / Sub-Modal */}
      {showItemPicker && (
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
            maxWidth: '850px',
            maxHeight: '85vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            {/* Picker Header */}
            <div style={{
              padding: '1rem 1.25rem',
              backgroundColor: '#1e293b',
              borderBottom: '1px solid #334155',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 600, margin: 0, color: 'white' }}>
                  Add Line Item to Quotation
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Select from 61 catalogue services, packages, or configure a custom service/product.
                </span>
              </div>
              <button
                onClick={() => setShowItemPicker(false)}
                style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Picker Tabs */}
            <div style={{
              display: 'flex',
              backgroundColor: '#0f172a',
              borderBottom: '1px solid #334155',
              padding: '0 1rem'
            }}>
              <button
                type="button"
                onClick={() => setPickerTab('services')}
                style={{
                  padding: '0.75rem 1rem',
                  border: 'none',
                  background: 'none',
                  color: pickerTab === 'services' ? '#38bdf8' : '#94a3b8',
                  borderBottom: pickerTab === 'services' ? '2px solid #38bdf8' : 'none',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem'
                }}
              >
                <FlaskConical size={16} />
                Catalogue Services (61)
              </button>

              <button
                type="button"
                onClick={() => setPickerTab('packages')}
                style={{
                  padding: '0.75rem 1rem',
                  border: 'none',
                  background: 'none',
                  color: pickerTab === 'packages' ? '#38bdf8' : '#94a3b8',
                  borderBottom: pickerTab === 'packages' ? '2px solid #38bdf8' : 'none',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem'
                }}
              >
                <PackageIcon size={16} />
                Packages & Bundles ({packages.length})
              </button>

              <button
                type="button"
                onClick={() => setPickerTab('custom')}
                style={{
                  padding: '0.75rem 1rem',
                  border: 'none',
                  background: 'none',
                  color: pickerTab === 'custom' ? '#f59e0b' : '#94a3b8',
                  borderBottom: pickerTab === 'custom' ? '2px solid #f59e0b' : 'none',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem'
                }}
              >
                <Sparkles size={16} />
                Custom Product / Service
              </button>
            </div>

            {/* Picker Content */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
              {pickerTab === 'services' && (
                <div>
                  {/* Category Filter & Search */}
                  <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem' }}>
                    <select
                      value={selectedCategoryFilter}
                      onChange={e => setSelectedCategoryFilter(e.target.value)}
                      style={{
                        padding: '0.5rem',
                        backgroundColor: '#1e293b',
                        border: '1px solid #475569',
                        borderRadius: '6px',
                        color: 'white',
                        fontSize: '0.82rem',
                        width: '260px'
                      }}
                    >
                      <option value="all">All 4 Categories</option>
                      {categories.map(c => (
                        <option key={c.id} value={c.id}>{c.categoryName}</option>
                      ))}
                    </select>

                    <input
                      type="text"
                      placeholder="Search 61 services by name or code..."
                      value={pickerSearch}
                      onChange={e => setPickerSearch(e.target.value)}
                      style={{
                        flex: 1,
                        padding: '0.5rem 0.75rem',
                        backgroundColor: '#1e293b',
                        border: '1px solid #475569',
                        borderRadius: '6px',
                        color: 'white',
                        fontSize: '0.82rem'
                      }}
                    />
                  </div>

                  {/* Services Grid / List */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.75rem' }}>
                    {filteredServices.map(srv => (
                      <div
                        key={srv.id}
                        onClick={() => handleAddService(srv)}
                        style={{
                          backgroundColor: '#1e293b',
                          border: '1px solid #334155',
                          borderRadius: '8px',
                          padding: '0.75rem',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={e => e.currentTarget.style.borderColor = '#0284c7'}
                        onMouseLeave={e => e.currentTarget.style.borderColor = '#334155'}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                          <span style={{ fontSize: '0.7rem', color: '#38bdf8', fontWeight: 600 }}>{srv.serviceCode}</span>
                          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#34d399' }}>₹{Number(srv.standardPrice || 0).toLocaleString('en-IN')}</span>
                        </div>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'white', lineHeight: 1.25, marginBottom: '4px' }}>
                          {srv.serviceName}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                          {srv.categoryName} • Unit: {srv.billingUnitName || 'Test'}
                        </div>
                      </div>
                    ))}
                    {filteredServices.length === 0 && (
                      <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                        No services found matching search filters.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {pickerTab === 'packages' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.75rem' }}>
                  {packages.map(pkg => (
                    <div
                      key={pkg.id}
                      onClick={() => handleAddPackage(pkg)}
                      style={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                        padding: '1rem',
                        cursor: 'pointer'
                      }}
                      onMouseEnter={e => e.currentTarget.style.borderColor = '#6366f1'}
                      onMouseLeave={e => e.currentTarget.style.borderColor = '#334155'}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <span style={{ fontSize: '0.7rem', color: '#818cf8', fontWeight: 600 }}>{pkg.packageCode}</span>
                        <span style={{ fontSize: '0.9rem', fontWeight: 700, color: '#34d399' }}>
                          ₹{Number(pkg.activeVersion?.packagePrice || 0).toLocaleString('en-IN')}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'white', margin: '4px 0' }}>
                        {pkg.packageName}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                        {pkg.description || 'Pre-configured test bundle'}
                      </div>
                    </div>
                  ))}
                  {packages.length === 0 && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '2rem', color: '#94a3b8' }}>
                      No active packages available.
                    </div>
                  )}
                </div>
              )}

              {pickerTab === 'custom' && (
                <div style={{ backgroundColor: '#1e293b', padding: '1.25rem', borderRadius: '8px', border: '1px solid #334155' }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 600, margin: '0 0 1rem', color: '#f59e0b' }}>
                    Configure Custom Item
                  </h4>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>Item Type</label>
                      <select
                        value={customItemType}
                        onChange={e => setCustomItemType(e.target.value)}
                        style={{
                          width: '100%',
                          marginTop: '4px',
                          padding: '0.5rem',
                          backgroundColor: '#0f172a',
                          border: '1px solid #475569',
                          borderRadius: '6px',
                          color: 'white',
                          fontSize: '0.85rem'
                        }}
                      >
                        <option value="CUSTOM_SERVICE">Custom Service</option>
                        <option value="CUSTOM_PRODUCT">Custom Product</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>Item Name *</label>
                      <input
                        type="text"
                        value={customItemName}
                        onChange={e => setCustomItemName(e.target.value)}
                        placeholder="e.g. Specialized Heavy Metal Profiling"
                        style={{
                          width: '100%',
                          marginTop: '4px',
                          padding: '0.5rem',
                          backgroundColor: '#0f172a',
                          border: '1px solid #475569',
                          borderRadius: '6px',
                          color: 'white',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>Unit Price (₹) *</label>
                      <input
                        type="number"
                        min="0"
                        value={customItemPrice}
                        onChange={e => setCustomItemPrice(e.target.value)}
                        placeholder="e.g. 4500"
                        style={{
                          width: '100%',
                          marginTop: '4px',
                          padding: '0.5rem',
                          backgroundColor: '#0f172a',
                          border: '1px solid #475569',
                          borderRadius: '6px',
                          color: 'white',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>Billing Unit</label>
                      <input
                        type="text"
                        value={customItemUnit}
                        onChange={e => setCustomItemUnit(e.target.value)}
                        placeholder="e.g. Test, Sample, Unit, Month"
                        style={{
                          width: '100%',
                          marginTop: '4px',
                          padding: '0.5rem',
                          backgroundColor: '#0f172a',
                          border: '1px solid #475569',
                          borderRadius: '6px',
                          color: 'white',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>
                  </div>

                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>Description / Scope of Work</label>
                    <textarea
                      rows={2}
                      value={customItemDescription}
                      onChange={e => setCustomItemDescription(e.target.value)}
                      placeholder="Optional description"
                      style={{
                        width: '100%',
                        marginTop: '4px',
                        padding: '0.5rem',
                        backgroundColor: '#0f172a',
                        border: '1px solid #475569',
                        borderRadius: '6px',
                        color: 'white',
                        fontSize: '0.85rem'
                      }}
                    />
                  </div>

                  {/* Custom handling choice: One-time vs Permanent Save */}
                  <div style={{
                    backgroundColor: '#0f172a',
                    padding: '1rem',
                    borderRadius: '6px',
                    border: '1px solid #334155',
                    marginBottom: '1rem'
                  }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc', display: 'block', marginBottom: '0.5rem' }}>
                      Catalogue Storage Choice:
                    </span>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginBottom: '0.5rem' }}>
                      <input
                        type="radio"
                        name="customSaveChoice"
                        checked={!customSavePermanently}
                        onChange={() => setCustomSavePermanently(false)}
                      />
                      <span style={{ fontSize: '0.82rem', color: '#cbd5e1' }}>
                        <strong>Add as a one-time item</strong> for this quotation only (does not alter catalogue)
                      </span>
                    </label>

                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: canManageCatalogue ? 'pointer' : 'not-allowed' }}>
                      <input
                        type="radio"
                        name="customSaveChoice"
                        checked={customSavePermanently}
                        disabled={!canManageCatalogue}
                        onChange={() => setCustomSavePermanently(true)}
                      />
                      <span style={{ fontSize: '0.82rem', color: canManageCatalogue ? '#f59e0b' : '#64748b' }}>
                        <strong>Save permanently to catalogue</strong> for future use {canManageCatalogue ? '' : '(Requires CRM Admin permission)'}
                      </span>
                    </label>

                    {customSavePermanently && (
                      <div style={{ marginTop: '0.75rem', paddingLeft: '1.5rem' }}>
                        <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8' }}>
                          Select Category for Permanent Addition:
                        </label>
                        <select
                          value={customCategoryId}
                          onChange={e => setCustomCategoryId(e.target.value)}
                          style={{
                            display: 'block',
                            marginTop: '4px',
                            padding: '0.4rem 0.6rem',
                            backgroundColor: '#1e293b',
                            border: '1px solid #475569',
                            borderRadius: '4px',
                            color: 'white',
                            fontSize: '0.82rem'
                          }}
                        >
                          {categories.map(c => (
                            <option key={c.id} value={c.id}>{c.categoryName}</option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                    <button
                      type="button"
                      onClick={() => setShowItemPicker(false)}
                      style={{
                        padding: '0.5rem 1rem',
                        backgroundColor: '#334155',
                        border: 'none',
                        color: '#cbd5e1',
                        borderRadius: '6px',
                        fontSize: '0.85rem',
                        cursor: 'pointer'
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleAddCustomItem}
                      style={{
                        padding: '0.5rem 1.25rem',
                        backgroundColor: '#f59e0b',
                        border: 'none',
                        color: '#0f172a',
                        fontWeight: 700,
                        borderRadius: '6px',
                        fontSize: '0.85rem',
                        cursor: 'pointer'
                      }}
                    >
                      Add Custom Item to Quote
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
