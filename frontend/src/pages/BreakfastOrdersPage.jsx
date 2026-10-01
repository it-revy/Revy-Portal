import React, { useState, useEffect } from 'react';
import API from '../services/api';
import Modal from '../components/Modal';
import HistoricalRecordEditModal from '../components/HistoricalRecordEditModal';
import {
  FileText,
  Search,
  Calendar,
  Filter,
  RefreshCw,
  ShoppingBag,
  Coffee,
  Eye,
  CheckCircle2,
  Clock,
  User,
  Users,
  DollarSign,
  ChevronLeft,
  ChevronRight,
  Receipt,
  X,
  Layers,
  Edit2
} from 'lucide-react';

const BreakfastOrdersPage = () => {
  const [orders, setOrders] = useState([]);
  const [summary, setSummary] = useState({ totalOrders: 0, totalAmount: 0, dailyCount: 0, additionalCount: 0 });
  const [pagination, setPagination] = useState({ total: 0, page: 1, limit: 20, totalPages: 1 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Historical Record Edit State
  const [editingHistoricalRecord, setEditingHistoricalRecord] = useState(null);
  const [showHistoricalEditModal, setShowHistoricalEditModal] = useState(false);

  // Filter States
  const [searchTerm, setSearchTerm] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [orderTypeFilter, setOrderTypeFilter] = useState('ALL');
  const [createdByFilter, setCreatedByFilter] = useState('ALL');
  const [minAmount, setMinAmount] = useState('');
  const [maxAmount, setMaxAmount] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  // Selected Order for Details Modal
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  useEffect(() => {
    fetchOrders();
  }, [currentPage, orderTypeFilter]);

  const fetchOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      let queryParams = new URLSearchParams();
      queryParams.append('page', currentPage);
      queryParams.append('limit', 20);
      
      if (orderTypeFilter !== 'ALL') queryParams.append('type', orderTypeFilter);
      if (startDate) queryParams.append('startDate', startDate);
      if (endDate) queryParams.append('endDate', endDate);
      if (searchTerm.trim()) queryParams.append('search', searchTerm.trim());
      if (createdByFilter !== 'ALL') queryParams.append('createdBy', createdByFilter);
      if (minAmount) queryParams.append('minAmount', minAmount);
      if (maxAmount) queryParams.append('maxAmount', maxAmount);

      const res = await API.get(`/breakfast/orders?${queryParams.toString()}`);
      if (res.data.success) {
        setOrders(res.data.orders || []);
        if (res.data.summary) setSummary(res.data.summary);
        if (res.data.pagination) setPagination(res.data.pagination);
      } else {
        throw new Error(res.data.message || 'Failed to fetch orders');
      }
    } catch (err) {
      console.error('Failed to fetch orders:', err);
      setError(err.response?.data?.message || err.message || 'Failed to load breakfast orders.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setCurrentPage(1);
    fetchOrders();
  };

  const handleResetFilters = () => {
    setSearchTerm('');
    setStartDate('');
    setEndDate('');
    setOrderTypeFilter('ALL');
    setCreatedByFilter('ALL');
    setMinAmount('');
    setMaxAmount('');
    setCurrentPage(1);
    setTimeout(() => {
      fetchOrders();
    }, 0);
  };

  const handleOpenDetails = (order) => {
    setSelectedOrder(order);
    setShowDetailsModal(true);
  };

  const formatDateDisplay = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className="page-body">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.4rem', margin: 0 }}>
            <FileText color="var(--accent-primary)" size={28} /> All Breakfast Orders & Entries
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem', fontSize: '0.85rem' }}>
            Unified administrative view combining Daily Breakfast Entries & Additional Breakfast Orders
          </p>
        </div>

        <button className="btn btn-secondary" onClick={fetchOrders} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <RefreshCw size={16} /> Refresh Orders
        </button>
      </div>

      {/* Summary Metrics Banner */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
        <div className="glass-panel metric-card" style={{ padding: '1.15rem', borderLeft: '5px solid #2563eb' }}>
          <div>
            <div className="metric-label">TOTAL ALL ORDERS</div>
            <div className="metric-val" style={{ color: '#2563eb', fontSize: '1.75rem', fontWeight: 800 }}>
              {summary.totalOrders || 0}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Unified Database Count</span>
          </div>
          <Layers size={34} color="#2563eb" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1.15rem', borderLeft: '5px solid #16a34a' }}>
          <div>
            <div className="metric-label">TOTAL ORDERS AMOUNT</div>
            <div className="metric-val" style={{ color: '#16a34a', fontSize: '1.75rem', fontWeight: 800 }}>
              ₹{(summary.totalAmount || 0).toLocaleString('en-IN')}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Sum of All Recorded Expenses</span>
          </div>
          <DollarSign size={34} color="#16a34a" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1.15rem', borderLeft: '5px solid #0284c7' }}>
          <div>
            <div className="metric-label">DAILY BREAKFAST ENTRIES</div>
            <div className="metric-val" style={{ color: '#0284c7', fontSize: '1.75rem', fontWeight: 800 }}>
              {summary.dailyCount || 0}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Primary Daily Headcount Entries</span>
          </div>
          <Coffee size={34} color="#0284c7" opacity={0.8} />
        </div>

        <div className="glass-panel metric-card" style={{ padding: '1.15rem', borderLeft: '5px solid #8b5cf6' }}>
          <div>
            <div className="metric-label">ADDITIONAL ORDERS</div>
            <div className="metric-val" style={{ color: '#8b5cf6', fontSize: '1.75rem', fontWeight: 800 }}>
              {summary.additionalCount || 0}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Extra Tea, Snacks & Client Orders</span>
          </div>
          <ShoppingBag size={34} color="#8b5cf6" opacity={0.8} />
        </div>
      </div>

      {/* Unified Filters Toolbar */}
      <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1.5rem' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', alignItems: 'end' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.75rem', fontWeight: 600 }}>Search Order</label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="form-input"
                placeholder="ID, Title, Item, Creator..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ paddingLeft: '2.2rem' }}
              />
              <Search size={16} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            </div>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.75rem', fontWeight: 600 }}>Order Type</label>
            <select className="form-select" value={orderTypeFilter} onChange={(e) => setOrderTypeFilter(e.target.value)}>
              <option value="ALL">All Order Types</option>
              <option value="DAILY_ENTRY">Daily Breakfast</option>
              <option value="ADDITIONAL_ORDER">Additional Order</option>
              <option value="HISTORICAL">Historical Breakfast</option>
            </select>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.75rem', fontWeight: 600 }}>Date From</label>
            <input
              type="date"
              className="form-input"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.75rem', fontWeight: 600 }}>Date To</label>
            <input
              type="date"
              className="form-input"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: '0.75rem', fontWeight: 600 }}>Min Amount (₹)</label>
            <input
              type="number"
              className="form-input"
              placeholder="0"
              value={minAmount}
              onChange={(e) => setMinAmount(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', gridColumn: 'span 1' }}>
            <button type="submit" className="btn btn-primary" style={{ flex: 1, height: '38px', padding: '0 1rem' }}>
              <Search size={16} /> Search
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleResetFilters} style={{ height: '38px', padding: '0 0.85rem' }} title="Reset Filters">
              Reset
            </button>
          </div>
        </form>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
          <RefreshCw size={32} color="var(--accent-primary)" style={{ animation: 'spin 1s linear infinite' }} />
          <h3 style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Loading order list...</h3>
        </div>
      ) : error ? (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
          <h2 style={{ color: 'var(--danger)', marginBottom: '0.5rem' }}>Failed to load orders</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>{error}</p>
          <button className="btn btn-primary" onClick={fetchOrders}>
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      ) : orders.length === 0 ? (
        <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
          <FileText size={44} color="var(--text-muted)" style={{ marginBottom: '1rem' }} />
          <h3>No Orders Found</h3>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            No breakfast daily entries or additional orders match your active filter criteria.
          </p>
          <button className="btn btn-secondary" style={{ marginTop: '1rem' }} onClick={handleResetFilters}>
            Reset All Filters
          </button>
        </div>
      ) : (
        <>
          {/* DESKTOP TABLE VIEW (Visible on tablet & desktop) */}
          <div className="glass-panel desktop-only" style={{ padding: '1.5rem', marginBottom: '1.5rem' }}>
            <div className="table-container">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Order ID</th>
                    <th>Business Date</th>
                    <th>Order Type</th>
                    <th>Order Title</th>
                    <th>Time</th>
                    <th>Applicable Employees</th>
                    <th>Items Breakdown</th>
                    <th>Total Cost</th>
                    <th>Created By</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map(order => {
                    const totalItems = (order.breakfastItems?.length || 0) + (order.commonItems?.length || 0);
                    return (
                      <tr key={order._id}>
                        <td>
                          <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', fontWeight: 700, color: 'var(--accent-primary)' }}>
                            {order.orderId}
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}>
                            <Calendar size={14} color="var(--text-muted)" />
                            {formatDateDisplay(order.businessDate)}
                          </div>
                        </td>
                        <td>
                          <span className={`badge ${
                            order.orderType === 'HISTORICAL' ? 'badge-historical' :
                            order.orderType === 'DAILY_ENTRY' ? 'badge-info' : 'badge-role'
                          }`} style={order.orderType === 'HISTORICAL' ? { fontSize: '0.7rem' } : {
                            background: order.orderType === 'DAILY_ENTRY' ? '#e0f2fe' : '#f3e8ff',
                            color: order.orderType === 'DAILY_ENTRY' ? '#0369a1' : '#6b21a8',
                            borderColor: order.orderType === 'DAILY_ENTRY' ? '#bae6fd' : '#e9d5ff',
                            fontWeight: 700,
                            fontSize: '0.7rem'
                          }}>
                            {order.orderTypeLabel}
                          </span>
                        </td>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{order.orderTitle}</div>
                        </td>
                        <td>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{order.orderTime || '12:00'}</span>
                        </td>
                        <td>
                          {order.orderType === 'HISTORICAL' ? (
                            <span style={{ fontSize: '0.8rem', color: '#7c3aed', fontWeight: 600 }}>
                              Not Recorded
                            </span>
                          ) : (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem' }}>
                              <Users size={14} color="var(--text-muted)" />
                              <span>{order.applicableEmployeeCount || 0} employees</span>
                            </div>
                          )}
                        </td>
                        <td>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            {totalItems} item{totalItems !== 1 ? 's' : ''} ({order.breakfastItems?.length || 0} breakfast, {order.commonItems?.length || 0} common)
                          </span>
                        </td>
                        <td>
                          <strong style={{ fontSize: '1rem', color: '#16a34a' }}>
                            ₹{order.totalCost.toLocaleString('en-IN')}
                          </strong>
                        </td>
                        <td>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{order.createdBy}</span>
                        </td>
                        <td>
                          <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                            <CheckCircle2 size={12} /> {order.status}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.35rem' }}>
                            <button
                              className="btn btn-secondary"
                              onClick={() => handleOpenDetails(order)}
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem' }}
                            >
                              <Eye size={13} /> View
                            </button>
                            {order.isHistorical && (
                              <button
                                className="btn btn-secondary"
                                onClick={() => {
                                  setEditingHistoricalRecord(order);
                                  setShowHistoricalEditModal(true);
                                }}
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem', color: '#7c3aed', borderColor: '#d8b4fe' }}
                                title="Edit Historical Record"
                              >
                                <Edit2 size={13} /> Edit
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* MOBILE CARDS VIEW (Visible on mobile screens) */}
          <div className="mobile-only mobile-card-list" style={{ marginBottom: '1.5rem' }}>
            {orders.map(order => (
              <div key={order._id} className="glass-panel" style={{
                padding: '1.25rem',
                borderLeft: `5px solid ${order.orderType === 'HISTORICAL' ? '#7c3aed' : order.orderType === 'DAILY_ENTRY' ? '#0284c7' : '#8b5cf6'}`
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', fontWeight: 700, color: 'var(--accent-primary)' }}>{order.orderId}</span>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: '0.2rem 0' }}>{order.orderTitle}</h3>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Date: {formatDateDisplay(order.businessDate)}</div>
                  </div>
                  <span className={`badge ${
                    order.orderType === 'HISTORICAL' ? 'badge-historical' :
                    order.orderType === 'DAILY_ENTRY' ? 'badge-info' : 'badge-role'
                  }`} style={{ fontSize: '0.7rem' }}>
                    {order.orderTypeLabel}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', background: '#f8fafc', padding: '0.75rem', borderRadius: 'var(--radius-sm)', marginBottom: '0.85rem', fontSize: '0.8rem' }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Total Cost</span>
                    <strong style={{ color: '#16a34a', fontSize: '1.1rem' }}>₹{order.totalCost.toLocaleString('en-IN')}</strong>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Employees</span>
                    <strong>{order.orderType === 'HISTORICAL' ? 'Not Recorded' : `${order.applicableEmployeeCount} Persons`}</strong>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>By: {order.createdBy}</span>
                  <div style={{ display: 'flex', gap: '0.35rem' }}>
                    <button className="btn btn-secondary" onClick={() => handleOpenDetails(order)} style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}>
                      <Eye size={14} /> View
                    </button>
                    {order.isHistorical && (
                      <button
                        className="btn btn-secondary"
                        onClick={() => {
                          setEditingHistoricalRecord(order);
                          setShowHistoricalEditModal(true);
                        }}
                        style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem', color: '#7c3aed', borderColor: '#d8b4fe' }}
                      >
                        <Edit2 size={13} /> Edit
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination Controls */}
          {pagination.totalPages > 1 && (
            <div className="glass-panel" style={{ padding: '0.85rem 1.25rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Showing page <strong>{pagination.page}</strong> of <strong>{pagination.totalPages}</strong> (Total <strong>{pagination.total}</strong> orders)
              </span>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  className="btn btn-secondary"
                  disabled={currentPage <= 1}
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  style={{ padding: '0.4rem 0.75rem' }}
                >
                  <ChevronLeft size={16} /> Previous
                </button>
                <button
                  className="btn btn-secondary"
                  disabled={currentPage >= pagination.totalPages}
                  onClick={() => setCurrentPage(prev => Math.min(pagination.totalPages, prev + 1))}
                  style={{ padding: '0.4rem 0.75rem' }}
                >
                  Next <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ORDER DETAILS MODAL / DRAWER */}
      {showDetailsModal && selectedOrder && (
        <Modal
          isOpen={showDetailsModal}
          onClose={() => setShowDetailsModal(false)}
          title={`Order Details — ${selectedOrder.orderId}`}
        >
          <div style={{ padding: '0.25rem' }}>
            {/* Header info card */}
            <div style={{
              background: selectedOrder.orderType === 'HISTORICAL' ? '#faf5ff' : selectedOrder.orderType === 'DAILY_ENTRY' ? '#f0f9ff' : '#faf5ff',
              border: `1px solid ${selectedOrder.orderType === 'HISTORICAL' ? '#d8b4fe' : selectedOrder.orderType === 'DAILY_ENTRY' ? '#bae6fd' : '#e9d5ff'}`,
              borderRadius: 'var(--radius-sm)',
              padding: '1.25rem',
              marginBottom: '1.25rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <span style={{ fontSize: '0.8rem', fontFamily: 'monospace', fontWeight: 800, color: 'var(--accent-primary)' }}>{selectedOrder.orderId}</span>
                    <span className={`badge ${
                      selectedOrder.orderType === 'HISTORICAL' ? 'badge-historical' :
                      selectedOrder.orderType === 'DAILY_ENTRY' ? 'badge-info' : 'badge-role'
                    }`}>
                      {selectedOrder.orderTypeLabel}
                    </span>
                  </div>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: '0.25rem 0' }}>{selectedOrder.orderTitle}</h2>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '0.35rem' }}>
                    <span>📅 Date: <strong>{formatDateDisplay(selectedOrder.businessDate)}</strong></span>
                    <span>⏰ Time: <strong>{selectedOrder.orderTime || '12:00'}</strong></span>
                    <span>👥 {selectedOrder.orderType === 'HISTORICAL' ? <strong style={{ color: '#7c3aed' }}>Employee: Not Recorded</strong> : <>Applicable: <strong>{selectedOrder.applicableEmployeeCount} Employees</strong></>}</span>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>TOTAL ORDER COST</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#16a34a' }}>
                    ₹{selectedOrder.totalCost.toLocaleString('en-IN')}
                  </div>
                </div>
              </div>
            </div>

            {selectedOrder.isHistorical && (
              <div style={{ background: '#f5f3ff', border: '1px solid #ddd6fe', borderRadius: 'var(--radius-sm)', padding: '0.85rem 1rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                  <div>Paid By: <strong style={{ color: 'var(--text-primary)' }}>{selectedOrder.paidBy || 'Not Specified'}</strong></div>
                  <div>Payment Type: <strong style={{ color: 'var(--text-primary)' }}>{selectedOrder.paymentType || 'Not Specified'}</strong></div>
                  {selectedOrder.sourceId && <div>Source ID: <strong style={{ color: '#7c3aed', fontFamily: 'monospace' }}>{selectedOrder.sourceId}</strong></div>}
                </div>
              </div>
            )}

            {/* Breakfast Items Breakdown */}
            <div style={{ marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Coffee size={18} color="var(--accent-primary)" /> Breakfast Per-Head Items ({selectedOrder.breakfastItems?.length || 0})
              </h3>
              {selectedOrder.breakfastItems && selectedOrder.breakfastItems.length > 0 ? (
                <div className="table-container">
                  <table className="custom-table" style={{ fontSize: '0.85rem' }}>
                    <thead>
                      <tr>
                        <th>Item Name</th>
                        <th>Unit Price</th>
                        <th>Quantity</th>
                        <th style={{ textAlign: 'right' }}>Total Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedOrder.breakfastItems.map((item, idx) => (
                        <tr key={idx}>
                          <td><strong>{item.name}</strong></td>
                          <td>₹{item.unitPrice}</td>
                          <td>{item.quantity}</td>
                          <td style={{ textAlign: 'right', fontWeight: 700, color: '#16a34a' }}>₹{item.total}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  No per-head breakfast items recorded.
                </div>
              )}
            </div>

            {/* Common Items Breakdown */}
            <div style={{ marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShoppingBag size={18} color="#8b5cf6" /> Shared / Common Group Items ({selectedOrder.commonItems?.length || 0})
              </h3>
              {selectedOrder.commonItems && selectedOrder.commonItems.length > 0 ? (
                <div className="table-container">
                  <table className="custom-table" style={{ fontSize: '0.85rem' }}>
                    <thead>
                      <tr>
                        <th>Item Name</th>
                        <th>Unit Price</th>
                        <th>Quantity</th>
                        <th style={{ textAlign: 'right' }}>Total Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedOrder.commonItems.map((item, idx) => (
                        <tr key={idx}>
                          <td><strong>{item.name}</strong></td>
                          <td>₹{item.unitPrice}</td>
                          <td>{item.quantity}</td>
                          <td style={{ textAlign: 'right', fontWeight: 700, color: '#16a34a' }}>₹{item.total}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  No common/shared items recorded.
                </div>
              )}
            </div>

            {/* Financial Reference & Audit Metadata */}
            <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 'var(--radius-sm)', padding: '1rem', fontSize: '0.85rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem' }}>Created By</span>
                  <strong>{selectedOrder.createdBy}</strong>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem' }}>Created At</span>
                  <span>{new Date(selectedOrder.createdAt).toLocaleString('en-IN')}</span>
                </div>
                {selectedOrder.updatedBy && (
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem' }}>Updated By</span>
                    <span>{selectedOrder.updatedBy}</span>
                  </div>
                )}
                <div>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem' }}>Money Ledger Reference</span>
                  <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#2563eb' }}>
                    {selectedOrder.financialReference?.referenceType} : {selectedOrder.financialReference?.referenceId}
                  </span>
                </div>
              </div>
            </div>

            <div style={{ marginTop: '1.25rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              {selectedOrder.isHistorical && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setEditingHistoricalRecord(selectedOrder);
                    setShowHistoricalEditModal(true);
                  }}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#7c3aed', borderColor: '#d8b4fe' }}
                >
                  <Edit2 size={14} /> Edit Historical Record
                </button>
              )}
              <button className="btn btn-primary" onClick={() => setShowDetailsModal(false)}>
                Close Details
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* HISTORICAL RECORD EDIT MODAL */}
      {showHistoricalEditModal && editingHistoricalRecord && (
        <HistoricalRecordEditModal
          isOpen={showHistoricalEditModal}
          onClose={() => {
            setShowHistoricalEditModal(false);
            setEditingHistoricalRecord(null);
          }}
          record={editingHistoricalRecord}
          onSaved={() => {
            setShowHistoricalEditModal(false);
            setShowDetailsModal(false);
            fetchOrders();
          }}
        />
      )}
    </div>
  );
};

export default BreakfastOrdersPage;
