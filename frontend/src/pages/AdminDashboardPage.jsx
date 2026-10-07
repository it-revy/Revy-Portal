import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import API from '../services/api';
import {
  Users,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  Coffee,
  Wallet,
  AlertCircle,
  RefreshCw,
  ShoppingBag,
  DollarSign
} from 'lucide-react';

const AdminDashboardPage = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [recordsData, setRecordsData] = useState({ takingList: [], notTakingList: [], noResponseList: [], permanentNotTakingList: [] });
  const [moneyMetrics, setMoneyMetrics] = useState(null);
  const [dailyCost, setDailyCost] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().substring(0, 10));
  const [departmentFilter, setDepartmentFilter] = useState('ALL');
  const [activeTab, setActiveTab] = useState('TAKING');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchDashboardData();
  }, [selectedDate, departmentFilter]);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, recRes] = await Promise.all([
        API.get(`/breakfast/admin/summary?date=${selectedDate}`),
        API.get(`/breakfast/admin/records?date=${selectedDate}&department=${departmentFilter}&search=${searchTerm}`)
      ]);

      if (sumRes.data.success) {
        setSummary(sumRes.data);
        if (sumRes.data.metrics?.todayBreakfastCost !== undefined) {
          setDailyCost(sumRes.data.metrics.todayBreakfastCost);
        }
      } else {
        throw new Error(sumRes.data.message || 'Failed to fetch summary');
      }

      if (recRes.data.success) {
        setRecordsData(recRes.data);
      }

      // Fetch money balance metrics if permitted
      try {
        const moneyRes = await API.get('/breakfast/money/balance');
        if (moneyRes.data.success) {
          setMoneyMetrics(moneyRes.data.metrics);
        }
      } catch (mErr) {
        // Non-fatal if user doesn't have money permission
      }

      // Fetch daily cost from authoritative orders if available
      try {
        const ordersRes = await API.get(`/breakfast/orders?startDate=${selectedDate}&endDate=${selectedDate}&limit=ALL`);
        if (ordersRes.data.success && ordersRes.data.summary) {
          const cost = ordersRes.data.summary.totalAmount ?? ordersRes.data.summary.grandTotal;
          if (cost !== undefined) {
            setDailyCost(cost);
          }
        } else {
          const fallbackRes = await API.get(`/orders?date=${selectedDate}`);
          if (fallbackRes.data.success && fallbackRes.data.summary) {
            setDailyCost(fallbackRes.data.summary.grandTotal || 0);
          }
        }
      } catch (oErr) {
        try {
          const fallbackRes = await API.get(`/orders?date=${selectedDate}`);
          if (fallbackRes.data.success && fallbackRes.data.summary) {
            setDailyCost(fallbackRes.data.summary.grandTotal || 0);
          }
        } catch (fErr) {
          // Non-fatal, dailyCost was already set from sumRes.data.metrics.todayBreakfastCost
        }
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError(err.response?.data?.message || err.message || 'Unable to load dashboard data. Please check connection.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchDashboardData();
  };

  // State 1: Loading
  if (loading) {
    return (
      <div className="page-body">
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
          <RefreshCw size={32} color="var(--accent-primary)" style={{ animation: 'spin 1s linear infinite' }} />
          <h3 style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Loading dashboard...</h3>
        </div>
      </div>
    );
  }

  // State 2: Error with Retry button
  if (error) {
    return (
      <div className="page-body">
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
          <AlertCircle size={40} color="var(--danger)" style={{ marginBottom: '1rem' }} />
          <h2 style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>Unable to load dashboard data</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>{error}</p>
          <button className="btn btn-primary" onClick={fetchDashboardData}>
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  // State 3: Empty check
  if (!summary) {
    return (
      <div className="page-body">
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
          <Coffee size={40} color="var(--text-muted)" style={{ marginBottom: '1rem' }} />
          <h3>No dashboard data available</h3>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            No records or summary found for {selectedDate}.
          </p>
          <button className="btn btn-secondary" style={{ marginTop: '1rem' }} onClick={fetchDashboardData}>
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>
    );
  }

  const metrics = summary?.metrics || {};

  return (
    <div className="page-body">
      {/* Header & Date/Department Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.4rem' }}>
            <Coffee color="var(--accent-primary)" /> Breakfast Operations Dashboard
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.2rem', fontSize: '0.85rem' }}>
            Authoritative headcount, daily participation & financial operational dashboard
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap', width: 'auto' }}>
          <input
            type="date"
            className="form-input"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            style={{ width: 'auto', minWidth: '140px', flex: '1 1 auto', padding: '0.45rem 0.75rem' }}
          />
          <select
            className="form-select"
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            style={{ width: 'auto', minWidth: '160px', flex: '1 1 auto', padding: '0.45rem 0.75rem' }}
          >
            <option value="ALL">All Departments</option>
            <option value="IT Infrastructure">IT Infrastructure</option>
            <option value="Administration">Administration</option>
            <option value="Engineering">Engineering</option>
            <option value="Research & Development">Research & Development</option>
            <option value="Executive Office">Executive Office</option>
          </select>
        </div>
      </div>

      {/* Low Balance Alert Banner (< ₹100) */}
      {moneyMetrics && moneyMetrics.currentBalance < 100 && (
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
          <div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#991b1b' }}>LOW BREAKFAST BALANCE</div>
            <div style={{ fontSize: '0.85rem', color: '#7f1d1d', marginTop: '0.2rem' }}>
              Current Balance: <strong>₹{moneyMetrics.currentBalance}</strong> | Maximum Current Balance: <strong>₹2,500</strong> | Suggested Request: <strong>₹{2500 - moneyMetrics.currentBalance}</strong>
            </div>
          </div>
          <button className="btn btn-primary" onClick={() => navigate('/admin/breakfast-money')} style={{ background: '#dc2626', borderColor: '#b91c1c' }}>
            Request Money
          </button>
        </div>
      )}

      {/* THREE PRIMARY QUICK ACTIONS */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: '1.25rem', marginBottom: '1.75rem' }}>
        <div
          className="panel-card"
          style={{
            padding: '1.25rem',
            background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
            color: 'white',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            border: '1px solid rgba(255,255,255,0.1)'
          }}
          onClick={() => navigate('/admin/daily-entry')}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8', fontWeight: 600 }}>
              PRIMARY WORKSTATION
            </span>
            <span className="badge badge-primary" style={{ background: '#2563eb' }}>Daily Entry</span>
          </div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'white', marginBottom: '0.35rem' }}>
            Daily Entry
          </h2>
          <p style={{ fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '0.85rem' }}>
            Manage daily breakfast planning & employee request status.
          </p>
          <button className="btn btn-primary" style={{ width: '100%', background: '#2563eb', padding: '0.5rem' }}>
            Open Daily Entry →
          </button>
        </div>

        <div
          className="panel-card"
          style={{
            padding: '1.25rem',
            background: 'linear-gradient(135deg, #1e1b4b 0%, #311b92 100%)',
            color: 'white',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            border: '1px solid rgba(255,255,255,0.1)'
          }}
          onClick={() => navigate('/admin/additional-orders')}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#c7d2fe', fontWeight: 600 }}>
              EXTRA PURCHASES
            </span>
            <span className="badge badge-info" style={{ background: '#6366f1' }}>Additional Orders</span>
          </div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'white', marginBottom: '0.35rem' }}>
            Additional Orders
          </h2>
          <p style={{ fontSize: '0.8rem', color: '#e0e7ff', marginBottom: '0.85rem' }}>
            Record extra snack/tea orders for today's business date.
          </p>
          <button className="btn btn-primary" style={{ width: '100%', background: '#4f46e5', padding: '0.5rem' }}>
            Open Additional Orders →
          </button>
        </div>

        <div
          className="panel-card"
          style={{
            padding: '1.25rem',
            background: 'linear-gradient(135deg, #064e3b 0%, #047857 100%)',
            color: 'white',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            border: '1px solid rgba(255,255,255,0.1)'
          }}
          onClick={() => navigate('/admin/breakfast-money')}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#a7f3d0', fontWeight: 600 }}>
              CASH LEDGER
            </span>
            <span className="badge badge-success" style={{ background: '#059669' }}>Fund Balance</span>
          </div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'white', marginBottom: '0.35rem' }}>
            Breakfast Money
          </h2>
          <p style={{ fontSize: '0.8rem', color: '#ecfdf5', marginBottom: '0.85rem' }}>
            Manage money received from Finance and cash balance ledger.
          </p>
          <button className="btn btn-success" style={{ width: '100%', background: '#059669', padding: '0.5rem' }}>
            Open Money Workstation →
          </button>
        </div>
      </div>

      {/* METRICS CARDS GRID */}
      <div className="grid-metrics" style={{ marginBottom: '1.75rem' }}>
        <div className="glass-panel metric-card" style={{ padding: '1.15rem' }}>
          <div>
            <div className="metric-label">APPLICABLE EMPLOYEES</div>
            <div className="metric-val">{metrics.totalActive || 0}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Normal: {metrics.normalEmployeesCount || 0} | Perm: {metrics.permanentNotTakingCount || 0}
            </span>
          </div>
          <Users size={32} color="var(--accent-primary)" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1.15rem', borderLeft: '4px solid var(--success)' }}>
          <div>
            <div className="metric-label">CONFIRMED TAKING</div>
            <div className="metric-val" style={{ color: 'var(--success)' }}>{metrics.takingBreakfastCount || 0}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Expected Headcount Today</span>
          </div>
          <CheckCircle2 size={32} color="var(--success)" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1.15rem', borderLeft: '4px solid var(--danger)' }}>
          <div>
            <div className="metric-label">NOT TAKING TODAY</div>
            <div className="metric-val" style={{ color: 'var(--danger)' }}>{metrics.notTakingBreakfastCount || 0}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Opted out with reason</span>
          </div>
          <XCircle size={32} color="var(--danger)" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1.15rem', borderLeft: '4px solid var(--warning)' }}>
          <div>
            <div className="metric-label">PENDING RESPONSE</div>
            <div className="metric-val" style={{ color: 'var(--warning)' }}>{metrics.pendingCount || 0}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Normal employees pending</span>
          </div>
          <Clock size={32} color="var(--warning)" opacity={0.8} />
        </div>

        {moneyMetrics && (
          <div className="glass-panel metric-card" style={{ padding: '1.15rem', borderLeft: '4px solid #3b82f6' }}>
            <div>
              <div className="metric-label">CURRENT BREAKFAST BALANCE</div>
              <div className="metric-val" style={{ color: '#2563eb' }}>
                ₹{moneyMetrics.currentBalance ? moneyMetrics.currentBalance.toLocaleString('en-IN') : 0}
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Max Current Balance: ₹2,500</span>
            </div>
            <Wallet size={32} color="#2563eb" opacity={0.8} />
          </div>
        )}

        <div className="glass-panel metric-card" style={{ padding: '1.15rem', borderLeft: '4px solid #8b5cf6' }}>
          <div>
            <div className="metric-label">TODAY'S BREAKFAST COST</div>
            <div className="metric-val" style={{ color: '#7c3aed' }}>₹{dailyCost.toLocaleString('en-IN')}</div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Date: {selectedDate}</span>
          </div>
          <DollarSign size={32} color="#7c3aed" opacity={0.8} />
        </div>
      </div>

      {/* Tabs & Table */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div className="tabs-scroll">
            <button
              className={`btn ${activeTab === 'TAKING' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('TAKING')}
              style={{ fontSize: '0.82rem' }}
            >
              Taking ({(recordsData?.takingList || []).length})
            </button>
            <button
              className={`btn ${activeTab === 'NOT_TAKING' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('NOT_TAKING')}
              style={{ fontSize: '0.82rem' }}
            >
              Not Taking ({(recordsData?.notTakingList || []).length})
            </button>
            <button
              className={`btn ${activeTab === 'NO_RESPONSE' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('NO_RESPONSE')}
              style={{ fontSize: '0.82rem' }}
            >
              No Response ({(recordsData?.noResponseList || []).length})
            </button>
            <button
              className={`btn ${activeTab === 'PERMANENT' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('PERMANENT')}
              style={{ fontSize: '0.82rem' }}
            >
              Permanent Non-Takers ({(recordsData?.permanentNotTakingList || []).length})
            </button>
          </div>

          <form onSubmit={handleSearch} style={{ display: 'flex', gap: '0.5rem', flex: '1 1 200px', maxWidth: '340px' }}>
            <input
              type="text"
              className="form-input"
              placeholder="Search employee name or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ flex: 1, padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}
            />
            <button type="submit" className="btn btn-secondary" style={{ padding: '0.4rem 0.75rem' }}>
              <Search size={15} />
            </button>
          </form>
        </div>

        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Employee ID</th>
                <th>Name</th>
                <th>Department</th>
                <th>Designation</th>
                <th>Response Status</th>
                <th>Reason / Description</th>
              </tr>
            </thead>
            <tbody>
              {getCurrentList(activeTab, recordsData).length === 0 ? (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2.5rem' }}>
                    No employee records found in this category for {selectedDate}.
                  </td>
                </tr>
              ) : (
                getCurrentList(activeTab, recordsData).map(emp => (
                  <tr key={emp.employeeId}>
                    <td><strong style={{ color: 'var(--text-primary)' }}>{emp.employeeId}</strong></td>
                    <td>{emp.name}</td>
                    <td>{emp.department}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{emp.designation}</td>
                    <td>
                      <span className={`badge ${
                        emp.status === 'TAKING' ? 'badge-success' :
                        emp.status === 'NOT_TAKING' ? 'badge-danger' :
                        emp.status === 'PERMANENT_NOT_TAKING' ? 'badge-info' : 'badge-warning'
                      }`}>
                        {emp.status}
                      </span>
                    </td>
                    <td>{emp.reasonText || emp.reasonCode || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const getCurrentList = (tab, data) => {
  if (!data) return [];
  switch (tab) {
    case 'TAKING': return data.takingList || [];
    case 'NOT_TAKING': return data.notTakingList || [];
    case 'NO_RESPONSE': return data.noResponseList || [];
    case 'PERMANENT': return data.permanentNotTakingList || [];
    default: return data.takingList || [];
  }
};

export default AdminDashboardPage;
