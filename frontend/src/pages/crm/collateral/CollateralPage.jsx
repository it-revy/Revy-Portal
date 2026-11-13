import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import {
  FileText,
  Receipt,
  Search,
  Filter,
  Eye,
  Edit,
  Copy,
  Printer,
  Plus,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  CheckCircle,
  Clock,
  Layers,
  ArrowRight,
  AlertCircle
} from 'lucide-react';
import { invoiceService } from '../../../services/invoiceService';
import crmService from '../../../services/crmService';
import { PageHeader, StatusBadge, SearchInput, Pagination } from '../../../components/ui';
import QuotationManagerModal from '../../../components/crm/QuotationManagerModal';
import InvoicePreparationModal from '../../../components/crm/InvoicePreparationModal';

export default function CollateralPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();

  // Determine active view: 'all', 'quotations', 'invoices'
  const currentPath = location.pathname;
  let defaultView = 'all';
  if (currentPath.includes('/quotations')) {
    defaultView = 'quotations';
  } else if (currentPath.includes('/invoices')) {
    defaultView = 'invoices';
  } else if (searchParams.get('view')) {
    defaultView = searchParams.get('view');
  }

  const [activeTab, setActiveTab] = useState(defaultView);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [page, setPage] = useState(parseInt(searchParams.get('page') || '1', 10));
  const [pageSize, setPageSize] = useState(25);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [items, setItems] = useState([]);
  const [totalCount, setTotalCount] = useState(0);

  // Modals
  const [quotationModalOpen, setQuotationModalOpen] = useState(false);
  const [invoiceModalOpen, setInvoiceModalOpen] = useState(false);
  const [selectedOpportunity, setSelectedOpportunity] = useState(null);
  const [selectedQuotation, setSelectedQuotation] = useState(null);

  // Notification Toast
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Sync tab with URL
  useEffect(() => {
    if (currentPath.endsWith('/quotations')) {
      setActiveTab('quotations');
    } else if (currentPath.endsWith('/invoices')) {
      setActiveTab('invoices');
    }
  }, [currentPath]);

  // Fetch Collateral Data
  const fetchCollateral = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await invoiceService.getCollateral({
        view: activeTab === 'all' ? 'all' : activeTab,
        search: searchQuery || undefined,
        page: page,
        pageSize: pageSize
      });

      if (res.data?.success) {
        setItems(res.data.items || []);
        setTotalCount(res.data.totalCount || 0);
      }
    } catch (err) {
      console.error('Failed to load collateral:', err);
      setError(err.response?.data?.message || err.message || 'Failed to load collateral records.');
    } finally {
      setLoading(false);
    }
  }, [activeTab, searchQuery, page, pageSize]);

  useEffect(() => {
    fetchCollateral();
  }, [fetchCollateral]);

  // Tab change handler
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setPage(1);
    if (tab === 'quotations') {
      navigate('/crm/collateral/quotations');
    } else if (tab === 'invoices') {
      navigate('/crm/collateral/invoices');
    } else {
      navigate('/crm/collateral');
    }
  };

  // Open Quotation Manager Modal for an opportunity
  const handleOpenQuotation = async (item) => {
    try {
      const oppRes = await crmService.getOpportunityById(item.opportunityId);
      if (oppRes.data?.success && oppRes.data.opportunity) {
        setSelectedOpportunity(oppRes.data.opportunity);
        setQuotationModalOpen(true);
      } else {
        // Fallback opportunity object
        setSelectedOpportunity({
          id: item.opportunityId,
          opportunityId: item.opportunityNumber,
          name: item.opportunityName,
          accountId: item.accountId,
          accountName: item.accountName
        });
        setQuotationModalOpen(true);
      }
    } catch (err) {
      console.error('Error fetching opp for quote modal:', err);
      setSelectedOpportunity({
        id: item.opportunityId,
        opportunityId: item.opportunityNumber,
        name: item.opportunityName,
        accountId: item.accountId,
        accountName: item.accountName
      });
      setQuotationModalOpen(true);
    }
  };

  // Quick Copy Quotation
  const handleCopyQuote = async (e, quotationId) => {
    e.stopPropagation();
    try {
      const res = await invoiceService.getQuotationEmailText(quotationId);
      if (res.data?.emailText) {
        await navigator.clipboard.writeText(res.data.emailText);
        showToast('Quotation text copied to clipboard! Ready to paste into email.');
      } else {
        showToast('Quotation text generated.');
      }
    } catch (err) {
      console.error('Copy quote error:', err);
      alert('Failed to copy quotation text.');
    }
  };

  // Quick Create / Approve Invoice from row
  const handleCreateInvoiceFromRow = async (e, item) => {
    e.stopPropagation();
    try {
      const [oppRes, quoteRes] = await Promise.all([
        crmService.getOpportunityById(item.opportunityId),
        invoiceService.getCurrentQuotation(item.opportunityId)
      ]);

      const opp = oppRes.data?.opportunity || {
        id: item.opportunityId,
        opportunityId: item.opportunityNumber,
        name: item.opportunityName,
        accountId: item.accountId,
        accountName: item.accountName
      };

      const quote = quoteRes.data?.quotation;
      if (!quote) {
        alert('No quotation found for this opportunity. Please create a quotation first.');
        return;
      }

      setSelectedOpportunity(opp);
      setSelectedQuotation(quote);
      setInvoiceModalOpen(true);
    } catch (err) {
      console.error('Failed to prepare invoice:', err);
      alert('Failed to load quotation for invoice preparation.');
    }
  };

  // Callback from Quotation Modal to approve & create invoice
  const handleApproveQuotationAndProceed = (quote) => {
    setQuotationModalOpen(false);
    setSelectedQuotation(quote);
    setInvoiceModalOpen(true);
  };

  // Open PI in print tab
  const handlePrintPI = (e, piId) => {
    e.stopPropagation();
    const url = invoiceService.getInvoiceHtmlUrl(piId);
    window.open(url, '_blank');
  };

  // Navigate to PI detail page
  const handleViewPI = (e, piId) => {
    e.stopPropagation();
    navigate(`/crm/proforma-invoices/${piId}`);
  };

  return (
    <div className="crm-page-container" style={{ padding: '1.5rem', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Toast Notification */}
      {toastMessage && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          zIndex: 10001,
          backgroundColor: '#065f46',
          color: '#ecfdf5',
          border: '1px solid #10b981',
          borderRadius: '8px',
          padding: '0.75rem 1.25rem',
          boxShadow: '0 10px 15px -3px rgba(0,0,0,0.3)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.88rem',
          fontWeight: 500
        }}>
          <CheckCircle size={18} />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f8fafc', margin: 0, display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <FileText size={28} color="#f59e0b" />
            Collateral
          </h1>
          <p style={{ color: '#94a3b8', fontSize: '0.88rem', margin: '4px 0 0' }}>
            Official quotations and Proforma Invoices generated across sales opportunities.
          </p>
        </div>

        <button
          onClick={fetchCollateral}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.4rem',
            backgroundColor: '#1e293b',
            color: '#cbd5e1',
            border: '1px solid #334155',
            borderRadius: '6px',
            padding: '0.5rem 0.85rem',
            fontSize: '0.85rem',
            cursor: 'pointer'
          }}
          title="Refresh collateral records"
        >
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      {/* View Switcher Tabs */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid #334155',
        marginBottom: '1.25rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => handleTabChange('all')}
            style={{
              padding: '0.65rem 1.1rem',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === 'all' ? '2px solid #f59e0b' : '2px solid transparent',
              color: activeTab === 'all' ? '#f59e0b' : '#94a3b8',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <Layers size={17} />
            All Collateral
          </button>

          <button
            onClick={() => handleTabChange('quotations')}
            style={{
              padding: '0.65rem 1.1rem',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === 'quotations' ? '2px solid #0284c7' : '2px solid transparent',
              color: activeTab === 'quotations' ? '#38bdf8' : '#94a3b8',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <FileText size={17} />
            Quotations
          </button>

          <button
            onClick={() => handleTabChange('invoices')}
            style={{
              padding: '0.65rem 1.1rem',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === 'invoices' ? '2px solid #10b981' : '2px solid transparent',
              color: activeTab === 'invoices' ? '#34d399' : '#94a3b8',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}
          >
            <Receipt size={17} />
            Proforma Invoices
          </button>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', width: '320px' }}>
          <Search size={16} color="#94a3b8" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }} />
          <input
            type="text"
            placeholder="Search opportunity, account, quotation or PI..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.45rem 0.75rem 0.45rem 2.2rem',
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px',
              color: 'white',
              fontSize: '0.85rem'
            }}
          />
        </div>
      </div>

      {/* Main Table Card */}
      <div style={{
        backgroundColor: '#1e293b',
        borderRadius: '8px',
        border: '1px solid #334155',
        overflow: 'hidden',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)'
      }}>
        {error && (
          <div style={{
            padding: '1rem',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            borderBottom: '1px solid #ef4444',
            color: '#fca5a5',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.85rem'
          }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div style={{ padding: '3.5rem', textAlign: 'center', color: '#94a3b8' }}>
            <RefreshCw size={28} className="animate-spin" style={{ margin: '0 auto 0.75rem', opacity: 0.7 }} />
            <p style={{ margin: 0 }}>Loading collateral records...</p>
          </div>
        ) : items.length === 0 ? (
          <div style={{ padding: '3.5rem', textAlign: 'center', color: '#94a3b8' }}>
            <FileText size={40} style={{ margin: '0 auto 1rem', opacity: 0.4 }} />
            <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: '#f8fafc', margin: '0 0 0.5rem' }}>
              No collateral documents found
            </h3>
            <p style={{ fontSize: '0.85rem', margin: 0, maxWidth: '450px', marginLeft: 'auto', marginRight: 'auto' }}>
              {activeTab === 'invoices'
                ? 'No Proforma Invoices have been created yet. Open an opportunity quotation and select "Approve Quotation and Create Invoice" to generate one.'
                : 'Only opportunities with at least one quotation or Proforma Invoice are displayed here. Open an opportunity from the Sales Funnel to create a quotation.'}
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ backgroundColor: '#0f172a', color: '#94a3b8', textAlign: 'left', borderBottom: '1px solid #334155' }}>
                  <th style={{ padding: '0.75rem 1rem' }}>Opportunity</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Account / Customer</th>
                  <th style={{ padding: '0.75rem 1rem' }}>Owner</th>
                  {(activeTab === 'all' || activeTab === 'quotations') && (
                    <th style={{ padding: '0.75rem 1rem' }}>Quotation</th>
                  )}
                  {(activeTab === 'all' || activeTab === 'invoices') && (
                    <th style={{ padding: '0.75rem 1rem' }}>Proforma Invoice</th>
                  )}
                  <th style={{ padding: '0.75rem 1rem' }}>Last Updated</th>
                  <th style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => {
                  return (
                    <tr
                      key={it.opportunityId}
                      style={{
                        borderBottom: '1px solid #334155',
                        transition: 'background-color 0.15s ease'
                      }}
                      onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.02)'}
                      onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                      {/* Opportunity */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <div
                          onClick={() => navigate(`/crm/opportunities/${it.opportunityId}/edit`)}
                          style={{
                            fontWeight: 600,
                            color: '#f8fafc',
                            cursor: 'pointer',
                            display: 'inline-block'
                          }}
                          onMouseEnter={e => e.currentTarget.style.color = '#38bdf8'}
                          onMouseLeave={e => e.currentTarget.style.color = '#f8fafc'}
                        >
                          {it.opportunityName}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '2px' }}>
                          {it.opportunityNumber}
                        </div>
                      </td>

                      {/* Account */}
                      <td style={{ padding: '0.75rem 1rem' }}>
                        <div style={{ fontWeight: 500, color: '#e2e8f0' }}>{it.accountName}</div>
                        {it.customerId && (
                          <span style={{ fontSize: '0.72rem', color: '#f59e0b', fontWeight: 600 }}>
                            Cust ID: {it.customerId}
                          </span>
                        )}
                      </td>

                      {/* Owner */}
                      <td style={{ padding: '0.75rem 1rem', color: '#cbd5e1' }}>
                        {it.ownerName || 'Unassigned'}
                      </td>

                      {/* Quotation Details */}
                      {(activeTab === 'all' || activeTab === 'quotations') && (
                        <td style={{ padding: '0.75rem 1rem' }}>
                          {it.quotationNumber ? (
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                <span style={{ fontWeight: 600, color: '#38bdf8' }}>{it.quotationNumber}</span>
                                <span style={{
                                  fontSize: '0.7rem',
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  backgroundColor: '#0369a1',
                                  color: '#e0f2fe',
                                  fontWeight: 600
                                }}>
                                  {it.quotationStatus || 'Draft'}
                                </span>
                              </div>
                              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f8fafc', marginTop: '3px' }}>
                                ₹{Number(it.quotationAmount || 0).toLocaleString('en-IN')}
                              </div>
                            </div>
                          ) : (
                            <span style={{ color: '#64748b', fontSize: '0.8rem', fontStyle: 'italic' }}>
                              No quotation
                            </span>
                          )}
                        </td>
                      )}

                      {/* Proforma Invoice Details */}
                      {(activeTab === 'all' || activeTab === 'invoices') && (
                        <td style={{ padding: '0.75rem 1rem' }}>
                          {it.piNumber ? (
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                <span
                                  onClick={(e) => handleViewPI(e, it.piId)}
                                  style={{ fontWeight: 600, color: '#34d399', cursor: 'pointer' }}
                                  title="View Proforma Invoice"
                                >
                                  {it.piNumber}
                                </span>
                                <span style={{
                                  fontSize: '0.7rem',
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  backgroundColor: '#065f46',
                                  color: '#d1fae5',
                                  fontWeight: 600
                                }}>
                                  Rev {it.piRevisionNumber || 1}
                                </span>
                              </div>
                              <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f8fafc', marginTop: '3px' }}>
                                ₹{Number(it.piAmount || 0).toLocaleString('en-IN')}
                              </div>
                            </div>
                          ) : (
                            <span style={{ color: '#64748b', fontSize: '0.8rem', fontStyle: 'italic' }}>
                              No PI generated
                            </span>
                          )}
                        </td>
                      )}

                      {/* Last Updated */}
                      <td style={{ padding: '0.75rem 1rem', color: '#94a3b8', fontSize: '0.8rem' }}>
                        {new Date(it.lastUpdatedDate).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric'
                        })}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.4rem' }}>
                          {/* Quotation Actions */}
                          <button
                            onClick={() => handleOpenQuotation(it)}
                            style={{
                              backgroundColor: '#334155',
                              border: '1px solid #475569',
                              color: '#cbd5e1',
                              borderRadius: '4px',
                              padding: '4px 8px',
                              fontSize: '0.78rem',
                              fontWeight: 500,
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '3px'
                            }}
                            title="Manage Quotation"
                          >
                            <Edit size={13} />
                            {it.quotationId ? 'Edit Quote' : '+ Quote'}
                          </button>

                          {it.quotationId && (
                            <button
                              onClick={(e) => handleCopyQuote(e, it.quotationId)}
                              style={{
                                backgroundColor: '#1e293b',
                                border: '1px solid #475569',
                                color: '#94a3b8',
                                borderRadius: '4px',
                                padding: '4px 7px',
                                fontSize: '0.78rem',
                                cursor: 'pointer'
                              }}
                              title="Copy email quotation text"
                            >
                              <Copy size={13} />
                            </button>
                          )}

                          {it.quotationId && !it.piId && (
                            <button
                              onClick={(e) => handleCreateInvoiceFromRow(e, it)}
                              style={{
                                backgroundColor: '#065f46',
                                border: '1px solid #10b981',
                                color: '#ecfdf5',
                                borderRadius: '4px',
                                padding: '4px 8px',
                                fontSize: '0.78rem',
                                fontWeight: 600,
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '3px'
                              }}
                              title="Approve Quotation and Create Proforma Invoice"
                            >
                              <Receipt size={13} />
                              Create PI
                            </button>
                          )}

                          {/* Invoice Actions */}
                          {it.piId && (
                            <>
                              <button
                                onClick={(e) => handleViewPI(e, it.piId)}
                                style={{
                                  backgroundColor: '#0f766e',
                                  border: '1px solid #14b8a6',
                                  color: '#ccfbf1',
                                  borderRadius: '4px',
                                  padding: '4px 8px',
                                  fontSize: '0.78rem',
                                  fontWeight: 600,
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '3px'
                                }}
                                title="View Proforma Invoice Details"
                              >
                                <Eye size={13} />
                                View PI
                              </button>

                              <button
                                onClick={(e) => handlePrintPI(e, it.piId)}
                                style={{
                                  backgroundColor: '#1e293b',
                                  border: '1px solid #475569',
                                  color: '#cbd5e1',
                                  borderRadius: '4px',
                                  padding: '4px 7px',
                                  fontSize: '0.78rem',
                                  cursor: 'pointer'
                                }}
                                title="Print / Download PDF"
                              >
                                <Printer size={13} />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination footer */}
        {totalCount > pageSize && (
          <div style={{ padding: '0.75rem 1rem', borderTop: '1px solid #334155', display: 'flex', justifyContent: 'flex-end' }}>
            <Pagination
              currentPage={page}
              totalCount={totalCount}
              pageSize={pageSize}
              onPageChange={setPage}
            />
          </div>
        )}
      </div>

      {/* Quotation Manager Modal */}
      {quotationModalOpen && selectedOpportunity && (
        <QuotationManagerModal
          isOpen={quotationModalOpen}
          onClose={() => {
            setQuotationModalOpen(false);
            fetchCollateral();
          }}
          opportunity={selectedOpportunity}
          onQuotationSaved={() => {
            fetchCollateral();
          }}
          onApproveAndCreateInvoice={handleApproveQuotationAndProceed}
        />
      )}

      {/* Invoice Preparation Modal */}
      {invoiceModalOpen && selectedOpportunity && selectedQuotation && (
        <InvoicePreparationModal
          isOpen={invoiceModalOpen}
          onClose={() => {
            setInvoiceModalOpen(false);
            fetchCollateral();
          }}
          opportunity={selectedOpportunity}
          quotation={selectedQuotation}
          onInvoiceCreated={(piData) => {
            fetchCollateral();
            if (piData?.proformaInvoiceId) {
              navigate(`/crm/proforma-invoices/${piData.proformaInvoiceId}`);
            }
          }}
        />
      )}
    </div>
  );
}
