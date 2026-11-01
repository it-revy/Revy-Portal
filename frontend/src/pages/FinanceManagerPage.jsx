import React, { useState, useEffect } from 'react';
import API from '../services/api';
import Modal from '../components/Modal';
import {
  Wallet,
  CheckCircle2,
  XCircle,
  Clock,
  Send,
  AlertCircle,
  FileText,
  Search,
  RefreshCw,
  ArrowUpRight,
  TrendingDown,
  ShieldCheck,
  DollarSign
} from 'lucide-react';
import { PageHeader, Button, SearchInput, Select, FilterBar, FilterField } from '../components/ui';

const FinanceManagerPage = () => {
  const [metrics, setMetrics] = useState({ currentBalance: 0, fundLimit: 2500, totalReceived: 0, totalSpent: 0 });
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [search, setSearch] = useState('');
  const [message, setMessage] = useState(null);

  // Modals state
  const [approveModal, setApproveModal] = useState(null); // request object
  const [rejectModal, setRejectModal] = useState(null); // request object
  const [provideModal, setProvideModal] = useState(null); // request object

  // Form states
  const [approveAmount, setApproveAmount] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [provideForm, setProvideForm] = useState({
    providedAmount: '',
    providedDate: new Date().toISOString().substring(0, 10),
    providedTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    reference: '',
    note: ''
  });

  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState(null);

  useEffect(() => {
    fetchFundData();
  }, [statusFilter]);

  const fetchFundData = async () => {
    setLoading(true);
    try {
      const res = await API.get(`/breakfast/money/requests?status=${statusFilter}`);
      if (res.data.success) {
        setRequests(res.data.requests || []);
        if (res.data.metrics) setMetrics(res.data.metrics);
      }
    } catch (err) {
      console.error('Failed to fetch finance requests:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setModalError(null);
    try {
      const res = await API.put(`/breakfast/money/requests/${approveModal.requestId}/approve`, {
        approvedAmount: approveAmount || approveModal.requestedAmount
      });
      if (res.data.success) {
        setMessage({ type: 'success', text: res.data.message });
        setApproveModal(null);
        fetchFundData();
      }
    } catch (err) {
      setModalError(err.response?.data?.message || 'Failed to approve request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRejectSubmit = async (e) => {
    e.preventDefault();
    if (!rejectionReason.trim()) {
      setModalError('Rejection reason is required');
      return;
    }
    setSubmitting(true);
    setModalError(null);
    try {
      const res = await API.put(`/breakfast/money/requests/${rejectModal.requestId}/reject`, {
        rejectionReason
      });
      if (res.data.success) {
        setMessage({ type: 'success', text: res.data.message });
        setRejectModal(null);
        fetchFundData();
      }
    } catch (err) {
      setModalError(err.response?.data?.message || 'Failed to reject request');
    } finally {
      setSubmitting(false);
    }
  };

  const handleProvideSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setModalError(null);
    try {
      const res = await API.put(`/breakfast/money/requests/${provideModal.requestId}/provide`, provideForm);
      if (res.data.success) {
        setMessage({ type: 'success', text: res.data.message });
        setProvideModal(null);
        fetchFundData();
      }
    } catch (err) {
      setModalError(err.response?.data?.message || 'Failed to record provided money');
    } finally {
      setSubmitting(false);
    }
  };

  const filteredRequests = requests.filter(r => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      r.requestId.toLowerCase().includes(term) ||
      r.requestedBy.toLowerCase().includes(term) ||
      (r.reason && r.reason.toLowerCase().includes(term))
    );
  });

  const pendingCount = requests.filter(r => r.status === 'PENDING_APPROVAL' || r.status === 'SUBMITTED').length;
  const receiptPendingCount = requests.filter(r => r.status === 'RECEIPT_PENDING' || r.status === 'APPROVED').length;

  return (
    <div className="page-body">
      {/* Standard Enterprise Page Header */}
      <PageHeader
        title="Finance Manager — Breakfast Money Management"
        subtitle={`Review, approve, and record money provision for Breakfast Money Requests (Maximum Current Balance: ₹${metrics.fundLimit?.toLocaleString('en-IN')})`}
        icon={Wallet}
        iconBg="linear-gradient(135deg, #10b981, #059669)"
        actions={
          <Button variant="secondary" icon={RefreshCw} onClick={fetchFundData}>
            Refresh
          </Button>
        }
      />

      {message && (
        <div style={{
          background: message.type === 'success' ? 'var(--success-bg)' : 'var(--danger-bg)',
          border: `1px solid ${message.type === 'success' ? '#a7f3d0' : '#fca5a5'}`,
          color: message.type === 'success' ? 'var(--success-text)' : 'var(--danger-text)',
          padding: '0.85rem 1.25rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.5rem',
          fontSize: '0.9rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <CheckCircle2 size={18} />
          {message.text}
        </div>
      )}

      {/* Finance Metrics Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem', marginBottom: '1.75rem' }}>
        <div className="glass-panel" style={{ padding: '1.25rem', borderLeft: '4px solid var(--accent-primary)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>Maximum Current Balance</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.2rem' }}>₹{metrics.fundLimit?.toLocaleString('en-IN')}</div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Max Operating Cash Held</span>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem', borderLeft: '4px solid #2563eb' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>Current Available Balance</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#2563eb', marginTop: '0.2rem' }}>₹{metrics.currentBalance?.toLocaleString('en-IN')}</div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Verified Ledger Balance</span>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem', borderLeft: '4px solid #f59e0b' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>Pending Approvals</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#f59e0b', marginTop: '0.2rem' }}>{pendingCount} Requests</div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Awaiting Finance Action</span>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem', borderLeft: '4px solid #10b981' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>Total Money Provided</div>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#10b981', marginTop: '0.2rem' }}>₹{metrics.totalReceived?.toLocaleString('en-IN')}</div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Verified Total Disbursed</span>
        </div>
      </div>

      {/* Fund Requests Workstation Panel */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
          <h3 style={{ fontSize: '1.1rem', margin: 0, fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileText size={20} color="var(--accent-primary)" /> Breakfast Fund Requests
          </h3>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', width: '100%', maxWidth: '480px' }}>
            <div style={{ flex: '1 1 200px', minWidth: '160px' }}>
              <SearchInput
                placeholder="Search request ID, requester..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            <Select
              size="md"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ width: 'auto', minWidth: '160px' }}
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING_APPROVAL">Pending Approval</option>
              <option value="APPROVED">Approved</option>
              <option value="RECEIPT_PENDING">Receipt Pending</option>
              <option value="RECEIVED_VERIFIED">Received & Verified</option>
              <option value="REJECTED">Rejected</option>
            </Select>
          </div>
        </div>

        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Request ID</th>
                <th>Requested By & Date</th>
                <th>Current / Limit</th>
                <th>Requested Amount</th>
                <th>Expected Balance</th>
                <th>Reason</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Finance Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '2rem' }}>Loading fund requests...</td></tr>
              ) : filteredRequests.length === 0 ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No fund requests match the selected filter.</td></tr>
              ) : (
                filteredRequests.map(r => (
                  <tr key={r._id || r.requestId}>
                    <td style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--accent-primary)' }}>{r.requestId}</td>
                    <td>
                      <div><strong>{r.requestedBy}</strong></div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{r.requestDate} {r.requestTime}</span>
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>
                      ₹{r.currentBalance} / ₹{r.fundLimit || 2500}
                    </td>
                    <td>
                      <strong style={{ color: 'var(--accent-primary)', fontSize: '1rem' }}>₹{r.requestedAmount}</strong>
                    </td>
                    <td style={{ fontSize: '0.85rem', fontWeight: 600, color: '#10b981' }}>
                      ₹{r.expectedBalance}
                    </td>
                    <td style={{ fontSize: '0.85rem', maxWidth: '200px' }}>{r.reason}</td>
                    <td>
                      <span className={`badge ${
                        r.status === 'RECEIVED_VERIFIED' ? 'badge-success' :
                        r.status === 'APPROVED' ? 'badge-info' :
                        r.status === 'RECEIPT_PENDING' ? 'badge-warning' :
                        r.status === 'REJECTED' ? 'badge-danger' : 'badge-warning'
                      }`}>
                        {r.status}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.4rem' }}>
                        {(r.status === 'PENDING_APPROVAL' || r.status === 'SUBMITTED') && (
                          <>
                            <button
                              className="btn btn-success"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem' }}
                              onClick={() => {
                                setApproveModal(r);
                                setApproveAmount(r.requestedAmount);
                                setModalError(null);
                              }}
                            >
                              <CheckCircle2 size={14} /> Approve
                            </button>
                            <button
                              className="btn btn-secondary"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem', color: 'var(--danger)', borderColor: '#fca5a5' }}
                              onClick={() => {
                                setRejectModal(r);
                                setRejectionReason('');
                                setModalError(null);
                              }}
                            >
                              <XCircle size={14} /> Reject
                            </button>
                          </>
                        )}

                        {r.status === 'APPROVED' && (
                          <button
                            className="btn btn-primary"
                            style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                            onClick={() => {
                              setProvideModal(r);
                              setProvideForm({
                                providedAmount: r.approvedAmount || r.requestedAmount,
                                providedDate: new Date().toISOString().substring(0, 10),
                                providedTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                                reference: `TRF-${Date.now().toString().slice(-6)}`,
                                note: ''
                              });
                              setModalError(null);
                            }}
                          >
                            <Send size={14} /> Provide Money
                          </button>
                        )}

                        {r.status === 'RECEIPT_PENDING' && (
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                            Awaiting BF Admin Receipt
                          </span>
                        )}

                        {r.status === 'RECEIVED_VERIFIED' && (
                          <span style={{ fontSize: '0.8rem', color: 'var(--success)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                            <ShieldCheck size={14} /> Verified
                          </span>
                        )}

                        {r.status === 'REJECTED' && (
                          <span style={{ fontSize: '0.8rem', color: 'var(--danger)', fontStyle: 'italic' }}>
                            {r.rejectionReason}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* APPROVE MODAL */}
      {approveModal && (
        <Modal
          isOpen={!!approveModal}
          onClose={() => setApproveModal(null)}
          title={`Approve Fund Request (${approveModal.requestId})`}
        >
          <form onSubmit={handleApproveSubmit}>
            {modalError && (
              <div style={{ padding: '0.75rem', background: 'var(--danger-bg)', border: '1px solid #fca5a5', color: 'var(--danger-text)', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                <AlertCircle size={16} /> {modalError}
              </div>
            )}

            <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: 'var(--radius-sm)', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
              <div>Requested By: <strong>{approveModal.requestedBy}</strong></div>
              <div>Requested Amount: <strong>₹{approveModal.requestedAmount}</strong></div>
              <div>Reason: <span>{approveModal.reason}</span></div>
            </div>

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label className="form-label">Approved Amount (₹) *</label>
              <input
                type="number"
                min="1"
                className="form-input"
                value={approveAmount}
                onChange={(e) => setApproveAmount(e.target.value)}
                required
              />
            </div>

            <div style={{ padding: '0.75rem', background: '#eff6ff', border: '1px solid #bfdbfe', color: '#1e40af', borderRadius: 'var(--radius-sm)', marginBottom: '1.5rem', fontSize: '0.8rem' }}>
              ℹ Note: Approval sets status to APPROVED. The available Breakfast Fund balance will NOT update until money is provided and Breakfast Admin verifies receipt.
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setApproveModal(null)}>Cancel</button>
              <button type="submit" className="btn btn-success" disabled={submitting}>
                {submitting ? 'Approving...' : 'Confirm Approval'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* REJECT MODAL */}
      {rejectModal && (
        <Modal
          isOpen={!!rejectModal}
          onClose={() => setRejectModal(null)}
          title={`Reject Fund Request (${rejectModal.requestId})`}
        >
          <form onSubmit={handleRejectSubmit}>
            {modalError && (
              <div style={{ padding: '0.75rem', background: 'var(--danger-bg)', border: '1px solid #fca5a5', color: 'var(--danger-text)', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                <AlertCircle size={16} /> {modalError}
              </div>
            )}

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label className="form-label">Rejection Reason *</label>
              <textarea
                className="form-input"
                rows="3"
                placeholder="State the explicit reason for rejecting this fund request..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                required
              ></textarea>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setRejectModal(null)}>Cancel</button>
              <button type="submit" className="btn btn-danger" disabled={submitting}>
                {submitting ? 'Rejecting...' : 'Reject Request'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* PROVIDE MONEY MODAL */}
      {provideModal && (
        <Modal
          isOpen={!!provideModal}
          onClose={() => setProvideModal(null)}
          title={`Record Money Provided (${provideModal.requestId})`}
        >
          <form onSubmit={handleProvideSubmit}>
            {modalError && (
              <div style={{ padding: '0.75rem', background: 'var(--danger-bg)', border: '1px solid #fca5a5', color: 'var(--danger-text)', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                <AlertCircle size={16} /> {modalError}
              </div>
            )}

            <div className="form-grid-2" style={{ marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Provided Amount (₹) *</label>
                <input
                  type="number"
                  min="1"
                  className="form-input"
                  value={provideForm.providedAmount}
                  onChange={(e) => setProvideForm({ ...provideForm, providedAmount: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Transfer Reference</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. UTR / Receipt Ref"
                  value={provideForm.reference}
                  onChange={(e) => setProvideForm({ ...provideForm, reference: e.target.value })}
                />
              </div>
            </div>

            <div className="form-grid-2" style={{ marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Provided Date *</label>
                <input
                  type="date"
                  className="form-input"
                  value={provideForm.providedDate}
                  onChange={(e) => setProvideForm({ ...provideForm, providedDate: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Provided Time *</label>
                <input
                  type="text"
                  className="form-input"
                  value={provideForm.providedTime}
                  onChange={(e) => setProvideForm({ ...provideForm, providedTime: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label className="form-label">Note / Instructions</label>
              <textarea
                className="form-input"
                rows="2"
                placeholder="Optional transfer note..."
                value={provideForm.note}
                onChange={(e) => setProvideForm({ ...provideForm, note: e.target.value })}
              ></textarea>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setProvideModal(null)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Recording...' : 'Record Money Provided'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};

export default FinanceManagerPage;
