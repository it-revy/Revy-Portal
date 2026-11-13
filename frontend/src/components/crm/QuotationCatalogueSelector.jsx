import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Layers,
  Package as PackageIcon,
  Plus,
  Trash2,
  AlertCircle,
  Check,
  Search,
  Info,
  DollarSign,
  Tag,
  FlaskConical,
  TestTube,
  Sparkles,
  ShoppingBag,
  Filter
} from 'lucide-react';
import catalogueService from '../../services/catalogueService';
import { Button, Card, StatusBadge, SearchInput } from '../ui';
import { useAuth } from '../../context/AuthContext';

export default function QuotationCatalogueSelector({
  quotationId,
  currency = 'INR',
  onTotalChanged,
  readOnly = false,
  onSelectService,
  onSelectPackage,
  onSelectItem
}) {
  const { user, activeRole } = useAuth?.() || {};
  const userRoles = [
    ...(user?.roles || []),
    activeRole
  ].filter(Boolean);
  const canManageCatalogue = userRoles.some(r =>
    ['CRM_ADMIN', 'Admin', 'SuperAdmin', 'IT_ADMIN', 'DIRECTOR', 'Director'].includes(r)
  );

  const [lineItems, setLineItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Modal State
  const [selectorModalOpen, setSelectorModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('services'); // 'services', 'packages', 'addons', 'products', 'custom'
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState('ALL');

  // Catalogue Options
  const [availableCategories, setAvailableCategories] = useState([]);
  const [availableServices, setAvailableServices] = useState([]);
  const [availablePackages, setAvailablePackages] = useState([]);
  const [taxConfigurations, setTaxConfigurations] = useState([]);
  const [selectedTaxConfigId, setSelectedTaxConfigId] = useState('');
  const [loadingCatalogue, setLoadingCatalogue] = useState(false);

  // Service / Add-on / Product Selection Form State
  const [selectedService, setSelectedService] = useState(null);
  const [serviceQty, setServiceQty] = useState(1);
  const [serviceCustomPrice, setServiceCustomPrice] = useState('');
  const [serviceSampleType, setServiceSampleType] = useState('');
  const [serviceTestingMethod, setServiceTestingMethod] = useState('');

  // Package Selection Form State
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [packageQty, setPackageQty] = useState(1);
  const [packageCustomPrice, setPackageCustomPrice] = useState('');

  // Custom Item Form State
  const [customItemType, setCustomItemType] = useState('CUSTOM_SERVICE'); // 'CUSTOM_SERVICE' or 'CUSTOM_PRODUCT'
  const [customItemName, setCustomItemName] = useState('');
  const [customItemDescription, setCustomItemDescription] = useState('');
  const [customItemUnit, setCustomItemUnit] = useState('Test');
  const [customItemPrice, setCustomItemPrice] = useState('');
  const [customItemQty, setCustomItemQty] = useState(1);
  const [customSavePermanently, setCustomSavePermanently] = useState(false);
  const [customCategoryId, setCustomCategoryId] = useState('');

  const [savingItem, setSavingItem] = useState(false);

  // Defensive normalization of search term
  const safeSearchTerm = useMemo(() => {
    const raw =
      typeof searchTerm === 'string'
        ? searchTerm
        : searchTerm?.target?.value ??
          searchTerm?.value ??
          searchTerm?.label ??
          searchTerm?.name ??
          '';
    return String(raw).toLowerCase().trim();
  }, [searchTerm]);

  // Safe search change handler
  const handleSearchChange = (val) => {
    if (typeof val === 'string') {
      setSearchTerm(val);
    } else if (val && typeof val.target?.value === 'string') {
      setSearchTerm(val.target.value);
    } else if (val && typeof val.value === 'string') {
      setSearchTerm(val.value);
    } else {
      setSearchTerm('');
    }
  };

  const handleClearSearch = () => {
    setSearchTerm('');
  };

  // Fetch Quotation Line Items (if quotationId provided)
  const fetchLineItems = useCallback(async () => {
    if (!quotationId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await catalogueService.getQuotationItems(quotationId);
      const items = catalogueService.normalizeArray(res, 'items');
      setLineItems(items);
      if (onTotalChanged) {
        const total = items.reduce((sum, item) => sum + Number(item?.totalPrice || 0), 0);
        onTotalChanged(total, items);
      }
    } catch (err) {
      console.error('Failed to load quotation items:', err);
      setError(err.response?.data?.message || err.response?.data?.detail || 'Failed to load quotation items.');
    } finally {
      setLoading(false);
    }
  }, [quotationId, onTotalChanged]);

  useEffect(() => {
    fetchLineItems();
  }, [fetchLineItems]);

  // Load Catalogue data when modal opens
  const handleOpenSelector = async () => {
    setSelectorModalOpen(true);
    setLoadingCatalogue(true);
    setError(null);
    try {
      const [srvRes, pkgRes, taxRes, catRes] = await Promise.all([
        catalogueService.getServices({ isActive: true, limit: 100 }),
        catalogueService.getPackages({ isActive: true }),
        catalogueService.getTaxConfigurations({ includeInactive: false }),
        catalogueService.getCategories({ includeInactive: false })
      ]);

      const srvs = catalogueService.normalizeArray(srvRes, 'services');
      const pkgs = catalogueService.normalizeArray(pkgRes, 'packages');
      const taxes = catalogueService.normalizeArray(taxRes, 'taxConfigurations');
      const cats = catalogueService.normalizeArray(catRes, 'categories');

      setAvailableServices(srvs);
      setAvailablePackages(pkgs);
      setTaxConfigurations(taxes);
      setAvailableCategories(cats);

      if (cats.length > 0 && !customCategoryId) {
        setCustomCategoryId(cats[0].id);
      }

      if (taxes.length > 0 && !selectedTaxConfigId) {
        const def = taxes.find(t => t.isDefault) || taxes[0];
        if (def) setSelectedTaxConfigId(def.id);
      }
    } catch (err) {
      console.error('Failed to load catalogue options:', err);
      setError('Unable to load catalogue items. Please verify network or try again.');
    } finally {
      setLoadingCatalogue(false);
    }
  };

  // Select service
  const handleSelectService = (srv) => {
    if (!srv) return;
    setSelectedService(srv);
    setSelectedPackage(null);
    setServiceQty(srv.minimumBillingQuantity || 1);
    setServiceCustomPrice(srv.standardPrice || '');
    setServiceSampleType(srv.sampleTypes?.[0]?.sampleTypeName || '');
    setServiceTestingMethod(srv.testingMethods?.[0]?.testingMethodName || '');

    if (onSelectService) {
      onSelectService(srv);
    }
    if (onSelectItem) {
      onSelectItem({
        type: 'SERVICE',
        serviceId: srv.id,
        name: srv.name,
        code: srv.code || srv.serviceCode,
        price: srv.standardPrice,
        unit: srv.billingUnitName || 'TEST',
        raw: srv
      });
    }
  };

  // Select package
  const handleSelectPackage = (pkg) => {
    if (!pkg) return;
    setSelectedPackage(pkg);
    setSelectedService(null);
    setPackageQty(1);
    const activeVer = pkg.activeVersion;
    setPackageCustomPrice(activeVer?.packagePrice || '');

    if (onSelectPackage) {
      onSelectPackage(pkg);
    }
    if (onSelectItem) {
      onSelectItem({
        type: 'PACKAGE',
        packageId: pkg.id,
        name: pkg.name,
        code: pkg.code || pkg.packageCode,
        price: activeVer?.packagePrice || 0,
        unit: 'PACKAGE',
        raw: pkg
      });
    }
  };

  // Add Service Item to quotation
  const handleAddServiceItem = async () => {
    if (!selectedService) return;
    if (!quotationId) {
      // If no quotationId, quick-select mode
      if (onSelectService) onSelectService(selectedService);
      setSelectorModalOpen(false);
      return;
    }
    setSavingItem(true);
    try {
      await catalogueService.addQuotationItem(quotationId, {
        itemType: activeTab === 'addons' ? 'ADDON' : activeTab === 'products' ? 'PRODUCT' : 'SERVICE',
        serviceId: selectedService.id,
        quantity: Math.max(1, Number(serviceQty) || 1),
        unitPrice: serviceCustomPrice !== '' ? Number(serviceCustomPrice) : undefined,
        sampleType: serviceSampleType || undefined,
        testingMethod: serviceTestingMethod || undefined,
        taxConfigurationId: selectedTaxConfigId || undefined
      });
      setSelectedService(null);
      setSelectorModalOpen(false);
      fetchLineItems();
    } catch (err) {
      alert(err.response?.data?.message || err.response?.data?.detail || 'Failed to add item to quotation.');
    } finally {
      setSavingItem(false);
    }
  };

  // Add Package Item to quotation
  const handleAddPackageItem = async () => {
    if (!selectedPackage) return;
    if (!quotationId) {
      // If no quotationId, quick-select mode
      if (onSelectPackage) onSelectPackage(selectedPackage);
      setSelectorModalOpen(false);
      return;
    }
    setSavingItem(true);
    try {
      await catalogueService.addQuotationItem(quotationId, {
        itemType: 'PACKAGE',
        packageId: selectedPackage.id,
        quantity: Math.max(1, Number(packageQty) || 1),
        unitPrice: packageCustomPrice !== '' ? Number(packageCustomPrice) : undefined,
        taxConfigurationId: selectedTaxConfigId || undefined
      });
      setSelectedPackage(null);
      setSelectorModalOpen(false);
      fetchLineItems();
    } catch (err) {
      alert(err.response?.data?.message || err.response?.data?.detail || 'Failed to add package item.');
    } finally {
      setSavingItem(false);
    }
  };

  // Add Custom Item to quotation
  const handleAddCustomItem = async () => {
    if (!customItemName.trim()) {
      alert('Please enter an item name for the custom product/service.');
      return;
    }
    const price = Number(customItemPrice);
    if (isNaN(price) || price < 0) {
      alert('Please enter a valid unit price.');
      return;
    }

    if (!quotationId) {
      if (onSelectItem) {
        onSelectItem({
          type: customItemType,
          name: customItemName.trim(),
          price: price,
          quantity: Math.max(1, Number(customItemQty) || 1),
          unit: customItemUnit.trim() || 'Unit'
        });
      }
      setSelectorModalOpen(false);
      return;
    }

    setSavingItem(true);
    try {
      await catalogueService.addQuotationItem(quotationId, {
        itemType: customItemType,
        itemName: customItemName.trim(),
        description: customItemDescription.trim() || undefined,
        billingUnit: customItemUnit.trim() || 'Unit',
        unitPrice: price,
        quantity: Math.max(1, Number(customItemQty) || 1),
        savePermanently: Boolean(customSavePermanently && canManageCatalogue),
        categoryId: customCategoryId || undefined,
        taxConfigurationId: selectedTaxConfigId || undefined
      });
      setCustomItemName('');
      setCustomItemDescription('');
      setCustomItemPrice('');
      setSelectorModalOpen(false);
      fetchLineItems();
    } catch (err) {
      alert(err.response?.data?.message || err.response?.data?.detail || 'Failed to add custom item.');
    } finally {
      setSavingItem(false);
    }
  };

  // Delete Item
  const handleDeleteItem = async (itemId) => {
    if (!window.confirm('Remove this line item from the quotation?')) return;
    try {
      await catalogueService.deleteQuotationItem(quotationId, itemId);
      fetchLineItems();
    } catch (err) {
      alert(err.response?.data?.message || err.response?.data?.detail || 'Failed to remove item.');
    }
  };

  // Filtered Services and Packages with defensive checks
  const filteredServices = useMemo(() => {
    if (!Array.isArray(availableServices)) return [];
    return availableServices.filter(s => {
      if (selectedCategoryFilter !== 'ALL' && s?.categoryId !== selectedCategoryFilter) {
        return false;
      }
      if (!safeSearchTerm) return true;
      const name = String(s?.name ?? '').toLowerCase();
      const code = String(s?.code ?? s?.serviceCode ?? '').toLowerCase();
      const catName = String(s?.categoryName ?? '').toLowerCase();
      return name.includes(safeSearchTerm) || code.includes(safeSearchTerm) || catName.includes(safeSearchTerm);
    });
  }, [availableServices, selectedCategoryFilter, safeSearchTerm]);

  const filteredPackages = useMemo(() => {
    if (!Array.isArray(availablePackages)) return [];
    return availablePackages.filter(p => {
      if (!safeSearchTerm) return true;
      const name = String(p?.name ?? p?.packageName ?? '').toLowerCase();
      const code = String(p?.code ?? p?.packageCode ?? '').toLowerCase();
      return name.includes(safeSearchTerm) || code.includes(safeSearchTerm);
    });
  }, [availablePackages, safeSearchTerm]);

  const filteredAddons = useMemo(() => {
    if (!Array.isArray(availableServices)) return [];
    return availableServices.filter(s => {
      const isAddon = s?.isAddonEligible === true || String(s?.billingUnitCode ?? '').toUpperCase() === 'ADDON';
      if (!isAddon) return false;
      if (selectedCategoryFilter !== 'ALL' && s?.categoryId !== selectedCategoryFilter) {
        return false;
      }
      if (!safeSearchTerm) return true;
      const name = String(s?.name ?? '').toLowerCase();
      const code = String(s?.code ?? s?.serviceCode ?? '').toLowerCase();
      const catName = String(s?.categoryName ?? '').toLowerCase();
      return name.includes(safeSearchTerm) || code.includes(safeSearchTerm) || catName.includes(safeSearchTerm);
    });
  }, [availableServices, selectedCategoryFilter, safeSearchTerm]);

  const filteredProducts = useMemo(() => {
    if (!Array.isArray(availableServices)) return [];
    return availableServices.filter(s => {
      const catName = String(s?.categoryName ?? '').toLowerCase();
      const isProd =
        s?.itemType === 'PRODUCT' ||
        catName.includes('product') ||
        catName.includes('consumable') ||
        String(s?.billingUnitCode ?? '').toUpperCase() === 'PRODUCT';
      if (!isProd) return false;
      if (!safeSearchTerm) return true;
      const name = String(s?.name ?? '').toLowerCase();
      const code = String(s?.code ?? s?.serviceCode ?? '').toLowerCase();
      return name.includes(safeSearchTerm) || code.includes(safeSearchTerm) || catName.includes(safeSearchTerm);
    });
  }, [availableServices, safeSearchTerm]);

  // Calculate totals safely
  const subtotal = useMemo(() => {
    if (!Array.isArray(lineItems)) return 0;
    return lineItems.reduce((acc, it) => {
      const lineTot = Number(it?.lineTotal);
      if (!isNaN(lineTot) && lineTot > 0) return acc + lineTot;
      const up = Number(it?.unitPrice || 0);
      const qty = Number(it?.quantity || 1);
      return acc + (up * qty);
    }, 0);
  }, [lineItems]);

  const totalTax = useMemo(() => {
    if (!Array.isArray(lineItems)) return 0;
    return lineItems.reduce((acc, it) => acc + Number(it?.taxAmount || 0), 0);
  }, [lineItems]);

  const grandTotal = useMemo(() => {
    if (!Array.isArray(lineItems)) return 0;
    return lineItems.reduce((acc, it) => acc + Number(it?.totalPrice || 0), 0);
  }, [lineItems]);

  return (
    <div style={{ marginTop: '1.25rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Layers size={18} />
            <span>Commercial Catalogue Items ({lineItems.length})</span>
          </h4>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Snapshot-based line items preserving exact laboratory service, package, and custom pricing.
          </span>
        </div>

        {!readOnly && (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            icon={Plus}
            onClick={handleOpenSelector}
          >
            Add Catalogue Item
          </Button>
        )}
      </div>

      {lineItems.length === 0 ? (
        <div style={{ padding: '2rem', textAlign: 'center', background: '#f8fafc', border: '1px dashed var(--border-color)', borderRadius: '6px' }}>
          <Tag size={28} style={{ margin: '0 auto 0.5rem', opacity: 0.4 }} />
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>No Catalogue Items Added</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            Click &quot;Add Catalogue Item&quot; to pick individual laboratory services, commercial packages, add-ons, or custom items.
          </div>
        </div>
      ) : (
        <div style={{ background: '#ffffff', border: '1px solid var(--border-color)', borderRadius: '6px', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
            <thead>
              <tr style={{ background: '#f8fafc', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                <th style={{ padding: '8px 12px' }}>Type</th>
                <th style={{ padding: '8px 12px' }}>Code & Name</th>
                <th style={{ padding: '8px 12px' }}>Details / Method</th>
                <th style={{ padding: '8px 12px', textAlign: 'right' }}>Qty</th>
                <th style={{ padding: '8px 12px', textAlign: 'right' }}>Unit Price</th>
                <th style={{ padding: '8px 12px', textAlign: 'right' }}>Line Total</th>
                <th style={{ padding: '8px 12px', textAlign: 'right' }}>Tax</th>
                <th style={{ padding: '8px 12px', textAlign: 'right' }}>Total ({currency})</th>
                {!readOnly && <th style={{ padding: '8px 12px', textAlign: 'center' }}>Action</th>}
              </tr>
            </thead>
            <tbody>
              {lineItems.map(item => (
                <tr key={item.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      background: item.itemType === 'PACKAGE' ? '#ede9fe' : item.itemType === 'ADDON' ? '#fef3c7' : item.itemType?.startsWith('CUSTOM') ? '#f3f4f6' : '#e0f2fe',
                      color: item.itemType === 'PACKAGE' ? '#6d28d9' : item.itemType === 'ADDON' ? '#b45309' : item.itemType?.startsWith('CUSTOM') ? '#374151' : '#0369a1'
                    }}>
                      {item.itemType === 'PACKAGE' ? <PackageIcon size={12} /> : item.itemType === 'ADDON' ? <Sparkles size={12} /> : item.itemType === 'PRODUCT' ? <ShoppingBag size={12} /> : <FlaskConical size={12} />}
                      {item.itemType}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{item.itemName}</div>
                    <div style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: 'var(--text-muted)' }}>{item.itemCode || '—'}</div>
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                    {item.testingMethod && <div><strong>Method:</strong> {item.testingMethod}</div>}
                    {item.sampleType && <div><strong>Sample:</strong> {item.sampleType}</div>}
                    {item.snapshotData?.versionNumber && (
                      <div style={{ color: '#6d28d9', fontWeight: 600 }}>v{item.snapshotData.versionNumber} bundle</div>
                    )}
                    {item.description && <div style={{ color: 'var(--text-muted)' }}>{item.description}</div>}
                    {!item.testingMethod && !item.sampleType && !item.snapshotData?.versionNumber && !item.description && '—'}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 600 }}>
                    {item.quantity}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                    ₹{Number(item.unitPrice || 0).toLocaleString()}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 600 }}>
                    ₹{Number(item.lineTotal || (Number(item.unitPrice || 0) * Number(item.quantity || 1))).toLocaleString()}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    ₹{Number(item.taxAmount || 0).toLocaleString()} ({item.taxRatePercentage || 0}%)
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700, color: 'var(--accent-primary)' }}>
                    ₹{Number(item.totalPrice || 0).toLocaleString()}
                  </td>
                  {!readOnly && (
                    <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                      <button
                        type="button"
                        onClick={() => handleDeleteItem(item.id)}
                        style={{ background: 'none', border: 'none', color: '#dc2626', cursor: 'pointer', padding: '4px' }}
                        title="Remove Item"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ background: '#f8fafc', borderTop: '2px solid var(--border-color)' }}>
                <td colSpan={5} style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 600 }}>
                  Subtotal:
                </td>
                <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 700 }}>
                  ₹{subtotal.toLocaleString()}
                </td>
                <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 600 }}>
                  ₹{totalTax.toLocaleString()}
                </td>
                <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 800, fontSize: '0.95rem', color: 'var(--accent-primary)' }}>
                  ₹{grandTotal.toLocaleString()}
                </td>
                {!readOnly && <td></td>}
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Catalogue Selection Modal */}
      {selectorModalOpen && (
        <div className="crm-modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(15, 23, 42, 0.65)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1100
        }}>
          <div className="crm-modal" style={{
            background: '#ffffff',
            borderRadius: 'var(--radius-lg, 8px)',
            width: '92%',
            maxWidth: '1000px',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.15)',
            border: '1px solid var(--border-color)',
            overflow: 'hidden'
          }}>
            {/* Header */}
            <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Tag size={20} color="var(--accent-primary)" />
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>Select Catalogue Item</h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectorModalOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.25rem', color: 'var(--text-muted)' }}
              >
                ✕
              </button>
            </div>

            {/* Modal Navigation Tabs & Search */}
            <div style={{ padding: '0.85rem 1.5rem', background: '#f8fafc', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => { setActiveTab('services'); setSelectedPackage(null); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.45rem 0.85rem',
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: activeTab === 'services' ? 'var(--accent-primary)' : 'var(--border-color)',
                    background: activeTab === 'services' ? '#e0f2fe' : '#ffffff',
                    color: activeTab === 'services' ? '#0369a1' : 'var(--text-secondary)',
                    fontWeight: activeTab === 'services' ? 700 : 500,
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  <FlaskConical size={15} />
                  <span>Services ({availableServices.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => { setActiveTab('packages'); setSelectedService(null); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.45rem 0.85rem',
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: activeTab === 'packages' ? '#6d28d9' : 'var(--border-color)',
                    background: activeTab === 'packages' ? '#ede9fe' : '#ffffff',
                    color: activeTab === 'packages' ? '#6d28d9' : 'var(--text-secondary)',
                    fontWeight: activeTab === 'packages' ? 700 : 500,
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  <PackageIcon size={15} />
                  <span>Packages ({availablePackages.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => { setActiveTab('addons'); setSelectedPackage(null); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.45rem 0.85rem',
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: activeTab === 'addons' ? '#b45309' : 'var(--border-color)',
                    background: activeTab === 'addons' ? '#fef3c7' : '#ffffff',
                    color: activeTab === 'addons' ? '#b45309' : 'var(--text-secondary)',
                    fontWeight: activeTab === 'addons' ? 700 : 500,
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  <Sparkles size={15} />
                  <span>Add-ons ({filteredAddons.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => { setActiveTab('products'); setSelectedPackage(null); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.45rem 0.85rem',
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: activeTab === 'products' ? '#0284c7' : 'var(--border-color)',
                    background: activeTab === 'products' ? '#f0f9ff' : '#ffffff',
                    color: activeTab === 'products' ? '#0284c7' : 'var(--text-secondary)',
                    fontWeight: activeTab === 'products' ? 700 : 500,
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  <ShoppingBag size={15} />
                  <span>Products ({filteredProducts.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => { setActiveTab('custom'); setSelectedService(null); setSelectedPackage(null); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.45rem 0.85rem',
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: activeTab === 'custom' ? '#d97706' : 'var(--border-color)',
                    background: activeTab === 'custom' ? '#fffbeb' : '#ffffff',
                    color: activeTab === 'custom' ? '#d97706' : 'var(--text-secondary)',
                    fontWeight: activeTab === 'custom' ? 700 : 500,
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  <Plus size={15} />
                  <span>Custom Item</span>
                </button>
              </div>

              {activeTab !== 'custom' && (
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  {['services', 'addons'].includes(activeTab) && availableCategories.length > 0 && (
                    <select
                      className="crm-select"
                      style={{ padding: '0.4rem 0.6rem', fontSize: '0.82rem', maxWidth: '200px' }}
                      value={selectedCategoryFilter}
                      onChange={e => setSelectedCategoryFilter(e.target.value)}
                    >
                      <option value="ALL">All Categories</option>
                      {availableCategories.map(cat => (
                        <option key={cat.id} value={cat.id}>{cat.code} - {cat.name}</option>
                      ))}
                    </select>
                  )}
                  <div style={{ width: '220px' }}>
                    <SearchInput
                      value={typeof searchTerm === 'string' ? searchTerm : ''}
                      onChange={handleSearchChange}
                      onClear={handleClearSearch}
                      placeholder={`Search ${activeTab}...`}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Tax Selection Bar */}
            <div style={{ padding: '0.65rem 1.5rem', background: '#ffffff', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.85rem', flexWrap: 'wrap' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Applicable Tax Config:</span>
              <select
                className="crm-select"
                style={{ width: 'auto', padding: '4px 8px', fontSize: '0.85rem' }}
                value={selectedTaxConfigId}
                onChange={e => setSelectedTaxConfigId(e.target.value)}
              >
                {taxConfigurations.map(t => (
                  <option key={t.id} value={t.id}>
                    {t.code} — {t.name} ({t.rates?.map(r => `${r.rateName || r.componentName}: ${r.percentage || r.ratePercentage}%`).join(', ') || '0%'})
                  </option>
                ))}
              </select>
            </div>

            {/* Modal Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1.5rem', display: 'grid', gridTemplateColumns: (selectedService || selectedPackage || activeTab === 'custom') ? '1.2fr 1fr' : '1fr', gap: '1.5rem' }}>
              {/* Left Column: Items List */}
              <div style={{ maxHeight: '55vh', overflowY: 'auto' }}>
                {loadingCatalogue ? (
                  <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    Loading catalogue data...
                  </div>
                ) : activeTab === 'services' ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {filteredServices.length === 0 ? (
                      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No services found matching search query.
                      </div>
                    ) : (
                      filteredServices.map(srv => {
                        const isSelected = selectedService?.id === srv.id;
                        return (
                          <div
                            key={srv.id}
                            onClick={() => handleSelectService(srv)}
                            style={{
                              padding: '0.75rem 1rem',
                              borderRadius: '6px',
                              border: isSelected ? '2px solid var(--accent-primary)' : '1px solid var(--border-color)',
                              background: isSelected ? '#f0f9ff' : '#ffffff',
                              cursor: 'pointer',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.75rem', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>
                                  {srv.code || srv.serviceCode}
                                </span>
                                <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9rem' }}>{srv.name}</span>
                              </div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                {srv.categoryName} • Unit: {srv.billingUnitName || 'TEST'}
                              </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ fontWeight: 700, color: 'var(--accent-primary)', fontSize: '0.95rem' }}>
                                ₹{Number(srv.standardPrice || 0).toLocaleString()}
                              </div>
                              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Min Qty: {srv.minimumBillingQuantity || 1}</div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                ) : activeTab === 'packages' ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {filteredPackages.length === 0 ? (
                      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No packages found matching search query.
                      </div>
                    ) : (
                      filteredPackages.map(pkg => {
                        const isSelected = selectedPackage?.id === pkg.id;
                        const activeVer = pkg.activeVersion;
                        return (
                          <div
                            key={pkg.id}
                            onClick={() => handleSelectPackage(pkg)}
                            style={{
                              padding: '0.85rem 1rem',
                              borderRadius: '6px',
                              border: isSelected ? '2px solid #6d28d9' : '1px solid var(--border-color)',
                              background: isSelected ? '#faf5ff' : '#ffffff',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                              <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                  <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.75rem', background: '#ede9fe', color: '#6d28d9', padding: '2px 6px', borderRadius: '4px' }}>
                                    {pkg.code || pkg.packageCode}
                                  </span>
                                  <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.95rem' }}>{pkg.name}</span>
                                  <span style={{ fontSize: '0.7rem', background: '#f3e8ff', color: '#7e22ce', padding: '1px 6px', borderRadius: '4px', fontWeight: 600 }}>
                                    v{activeVer?.versionNumber || 1}
                                  </span>
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                                  {activeVer?.components?.length || 0} component laboratory services
                                </div>
                              </div>
                              <div style={{ textAlign: 'right' }}>
                                <div style={{ fontWeight: 800, color: '#6d28d9', fontSize: '1.05rem' }}>
                                  ₹{Number(activeVer?.packagePrice || 0).toLocaleString()}
                                </div>
                                {activeVer?.referenceComponentSum > 0 && (
                                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textDecoration: 'line-through' }}>
                                    Ref: ₹{Number(activeVer.referenceComponentSum).toLocaleString()}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                ) : activeTab === 'addons' ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {filteredAddons.length === 0 ? (
                      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No add-on services found matching search query.
                      </div>
                    ) : (
                      filteredAddons.map(srv => {
                        const isSelected = selectedService?.id === srv.id;
                        return (
                          <div
                            key={srv.id}
                            onClick={() => handleSelectService(srv)}
                            style={{
                              padding: '0.75rem 1rem',
                              borderRadius: '6px',
                              border: isSelected ? '2px solid #b45309' : '1px solid var(--border-color)',
                              background: isSelected ? '#fef3c7' : '#ffffff',
                              cursor: 'pointer',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.75rem', background: '#fef3c7', color: '#b45309', padding: '2px 6px', borderRadius: '4px' }}>
                                  {srv.code || srv.serviceCode}
                                </span>
                                <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9rem' }}>{srv.name}</span>
                                <span style={{ fontSize: '0.7rem', background: '#ffedd5', color: '#c2410c', padding: '1px 5px', borderRadius: '3px', fontWeight: 600 }}>Add-on</span>
                              </div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                {srv.categoryName} • Unit: {srv.billingUnitName || 'ADDON'}
                              </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ fontWeight: 700, color: '#b45309', fontSize: '0.95rem' }}>
                                ₹{Number(srv.standardPrice || 0).toLocaleString()}
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                ) : activeTab === 'products' ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {filteredProducts.length === 0 ? (
                      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                        No products or consumables found matching search query.
                      </div>
                    ) : (
                      filteredProducts.map(srv => {
                        const isSelected = selectedService?.id === srv.id;
                        return (
                          <div
                            key={srv.id}
                            onClick={() => handleSelectService(srv)}
                            style={{
                              padding: '0.75rem 1rem',
                              borderRadius: '6px',
                              border: isSelected ? '2px solid #0284c7' : '1px solid var(--border-color)',
                              background: isSelected ? '#f0f9ff' : '#ffffff',
                              cursor: 'pointer',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.75rem', background: '#e0f2fe', color: '#0369a1', padding: '2px 6px', borderRadius: '4px' }}>
                                  {srv.code || srv.serviceCode}
                                </span>
                                <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9rem' }}>{srv.name}</span>
                              </div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                {srv.categoryName} • Unit: {srv.billingUnitName || 'Unit'}
                              </div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                              <div style={{ fontWeight: 700, color: '#0284c7', fontSize: '0.95rem' }}>
                                ₹{Number(srv.standardPrice || 0).toLocaleString()}
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                ) : (
                  /* Custom Item Info */
                  <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                    <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.95rem', fontWeight: 700 }}>Custom Non-Catalogue Item</h4>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0 0 1rem' }}>
                      Add a one-time product, custom service, or pilot study not present in the standard catalogue.
                      Users with CRM Admin rights can also save it permanently to the catalogue.
                    </p>
                    <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                        <input
                          type="radio"
                          name="customType"
                          value="CUSTOM_SERVICE"
                          checked={customItemType === 'CUSTOM_SERVICE'}
                          onChange={() => setCustomItemType('CUSTOM_SERVICE')}
                        />
                        <span>Custom Service / Study</span>
                      </label>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                        <input
                          type="radio"
                          name="customType"
                          value="CUSTOM_PRODUCT"
                          checked={customItemType === 'CUSTOM_PRODUCT'}
                          onChange={() => setCustomItemType('CUSTOM_PRODUCT')}
                        />
                        <span>Custom Product / Consumable</span>
                      </label>
                    </div>
                  </div>
                )}
              </div>

              {/* Right Column: Configure & Add */}
              {(selectedService || selectedPackage || activeTab === 'custom') && (
                <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: '6px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                      {activeTab === 'custom' ? 'Custom Item Details' : 'Selected for Quotation'}
                    </div>
                    <h4 style={{ margin: '0.2rem 0 0', fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {activeTab === 'custom'
                        ? (customItemName || 'New Custom Line Item')
                        : selectedService
                        ? selectedService.name
                        : selectedPackage.name}
                    </h4>
                  </div>

                  {activeTab === 'custom' ? (
                    <>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Item Name *</label>
                        <input
                          type="text"
                          className="crm-input"
                          placeholder="e.g. On-site Anaerobic Digestion Pilot"
                          value={customItemName}
                          onChange={e => setCustomItemName(e.target.value)}
                        />
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Description / Scope</label>
                        <textarea
                          className="crm-input"
                          rows={2}
                          placeholder="Scope of work or technical specifications"
                          value={customItemDescription}
                          onChange={e => setCustomItemDescription(e.target.value)}
                        />
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                        <div>
                          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Quantity</label>
                          <input
                            type="number"
                            className="crm-input"
                            min="1"
                            value={customItemQty}
                            onChange={e => setCustomItemQty(Math.max(1, parseInt(e.target.value) || 1))}
                          />
                        </div>
                        <div>
                          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Unit Price (INR) *</label>
                          <input
                            type="number"
                            className="crm-input"
                            placeholder="0.00"
                            value={customItemPrice}
                            onChange={e => setCustomItemPrice(e.target.value)}
                          />
                        </div>
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Billing Unit</label>
                        <input
                          type="text"
                          className="crm-input"
                          placeholder="e.g. Test, Sample, Month, Lot"
                          value={customItemUnit}
                          onChange={e => setCustomItemUnit(e.target.value)}
                        />
                      </div>

                      {canManageCatalogue && (
                        <div style={{ background: '#ffffff', padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', cursor: 'pointer', fontWeight: 600 }}>
                            <input
                              type="checkbox"
                              checked={customSavePermanently}
                              onChange={e => setCustomSavePermanently(e.target.checked)}
                            />
                            <span>Save permanently to Catalogue for future quotations</span>
                          </label>
                          {customSavePermanently && (
                            <div style={{ marginTop: '0.5rem' }}>
                              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '2px' }}>Catalogue Category:</label>
                              <select
                                className="crm-select"
                                value={customCategoryId}
                                onChange={e => setCustomCategoryId(e.target.value)}
                              >
                                {availableCategories.map(cat => (
                                  <option key={cat.id} value={cat.id}>{cat.code} - {cat.name}</option>
                                ))}
                              </select>
                            </div>
                          )}
                        </div>
                      )}

                      <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem', fontWeight: 700 }}>
                          <span>Estimated Line Total:</span>
                          <span style={{ color: 'var(--accent-primary)' }}>
                            ₹{(Number(customItemPrice || 0) * Number(customItemQty || 1)).toLocaleString()}
                          </span>
                        </div>
                        <Button
                          variant="primary"
                          style={{ width: '100%' }}
                          disabled={savingItem || !customItemName.trim() || !customItemPrice}
                          onClick={handleAddCustomItem}
                        >
                          {savingItem ? 'Adding...' : 'Add Custom Item to Quotation'}
                        </Button>
                      </div>
                    </>
                  ) : selectedService ? (
                    <>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Quantity</label>
                        <input
                          type="number"
                          className="crm-input"
                          min={selectedService.minimumBillingQuantity || 1}
                          value={serviceQty}
                          onChange={e => setServiceQty(Math.max(1, parseInt(e.target.value) || 1))}
                        />
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Unit Price (INR)</label>
                        <input
                          type="number"
                          className="crm-input"
                          value={serviceCustomPrice}
                          onChange={e => setServiceCustomPrice(e.target.value)}
                        />
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Standard catalogue price: ₹{selectedService.standardPrice}</span>
                      </div>

                      {selectedService.sampleTypes?.length > 0 && (
                        <div>
                          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Sample Type</label>
                          <select
                            className="crm-select"
                            value={serviceSampleType}
                            onChange={e => setServiceSampleType(e.target.value)}
                          >
                            <option value="">Select Sample Type...</option>
                            {selectedService.sampleTypes.map(st => (
                              <option key={st.id} value={st.sampleTypeName}>{st.sampleTypeName}</option>
                            ))}
                          </select>
                        </div>
                      )}

                      {selectedService.testingMethods?.length > 0 && (
                        <div>
                          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Testing Method</label>
                          <select
                            className="crm-select"
                            value={serviceTestingMethod}
                            onChange={e => setServiceTestingMethod(e.target.value)}
                          >
                            <option value="">Select Testing Method...</option>
                            {selectedService.testingMethods.map(tm => (
                              <option key={tm.id} value={tm.testingMethodName}>{tm.testingMethodName}</option>
                            ))}
                          </select>
                        </div>
                      )}

                      <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem', fontWeight: 700 }}>
                          <span>Estimated Line Total:</span>
                          <span style={{ color: 'var(--accent-primary)' }}>
                            ₹{(Number(serviceCustomPrice || 0) * Number(serviceQty || 1)).toLocaleString()}
                          </span>
                        </div>
                        <Button
                          variant="primary"
                          style={{ width: '100%' }}
                          disabled={savingItem}
                          onClick={handleAddServiceItem}
                        >
                          {savingItem ? 'Adding...' : quotationId ? 'Add to Quotation' : 'Select Item'}
                        </Button>
                      </div>
                    </>
                  ) : selectedPackage ? (
                    <>
                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Package Quantity</label>
                        <input
                          type="number"
                          className="crm-input"
                          min="1"
                          value={packageQty}
                          onChange={e => setPackageQty(Math.max(1, parseInt(e.target.value) || 1))}
                        />
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Package Price (INR)</label>
                        <input
                          type="number"
                          className="crm-input"
                          value={packageCustomPrice}
                          onChange={e => setPackageCustomPrice(e.target.value)}
                        />
                        {selectedPackage.activeVersion?.referenceComponentSum > 0 && (
                          <span style={{ fontSize: '0.7rem', color: '#6d28d9', fontWeight: 500 }}>
                            Components sum: ₹{Number(selectedPackage.activeVersion.referenceComponentSum).toLocaleString()}
                          </span>
                        )}
                      </div>

                      {/* Package Components Breakdown */}
                      <div style={{ fontSize: '0.75rem', background: '#ffffff', padding: '0.5rem', borderRadius: '4px', border: '1px solid #e2e8f0', maxHeight: '150px', overflowY: 'auto' }}>
                        <strong style={{ display: 'block', marginBottom: '4px', color: 'var(--text-secondary)' }}>Included Components:</strong>
                        {selectedPackage.activeVersion?.components?.map((c, i) => (
                          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                            <span>{c.serviceName} ({c.quantity * packageQty}x)</span>
                            <span style={{ color: 'var(--text-muted)' }}>₹{Number(c.referenceUnitPrice || 0).toLocaleString()}</span>
                          </div>
                        ))}
                      </div>

                      <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem', fontWeight: 700 }}>
                          <span>Estimated Package Total:</span>
                          <span style={{ color: '#6d28d9' }}>
                            ₹{(Number(packageCustomPrice || 0) * Number(packageQty || 1)).toLocaleString()}
                          </span>
                        </div>
                        <Button
                          variant="primary"
                          style={{ width: '100%', background: '#6d28d9', borderColor: '#6d28d9' }}
                          disabled={savingItem}
                          onClick={handleAddPackageItem}
                        >
                          {savingItem ? 'Adding...' : quotationId ? 'Add Package to Quotation' : 'Select Package'}
                        </Button>
                      </div>
                    </>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
