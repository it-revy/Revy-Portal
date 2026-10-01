import React, { useState, useEffect } from 'react';
import API from '../services/api';
import {
  Coffee,
  Plus,
  Trash2,
  Users,
  CheckCircle2,
  AlertCircle,
  Clock,
  DollarSign,
  Search,
  Filter,
  Eye,
  Edit2,
  X,
  RefreshCw,
  Wallet,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

const AdditionalOrdersPage = () => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().substring(0, 10));
  const [searchTerm, setSearchTerm] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [insufficientError, setInsufficientError] = useState(null);

  // Modals & Collapsibles state
  const [showModal, setShowModal] = useState(false); // New/Edit Modal
  const [viewOrder, setViewOrder] = useState(null); // View Modal
  const [editingOrder, setEditingOrder] = useState(null); // null for new, order object for edit
  const [showEmployeeList, setShowEmployeeList] = useState(false);

  // Form State
  const [orderTitle, setOrderTitle] = useState('Afternoon Tea');
  const [orderTime, setOrderTime] = useState('04:00 PM');
  const [breakfastItems, setBreakfastItems] = useState([
    { name: 'Samosa / Snack', unitPrice: 20, quantity: '' }
  ]);
  const [commonItems, setCommonItems] = useState([
    { name: 'Tea Container / Biscuits', unitPrice: 150, quantity: 1 }
  ]);

  useEffect(() => {
    fetchAdditionalOrders();
  }, [selectedDate]);

  const fetchAdditionalOrders = async () => {
    setLoading(true);
    setError(false);
    setMessage(null);
    try {
      const res = await API.get(`/breakfast/additional-orders?date=${selectedDate}`);
      if (res.data.success) {
        setData(res.data);
      } else {
        setError(true);
      }
    } catch (err) {
      console.error('Failed to fetch additional orders:', err);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenNewModal = () => {
    setEditingOrder(null);
    setOrderTitle('Afternoon Tea');
    setOrderTime('04:00 PM');
    setBreakfastItems([{ name: '', unitPrice: '', quantity: '' }]);
    setCommonItems([{ name: '', unitPrice: '', quantity: 1 }]);
    setInsufficientError(null);
    setMessage(null);
    setShowModal(true);
  };

  const handleOpenEditModal = (ord) => {
    setEditingOrder(ord);
    setOrderTitle(ord.orderTitle || '');
    setOrderTime(ord.orderTime || '');
    setBreakfastItems(
      ord.breakfastItems && ord.breakfastItems.length > 0
        ? ord.breakfastItems.map(i => ({ name: i.name, unitPrice: i.unitPrice, quantity: i.quantity || '' }))
        : [{ name: '', unitPrice: '', quantity: '' }]
    );
    setCommonItems(
      ord.commonItems && ord.commonItems.length > 0
        ? ord.commonItems.map(i => ({ name: i.name, unitPrice: i.unitPrice, quantity: i.quantity || 1 }))
        : [{ name: '', unitPrice: '', quantity: 1 }]
    );
    setInsufficientError(null);
    setMessage(null);
    setShowModal(true);
  };

  // Items manipulation
  const addBreakfastItem = () => {
    setBreakfastItems([...breakfastItems, { name: '', unitPrice: '', quantity: '' }]);
  };

  const updateBreakfastItem = (index, field, value) => {
    const updated = [...breakfastItems];
    updated[index][field] = value;
    setBreakfastItems(updated);
  };

  const removeBreakfastItem = (index) => {
    setBreakfastItems(breakfastItems.filter((_, i) => i !== index));
  };

  const addCommonItem = () => {
    setCommonItems([...commonItems, { name: '', unitPrice: '', quantity: 1 }]);
  };

  const updateCommonItem = (index, field, value) => {
    const updated = [...commonItems];
    updated[index][field] = value;
    setCommonItems(updated);
  };

  const removeCommonItem = (index) => {
    setCommonItems(commonItems.filter((_, i) => i !== index));
  };

  const handleDeleteOrder = async (orderId) => {
    if (!window.confirm(`Are you sure you want to delete order ${orderId}? Any recorded expense will be refunded back to the Breakfast Money balance.`)) return;
    try {
      const res = await API.delete(`/breakfast/additional-orders/${orderId}`);
      if (res.data.success) {
        setMessage({ type: 'success', text: res.data.message || 'Order deleted and ledger refunded successfully.' });
        fetchAdditionalOrders();
      }
    } catch (err) {
      setMessage({ type: 'danger', text: err.response?.data?.message || 'Failed to delete additional order' });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    setInsufficientError(null);

    // Filter valid items
    const validBreakfast = breakfastItems.filter(i => i.name.trim() !== '');
    const validCommon = commonItems.filter(i => i.name.trim() !== '');

    if (validBreakfast.length === 0 && validCommon.length === 0) {
      setMessage({ type: 'danger', text: 'Please add at least one Breakfast Item or Common Item.' });
      setSaving(false);
      return;
    }

    const payload = {
      businessDate: selectedDate,
      orderTitle,
      orderTime,
      breakfastItems: validBreakfast,
      commonItems: validCommon
    };

    try {
      let res;
      if (editingOrder) {
        res = await API.put(`/breakfast/additional-orders/${editingOrder.orderId}`, payload);
      } else {
        res = await API.post('/breakfast/additional-orders', payload);
      }

      if (res.data.success) {
        setMessage({ type: 'success', text: res.data.message });
        setShowModal(false);
        fetchAdditionalOrders();
      }
    } catch (err) {
      const errData = err.response?.data;
      if (errData?.isInsufficient) {
        setInsufficientError({
          available: errData.currentBalance,
          required: errData.required,
          shortfall: errData.shortfall
        });
      } else {
        setMessage({ type: 'danger', text: errData?.message || 'Failed to save additional order.' });
      }
    } finally {
      setSaving(false);
    }
  };

  const applicableCount = data?.applicableCount || 0;
  const currentFundBalance = data?.fundMetrics?.currentBalance || 0;

  // Calculate live preview totals for the modal
  const liveBreakfastTotal = Number(breakfastItems.reduce((sum, item) => {
    if (!item.name.trim()) return sum;
    const price = parseFloat(item.unitPrice) || 0;
    const qty = item.quantity !== undefined && item.quantity !== '' ? parseFloat(item.quantity) : applicableCount;
    return sum + (price * qty);
  }, 0).toFixed(2));

  const liveCommonTotal = Number(commonItems.reduce((sum, item) => {
    if (!item.name.trim()) return sum;
    const price = parseFloat(item.unitPrice) || 0;
    const qty = item.quantity !== undefined && item.quantity !== '' ? parseFloat(item.quantity) : 1;
    return sum + (price * qty);
  }, 0).toFixed(2));

  const liveOrderTotal = Number((liveBreakfastTotal + liveCommonTotal).toFixed(2));

  // Filter orders by search term
  const filteredOrders = (data?.orders || []).filter(ord => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      ord.orderId.toLowerCase().includes(term) ||
      ord.orderTitle.toLowerCase().includes(term) ||
      (ord.createdBy && ord.createdBy.toLowerCase().includes(term))
    );
  });

  if (loading) {
    return (
      <div className="page-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh', gap: '1rem' }}>
        <RefreshCw size={32} className="spin" color="var(--accent-primary)" />
        <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Loading additional orders...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh', gap: '1.25rem' }}>
        <AlertCircle size={48} color="var(--danger)" />
        <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>Unable to load additional orders.</div>
        <button className="btn btn-primary" onClick={fetchAdditionalOrders} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <RefreshCw size={16} /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="page-body">
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: 0 }}>
            <Coffee size={28} color="var(--accent-primary)" /> Additional Orders
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: '0.25rem', fontSize: '0.875rem' }}>
            Manage multiple additional breakfast and snack orders per business date
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <div className="panel-card" style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Filter size={18} color="var(--accent-primary)" />
            <div>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', fontWeight: 600 }}>BUSINESS DATE</label>
              <input
                type="date"
                className="form-input"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                style={{ border: 'none', padding: 0, fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)', background: 'transparent' }}
              />
            </div>
          </div>

          <button className="btn btn-primary" onClick={handleOpenNewModal} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem 1.25rem' }}>
            <Plus size={18} /> New Order
          </button>
        </div>
      </div>

      {/* Notifications */}
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
          justifyContent: 'space-between',
          gap: '0.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {message.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
            <span>{message.text}</span>
          </div>
          <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }} onClick={() => setMessage(null)}>
            <X size={16} />
          </button>
        </div>
      )}

      {/* Financial Summary & Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: '1.25rem', marginBottom: '1.75rem' }}>
        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(37, 99, 235, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Wallet size={24} color="var(--accent-primary)" />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>Available Fund Balance</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>₹{currentFundBalance}</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(16, 185, 129, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Users size={24} color="var(--success)" />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>Applicable Employees</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>{applicableCount} Members</div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '1.25rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(245, 158, 11, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Coffee size={24} color="#f59e0b" />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600, textTransform: 'uppercase' }}>Orders for Date ({selectedDate})</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>{data?.orders?.length || 0} Orders</div>
          </div>
        </div>
      </div>

      {/* Section: Applicable Employee Status List */}
      <div className="glass-panel" style={{ padding: '1.25rem', marginBottom: '1.75rem' }}>
        <div
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer', userSelect: 'none' }}
          onClick={() => setShowEmployeeList(!showEmployeeList)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Users size={20} color="var(--accent-primary)" />
            <h3 style={{ fontSize: '1rem', margin: 0, fontWeight: 700 }}>Applicable Employee Status List ({applicableCount})</h3>
          </div>
          <button className="btn btn-secondary" style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            {showEmployeeList ? <>Hide List <ChevronUp size={14} /></> : <>View List <ChevronDown size={14} /></>}
          </button>
        </div>

        {showEmployeeList && (
          <div style={{ marginTop: '1.25rem' }}>
            <div className="table-container">
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Employee ID</th>
                    <th>Employee Name</th>
                    <th>Department</th>
                    <th>Employee Request</th>
                    <th>Actual Status</th>
                  </tr>
                </thead>
                <tbody>
                  {!data?.applicableEmployees || data.applicableEmployees.length === 0 ? (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '1.5rem' }}>No applicable employees for this date.</td>
                    </tr>
                  ) : (
                    data.applicableEmployees.map((emp) => (
                      <tr key={emp.employeeId}>
                        <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{emp.employeeId}</td>
                        <td><strong>{emp.name}</strong></td>
                        <td>{emp.department}</td>
                        <td>
                          <span className={`badge ${emp.employeeRequest === 'TAKING' ? 'badge-success' : emp.employeeRequest === 'NOT_TAKING' ? 'badge-danger' : 'badge-warning'}`}>
                            {emp.employeeRequest}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${emp.actualStatus === 'TAKEN' ? 'badge-success' : emp.actualStatus === 'NOT_TAKEN' ? 'badge-danger' : 'badge-warning'}`}>
                            {emp.actualStatus}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Section: Existing Orders List Header & Filters */}
      <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
          <h3 style={{ fontSize: '1.1rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700 }}>
            <Coffee size={20} color="var(--accent-primary)" /> Existing Orders for {selectedDate}
          </h3>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', width: '100%', maxWidth: '340px' }}>
            <div style={{ position: 'relative', width: '100%' }}>
              <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)' }} />
              <input
                type="text"
                className="form-input"
                placeholder="Search orders..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ paddingLeft: '2.35rem', fontSize: '0.85rem' }}
              />
            </div>
          </div>
        </div>

        {/* Existing Orders: Desktop Table View */}
        <div className="desktop-only">
          <div className="table-container">
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Date</th>
                  <th>Title</th>
                  <th>Time</th>
                  <th style={{ textAlign: 'center' }}>Employees</th>
                  <th style={{ textAlign: 'right' }}>Total</th>
                  <th>Created By</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.length === 0 ? (
                  <tr>
                    <td colSpan="8">
                      <div style={{ padding: '3rem 1.5rem', textAlign: 'center' }}>
                        <Coffee size={40} color="var(--text-muted)" style={{ opacity: 0.5, marginBottom: '0.75rem' }} />
                        <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                          No additional breakfast orders found.
                        </div>
                        <button className="btn btn-primary" onClick={handleOpenNewModal} style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                          <Plus size={16} /> Create Additional Order
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredOrders.map((ord) => (
                    <tr key={ord.orderId}>
                      <td style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--accent-primary)' }}>{ord.orderId}</td>
                      <td style={{ whiteSpace: 'nowrap' }}>{ord.businessDate}</td>
                      <td><strong>{ord.orderTitle}</strong></td>
                      <td><span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{ord.orderTime}</span></td>
                      <td style={{ textAlign: 'center' }}>
                        <span className="badge badge-info">{ord.applicableEmployeeCount}</span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <strong style={{ color: 'var(--success)', fontSize: '0.95rem' }}>₹{ord.totalCost}</strong>
                      </td>
                      <td style={{ fontSize: '0.85rem' }}>{ord.createdBy || 'BF Admin'}</td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.4rem' }}>
                          <button className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem', fontSize: '0.8rem' }} onClick={() => setViewOrder(ord)} title="View Order">
                            <Eye size={14} /> View
                          </button>
                          <button className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem', fontSize: '0.8rem', color: 'var(--accent-primary)' }} onClick={() => handleOpenEditModal(ord)} title="Edit Order">
                            <Edit2 size={14} /> Edit
                          </button>
                          <button className="btn btn-secondary" style={{ padding: '0.35rem 0.6rem', fontSize: '0.8rem', color: 'var(--danger)' }} onClick={() => handleDeleteOrder(ord.orderId)} title="Delete Order">
                            <Trash2 size={14} /> Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Existing Orders: Mobile Card View (< 768px) */}
        <div className="mobile-only" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {filteredOrders.length === 0 ? (
            <div style={{ padding: '2.5rem 1rem', textAlign: 'center', background: '#f8fafc', borderRadius: 'var(--radius-sm)' }}>
              <Coffee size={36} color="var(--text-muted)" style={{ opacity: 0.5, marginBottom: '0.75rem' }} />
              <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                No additional breakfast orders found.
              </div>
              <button className="btn btn-primary" onClick={handleOpenNewModal} style={{ width: '100%', justifyContent: 'center' }}>
                <Plus size={16} /> Create Additional Order
              </button>
            </div>
          ) : (
            filteredOrders.map((ord) => (
              <div key={ord.orderId} className="panel-card" style={{ padding: '1.25rem', borderLeft: '4px solid var(--accent-primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--accent-primary)', fontWeight: 700 }}>{ord.orderId}</span>
                    <h4 style={{ margin: '0.2rem 0', fontSize: '1.05rem', fontWeight: 700 }}>{ord.orderTitle}</h4>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span>{ord.businessDate}</span>
                      <span>•</span>
                      <span>{ord.orderTime}</span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', textTransform: 'uppercase' }}>Total</span>
                    <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--success)' }}>₹{ord.totalCost}</span>
                  </div>
                </div>

                <div style={{ padding: '0.6rem 0.8rem', background: '#f1f5f9', borderRadius: 'var(--radius-sm)', marginBottom: '1rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  <div>Employees: <strong>{ord.applicableEmployeeCount}</strong></div>
                  <div>Created By: <strong>{ord.createdBy || 'BF Admin'}</strong></div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
                  <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center', padding: '0.5rem', fontSize: '0.8rem' }} onClick={() => setViewOrder(ord)}>
                    <Eye size={14} /> View
                  </button>
                  <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center', padding: '0.5rem', fontSize: '0.8rem', color: 'var(--accent-primary)' }} onClick={() => handleOpenEditModal(ord)}>
                    <Edit2 size={14} /> Edit
                  </button>
                  <button className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center', padding: '0.5rem', fontSize: '0.8rem', color: 'var(--danger)' }} onClick={() => handleDeleteOrder(ord.orderId)}>
                    <Trash2 size={14} /> Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* CREATE / EDIT ORDER MODAL */}
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '750px' }}>
            {/* Modal Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
              <h2 style={{ fontSize: '1.2rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Coffee size={22} color="var(--accent-primary)" />
                {editingOrder ? `Edit Order (${editingOrder.orderId})` : 'New Additional Order'}
              </h2>
              <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }} onClick={() => setShowModal(false)}>
                <X size={20} />
              </button>
            </div>

            {/* Insufficient Balance Error Alert Banner */}
            {insufficientError && (
              <div style={{
                background: '#fef2f2',
                border: '1px solid #fca5a5',
                color: '#991b1b',
                padding: '1rem 1.25rem',
                borderRadius: 'var(--radius-sm)',
                marginBottom: '1.25rem',
                fontSize: '0.9rem'
              }}>
                <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <AlertCircle size={18} color="#dc2626" /> Insufficient breakfast fund.
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '0.75rem', marginTop: '0.5rem', background: 'white', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid #fee2e2', textAlign: 'center' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>Available</span>
                    <strong style={{ color: '#059669', fontSize: '1rem' }}>₹{insufficientError.available}</strong>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>Required</span>
                    <strong style={{ color: '#dc2626', fontSize: '1rem' }}>₹{insufficientError.required}</strong>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.75rem', color: '#6b7280', display: 'block' }}>Shortfall</span>
                    <strong style={{ color: '#d97706', fontSize: '1rem' }}>₹{insufficientError.shortfall}</strong>
                  </div>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit}>
              {/* Order Info */}
              <div className="form-grid-2" style={{ marginBottom: '1.25rem' }}>
                <div className="form-group">
                  <label className="form-label">Order Title *</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Afternoon Tea, Client Snacks"
                    value={orderTitle}
                    onChange={(e) => setOrderTitle(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Order Time</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="04:00 PM"
                    value={orderTime}
                    onChange={(e) => setOrderTime(e.target.value)}
                  />
                </div>
              </div>

              {/* Breakfast Items (Optional) */}
              <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: 'var(--radius-sm)', marginBottom: '1.25rem', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                  <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <DollarSign size={16} color="var(--success)" /> Breakfast Items (Optional)
                  </h4>
                  <button type="button" className="btn btn-secondary" onClick={addBreakfastItem} style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}>
                    <Plus size={14} /> Add Item
                  </button>
                </div>

                {breakfastItems.map((item, idx) => {
                  const price = Number(item.unitPrice) || 0;
                  const qty = item.quantity !== undefined && item.quantity !== '' ? Number(item.quantity) : applicableCount;
                  const total = price * qty;
                  return (
                    <div key={idx} className="item-input-row">
                      <input
                        type="text"
                        className="form-input"
                        placeholder="Item name (e.g. Samosa)"
                        value={item.name}
                        onChange={(e) => updateBreakfastItem(idx, 'name', e.target.value)}
                        style={{ fontSize: '0.85rem' }}
                      />
                      <input
                        type="number"
                        min="0"
                        step="any"
                        className="form-input"
                        placeholder="Price (₹)"
                        value={item.unitPrice}
                        onChange={(e) => updateBreakfastItem(idx, 'unitPrice', e.target.value)}
                        style={{ fontSize: '0.85rem' }}
                      />
                      <input
                        type="number"
                        min="0"
                        step="any"
                        className="form-input"
                        placeholder={`Qty (${applicableCount})`}
                        value={item.quantity}
                        onChange={(e) => updateBreakfastItem(idx, 'quantity', e.target.value)}
                        style={{ fontSize: '0.85rem' }}
                      />
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, padding: '0.5rem', background: '#f1f5f9', borderRadius: '4px', textAlign: 'center' }}>
                        ₹{total}
                      </div>
                      <button type="button" className="btn btn-secondary" onClick={() => removeBreakfastItem(idx)} style={{ color: 'var(--danger)', padding: '0.4rem', border: 'none' }}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  );
                })}
              </div>

              {/* Common / Shared Items (Optional) */}
              <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: 'var(--radius-sm)', marginBottom: '1.25rem', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                  <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Plus size={16} color="var(--accent-primary)" /> Common / Shared Breakfast Items (Optional)
                  </h4>
                  <button type="button" className="btn btn-secondary" onClick={addCommonItem} style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}>
                    <Plus size={14} /> Add Common Item
                  </button>
                </div>

                {commonItems.map((item, idx) => {
                  const price = parseFloat(item.unitPrice) || 0;
                  const qty = item.quantity !== undefined && item.quantity !== '' ? parseFloat(item.quantity) : 1;
                  const total = Number((price * qty).toFixed(2));
                  return (
                    <div key={idx} className="item-input-row">
                      <input
                        type="text"
                        className="form-input"
                        placeholder="Common Item (e.g. Tea Container)"
                        value={item.name}
                        onChange={(e) => updateCommonItem(idx, 'name', e.target.value)}
                        style={{ fontSize: '0.85rem' }}
                      />
                      <input
                        type="number"
                        min="0"
                        step="any"
                        className="form-input"
                        placeholder="Price (₹)"
                        value={item.unitPrice}
                        onChange={(e) => updateCommonItem(idx, 'unitPrice', e.target.value)}
                        style={{ fontSize: '0.85rem' }}
                      />
                      <input
                        type="number"
                        min="0"
                        step="any"
                        className="form-input"
                        placeholder="Qty (1)"
                        value={item.quantity}
                        onChange={(e) => updateCommonItem(idx, 'quantity', e.target.value)}
                        style={{ fontSize: '0.85rem' }}
                      />
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, padding: '0.5rem', background: '#f1f5f9', borderRadius: '4px', textAlign: 'center' }}>
                        ₹{total}
                      </div>
                      <button type="button" className="btn btn-secondary" onClick={() => removeCommonItem(idx)} style={{ color: 'var(--danger)', padding: '0.4rem', border: 'none' }}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  );
                })}
              </div>

              {/* Financial Summary & Actions */}
              <div style={{ background: '#0f172a', color: 'white', padding: '1.25rem', borderRadius: 'var(--radius-sm)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Order Total</span>
                  <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#4ade80' }}>₹{liveOrderTotal}</div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-primary" disabled={saving}>
                    {saving ? 'Saving...' : editingOrder ? 'Update Order' : 'Save Order'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* VIEW ORDER DETAILS MODAL */}
      {viewOrder && (
        <div className="modal-backdrop">
          <div className="modal-content" style={{ maxWidth: '600px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem' }}>
              <div>
                <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--accent-primary)', fontWeight: 700 }}>{viewOrder.orderId}</span>
                <h2 style={{ fontSize: '1.2rem', margin: '0.2rem 0 0 0', fontWeight: 700 }}>{viewOrder.orderTitle}</h2>
              </div>
              <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }} onClick={() => setViewOrder(null)}>
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
              <div>
                <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.75rem' }}>Business Date</span>
                <strong>{viewOrder.businessDate}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.75rem' }}>Order Time</span>
                <strong>{viewOrder.orderTime}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.75rem' }}>Applicable Employees</span>
                <strong>{viewOrder.applicableEmployeeCount} Employees</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.75rem' }}>Total Cost</span>
                <strong style={{ color: 'var(--success)', fontSize: '1.1rem' }}>₹{viewOrder.totalCost}</strong>
              </div>
            </div>

            {/* Breakfast Items Breakdown */}
            <div style={{ marginBottom: '1.25rem' }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Breakfast Items</h4>
              {viewOrder.breakfastItems && viewOrder.breakfastItems.length > 0 ? (
                <div style={{ background: '#f8fafc', borderRadius: 'var(--radius-sm)', padding: '0.75rem' }}>
                  {viewOrder.breakfastItems.map((item, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                      <span>{item.name} (₹{item.unitPrice} × {item.quantity})</span>
                      <strong>₹{item.total}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>None</div>
              )}
            </div>

            {/* Common Items Breakdown */}
            <div style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Common / Shared Items</h4>
              {viewOrder.commonItems && viewOrder.commonItems.length > 0 ? (
                <div style={{ background: '#f8fafc', borderRadius: 'var(--radius-sm)', padding: '0.75rem' }}>
                  {viewOrder.commonItems.map((item, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                      <span>{item.name} (₹{item.unitPrice} × {item.quantity || 1})</span>
                      <strong>₹{item.total}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>None</div>
              )}
            </div>

            {/* Audit Trail Info */}
            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem', fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
              <div>Created By: <strong>{viewOrder.createdBy || 'BF Admin'}</strong></div>
              <div>Created At: <strong>{viewOrder.createdAt ? new Date(viewOrder.createdAt).toLocaleString() : 'N/A'}</strong></div>
              {viewOrder.updatedBy && <div>Updated By: <strong>{viewOrder.updatedBy}</strong></div>}
              {viewOrder.updatedAt && <div>Updated At: <strong>{new Date(viewOrder.updatedAt).toLocaleString()}</strong></div>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdditionalOrdersPage;
