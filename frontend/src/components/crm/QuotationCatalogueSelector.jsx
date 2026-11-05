import React, { useState, useEffect, useCallback } from 'react';
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
  TestTube
} from 'lucide-react';
import catalogueService from '../../services/catalogueService';
import { Button, Card, StatusBadge, SearchInput } from '../ui';

export default function QuotationCatalogueSelector({ quotationId, currency = 'INR', onTotalChanged, readOnly = false }) {
  const [lineItems, setLineItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal State
  const [selectorModalOpen, setSelectorModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('services'); // 'services' or 'packages'
  const [searchTerm, setSearchTerm] = useState('');

  // Catalogue Options
  const [availableServices, setAvailableServices] = useState([]);
  const [availablePackages, setAvailablePackages] = useState([]);
  const [taxConfigurations, setTaxConfigurations] = useState([]);
  const [selectedTaxConfigId, setSelectedTaxConfigId] = useState('');
  const [loadingCatalogue, setLoadingCatalogue] = useState(false);

  // Service Selection Form State
  const [selectedService, setSelectedService] = useState(null);
  const [serviceQty, setServiceQty] = useState(1);
  const [serviceCustomPrice, setServiceCustomPrice] = useState('');
  const [serviceSampleType, setServiceSampleType] = useState('');
  const [serviceTestingMethod, setServiceTestingMethod] = useState('');

  // Package Selection Form State
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [packageQty, setPackageQty] = useState(1);
  const [packageCustomPrice, setPackageCustomPrice] = useState('');

  const [savingItem, setSavingItem] = useState(false);

  // Fetch Quotation Line Items
  const fetchLineItems = useCallback(async () => {
    if (!quotationId) return;
    setLoading(true);
    try {
      const res = await catalogueService.getQuotationItems(quotationId);
      if (res.data?.success) {
        const items = res.data.items || [];
        setLineItems(items);
        if (onTotalChanged) {
          const total = items.reduce((sum, item) => sum + Number(item.totalPrice || 0), 0);
          onTotalChanged(total, items);
        }
      }
    } catch (err) {
      console.error('Failed to load quotation items:', err);
      setError(err.response?.data?.message || 'Failed to load quotation items.');
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
    try {
      const [srvRes, pkgRes, taxRes] = await Promise.all([
        catalogueService.getServices({ isActive: true, limit: 100 }),
        catalogueService.getPackages({ isActive: true }),
        catalogueService.getTaxConfigurations({ includeInactive: false })
      ]);

      if (srvRes.data?.success) setAvailableServices(srvRes.data.services || []);
      if (pkgRes.data?.success) setAvailablePackages(pkgRes.data.packages || []);
      if (taxRes.data?.success) {
        const taxes = taxRes.data.taxConfigurations || [];
        setTaxConfigurations(taxes);
        const def = taxes.find(t => t.isDefault) || taxes[0];
        if (def) setSelectedTaxConfigId(def.id);
      }
    } catch (err) {
      console.error('Failed to load catalogue options:', err);
    } finally {
      setLoadingCatalogue(false);
    }
  };

  // Select service
  const handleSelectService = (srv) => {
    setSelectedService(srv);
    setServiceQty(srv.minimumBillingQuantity || 1);
    setServiceCustomPrice(srv.standardPrice || '');
    setServiceSampleType(srv.sampleTypes?.[0]?.sampleTypeName || '');
    setServiceTestingMethod(srv.testingMethods?.[0]?.testingMethodName || '');
  };

  // Select package
  const handleSelectPackage = (pkg) => {
    setSelectedPackage(pkg);
    setPackageQty(1);
    const activeVer = pkg.activeVersion;
    setPackageCustomPrice(activeVer?.packagePrice || '');
  };

  // Add Service Item
  const handleAddServiceItem = async () => {
    if (!selectedService) return;
    setSavingItem(true);
    try {
      await catalogueService.addQuotationItem(quotationId, {
        itemType: 'SERVICE',
        serviceId: selectedService.id,
        quantity: Number(serviceQty) || 1,
        unitPrice: serviceCustomPrice !== '' ? Number(serviceCustomPrice) : undefined,
        sampleType: serviceSampleType || undefined,
        testingMethod: serviceTestingMethod || undefined,
        taxConfigurationId: selectedTaxConfigId || undefined
      });
      setSelectedService(null);
      setSelectorModalOpen(false);
      fetchLineItems();
    } catch (err) {
      alert(err.response?.data?.message || err.response?.data?.detail || 'Failed to add service item.');
    } finally {
      setSavingItem(false);
    }
  };

  // Add Package Item
  const handleAddPackageItem = async () => {
    if (!selectedPackage) return;
    setSavingItem(true);
    try {
      await catalogueService.addQuotationItem(quotationId, {
        itemType: 'PACKAGE',
        packageId: selectedPackage.id,
        quantity: Number(packageQty) || 1,
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

  // Filtered Services and Packages
  const filteredServices = availableServices.filter(s => {
    if (!searchTerm) return true;
    const q = searchTerm.toLowerCase();
    return s.name.toLowerCase().includes(q) || s.code.toLowerCase().includes(q) || s.categoryName?.toLowerCase().includes(q);
  });

  const filteredPackages = availablePackages.filter(p => {
    if (!searchTerm) return true;
    const q = searchTerm.toLowerCase();
    return p.name.toLowerCase().includes(q) || p.code.toLowerCase().includes(q);
  });

  // Calculate totals
  const subtotal = lineItems.reduce((acc, it) => acc + (Number(it.lineTotal) || (Number(it.unitPrice) * Number(it.quantity))), 0);
  const totalTax = lineItems.reduce((acc, it) => acc + Number(it.taxAmount || 0), 0);
  const grandTotal = lineItems.reduce((acc, it) => acc + Number(it.totalPrice || 0), 0);

  return (
    <div style={{ marginTop: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div>
          <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Layers size={18} />
            <span>Commercial Catalogue Items ({lineItems.length})</span>
          </h4>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Snapshot-based line items preserving exact laboratory service and package pricing.
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
            Click &quot;Add Catalogue Item&quot; to pick individual laboratory services or commercial packages.
          </div>
        </div>
      ) : (
        <div style={{ background: '#ffffff', border: '1px solid var(--border-color)', borderRadius: '6px', overflow: 'hidden' }}>
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
                      background: item.itemType === 'PACKAGE' ? '#ede9fe' : '#e0f2fe',
                      color: item.itemType === 'PACKAGE' ? '#6d28d9' : '#0369a1'
                    }}>
                      {item.itemType === 'PACKAGE' ? <PackageIcon size={12} /> : <FlaskConical size={12} />}
                      {item.itemType}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{item.itemName}</div>
                    <div style={{ fontSize: '0.7rem', fontFamily: 'monospace', color: 'var(--text-muted)' }}>{item.itemCode}</div>
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                    {item.testingMethod && <div><strong>Method:</strong> {item.testingMethod}</div>}
                    {item.sampleType && <div><strong>Sample:</strong> {item.sampleType}</div>}
                    {item.snapshotData?.versionNumber && (
                      <div style={{ color: '#6d28d9', fontWeight: 600 }}>v{item.snapshotData.versionNumber} bundle</div>
                    )}
                    {!item.testingMethod && !item.sampleType && !item.snapshotData?.versionNumber && '—'}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 600 }}>
                    {item.quantity}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                    ₹{Number(item.unitPrice).toLocaleString()}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right', fontWeight: 600 }}>
                    ₹{Number(item.lineTotal || (Number(item.unitPrice) * Number(item.quantity))).toLocaleString()}
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
            borderRadius: 'var(--radius-lg)',
            width: '90%',
            maxWidth: '900px',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.08)',
            border: '1px solid var(--color-border)',
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

            {/* Modal Tabs & Search */}
            <div style={{ padding: '1rem 1.5rem', background: '#f8fafc', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => { setActiveTab('services'); setSelectedPackage(null); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.5rem 1rem',
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: activeTab === 'services' ? 'var(--accent-primary)' : 'var(--border-color)',
                    background: activeTab === 'services' ? '#e0f2fe' : '#ffffff',
                    color: activeTab === 'services' ? '#0369a1' : 'var(--text-secondary)',
                    fontWeight: activeTab === 'services' ? 700 : 500,
                    cursor: 'pointer'
                  }}
                >
                  <FlaskConical size={16} />
                  <span>Individual Services ({availableServices.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => { setActiveTab('packages'); setSelectedService(null); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    padding: '0.5rem 1rem',
                    borderRadius: '6px',
                    border: '1px solid',
                    borderColor: activeTab === 'packages' ? '#6d28d9' : 'var(--border-color)',
                    background: activeTab === 'packages' ? '#ede9fe' : '#ffffff',
                    color: activeTab === 'packages' ? '#6d28d9' : 'var(--text-secondary)',
                    fontWeight: activeTab === 'packages' ? 700 : 500,
                    cursor: 'pointer'
                  }}
                >
                  <PackageIcon size={16} />
                  <span>Commercial Packages ({availablePackages.length})</span>
                </button>
              </div>

              <div style={{ width: '280px' }}>
                <SearchInput
                  value={searchTerm}
                  onChange={setSearchTerm}
                  placeholder={`Search ${activeTab}...`}
                />
              </div>
            </div>

            {/* Tax Selection Bar */}
            <div style={{ padding: '0.65rem 1.5rem', background: '#ffffff', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.85rem' }}>
              <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Applicable Tax Config:</span>
              <select
                className="crm-select"
                style={{ width: 'auto', padding: '4px 8px', fontSize: '0.85rem' }}
                value={selectedTaxConfigId}
                onChange={e => setSelectedTaxConfigId(e.target.value)}
              >
                {taxConfigurations.map(t => (
                  <option key={t.id} value={t.id}>
                    {t.code} — {t.name} ({t.rates?.map(r => `${r.rateName}: ${r.percentage}%`).join(', ') || '0%'})
                  </option>
                ))}
              </select>
            </div>

            {/* Modal Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'grid', gridTemplateColumns: (selectedService || selectedPackage) ? '1.2fr 1fr' : '1fr', gap: '1.5rem' }}>
              {/* Left Column: List */}
              <div style={{ maxHeight: '55vh', overflowY: 'auto' }}>
                {activeTab === 'services' ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {filteredServices.map(srv => {
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
                            alignItems: 'center'
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                              <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.75rem', background: '#f1f5f9', padding: '2px 6px', borderRadius: '4px' }}>
                                {srv.code}
                              </span>
                              <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9rem' }}>{srv.name}</span>
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                              {srv.categoryName} • Unit: {srv.billingUnitName || 'TEST'}
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontWeight: 700, color: 'var(--accent-primary)', fontSize: '0.95rem' }}>
                              ₹{Number(srv.standardPrice).toLocaleString()}
                            </div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Min Qty: {srv.minimumBillingQuantity}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {filteredPackages.map(pkg => {
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
                            cursor: 'pointer'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.75rem', background: '#ede9fe', color: '#6d28d9', padding: '2px 6px', borderRadius: '4px' }}>
                                  {pkg.code}
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
                    })}
                  </div>
                )}
              </div>

              {/* Right Column: Configure & Add */}
              {(selectedService || selectedPackage) && (
                <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: '6px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                      Selected for Quotation
                    </div>
                    <h4 style={{ margin: '0.2rem 0 0', fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {selectedService ? selectedService.name : selectedPackage.name}
                    </h4>
                  </div>

                  {selectedService && (
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
                          {savingItem ? 'Adding...' : 'Add to Quotation'}
                        </Button>
                      </div>
                    </>
                  )}

                  {selectedPackage && (
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
                          {savingItem ? 'Adding...' : 'Add Package to Quotation'}
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

