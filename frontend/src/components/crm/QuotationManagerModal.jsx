import React, { useState, useEffect, useMemo } from 'react';
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
  Send,
  History,
  FileSpreadsheet,
  ChevronDown,
  Building,
  User,
  MapPin,
  Calendar,
  Clock
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
  onApproveAndCreateInvoice,
  onGenerateInvoice
}) {
  const { user, isGlobalAdmin, hasRole, hasPermission } = useAuth?.() || {};
  const globalAdminActive = typeof isGlobalAdmin === 'function' ? isGlobalAdmin() : Boolean(isGlobalAdmin);
  const userRoles = [
    ...(user?.roles || []),
    user?.role,
    user?.user_metadata?.role
  ].filter(Boolean).map(r => String(r).toUpperCase());

  // CRM Admin and CRM Manager have full write / generate permissions; others have read-only view
  const canEdit = globalAdminActive ||
    userRoles.some(r => ['CRM_ADMIN', 'CRM_MANAGER', 'ADMIN', 'SUPERADMIN', 'DIRECTOR', 'IT_ADMIN'].includes(r));

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Active Quotation State
  const [quotationId, setQuotationId] = useState(null);
  const [quotationNumber, setQuotationNumber] = useState(null);
  const [revisionNumber, setRevisionNumber] = useState(1);
  const [quotationStatus, setQuotationStatus] = useState('Draft');
  const [title, setTitle] = useState('');
  const [validUntilDate, setValidUntilDate] = useState('');
  const [termsAndConditions, setTermsAndConditions] = useState('');
  const [notes, setNotes] = useState('');
  const [currency, setCurrency] = useState('INR');
  const [taxType, setTaxType] = useState('INTRA_STATE');
  const [selectedTaxConfigId, setSelectedTaxConfigId] = useState('');
  const [emailText, setEmailText] = useState('');
  const [revisions, setRevisions] = useState([]);
  const [showRevisionHistory, setShowRevisionHistory] = useState(false);

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
      if (catRes.data?.categories || catRes.data?.success) {
        const catList = catRes.data?.categories || catRes.data?.data || [];
        setCategories(catList);
        if (catList.length > 0) {
          setCustomCategoryId(catList[0].id);
        }
      }

      // Services
      if (srvRes.data?.services || srvRes.data?.success) {
        setServices(srvRes.data?.services || srvRes.data?.data || []);
      }

      // Packages
      if (pkgRes.data?.packages || pkgRes.data?.success) {
        setPackages(pkgRes.data?.packages || pkgRes.data?.data || []);
      }

  // Taxes
      let taxes = [];
      if (taxRes.data?.taxConfigurations || taxRes.data?.success) {
        taxes = taxRes.data?.taxConfigurations || taxRes.data?.data || [];
        setTaxConfigurations(taxes);
      }

      // Revisions summary
      if (quoteRes.data?.revisions) {
        setRevisions(quoteRes.data.revisions);
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
        setRevisionNumber(q.revisionNumber || 1);
        setQuotationStatus(q.status || 'Active');
        setTitle(q.title || `Quotation for ${opportunity.name}`);
        setValidUntilDate(q.validUntilDate || '');
        setTermsAndConditions(q.termsAndConditions || defaultTermsText);
        setNotes(q.notes || '');
        setCurrency(q.currency || 'INR');
        const qTaxType = q.taxType || 'INTRA_STATE';
        setTaxType(qTaxType);
        if (q.taxConfigurationId) {
          setSelectedTaxConfigId(q.taxConfigurationId);
        } else {
          const matching = taxes.find(t => (t.taxType || t.tax_type) === qTaxType);
          if (matching) setSelectedTaxConfigId(matching.id);
        }
        setEmailText(q.emailText || '');

        const mapped = (q.items || []).map(it => {
          const qty = Number(it.quantity || 1);
          const price = Number(it.negotiatedUnitPrice !== null && it.negotiatedUnitPrice !== undefined ? it.negotiatedUnitPrice : it.unitPrice || 0);
          const disc = Number(it.discountAmount || 0);
          return {
            id: it.id,
            itemType: it.itemType || 'SERVICE',
            serviceId: it.serviceId,
            packageId: it.packageId,
            packageVersionId: it.packageVersionId,
            parentItemId: it.parentItemId || null,
            itemName: it.itemName || it.name,
            itemCode: it.itemCode,
            description: it.description || '',
            billingUnit: it.billingUnit || 'Test',
            standardPrice: Number(it.unitPrice || price),
            unitPrice: price,
            quantity: qty,
            discountAmount: disc,
            savePermanently: false,
            categoryId: null
          };
        });
        setItems(mapped);
      } else {
        // Draft defaults
        setQuotationId(null);
        setQuotationNumber(null);
        setRevisionNumber(1);
        setQuotationStatus('Draft');
        setTitle(`Quotation for ${opportunity.name}`);
        setTaxType('INTRA_STATE');
        const matching = taxes.find(t => (t.taxType || t.tax_type) === 'INTRA_STATE') || taxes.find(t => t.isDefault) || taxes[0];
        if (matching) setSelectedTaxConfigId(matching.id);
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

  // Authoritative Financial Calculations (Paise Rounding)
  const grossSubtotal = useMemo(() => {
    return items.reduce((sum, item) => {
      const gross = (Number(item.quantity || 1) * Number(item.unitPrice || 0));
      return sum + Math.max(0, gross);
    }, 0);
  }, [items]);

  const totalDiscount = useMemo(() => {
    return items.reduce((sum, item) => sum + Number(item.discountAmount || 0), 0);
  }, [items]);

  const taxableSubtotal = useMemo(() => {
    return Math.max(0, grossSubtotal - totalDiscount);
  }, [grossSubtotal, totalDiscount]);

  const { cgstAmount, sgstAmount, igstAmount, totalTax, grandTotal } = useMemo(() => {
    let cgst = 0;
    let sgst = 0;
    let igst = 0;

    if (taxType === 'INTRA_STATE') {
      cgst = Math.round(taxableSubtotal * (cgstRate / 100) * 100) / 100;
      sgst = Math.round(taxableSubtotal * (sgstRate / 100) * 100) / 100;
    } else if (taxType === 'INTER_STATE') {
      igst = Math.round(taxableSubtotal * (igstRate / 100) * 100) / 100;
    }

    const tax = cgst + sgst + igst;
    return {
      cgstAmount: cgst,
      sgstAmount: sgst,
      igstAmount: igst,
      totalTax: tax,
      grandTotal: taxableSubtotal + tax
    };
  }, [taxableSubtotal, taxType, cgstRate, sgstRate, igstRate]);

  // Add standard service from catalogue
  const handleAddService = (srv) => {
    const newItem = {
      itemType: 'SERVICE',
      serviceId: srv.id,
      packageId: null,
      packageVersionId: null,
      parentItemId: null,
      itemName: srv.name || srv.serviceName,
      itemCode: srv.code || srv.serviceCode,
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
      parentItemId: null,
      itemName: pkg.name || pkg.packageName,
      itemCode: pkg.code || pkg.packageCode,
      description: pkg.description || `Package includes ${activeVer?.components?.length || activeVer?.items?.length || 0} services`,
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
      parentItemId: null,
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
    const item = { ...updated[index] };

    if (field === 'discountAmount') {
      const gross = Number(item.quantity || 1) * Number(item.unitPrice || 0);
      const disc = Math.max(0, Math.min(Number(value) || 0, gross));
      item.discountAmount = disc;
    } else if (field === 'quantity') {
      item.quantity = Math.max(1, Number(value) || 1);
    } else if (field === 'unitPrice') {
      item.unitPrice = Math.max(0, Number(value) || 0);
    } else {
      item[field] = value;
    }

    updated[index] = item;
    setItems(updated);
  };

  const handleRemoveItem = (index) => {
    setItems(items.filter((_, i) => i !== index));
  };

  // Save Quotation to Backend
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
        taxConfigurationId: activeTaxConfig?.id || selectedTaxConfigId || undefined,
        validUntilDate: validUntilDate || undefined,
        termsAndConditions: termsAndConditions,
        notes: notes,
        items: items.map(it => ({
          itemType: it.itemType,
          serviceId: it.serviceId || undefined,
          packageId: it.packageId || undefined,
          packageVersionId: it.packageVersionId || undefined,
          parentItemId: it.parentItemId || undefined,
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
        setRevisionNumber(savedQuote.revisionNumber || 1);
        setQuotationStatus(savedQuote.status || 'Active');
        setEmailText(savedQuote.emailText || '');

        if (res.data.revisions) {
          setRevisions(res.data.revisions);
        }

        if (!silent) {
          const revMsg = savedQuote.revisionNumber > 1 ? ` (Revision R${savedQuote.revisionNumber})` : '';
          showToast(`Quotation ${savedQuote.quotationNumber}${revMsg} saved successfully.`);
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

  // Direct PI Generation (Authorized CRM Admin / Manager)
  const handleProceedToInvoice = async () => {
    // 1. Save changes first
    const savedQuote = await handleSaveQuotation(true);
    if (!savedQuote) return;

    // 2. Open Invoice Preparation
    const launchInvoice = onGenerateInvoice || onApproveAndCreateInvoice;
    if (launchInvoice) {
      launchInvoice(savedQuote);
    }
  };

  // Copy Quotation Text (Email-Ready)
  const handleCopyQuotation = async () => {
    let lines = [];
    lines.push('===========================================================');
    lines.push('REVY ENVIRONMENTAL SOLUTIONS PVT. LTD. - COMMERCIAL QUOTATION');
    lines.push('===========================================================');
    lines.push(`Opportunity: ${opportunity.name} (${opportunity.opportunityId || ''})`);
    lines.push(`Customer: ${opportunity.accountName || opportunity.account?.name || 'Valued Client'}`);
    lines.push(`Quotation: ${quotationNumber || 'DRAFT'} (Rev: R${revisionNumber})`);
    lines.push(`Date: ${new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}`);
    lines.push('-----------------------------------------------------------');
    lines.push('ITEMS & PRICING:');
    items.forEach((it, idx) => {
      const gross = (Number(it.quantity || 1) * Number(it.unitPrice || 0));
      const taxable = Math.max(0, gross - Number(it.discountAmount || 0));
      lines.push(`${idx + 1}. ${it.itemName}`);
      if (it.description) lines.push(`   Description: ${it.description}`);
      lines.push(`   Qty: ${it.quantity} ${it.billingUnit} @ ₹${Number(it.unitPrice).toLocaleString('en-IN')}`);
      if (Number(it.discountAmount) > 0) {
        lines.push(`   Discount: -₹${Number(it.discountAmount).toLocaleString('en-IN')}`);
      }
      lines.push(`   Taxable Amount: ₹${taxable.toLocaleString('en-IN')}`);
    });
    lines.push('-----------------------------------------------------------');
    lines.push(`Gross Subtotal: ₹${grossSubtotal.toLocaleString('en-IN')}`);
    if (totalDiscount > 0) {
      lines.push(`Total Discount: -₹${totalDiscount.toLocaleString('en-IN')}`);
      lines.push(`Taxable Amount: ₹${taxableSubtotal.toLocaleString('en-IN')}`);
    }
    if (taxType === 'INTRA_STATE') {
      lines.push(`CGST (${cgstRate}%): ₹${cgstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
      lines.push(`SGST (${sgstRate}%): ₹${sgstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
    } else if (taxType === 'INTER_STATE') {
      lines.push(`IGST (${igstRate}%): ₹${igstAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
    } else {
      lines.push('Taxes: Exempt / Not Applicable (₹0.00)');
    }
    lines.push(`Total Tax: ₹${totalTax.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
    lines.push(`GRAND TOTAL: ₹${grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
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

    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      setCopied(true);
      showToast('Quotation text copied to clipboard! Ready to paste into email.');
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      alert('Unable to copy automatically. Please select and copy manually.');
    }
  };

  // Filtered Services in Picker
  const filteredServices = useMemo(() => {
    return services.filter(s => {
      const matchesCat = selectedCategoryFilter === 'all' || s.categoryId === selectedCategoryFilter;
      const sName = String(s.name || s.serviceName || '').toLowerCase();
      const sCode = String(s.code || s.serviceCode || '').toLowerCase();
      const search = pickerSearch.toLowerCase().trim();
      const matchesSearch = !search || sName.includes(search) || sCode.includes(search);
      return matchesCat && matchesSearch;
    });
  }, [services, selectedCategoryFilter, pickerSearch]);

  if (!isOpen || !opportunity) return null;

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
      zIndex: 9999,
      padding: '1.25rem'
    }}>
      <div style={{
        backgroundColor: '#ffffff',
        borderRadius: '8px',
        width: '100%',
        maxWidth: '1200px',
        maxHeight: '94vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
        border: '1px solid #e2e8f0',
        color: '#0f172a',
        overflow: 'hidden'
      }}>
        {/* SECTION A: HEADER */}
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
              width: '40px',
              height: '40px',
              borderRadius: '8px',
              backgroundColor: '#0284c7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              flexShrink: 0
            }}>
              <FileSpreadsheet size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>
                  Quotation Management
                </h2>
                {quotationNumber ? (
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    backgroundColor: '#e0f2fe',
                    color: '#0369a1',
                    fontFamily: 'monospace'
                  }}>
                    {quotationNumber}
                  </span>
                ) : (
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    backgroundColor: '#f1f5f9',
                    color: '#64748b'
                  }}>
                    Draft
                  </span>
                )}
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  backgroundColor: '#ede9fe',
                  color: '#6d28d9'
                }}>
                  Revision R{revisionNumber}
                </span>
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  backgroundColor: quotationStatus === 'Active' ? '#dcfce7' : quotationStatus === 'Superseded' ? '#f1f5f9' : '#fef3c7',
                  color: quotationStatus === 'Active' ? '#15803d' : quotationStatus === 'Superseded' ? '#64748b' : '#b45309'
                }}>
                  {quotationStatus}
                </span>
                {!canEdit && (
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    backgroundColor: '#fee2e2',
                    color: '#b91c1c'
                  }}>
                    Read-Only
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.825rem', color: '#64748b', margin: '3px 0 0' }}>
                Opportunity: <strong>{opportunity.name}</strong> • Customer: <strong>{opportunity.accountName || account.name || 'Valued Client'}</strong>
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {toastMessage && (
              <span style={{
                fontSize: '0.8rem',
                color: '#15803d',
                backgroundColor: '#dcfce7',
                border: '1px solid #bbf7d0',
                padding: '4px 10px',
                borderRadius: '6px',
                fontWeight: 600
              }}>
                {toastMessage}
              </span>
            )}

            {revisions.length > 1 && (
              <button
                type="button"
                onClick={() => setShowRevisionHistory(!showRevisionHistory)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '5px 10px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  background: '#ffffff',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: '#475569',
                  cursor: 'pointer'
                }}
              >
                <History size={14} />
                <span>Revisions ({revisions.length})</span>
                <ChevronDown size={14} />
              </button>
            )}

            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: '#64748b',
                cursor: 'pointer',
                padding: '0.4rem',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
              title="Close"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* REVISION HISTORY DRAWER */}
        {showRevisionHistory && (
          <div style={{
            backgroundColor: '#f8fafc',
            borderBottom: '1px solid #e2e8f0',
            padding: '0.75rem 1.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            overflowX: 'auto'
          }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#475569', whiteSpace: 'nowrap' }}>
              Historical Revisions:
            </span>
            {revisions.map(rev => (
              <div
                key={rev.id}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: '1px solid',
                  borderColor: rev.isActive ? '#0284c7' : '#cbd5e1',
                  background: rev.isActive ? '#e0f2fe' : '#ffffff',
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  whiteSpace: 'nowrap'
                }}
              >
                <span style={{ fontWeight: 700, color: rev.isActive ? '#0369a1' : '#334155' }}>
                  {rev.version || `R${rev.revisionNumber}`}
                </span>
                <span style={{ color: '#64748b' }}>₹{Number(rev.amount || 0).toLocaleString()}</span>
                <span style={{
                  fontSize: '0.7rem',
                  padding: '1px 5px',
                  borderRadius: '3px',
                  background: rev.isActive ? '#bae6fd' : '#f1f5f9',
                  color: rev.isActive ? '#0369a1' : '#64748b',
                  fontWeight: 600
                }}>
                  {rev.status}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* MODAL MAIN CONTENT BODY */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem 1.75rem' }}>
          {error && (
            <div style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '6px',
              padding: '0.75rem 1rem',
              marginBottom: '1.25rem',
              color: '#b91c1c',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          {stateMismatchNotice && (
            <div style={{
              backgroundColor: '#fffbeb',
              border: '1px solid #fde68a',
              borderRadius: '6px',
              padding: '0.65rem 0.9rem',
              marginBottom: '1.25rem',
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

          {/* SECTION B: CUSTOMER & OPPORTUNITY INFORMATION */}
          <div style={{
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '1rem 1.25rem',
            marginBottom: '1.5rem',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '1rem'
          }}>
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Building size={12} /> Account / Customer
              </span>
              <div style={{ fontWeight: 700, fontSize: '0.9rem', color: '#0f172a', marginTop: '2px' }}>
                {opportunity.accountName || account.name || 'Valued Client'}
              </div>
              {account.industry && (
                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{account.industry}</div>
              )}
            </div>

            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <User size={12} /> Contact Person
              </span>
              <div style={{ fontWeight: 600, fontSize: '0.875rem', color: '#0f172a', marginTop: '2px' }}>
                {opportunity.contactPerson || opportunity.primaryContact?.name || account.primaryContactName || 'N/A'}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                {opportunity.contactEmail || opportunity.primaryContact?.email || '—'}
              </div>
            </div>

            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <MapPin size={12} /> Billing Location / GSTIN
              </span>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#0f172a', marginTop: '2px' }}>
                {account.billingCity ? `${account.billingCity}, ${account.billingState || 'India'}` : 'Location on file'}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', fontFamily: 'monospace' }}>
                {account.gstin ? `GSTIN: ${account.gstin}` : 'GSTIN: Unregistered / Default'}
              </div>
            </div>

            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Calendar size={12} /> Opportunity Context
              </span>
              <div style={{ fontWeight: 600, fontSize: '0.85rem', color: '#0f172a', marginTop: '2px' }}>
                Stage: {opportunity.stage || 'Commercial Stage'}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                Estimated Value: ₹{Number(opportunity.value || 0).toLocaleString()}
              </div>
            </div>
          </div>

          {/* QUOTATION HEADER FIELDS */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '1rem',
            marginBottom: '1.5rem'
          }}>
            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Quotation Title *
              </label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                disabled={!canEdit}
                placeholder="e.g. Wastewater Bioculture & Analytical Proposal"
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  backgroundColor: canEdit ? '#ffffff' : '#f8fafc',
                  color: '#0f172a'
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Tax Regime
              </label>
              <select
                value={taxType}
                onChange={e => handleTaxTypeChange(e.target.value)}
                disabled={!canEdit}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  backgroundColor: canEdit ? '#ffffff' : '#f8fafc',
                  color: '#0f172a'
                }}
              >
                <option value="INTRA_STATE">Intra-State (CGST {cgstRate}% + SGST {sgstRate}%)</option>
                <option value="INTER_STATE">Inter-State (IGST {igstRate}%)</option>
                <option value="EXEMPT">Exempt / Zero Tax</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                Validity Date
              </label>
              <input
                type="date"
                value={validUntilDate ? validUntilDate.split('T')[0] : ''}
                onChange={e => setValidUntilDate(e.target.value)}
                disabled={!canEdit}
                style={{
                  width: '100%',
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  backgroundColor: canEdit ? '#ffffff' : '#f8fafc',
                  color: '#0f172a'
                }}
              />
            </div>
          </div>

          {/* SECTION D: QUOTATION ITEMS TABLE */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '0.75rem'
            }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
                  Commercial Line Items ({items.length})
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Laboratory services, test packages, and custom items
                </span>
              </div>

              {canEdit && (
                <button
                  type="button"
                  onClick={() => setShowItemPicker(true)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '5px',
                    padding: '6px 12px',
                    borderRadius: '6px',
                    backgroundColor: '#0284c7',
                    color: '#ffffff',
                    border: 'none',
                    fontSize: '0.825rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  <Plus size={15} />
                  <span>Add Line Item</span>
                </button>
              )}
            </div>

            {items.length === 0 ? (
              <div style={{
                padding: '2.5rem',
                textAlign: 'center',
                backgroundColor: '#f8fafc',
                border: '1px dashed #cbd5e1',
                borderRadius: '8px'
              }}>
                <FlaskConical size={32} color="#94a3b8" style={{ margin: '0 auto 0.5rem', display: 'block' }} />
                <div style={{ fontSize: '0.9rem', fontWeight: 600, color: '#334155' }}>
                  No Items Added Yet
                </div>
                <p style={{ fontSize: '0.8rem', color: '#64748b', margin: '4px 0 1rem' }}>
                  Select from all 61 active laboratory services, pre-configured packages, or add custom services.
                </p>
                {canEdit && (
                  <button
                    type="button"
                    onClick={() => setShowItemPicker(true)}
                    style={{
                      padding: '6px 14px',
                      borderRadius: '6px',
                      backgroundColor: '#0284c7',
                      color: '#ffffff',
                      border: 'none',
                      fontSize: '0.825rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    Open Service Catalogue
                  </button>
                )}
              </div>
            ) : (
              <div style={{ overflowX: 'auto', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#f8fafc', borderBottom: '1px solid #e2e8f0', textAlign: 'left' }}>
                      <th style={{ padding: '8px 12px', width: '38px', textAlign: 'center' }}>#</th>
                      <th style={{ padding: '8px 12px', minWidth: '180px' }}>Item Name</th>
                      <th style={{ padding: '8px 12px', width: '110px' }}>Type</th>
                      <th style={{ padding: '8px 12px', width: '90px', textAlign: 'right' }}>Qty</th>
                      <th style={{ padding: '8px 12px', width: '80px' }}>Unit</th>
                      <th style={{ padding: '8px 12px', width: '110px', textAlign: 'right' }}>Unit Price (₹)</th>
                      <th style={{ padding: '8px 12px', width: '100px', textAlign: 'right' }}>Discount (₹)</th>
                      <th style={{ padding: '8px 12px', width: '120px', textAlign: 'right' }}>Taxable Amt (₹)</th>
                      {canEdit && <th style={{ padding: '8px 12px', width: '40px', textAlign: 'center' }}></th>}
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item, idx) => {
                      const qty = Number(item.quantity || 1);
                      const unitPrice = Number(item.unitPrice || 0);
                      const disc = Number(item.discountAmount || 0);
                      const gross = qty * unitPrice;
                      const taxable = Math.max(0, gross - disc);

                      return (
                        <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '8px 12px', textAlign: 'center', color: '#64748b' }}>
                            {idx + 1}
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <div style={{ fontWeight: 600, color: '#0f172a' }}>{item.itemName}</div>
                            {item.itemCode && (
                              <div style={{ fontSize: '0.72rem', color: '#64748b', fontFamily: 'monospace' }}>
                                {item.itemCode}
                              </div>
                            )}
                            {item.description && (
                              <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
                                {item.description}
                              </div>
                            )}
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <span style={{
                              padding: '2px 6px',
                              borderRadius: '4px',
                              fontSize: '0.7rem',
                              fontWeight: 700,
                              backgroundColor:
                                item.itemType === 'PACKAGE' ? '#ede9fe' :
                                item.itemType === 'ADDON' ? '#fef3c7' :
                                item.itemType?.startsWith('CUSTOM') ? '#fff7ed' : '#e0f2fe',
                              color:
                                item.itemType === 'PACKAGE' ? '#6d28d9' :
                                item.itemType === 'ADDON' ? '#b45309' :
                                item.itemType?.startsWith('CUSTOM') ? '#c2410c' : '#0369a1'
                            }}>
                              {item.itemType}
                            </span>
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                            {canEdit ? (
                              <input
                                type="number"
                                min="1"
                                value={item.quantity}
                                onChange={e => handleItemFieldChange(idx, 'quantity', e.target.value)}
                                style={{
                                  width: '65px',
                                  padding: '4px 6px',
                                  border: '1px solid #cbd5e1',
                                  borderRadius: '4px',
                                  textAlign: 'right',
                                  fontSize: '0.825rem'
                                }}
                              />
                            ) : (
                              item.quantity
                            )}
                          </td>
                          <td style={{ padding: '8px 12px', color: '#64748b' }}>
                            {item.billingUnit}
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                            {canEdit ? (
                              <input
                                type="number"
                                min="0"
                                value={item.unitPrice}
                                onChange={e => handleItemFieldChange(idx, 'unitPrice', e.target.value)}
                                style={{
                                  width: '90px',
                                  padding: '4px 6px',
                                  border: '1px solid #cbd5e1',
                                  borderRadius: '4px',
                                  textAlign: 'right',
                                  fontSize: '0.825rem'
                                }}
                              />
                            ) : (
                              `₹${unitPrice.toLocaleString()}`
                            )}
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                            {canEdit ? (
                              <input
                                type="number"
                                min="0"
                                max={gross}
                                value={item.discountAmount}
                                onChange={e => handleItemFieldChange(idx, 'discountAmount', e.target.value)}
                                style={{
                                  width: '80px',
                                  padding: '4px 6px',
                                  border: '1px solid #cbd5e1',
                                  borderRadius: '4px',
                                  textAlign: 'right',
                                  fontSize: '0.825rem',
                                  color: disc > 0 ? '#b91c1c' : '#0f172a'
                                }}
                              />
                            ) : (
                              disc > 0 ? `-₹${disc.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '₹0.00'
                            )}
                          </td>
                          <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700, color: '#0f172a' }}>
                            ₹{taxable.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          {canEdit && (
                            <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                              <button
                                type="button"
                                onClick={() => handleRemoveItem(idx)}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  color: '#dc2626',
                                  cursor: 'pointer',
                                  padding: '4px',
                                  borderRadius: '4px'
                                }}
                                title="Remove item"
                              >
                                <Trash2 size={14} />
                              </button>
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* SECTION E: TERMS, NOTES & FINANCIAL SUMMARY */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 340px',
            gap: '1.5rem',
            alignItems: 'start'
          }}>
            <div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Terms &amp; Conditions
                </label>
                <textarea
                  rows={4}
                  value={termsAndConditions}
                  onChange={e => setTermsAndConditions(e.target.value)}
                  disabled={!canEdit}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.75rem',
                    border: '1px solid #cbd5e1',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    backgroundColor: canEdit ? '#ffffff' : '#f8fafc',
                    color: '#0f172a',
                    lineHeight: 1.45
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', fontWeight: 600, color: '#475569', display: 'block', marginBottom: '4px' }}>
                  Commercial Notes / Remarks
                </label>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  disabled={!canEdit}
                  style={{
                    width: '100%',
                    padding: '0.5rem 0.75rem',
                    border: '1px solid #cbd5e1',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    backgroundColor: canEdit ? '#ffffff' : '#f8fafc',
                    color: '#0f172a'
                  }}
                />
              </div>
            </div>

            {/* FINANCIAL SUMMARY CARD */}
            <div style={{
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '1.25rem'
            }}>
              <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.9rem', fontWeight: 700, color: '#0f172a' }}>
                Financial Summary
              </h4>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.825rem' }}>
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

                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#475569' }}>
                  <span>Total Tax:</span>
                  <span style={{ fontWeight: 600 }}>₹{totalTax.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>

                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  borderTop: '2px solid #0f172a',
                  paddingTop: '0.5rem',
                  marginTop: '0.5rem',
                  fontSize: '1.05rem',
                  fontWeight: 800,
                  color: '#0284c7'
                }}>
                  <span>Grand Total:</span>
                  <span>₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                </div>
              </div>

              {canEdit && (
                <div style={{ marginTop: '1.25rem' }}>
                  <button
                    type="button"
                    onClick={handleProceedToInvoice}
                    disabled={saving || items.length === 0}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.5rem',
                      backgroundColor: '#059669',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '0.75rem',
                      fontSize: '0.875rem',
                      fontWeight: 700,
                      cursor: saving || items.length === 0 ? 'not-allowed' : 'pointer',
                      opacity: saving || items.length === 0 ? 0.6 : 1,
                      boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
                    }}
                  >
                    <Send size={16} />
                    <span>Generate Proforma Invoice</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* SECTION F: MODAL FOOTER ACTIONS */}
        <div style={{
          padding: '1rem 1.75rem',
          borderTop: '1px solid #e2e8f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#f8fafc'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={handleCopyQuotation}
              disabled={items.length === 0}
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
                cursor: items.length === 0 ? 'not-allowed' : 'pointer'
              }}
              title="Copy formatted quotation text for email"
            >
              {copied ? <Check size={15} color="#15803d" /> : <Copy size={15} />}
              <span>{copied ? 'Copied!' : 'Copy Email Text'}</span>
            </button>
          </div>

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
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>

            {canEdit && (
              <button
                type="button"
                onClick={() => handleSaveQuotation(false)}
                disabled={saving || items.length === 0}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  backgroundColor: '#0284c7',
                  color: '#ffffff',
                  border: 'none',
                  padding: '0.5rem 1.25rem',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: saving || items.length === 0 ? 'not-allowed' : 'pointer',
                  opacity: saving || items.length === 0 ? 0.7 : 1
                }}
              >
                <Save size={16} />
                <span>{saving ? 'Saving...' : 'Save Quotation'}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* CATALOGUE ITEM PICKER DRAWER / SUB-MODAL */}
      {showItemPicker && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.7)',
          zIndex: 10000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1.5rem'
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            width: '100%',
            maxWidth: '900px',
            maxHeight: '88vh',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
          }}>
            {/* Picker Header */}
            <div style={{
              padding: '1rem 1.5rem',
              backgroundColor: '#f8fafc',
              borderBottom: '1px solid #e2e8f0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>
                  Select Catalogue Item
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Choose from active laboratory services, test packages, or custom items
                </span>
              </div>
              <button
                onClick={() => setShowItemPicker(false)}
                style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Picker Navigation Tabs */}
            <div style={{
              display: 'flex',
              backgroundColor: '#ffffff',
              borderBottom: '1px solid #e2e8f0',
              padding: '0 1rem'
            }}>
              <button
                type="button"
                onClick={() => setPickerTab('services')}
                style={{
                  padding: '0.75rem 1rem',
                  border: 'none',
                  background: 'none',
                  color: pickerTab === 'services' ? '#0284c7' : '#64748b',
                  borderBottom: pickerTab === 'services' ? '2px solid #0284c7' : 'none',
                  fontWeight: pickerTab === 'services' ? 700 : 500,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem'
                }}
              >
                <FlaskConical size={16} />
                <span>Laboratory Services ({services.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setPickerTab('packages')}
                style={{
                  padding: '0.75rem 1rem',
                  border: 'none',
                  background: 'none',
                  color: pickerTab === 'packages' ? '#6d28d9' : '#64748b',
                  borderBottom: pickerTab === 'packages' ? '2px solid #6d28d9' : 'none',
                  fontWeight: pickerTab === 'packages' ? 700 : 500,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem'
                }}
              >
                <PackageIcon size={16} />
                <span>Packages &amp; Bundles ({packages.length})</span>
              </button>

              <button
                type="button"
                onClick={() => setPickerTab('custom')}
                style={{
                  padding: '0.75rem 1rem',
                  border: 'none',
                  background: 'none',
                  color: pickerTab === 'custom' ? '#d97706' : '#64748b',
                  borderBottom: pickerTab === 'custom' ? '2px solid #d97706' : 'none',
                  fontWeight: pickerTab === 'custom' ? 700 : 500,
                  fontSize: '0.85rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem'
                }}
              >
                <Sparkles size={16} />
                <span>Custom Item</span>
              </button>
            </div>

            {/* Picker Content Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1.5rem' }}>
              {pickerTab === 'services' && (
                <div>
                  {/* Category Filter & Search */}
                  <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                    <select
                      value={selectedCategoryFilter}
                      onChange={e => setSelectedCategoryFilter(e.target.value)}
                      style={{
                        padding: '0.45rem 0.65rem',
                        backgroundColor: '#ffffff',
                        border: '1px solid #cbd5e1',
                        borderRadius: '6px',
                        color: '#0f172a',
                        fontSize: '0.825rem',
                        minWidth: '220px'
                      }}
                    >
                      <option value="all">All Service Categories ({categories.length})</option>
                      {categories.map(c => (
                        <option key={c.id} value={c.id}>{c.categoryName || c.name}</option>
                      ))}
                    </select>

                    <input
                      type="text"
                      placeholder="Search services by name or code..."
                      value={pickerSearch}
                      onChange={e => setPickerSearch(e.target.value)}
                      style={{
                        flex: 1,
                        minWidth: '220px',
                        padding: '0.45rem 0.75rem',
                        backgroundColor: '#ffffff',
                        border: '1px solid #cbd5e1',
                        borderRadius: '6px',
                        color: '#0f172a',
                        fontSize: '0.825rem'
                      }}
                    />
                  </div>

                  {/* Services Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.75rem' }}>
                    {filteredServices.map(srv => (
                      <div
                        key={srv.id}
                        onClick={() => handleAddService(srv)}
                        style={{
                          backgroundColor: '#ffffff',
                          border: '1px solid #e2e8f0',
                          borderRadius: '6px',
                          padding: '0.85rem',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={e => {
                          e.currentTarget.style.borderColor = '#0284c7';
                          e.currentTarget.style.backgroundColor = '#f0f9ff';
                        }}
                        onMouseLeave={e => {
                          e.currentTarget.style.borderColor = '#e2e8f0';
                          e.currentTarget.style.backgroundColor = '#ffffff';
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                          <span style={{ fontSize: '0.7rem', color: '#0369a1', fontWeight: 700, fontFamily: 'monospace' }}>
                            {srv.code || srv.serviceCode}
                          </span>
                          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a' }}>
                            ₹{Number(srv.standardPrice || 0).toLocaleString()}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a', lineHeight: 1.3, marginBottom: '4px' }}>
                          {srv.name || srv.serviceName}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
                          {srv.categoryName || 'Laboratory Service'} • Unit: {srv.billingUnitName || 'Test'}
                        </div>
                      </div>
                    ))}
                    {filteredServices.length === 0 && (
                      <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                        No services found matching search filters.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {pickerTab === 'packages' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.75rem' }}>
                  {packages.map(pkg => {
                    const activeVer = pkg.activeVersion;
                    const price = Number(activeVer?.packagePrice || 0);
                    return (
                      <div
                        key={pkg.id}
                        onClick={() => handleAddPackage(pkg)}
                        style={{
                          backgroundColor: '#ffffff',
                          border: '1px solid #e2e8f0',
                          borderRadius: '6px',
                          padding: '0.85rem',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={e => {
                          e.currentTarget.style.borderColor = '#6d28d9';
                          e.currentTarget.style.backgroundColor = '#faf5ff';
                        }}
                        onMouseLeave={e => {
                          e.currentTarget.style.borderColor = '#e2e8f0';
                          e.currentTarget.style.backgroundColor = '#ffffff';
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <span style={{ fontSize: '0.7rem', color: '#6d28d9', fontWeight: 700, fontFamily: 'monospace' }}>
                            {pkg.code || pkg.packageCode}
                          </span>
                          <span style={{ fontSize: '0.9rem', fontWeight: 700, color: '#0f172a' }}>
                            ₹{price.toLocaleString()}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#0f172a', margin: '4px 0' }}>
                          {pkg.name || pkg.packageName}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                          {pkg.description || `Pre-configured test bundle (v${activeVer?.versionNumber || 1})`}
                        </div>
                      </div>
                    );
                  })}
                  {packages.length === 0 && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                      No active packages available.
                    </div>
                  )}
                </div>
              )}

              {pickerTab === 'custom' && (
                <div style={{ backgroundColor: '#f8fafc', padding: '1.25rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: '0 0 1rem', color: '#0f172a' }}>
                    Configure Custom Item
                  </h4>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Item Type</label>
                      <select
                        value={customItemType}
                        onChange={e => setCustomItemType(e.target.value)}
                        style={{
                          width: '100%',
                          marginTop: '4px',
                          padding: '0.45rem',
                          backgroundColor: '#ffffff',
                          border: '1px solid #cbd5e1',
                          borderRadius: '6px',
                          fontSize: '0.85rem'
                        }}
                      >
                        <option value="CUSTOM_SERVICE">Custom Service</option>
                        <option value="CUSTOM_PRODUCT">Custom Product</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Item Name *</label>
                      <input
                        type="text"
                        value={customItemName}
                        onChange={e => setCustomItemName(e.target.value)}
                        placeholder="e.g. Specialized Effluent Testing"
                        style={{
                          width: '100%',
                          marginTop: '4px',
                          padding: '0.45rem',
                          backgroundColor: '#ffffff',
                          border: '1px solid #cbd5e1',
                          borderRadius: '6px',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Unit Price (₹) *</label>
                      <input
                        type="number"
                        min="0"
                        value={customItemPrice}
                        onChange={e => setCustomItemPrice(e.target.value)}
                        placeholder="e.g. 5000"
                        style={{
                          width: '100%',
                          marginTop: '4px',
                          padding: '0.45rem',
                          backgroundColor: '#ffffff',
                          border: '1px solid #cbd5e1',
                          borderRadius: '6px',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Billing Unit</label>
                      <input
                        type="text"
                        value={customItemUnit}
                        onChange={e => setCustomItemUnit(e.target.value)}
                        placeholder="e.g. Test, Sample, Unit, Month"
                        style={{
                          width: '100%',
                          marginTop: '4px',
                          padding: '0.45rem',
                          backgroundColor: '#ffffff',
                          border: '1px solid #cbd5e1',
                          borderRadius: '6px',
                          fontSize: '0.85rem'
                        }}
                      />
                    </div>
                  </div>

                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569' }}>Description / Scope of Work</label>
                    <textarea
                      rows={2}
                      value={customItemDescription}
                      onChange={e => setCustomItemDescription(e.target.value)}
                      placeholder="Optional description"
                      style={{
                        width: '100%',
                        marginTop: '4px',
                        padding: '0.45rem',
                        backgroundColor: '#ffffff',
                        border: '1px solid #cbd5e1',
                        borderRadius: '6px',
                        fontSize: '0.85rem'
                      }}
                    />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                    <button
                      type="button"
                      onClick={() => setShowItemPicker(false)}
                      style={{
                        padding: '0.45rem 0.85rem',
                        backgroundColor: '#ffffff',
                        border: '1px solid #cbd5e1',
                        color: '#475569',
                        borderRadius: '6px',
                        fontSize: '0.825rem',
                        cursor: 'pointer'
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleAddCustomItem}
                      style={{
                        padding: '0.45rem 1rem',
                        backgroundColor: '#d97706',
                        border: 'none',
                        color: '#ffffff',
                        fontWeight: 600,
                        borderRadius: '6px',
                        fontSize: '0.825rem',
                        cursor: 'pointer'
                      }}
                    >
                      Add Custom Item
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
