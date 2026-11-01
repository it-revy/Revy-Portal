import React, { useState, useEffect } from 'react';
import API from '../services/api';
import Modal from '../components/Modal';
import {
  Wallet,
  DollarSign,
  PlusCircle,
  MinusCircle,
  Calendar,
  Search,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Send,
  AlertTriangle,
  HelpCircle,
  ShieldCheck
} from 'lucide-react';
import { PageHeader, Button, SearchInput, Select, DatePicker, FilterBar, FilterField } from '../components/ui';

const BreakfastMoneyPage = () => {
  const [activeTab, setActiveTab] = useState('transactions'); // 'transactions' | 'daily' | 'monthly'
  const [metrics, setMetrics] = useState({
    currentBalance: 0,
    fundLimit: 2500,
    recommendedRequest: 2500,
    totalReceived: 0,
    totalSpent: 0,
    lowBalanceWarning: false
  });
  const [activeRequest, setActiveRequest] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters for Transaction History
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [search, setSearch] = useState('');

  // Daily Statement state
  const [dailyDate, setDailyDate] = useState(new Date().toISOString().substring(0, 10));
  const [dailyStatement, setDailyStatement] = useState(null);
  const [dailyLoading, setDailyLoading] = useState(false);

  // Monthly Statement state
  const [monthlyMonth, setMonthlyMonth] = useState(new Date().toISOString().substring(0, 7));
  const [monthlyStatement, setMonthlyStatement] = useState(null);
  const [monthlyLoading, setMonthlyLoading] = useState(false);

  // Modals state
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [showVerifyModal, setShowVerifyModal] = useState(false);
  const [showDifferenceModal, setShowDifferenceModal] = useState(false);

  // Request Money Form
  const [requestForm, setRequestForm] = useState({
    requestedAmount: '',
    reason: 'Operating cash fund replenishment'
  });

  // Record Expense Form
  const [expenseForm, setExpenseForm] = useState({
    transactionDate: new Date().toISOString().substring(0, 10),
    transactionTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    amount: '',
    source: 'Manual Expense',
    expenseCategory: 'OTHER_BREAKFAST_EXPENSE',
    expensePurpose: 'EMPLOYEE',
    description: '',
    note: ''
  });

  // Verify Receipt Form
  const [verifyForm, setVerifyForm] = useState({
    verifiedAmount: '',
    differenceNote: ''
  });

  const [formSubmitting, setFormSubmitting] = useState(false);
  const [modalError, setModalError] = useState(null);
  const [globalMessage, setGlobalMessage] = useState(null);

  useEffect(() => {
    fetchTransactions();
    fetchBalanceMetrics();
  }, [typeFilter, startDate, endDate]);

  useEffect(() => {
    if (activeTab === 'daily') {
      fetchDailyStatement();
    } else if (activeTab === 'monthly') {
      fetchMonthlyStatement();
    }
  }, [activeTab, dailyDate, monthlyMonth]);

  const fetchBalanceMetrics = async () => {
    try {
      const res = await API.get('/breakfast/money/balance');
      if (res.data.success) {
        if (res.data.metrics) setMetrics(res.data.metrics);
        setActiveRequest(res.data.activeRequest || null);
      }
    } catch (err) {
      console.error('Failed to fetch balance metrics:', err);
    }
  };

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      let url = `/breakfast/money/transactions?type=${typeFilter}`;
      if (startDate) url += `&startDate=${startDate}`;
      if (endDate) url += `&endDate=${endDate}`;
      if (search) url += `&search=${search}`;

      const res = await API.get(url);
      if (res.data.success) {
        setTransactions(res.data.transactions || []);
        if (res.data.metrics) setMetrics(res.data.metrics);
      }
    } catch (err) {
      console.error('Failed to fetch money transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchDailyStatement = async () => {
    setDailyLoading(true);
    try {
      const res = await API.get(`/breakfast/money/statement/daily?date=${dailyDate}`);
      if (res.data.success) {
        setDailyStatement(res.data.statement);
      }
    } catch (err) {
      console.error('Failed to fetch daily statement:', err);
    } finally {
      setDailyLoading(false);
    }
  };

  const fetchMonthlyStatement = async () => {
    setMonthlyLoading(true);
    try {
      const res = await API.get(`/breakfast/money/statement/monthly?month=${monthlyMonth}`);
      if (res.data.success) {
        setMonthlyStatement(res.data.statement);
      }
    } catch (err) {
      console.error('Failed to fetch monthly statement:', err);
    } finally {
      setMonthlyLoading(false);
    }
  };

  const handleOpenRequestModal = () => {
    setModalError(null);
    const rec = Math.max(0, (metrics.fundLimit || 2500) - metrics.currentBalance);
    setRequestForm({
      requestedAmount: rec,
      reason: 'Operating cash fund replenishment'
    });
    setShowRequestModal(true);
  };

  const handleRequestSubmit = async (e) => {
    e.preventDefault();
    setFormSubmitting(true);
    setModalError(null);

    const amount = Number(requestForm.requestedAmount);
    if (metrics.currentBalance + amount > (metrics.fundLimit || 2500)) {
      setModalError(`This exceeds the ₹${(metrics.fundLimit || 2500).toLocaleString('en-IN')} Breakfast Fund limit.`);
      setFormSubmitting(false);
      return;
    }

    try {
      const res = await API.post('/breakfast/money/requests', requestForm);
      if (res.data.success) {
        setShowRequestModal(false);
        setGlobalMessage({ type: 'success', text: res.data.message });
        fetchBalanceMetrics();
      }
    } catch (err) {
      const data = err.response?.data;
      if (data?.exceedsLimit) {
        setModalError(data.message);
      } else if (data?.existingRequest) {
        setModalError(data.message);
      } else {
        setModalError(data?.message || 'Failed to submit fund request');
      }
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleExpenseSubmit = async (e) => {
    e.preventDefault();
    setFormSubmitting(true);
    setModalError(null);

    try {
      const res = await API.post('/breakfast/money/expense', expenseForm);
      if (res.data.success) {
        setShowExpenseModal(false);
        setGlobalMessage({ type: 'success', text: res.data.message });
        setExpenseForm({
          transactionDate: new Date().toISOString().substring(0, 10),
          transactionTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          amount: '',
          source: 'Manual Expense',
          expenseCategory: 'OTHER_BREAKFAST_EXPENSE',
          expensePurpose: 'EMPLOYEE',
          description: '',
          note: ''
        });
        fetchBalanceMetrics();
        fetchTransactions();
      }
    } catch (err) {
      const data = err.response?.data;
      if (data?.isInsufficient) {
        setModalError(`Insufficient breakfast fund balance. Available: ₹${data.available}, Required: ₹${data.required}, Shortfall: ₹${data.shortfall}`);
      } else {
        setModalError(data?.message || 'Failed to record manual expense');
      }
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleOpenVerifyModal = () => {
    setModalError(null);
    setVerifyForm({
      verifiedAmount: activeRequest?.providedAmount || activeRequest?.approvedAmount || activeRequest?.requestedAmount || 0,
      differenceNote: ''
    });
    setShowVerifyModal(true);
  };

  const handleVerifySubmit = async (e) => {
    e.preventDefault();
    setFormSubmitting(true);
    setModalError(null);

    try {
      const res = await API.put(`/breakfast/money/requests/${activeRequest.requestId}/verify`, verifyForm);
      if (res.data.success) {
        setShowVerifyModal(false);
        setShowDifferenceModal(false);
        setGlobalMessage({ type: 'success', text: res.data.message });
        fetchBalanceMetrics();
        fetchTransactions();
      }
    } catch (err) {
      setModalError(err.response?.data?.message || 'Failed to verify receipt');
    } finally {
      setFormSubmitting(false);
    }
  };

  const fundLimit = metrics.fundLimit || 2500;
  const currentBalance = metrics.currentBalance || 0;
  const recommendedRequest = Math.max(0, fundLimit - currentBalance);
  const isLowBalance = currentBalance < 100;

  return (
    <div className="page-body">
      {/* Standard Enterprise Page Header */}
      <PageHeader
        title="Breakfast Money & Cash Balance"
        subtitle={`Authoritative cash management for money received from Finance (Maximum Current Balance: ₹${fundLimit.toLocaleString('en-IN')})`}
        icon={Wallet}
        iconBg="linear-gradient(135deg, #10b981, #059669)"
        actions={
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <Button
              variant="primary"
              icon={Send}
              onClick={handleOpenRequestModal}
            >
              Request Money
            </Button>
            <Button
              variant="secondary"
              icon={MinusCircle}
              onClick={() => { setModalError(null); setShowExpenseModal(true); }}
            >
              Record Expense
            </Button>
          </div>
        }
      />

      {/* Low Balance Alert Banner (< ₹100) */}
      {isLowBalance && (
        <div style={{
          background: '#fef2f2',
          border: '2px solid #ef4444',
          borderRadius: 'var(--radius-sm)',
          padding: '1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ width: '44px', height: '44px', borderRadius: '50%', background: '#fee2e2', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <AlertTriangle size={24} color="#dc2626" />
            </div>
            <div>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#991b1b' }}>LOW BREAKFAST BALANCE</div>
              <div style={{ fontSize: '0.85rem', color: '#7f1d1d', marginTop: '0.2rem' }}>
                Current Balance: <strong>₹{currentBalance}</strong> | Maximum Current Balance: <strong>₹2,500</strong> | Suggested Request: <strong>₹{recommendedRequest}</strong>
              </div>
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleOpenRequestModal} style={{ background: '#dc2626', borderColor: '#b91c1c' }}>
            <Send size={16} /> Request Money
          </button>
        </div>
      )}

      {/* Active Fund Request Status Banner */}
      {activeRequest && (
        <div style={{
          background: activeRequest.status === 'RECEIPT_PENDING' ? '#ecfdf5' : '#f0f9ff',
          border: `1px solid ${activeRequest.status === 'RECEIPT_PENDING' ? '#6ee7b7' : '#bae6fd'}`,
          borderRadius: 'var(--radius-sm)',
          padding: '1.25rem',
          marginBottom: '1.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', fontWeight: 700, color: 'var(--accent-primary)' }}>{activeRequest.requestId}</span>
                <span className={`badge ${
                  activeRequest.status === 'RECEIPT_PENDING' ? 'badge-success' :
                  activeRequest.status === 'APPROVED' ? 'badge-info' : 'badge-warning'
                }`}>
                  {activeRequest.status === 'RECEIPT_PENDING' ? 'Money Received Pending Verification' : activeRequest.status}
                </span>
              </div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                {activeRequest.status === 'RECEIPT_PENDING' ? (
                  <>
                    Finance provided <strong>₹{activeRequest.providedAmount}</strong> on {activeRequest.providedDate} ({activeRequest.reference || 'Ref N/A'}).
                    Confirm receipt to update available balance to <strong>₹{currentBalance + activeRequest.providedAmount}</strong>.
                  </>
                ) : activeRequest.status === 'APPROVED' ? (
                  <>
                    Request approved for <strong>₹{activeRequest.approvedAmount}</strong> by {activeRequest.approvedBy}. Awaiting Finance to provide money.
                  </>
                ) : (
                  <>
                    Money Request for <strong>₹{activeRequest.requestedAmount}</strong> is pending Finance Manager approval.
                  </>
                )}
              </div>
            </div>

            {activeRequest.status === 'RECEIPT_PENDING' && (
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn-success" onClick={handleOpenVerifyModal} style={{ padding: '0.55rem 1rem', fontSize: '0.85rem' }}>
                  <ShieldCheck size={16} /> Confirm Money Received
                </button>
                <button className="btn btn-secondary" onClick={() => { handleOpenVerifyModal(); setShowDifferenceModal(true); }} style={{ padding: '0.55rem 1rem', fontSize: '0.85rem', color: '#d97706' }}>
                  <AlertCircle size={16} /> Report Difference
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {globalMessage && (
        <div style={{
          background: globalMessage.type === 'success' ? 'var(--success-bg)' : 'var(--danger-bg)',
          border: `1px solid ${globalMessage.type === 'success' ? '#a7f3d0' : '#fca5a5'}`,
          color: globalMessage.type === 'success' ? 'var(--success-text)' : 'var(--danger-text)',
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1.25rem',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <CheckCircle2 size={16} /> {globalMessage.text}
        </div>
      )}

      {/* Summary Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
        <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '5px solid #2563eb', background: 'linear-gradient(135deg, rgba(37,99,235,0.05), rgba(59,130,246,0.1))' }}>
          <div>
            <div className="metric-label">CURRENT BALANCE</div>
            <div className="metric-val" style={{ color: '#2563eb', fontSize: '1.8rem', fontWeight: 800 }}>
              ₹{currentBalance.toLocaleString('en-IN')}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Authoritative Cash Held</span>
          </div>
          <Wallet size={36} color="#2563eb" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '5px solid #22c55e' }}>
          <div>
            <div className="metric-label">TOTAL RECEIVED</div>
            <div className="metric-val" style={{ color: '#16a34a', fontSize: '1.8rem', fontWeight: 800 }}>
              ₹{(metrics.totalReceived || 0).toLocaleString('en-IN')}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Verified Money Received</span>
          </div>
          <ArrowUpRight size={36} color="#22c55e" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1.25rem', borderLeft: '5px solid #ef4444' }}>
          <div>
            <div className="metric-label">TOTAL SPENT</div>
            <div className="metric-val" style={{ color: '#dc2626', fontSize: '1.8rem', fontWeight: 800 }}>
              ₹{(metrics.totalSpent || 0).toLocaleString('en-IN')}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Operations Spending</span>
          </div>
          <ArrowDownRight size={36} color="#ef4444" opacity={0.8} />
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="tabs-scroll" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
        <button
          className={`btn ${activeTab === 'transactions' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('transactions')}
          style={{ fontSize: '0.85rem', whiteSpace: 'nowrap' }}
        >
          <Clock size={16} /> Transaction History
        </button>
        <button
          className={`btn ${activeTab === 'daily' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('daily')}
          style={{ fontSize: '0.85rem', whiteSpace: 'nowrap' }}
        >
          <Calendar size={16} /> Daily Money Statement
        </button>
        <button
          className={`btn ${activeTab === 'monthly' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('monthly')}
          style={{ fontSize: '0.85rem', whiteSpace: 'nowrap' }}
        >
          <FileSpreadsheet size={16} /> Monthly Money Statement
        </button>
      </div>

      {/* TAB 1: Transaction History */}
      {activeTab === 'transactions' && (
        <div>
          {/* Standard Enterprise Filter Bar */}
          <FilterBar
            onReset={search || typeFilter !== 'ALL' || startDate || endDate ? () => {
              setSearch('');
              setTypeFilter('ALL');
              setStartDate('');
              setEndDate('');
            } : null}
          >
            <form onSubmit={(e) => { e.preventDefault(); fetchTransactions(); }} style={{ flex: '1 1 240px', display: 'flex', gap: 'var(--space-2)' }}>
              <SearchInput
                placeholder="Search transaction ID, source, note..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onSearch={fetchTransactions}
              />
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>

            <FilterField label="Type:">
              <Select
                size="md"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                style={{ width: 'auto', minWidth: '160px' }}
              >
                <option value="ALL">All Types</option>
                <option value="MONEY_RECEIVED">Money Received</option>
                <option value="BREAKFAST_EXPENSE">Breakfast Expense</option>
                <option value="ADJUSTMENT">Adjustments</option>
                <option value="REVERSAL">Reversals</option>
              </Select>
            </FilterField>

            <FilterField label="From:">
              <DatePicker
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                style={{ width: 'auto' }}
              />
            </FilterField>

            <FilterField label="To:">
              <DatePicker
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                style={{ width: 'auto' }}
              />
            </FilterField>
          </FilterBar>

          {/* Transactions Table */}
          <div className="panel-card" style={{ padding: '1.25rem' }}>
            <div className="table-container">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Date & Time</th>
                    <th>Transaction ID</th>
                    <th>Type</th>
                    <th>Purpose</th>
                    <th>Description / Source</th>
                    <th>Reference</th>
                    <th>Amount (₹)</th>
                    <th>Running Balance</th>
                    <th>Recorded By</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr><td colSpan="9" style={{ textAlign: 'center', padding: '2rem' }}>Loading money transactions...</td></tr>
                  ) : transactions.length === 0 ? (
                    <tr><td colSpan="9" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No ledger transactions recorded yet.</td></tr>
                  ) : (
                    transactions.map(txn => (
                      <tr key={txn._id}>
                        <td>
                          <div><strong>{txn.transactionDate}</strong></div>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{txn.transactionTime}</span>
                        </td>
                        <td><span style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{txn.transactionId}</span></td>
                        <td>
                          <span className={`badge ${
                            txn.type === 'MONEY_RECEIVED' ? 'badge-success' :
                            txn.type === 'BREAKFAST_EXPENSE' ? 'badge-danger' :
                            txn.type === 'REVERSAL' ? 'badge-info' : 'badge-warning'
                          }`}>
                            {txn.type}
                          </span>
                        </td>
                        <td>
                          <span className="badge badge-secondary" style={{ fontSize: '0.75rem' }}>
                            {txn.expensePurpose || 'EMPLOYEE'}
                          </span>
                        </td>
                        <td>
                          <div><strong>{txn.description}</strong></div>
                          {txn.note && <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Note: {txn.note}</span>}
                        </td>
                        <td>
                          <span className="badge badge-info" style={{ fontSize: '0.75rem' }}>
                            {txn.referenceType} ({txn.referenceId || 'N/A'})
                          </span>
                        </td>
                        <td>
                          <strong style={{ color: txn.type === 'MONEY_RECEIVED' || txn.type === 'REVERSAL' ? '#16a34a' : txn.type === 'BREAKFAST_EXPENSE' ? '#dc2626' : '#9333ea' }}>
                            {txn.type === 'MONEY_RECEIVED' || txn.type === 'REVERSAL' ? `+₹${txn.amount}` : txn.type === 'BREAKFAST_EXPENSE' ? `-₹${txn.amount}` : `±₹${txn.amount}`}
                          </strong>
                        </td>
                        <td><strong style={{ color: 'var(--text-primary)' }}>₹{txn.balanceAfterTransaction?.toLocaleString('en-IN')}</strong></td>
                        <td style={{ fontSize: '0.85rem' }}>{txn.createdBy}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Daily Money Statement */}
      {activeTab === 'daily' && (
        <div>
          <div className="panel-card" style={{ padding: '1rem', marginBottom: '1.25rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Select Statement Date:</span>
            <input
              type="date"
              className="form-input"
              value={dailyDate}
              onChange={(e) => setDailyDate(e.target.value)}
              style={{ width: '160px' }}
            />
          </div>

          {dailyLoading ? (
            <div className="panel-card" style={{ padding: '2rem', textAlign: 'center' }}>Loading daily statement...</div>
          ) : dailyStatement && (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                <div className="glass-panel metric-card" style={{ padding: '1rem' }}>
                  <div>
                    <div className="metric-label">MONEY RECEIVED TODAY</div>
                    <div className="metric-val" style={{ color: '#16a34a' }}>₹{dailyStatement.moneyReceived}</div>
                  </div>
                  <ArrowUpRight size={28} color="#22c55e" />
                </div>

                <div className="glass-panel metric-card" style={{ padding: '1rem' }}>
                  <div>
                    <div className="metric-label">DAILY BREAKFAST COST</div>
                    <div className="metric-val" style={{ color: '#dc2626' }}>₹{dailyStatement.dailyBreakfastExpense}</div>
                  </div>
                  <DollarSign size={28} color="#ef4444" />
                </div>

                <div className="glass-panel metric-card" style={{ padding: '1rem' }}>
                  <div>
                    <div className="metric-label">ADDITIONAL ORDERS COST</div>
                    <div className="metric-val" style={{ color: '#dc2626' }}>₹{dailyStatement.additionalOrderExpense}</div>
                  </div>
                  <MinusCircle size={28} color="#ef4444" />
                </div>

                <div className="glass-panel metric-card" style={{ padding: '1rem' }}>
                  <div>
                    <div className="metric-label">CLOSING BALANCE</div>
                    <div className="metric-val" style={{ color: '#2563eb' }}>₹{dailyStatement.closingBalance?.toLocaleString('en-IN')}</div>
                  </div>
                  <Wallet size={28} color="#2563eb" />
                </div>
              </div>

              <div className="panel-card" style={{ padding: '1.25rem' }}>
                <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Transactions for {dailyDate}</h3>
                <div className="table-container">
                  <table className="custom-table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Type</th>
                        <th>Purpose</th>
                        <th>Description</th>
                        <th>Amount</th>
                        <th>Balance After</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dailyStatement.transactions?.length === 0 ? (
                        <tr><td colSpan="6" style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>No transactions on this date.</td></tr>
                      ) : (
                        dailyStatement.transactions.map(t => (
                          <tr key={t._id}>
                            <td>{t.transactionTime}</td>
                            <td><span className="badge badge-info">{t.type}</span></td>
                            <td><span className="badge badge-secondary">{t.expensePurpose || 'EMPLOYEE'}</span></td>
                            <td>{t.description}</td>
                            <td><strong>₹{t.amount}</strong></td>
                            <td><strong>₹{t.balanceAfterTransaction}</strong></td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Monthly Money Statement */}
      {activeTab === 'monthly' && (
        <div>
          <div className="panel-card" style={{ padding: '1rem', marginBottom: '1.25rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Select Statement Month:</span>
            <input
              type="month"
              className="form-input"
              value={monthlyMonth}
              onChange={(e) => setMonthlyMonth(e.target.value)}
              style={{ width: '180px' }}
            />
          </div>

          {monthlyLoading ? (
            <div className="panel-card" style={{ padding: '2rem', textAlign: 'center' }}>Loading monthly statement...</div>
          ) : monthlyStatement && (
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FileSpreadsheet color="var(--accent-primary)" /> Monthly Financial Statement ({monthlyMonth})
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block' }}>OPENING BALANCE</span>
                  <strong style={{ fontSize: '1.3rem', color: 'var(--text-primary)' }}>₹{monthlyStatement.openingBalance?.toLocaleString('en-IN')}</strong>
                </div>

                <div style={{ padding: '1rem', background: '#f0fdf4', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.75rem', color: '#15803d', display: 'block' }}>TOTAL MONEY RECEIVED</span>
                  <strong style={{ fontSize: '1.3rem', color: '#16a34a' }}>+₹{monthlyStatement.totalReceived?.toLocaleString('en-IN')}</strong>
                </div>

                <div style={{ padding: '1rem', background: '#fef2f2', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.75rem', color: '#b91c1c', display: 'block' }}>DAILY BREAKFAST EXPENSES</span>
                  <strong style={{ fontSize: '1.3rem', color: '#dc2626' }}>-₹{monthlyStatement.dailyBreakfastExpenses?.toLocaleString('en-IN')}</strong>
                </div>

                <div style={{ padding: '1rem', background: '#fef2f2', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.75rem', color: '#b91c1c', display: 'block' }}>ADDITIONAL ORDERS EXPENSES</span>
                  <strong style={{ fontSize: '1.3rem', color: '#dc2626' }}>-₹{monthlyStatement.additionalOrderExpenses?.toLocaleString('en-IN')}</strong>
                </div>

                <div style={{ padding: '1rem', background: '#eff6ff', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.75rem', color: '#1e40af', display: 'block' }}>CLOSING BALANCE</span>
                  <strong style={{ fontSize: '1.3rem', color: '#2563eb' }}>₹{monthlyStatement.closingBalance?.toLocaleString('en-IN')}</strong>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* REQUEST MONEY MODAL */}
      {showRequestModal && (
        <Modal
          isOpen={showRequestModal}
          onClose={() => setShowRequestModal(false)}
          title="Request Breakfast Cash Replenishment"
        >
          <form onSubmit={handleRequestSubmit}>
            {modalError && (
              <div style={{ padding: '0.75rem', background: 'var(--danger-bg)', border: '1px solid #fca5a5', color: 'var(--danger-text)', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                <AlertCircle size={16} /> {modalError}
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', padding: '1rem', background: '#f8fafc', borderRadius: 'var(--radius-sm)', marginBottom: '1.25rem', textAlign: 'center' }}>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block' }}>Current Balance</span>
                <strong style={{ color: '#2563eb', fontSize: '1.1rem' }}>₹{currentBalance}</strong>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block' }}>Max Current Balance</span>
                <strong style={{ color: 'var(--text-primary)', fontSize: '1.1rem' }}>₹{fundLimit}</strong>
              </div>
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block' }}>Available to Request</span>
                <strong style={{ color: '#16a34a', fontSize: '1.1rem' }}>₹{recommendedRequest}</strong>
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label">Requested Amount (₹) *</label>
              <input
                type="number"
                min="1"
                max={recommendedRequest}
                className="form-input"
                value={requestForm.requestedAmount}
                onChange={(e) => setRequestForm({ ...requestForm, requestedAmount: e.target.value })}
                required
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'block' }}>
                Default = Maximum Current Balance (₹{fundLimit}) - Current Balance (₹{currentBalance}) = ₹{recommendedRequest}
              </span>
            </div>

            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label className="form-label">Reason / Note *</label>
              <textarea
                className="form-input"
                rows="3"
                value={requestForm.reason}
                onChange={(e) => setRequestForm({ ...requestForm, reason: e.target.value })}
                required
              ></textarea>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowRequestModal(false)}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={formSubmitting}>
                {formSubmitting ? 'Submitting...' : 'Submit Request'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* RECORD MANUAL EXPENSE MODAL */}
      {showExpenseModal && (
        <Modal
          isOpen={showExpenseModal}
          onClose={() => setShowExpenseModal(false)}
          title="Record Manual Breakfast Expense"
        >
          <form onSubmit={handleExpenseSubmit}>
            {modalError && (
              <div style={{ padding: '0.75rem', background: 'var(--danger-bg)', border: '1px solid #fca5a5', color: 'var(--danger-text)', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                <AlertCircle size={16} /> {modalError}
              </div>
            )}

            <div className="form-grid-2" style={{ marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Expense Date *</label>
                <input
                  type="date"
                  className="form-input"
                  value={expenseForm.transactionDate}
                  onChange={(e) => setExpenseForm({ ...expenseForm, transactionDate: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Expense Time *</label>
                <input
                  type="text"
                  className="form-input"
                  value={expenseForm.transactionTime}
                  onChange={(e) => setExpenseForm({ ...expenseForm, transactionTime: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="form-grid-2" style={{ marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Amount (₹) *</label>
                <input
                  type="number"
                  min="1"
                  className="form-input"
                  placeholder="e.g. 150"
                  value={expenseForm.amount}
                  onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Expense Purpose *</label>
                <select
                  className="form-select"
                  value={expenseForm.expensePurpose}
                  onChange={(e) => setExpenseForm({ ...expenseForm, expensePurpose: e.target.value })}
                >
                  <option value="EMPLOYEE">EMPLOYEE</option>
                  <option value="CLIENT">CLIENT</option>
                  <option value="OTHER">OTHER</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label className="form-label">Description *</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Snacks for client meeting"
                value={expenseForm.description}
                onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
                required
              />
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <label className="form-label">Reference / Note</label>
              <input
                type="text"
                className="form-input"
                placeholder="Optional reference"
                value={expenseForm.note}
                onChange={(e) => setExpenseForm({ ...expenseForm, note: e.target.value })}
              />
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowExpenseModal(false)}>Cancel</button>
              <button type="submit" className="btn btn-danger" disabled={formSubmitting}>
                {formSubmitting ? 'Recording...' : 'Record Expense'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* VERIFY RECEIPT MODAL */}
      {showVerifyModal && activeRequest && (
        <Modal
          isOpen={showVerifyModal}
          onClose={() => setShowVerifyModal(false)}
          title={`Confirm Money Received (${activeRequest.requestId})`}
        >
          <form onSubmit={handleVerifySubmit}>
            {modalError && (
              <div style={{ padding: '0.75rem', background: 'var(--danger-bg)', border: '1px solid #fca5a5', color: 'var(--danger-text)', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                <AlertCircle size={16} /> {modalError}
              </div>
            )}

            <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: 'var(--radius-sm)', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>Approved: <strong>₹{activeRequest.approvedAmount || activeRequest.requestedAmount}</strong></div>
                <div>Provided: <strong>₹{activeRequest.providedAmount}</strong></div>
                <div>Current Balance: <strong>₹{currentBalance}</strong></div>
                <div>Expected Balance: <strong style={{ color: '#16a34a' }}>₹{currentBalance + Number(verifyForm.verifiedAmount || activeRequest.providedAmount)}</strong></div>
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label className="form-label">Actual Amount Received (₹) *</label>
              <input
                type="number"
                min="1"
                className="form-input"
                value={verifyForm.verifiedAmount}
                onChange={(e) => setVerifyForm({ ...verifyForm, verifiedAmount: e.target.value })}
                required
              />
            </div>

            {showDifferenceModal || (Number(verifyForm.verifiedAmount) !== (activeRequest.providedAmount || 0)) ? (
              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label className="form-label" style={{ color: '#d97706' }}>Difference / Discrepancy Note *</label>
                <textarea
                  className="form-input"
                  rows="2"
                  placeholder="Explain difference between provided amount and received amount..."
                  value={verifyForm.differenceNote}
                  onChange={(e) => setVerifyForm({ ...verifyForm, differenceNote: e.target.value })}
                  required
                ></textarea>
              </div>
            ) : null}

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-secondary" onClick={() => setShowVerifyModal(false)}>Cancel</button>
              <button type="submit" className="btn btn-success" disabled={formSubmitting}>
                {formSubmitting ? 'Confirming...' : 'Confirm Receipt & Update Balance'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};

export default BreakfastMoneyPage;
